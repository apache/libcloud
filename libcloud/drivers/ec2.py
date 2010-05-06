# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Amazon EC2 driver
"""
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey
from libcloud.base import NodeDriver, NodeSize, NodeImage, NodeLocation
import base64
import hmac
from hashlib import sha256
import time
import urllib
from xml.etree import ElementTree as ET

EC2_US_EAST_HOST = 'ec2.us-east-1.amazonaws.com'
EC2_US_WEST_HOST = 'ec2.us-west-1.amazonaws.com'
EC2_EU_WEST_HOST = 'ec2.eu-west-1.amazonaws.com'
EC2_AP_SOUTHEAST_HOST = 'ec2.ap-southeast-1.amazonaws.com'

API_VERSION = '2009-11-30'

NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

"""
Sizes must be hardcoded, because Amazon doesn't provide an API to fetch them.
From http://aws.amazon.com/ec2/instance-types/
"""
EC2_INSTANCE_TYPES = {
    'm1.small': {
        'id': 'm1.small',
        'name': 'Small Instance',
        'ram': 1740,
        'disk': 160,
        'bandwidth': None
    },
    'm1.large': {
        'id': 'm1.large',
        'name': 'Large Instance',
        'ram': 7680,
        'disk': 850,
        'bandwidth': None
    },
    'm1.xlarge': {
        'id': 'm1.xlarge',
        'name': 'Extra Large Instance',
        'ram': 15360,
        'disk': 1690,
        'bandwidth': None
    },
    'c1.medium': {
        'id': 'c1.medium',
        'name': 'High-CPU Medium Instance',
        'ram': 1740,
        'disk': 350,
        'bandwidth': None
    },
    'c1.xlarge': {
        'id': 'c1.xlarge',
        'name': 'High-CPU Extra Large Instance',
        'ram': 7680,
        'disk': 1690,
        'bandwidth': None
    },
    'm2.xlarge': {
        'id': 'm2.xlarge',
        'name': 'High-Memory Extra Large Instance',
        'ram': 17510,
        'disk': 420,
        'bandwidth': None
    },
    'm2.2xlarge': {
        'id': 'm2.2xlarge',
        'name': 'High-Memory Double Extra Large Instance',
        'ram': 35021,
        'disk': 850,
        'bandwidth': None
    },
    'm2.4xlarge': {
        'id': 'm2.4xlarge',
        'name': 'High-Memory Quadruple Extra Large Instance',
        'ram': 70042,
        'disk': 1690,
        'bandwidth': None
    },
}

EC2_US_EAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_US_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_EU_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_AP_SOUTHEAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)

#
# On demand prices must also be hardcoded, because Amazon doesn't provide an
# API to fetch them. From http://aws.amazon.com/ec2/pricing/
#
EC2_US_EAST_INSTANCE_TYPES['m1.small']['price'] = '.085'
EC2_US_EAST_INSTANCE_TYPES['m1.large']['price'] = '.34'
EC2_US_EAST_INSTANCE_TYPES['m1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['c1.medium']['price'] = '.17'
EC2_US_EAST_INSTANCE_TYPES['c1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.50'
EC2_US_EAST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.2'
EC2_US_EAST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.4'

EC2_US_WEST_INSTANCE_TYPES['m1.small']['price'] = '.095'
EC2_US_WEST_INSTANCE_TYPES['m1.large']['price'] = '.38'
EC2_US_WEST_INSTANCE_TYPES['m1.xlarge']['price'] = '.76'
EC2_US_WEST_INSTANCE_TYPES['c1.medium']['price'] = '.19'
EC2_US_WEST_INSTANCE_TYPES['c1.xlarge']['price'] = '.76'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.57'
EC2_US_WEST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.34'
EC2_US_WEST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.68'

EC2_EU_WEST_INSTANCE_TYPES['m1.small']['price'] = '.095'
EC2_EU_WEST_INSTANCE_TYPES['m1.large']['price'] = '.38'
EC2_EU_WEST_INSTANCE_TYPES['m1.xlarge']['price'] = '.76'
EC2_EU_WEST_INSTANCE_TYPES['c1.medium']['price'] = '.19'
EC2_EU_WEST_INSTANCE_TYPES['c1.xlarge']['price'] = '.76'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.57'
EC2_EU_WEST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.34'
EC2_EU_WEST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.68'

# prices are the same
EC2_AP_SOUTHEAST_INSTANCE_TYPES = dict(EC2_EU_WEST_INSTANCE_TYPES)

class EC2Response(Response):
    """
    EC2 specific response parsing and error handling.
    """
    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        err_list = []
        # Okay, so for Eucalyptus, you can get a 403, with no body,
        # if you are using the wrong user/password.
        msg = "Failure: 403 Forbidden"
        if self.status == 403 and self.body[:len(msg)] == msg:
            raise InvalidCredsException(msg)

        for err in ET.XML(self.body).findall('Errors/Error'):
            code, message = err.getchildren()
            err_list.append("%s: %s" % (code.text, message.text))
            if code.text == "InvalidClientTokenId":
                raise InvalidCredsException(err_list[-1])
            if code.text == "SignatureDoesNotMatch":
                raise InvalidCredsException(err_list[-1])
            if code.text == "AuthFailure":
                raise InvalidCredsException(err_list[-1])
            if code.text == "OptInRequired":
                raise InvalidCredsException(err_list[-1])
        return "\n".join(err_list)

class EC2Connection(ConnectionUserAndKey):
    """
    Repersents a single connection to the EC2 Endpoint
    """

    host = EC2_US_EAST_HOST
    responseCls = EC2Response

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = API_VERSION
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key, self.action)
        return params

    def _get_aws_auth_param(self, params, secret_key, path='/'):
        """
        Creates the signature required for AWS, per
        http://bit.ly/aR7GaQ [docs.amazonwebservices.com]:

        StringToSign = HTTPVerb + "\n" +
                       ValueOfHostHeaderInLowercase + "\n" +
                       HTTPRequestURI + "\n" +
                       CanonicalizedQueryString <from the preceding step>
        """
        keys = params.keys()
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urllib.quote(key, safe='') + '=' +
                         urllib.quote(params[key], safe='-_~'))

        qs = '&'.join(pairs)
        string_to_sign = '\n'.join(('GET', self.host, path, qs))

        b64_hmac = base64.b64encode(
            hmac.new(secret_key, string_to_sign, digestmod=sha256).digest()
        )
        return b64_hmac

class EC2NodeDriver(NodeDriver):
    """
    Amazon EC2 node driver
    """

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2 (us-east-1)'
    path = '/'

    _instance_types = EC2_US_EAST_INSTANCE_TYPES

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'shutting-down': NodeState.TERMINATED,
        'terminated': NodeState.TERMINATED
    }

    def _findtext(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findattr(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _pathlist(self, key, arr):
        """
        Converts a key and an array of values into AWS query param format.
        """
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def _get_boolean(self, element):
        tag = "{%s}%s" % (NAMESPACE, 'return')
        return element.findtext(tag) == 'true'

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([ term_status == status
                     for term_status
                     in ('shutting-down', 'terminated') ])

    def _to_nodes(self, object, xpath, groups=None):
        return [ self._to_node(el, groups=groups)
                 for el in object.findall(self._fixxpath(xpath)) ]

    def _to_node(self, element, groups=None):
        try:
            state = self.NODE_STATE_MAP[
                self._findattr(element, "instanceState/name")
            ]
        except KeyError:
            state = NodeState.UNKNOWN

        n = Node(
            id=self._findtext(element, 'instanceId'),
            name=self._findtext(element, 'instanceId'),
            state=state,
            public_ip=[self._findtext(element, 'dnsName')],
            private_ip=[self._findtext(element, 'privateDnsName')],
            driver=self.connection.driver,
            extra={
                'dns_name': self._findattr(element, "dnsName"),
                'instanceId': self._findattr(element, "instanceId"),
                'imageId': self._findattr(element, "imageId"),
                'private_dns': self._findattr(element, "privateDnsName"),
                'status': self._findattr(element, "instanceState/name"),
                'keyname': self._findattr(element, "keyName"),
                'launchindex': self._findattr(element, "amiLaunchIndex"),
                'productcode':
                    [p.text for p in self._findall(
                        element, "productCodesSet/item/productCode"
                     )],
                'instancetype': self._findattr(element, "instanceType"),
                'launchdatetime': self._findattr(element, "launchTime"),
                'availability': self._findattr(element,
                                               "placement/availabilityZone"),
                'kernelid': self._findattr(element, "kernelId"),
                'ramdiskid': self._findattr(element, "ramdiskId"),
                'groups': groups
            }
        )
        return n

    def _to_images(self, object):
        return [ self._to_image(el)
                 for el in object.findall(
                    self._fixxpath('imagesSet/item')
                 ) ]

    def _to_image(self, element):
        n = NodeImage(id=self._findtext(element, 'imageId'),
                      name=self._findtext(element, 'imageLocation'),
                      driver=self.connection.driver)
        return n

    def list_nodes(self):
        params = {'Action': 'DescribeInstances' }
        elem=self.connection.request(self.path, params=params).object
        nodes=[]
        for rs in self._findall(elem, 'reservationSet/item'):
            groups=[g.findtext('')
                        for g in self._findall(rs, 'groupSet/item/groupId')]
            nodes += self._to_nodes(rs, 'instancesSet/item', groups)
        return nodes

    def list_sizes(self, location=None):
        return [ NodeSize(driver=self.connection.driver, **i)
                    for i in self._instance_types.values() ]

    def list_images(self, location=None):
        params = {'Action': 'DescribeImages'}
        images = self._to_images(
            self.connection.request(self.path, params=params).object
        )
        return images

    def ex_create_security_group(self, name, description):
        """Creates a new Security Group

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the security group to Create. This must be unique.

        @type description: C{str}
        @param description: Human readable description of a Security Group.
        """
        params = {'Action': 'CreateSecurityGroup',
                  'GroupName': name,
                  'GroupDescription': description}
        return self.connection.request(self.path, params=params).object

    def ex_authorize_security_group_permissive(self, name):
        """Edit a Security Group to allow all traffic.

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the security group to edit
        """

        results = []
        params = {'Action': 'AuthorizeSecurityGroupIngress',
                  'GroupName': name,
                  'IpProtocol': 'tcp',
                  'FromPort': '0',
                  'ToPort': '65535',
                  'CidrIp': '0.0.0.0/0'}
        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e
        params['IpProtocol'] = 'udp'

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e

        params.update({'IpProtocol': 'icmp', 'FromPort': '-1', 'ToPort': '-1'})

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception, e:
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e
        return results

    def create_node(self, **kwargs):
        """Create a new EC2 node

        See L{NodeDriver.create_node} for more keyword args.
        Reference: http://bit.ly/8ZyPSy [docs.amazonwebservices.com]

        @keyword    ex_mincount: Minimum number of instances to launch
        @type       ex_mincount: C{int}

        @keyword    ex_maxcount: Maximum number of instances to launch
        @type       ex_maxcount: C{int}

        @keyword    ex_securitygroup: Name of security group
        @type       ex_securitygroup: C{str}

        @keyword    ex_keyname: The name of the key pair
        @type       ex_keyname: C{str}

        @keyword    ex_userdata: User data
        @type       ex_userdata: C{str}
        """
        image = kwargs["image"]
        size = kwargs["size"]
        params = {
            'Action': 'RunInstances',
            'ImageId': image.id,
            'MinCount': kwargs.get('ex_mincount','1'),
            'MaxCount': kwargs.get('ex_maxcount','1'),
            'InstanceType': size.id
        }

        if 'ex_securitygroup' in kwargs:
            if not isinstance(kwargs['ex_securitygroup'], list):
                kwargs['ex_securitygroup'] = [kwargs['ex_securitygroup']]
            for sig in range(len(kwargs['ex_securitygroup'])):
                params['SecurityGroup.%d' % (sig+1,)]  = kwargs['ex_securitygroup'][sig]

        if 'ex_keyname' in kwargs:
            params['KeyName'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            params['UserData'] = base64.b64encode(kwargs['ex_userdata'])

        object = self.connection.request(self.path, params=params).object
        nodes = self._to_nodes(object, 'instancesSet/item')

        if len(nodes) == 1:
            return nodes[0]
        else:
            return nodes

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'Action': 'RebootInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_terminate_boolean(res)

    def list_locations(self):
        return [NodeLocation(0, 'Amazon US N. Virginia', 'US', self)]

class EC2EUConnection(EC2Connection):
    """
    Connection class for EC2 in the Western Europe Region
    """
    host = EC2_EU_WEST_HOST

class EC2EUNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western Europe Region
    """

    name = 'Amazon EC2 (eu-west-1)'
    connectionCls = EC2EUConnection
    _instance_types = EC2_EU_WEST_INSTANCE_TYPES
    def list_locations(self):
        return [NodeLocation(0, 'Amazon Europe Ireland', 'IE', self)]

class EC2USWestConnection(EC2Connection):
    """
    Connection class for EC2 in the Western US Region
    """

    host = EC2_US_WEST_HOST

class EC2USWestNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western US Region
    """

    name = 'Amazon EC2 (us-west-1)'
    connectionCls = EC2USWestConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES
    def list_locations(self):
        return [NodeLocation(0, 'Amazon US N. California', 'US', self)]

class EC2APSEConnection(EC2Connection):
    """
    Connection class for EC2 in the Southeast Asia Pacific Region
    """

    host = EC2_AP_SOUTHEAST_HOST

class EC2APSENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region
    """

    name = 'Amazon EC2 (ap-southeast-1)'
    connectionCls = EC2APSEConnection
    _instance_types = EC2_AP_SOUTHEAST_INSTANCE_TYPES
    def list_locations(self):
        return [NodeLocation(0, 'Amazon Asia-Pacific Singapore', 'SG', self)]

class EucConnection(EC2Connection):
    """
    Connection class for Eucalyptus
    """

    host = None

class EucNodeDriver(EC2NodeDriver):
    """
    Driver class for Eucalyptus
    """

    name = 'Eucalyptus'
    connectionCls = EucConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES

    def __init__(self, key, secret=None, secure=True, host=None, path=None, port=None):
        super(EucNodeDriver, self).__init__(key, secret, secure, host, port)
        if path is None:
            path = "/services/Eucalyptus"
        self.path = path

    def list_locations(self):
        raise NotImplementedError, \
            'list_locations not implemented for this driver'
