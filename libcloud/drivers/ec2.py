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
from libcloud.types import NodeState, InvalidCredsError, MalformedResponseError, LibcloudError
from libcloud.base import Node, Response, ConnectionUserAndKey
from libcloud.base import NodeDriver, NodeSize, NodeImage, NodeLocation
import base64
import hmac
import os
from hashlib import sha256
import time
import urllib
from xml.etree import ElementTree as ET

EC2_US_EAST_HOST = 'ec2.us-east-1.amazonaws.com'
EC2_US_WEST_HOST = 'ec2.us-west-1.amazonaws.com'
EC2_EU_WEST_HOST = 'ec2.eu-west-1.amazonaws.com'
EC2_AP_SOUTHEAST_HOST = 'ec2.ap-southeast-1.amazonaws.com'

API_VERSION = '2010-08-31'

NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

"""
Sizes must be hardcoded, because Amazon doesn't provide an API to fetch them.
From http://aws.amazon.com/ec2/instance-types/
"""
EC2_INSTANCE_TYPES = {
    't1.micro': {
        'id': 't1.micro',
        'name': 'Micro Instance',
        'ram': 613,
        'disk': 15,
        'bandwidth': None
    },
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
EC2_US_EAST_INSTANCE_TYPES['t1.micro']['price'] = '.02'
EC2_US_EAST_INSTANCE_TYPES['m1.small']['price'] = '.085'
EC2_US_EAST_INSTANCE_TYPES['m1.large']['price'] = '.34'
EC2_US_EAST_INSTANCE_TYPES['m1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['c1.medium']['price'] = '.17'
EC2_US_EAST_INSTANCE_TYPES['c1.xlarge']['price'] = '.68'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.50'
EC2_US_EAST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.2'
EC2_US_EAST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.4'

EC2_US_WEST_INSTANCE_TYPES['t1.micro']['price'] = '.025'
EC2_US_WEST_INSTANCE_TYPES['m1.small']['price'] = '.095'
EC2_US_WEST_INSTANCE_TYPES['m1.large']['price'] = '.38'
EC2_US_WEST_INSTANCE_TYPES['m1.xlarge']['price'] = '.76'
EC2_US_WEST_INSTANCE_TYPES['c1.medium']['price'] = '.19'
EC2_US_WEST_INSTANCE_TYPES['c1.xlarge']['price'] = '.76'
EC2_US_EAST_INSTANCE_TYPES['m2.xlarge']['price'] = '.57'
EC2_US_WEST_INSTANCE_TYPES['m2.2xlarge']['price'] = '1.34'
EC2_US_WEST_INSTANCE_TYPES['m2.4xlarge']['price'] = '2.68'

EC2_EU_WEST_INSTANCE_TYPES['t1.micro']['price'] = '.025'
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


class EC2NodeLocation(NodeLocation):
    def __init__(self, id, name, country, driver, availability_zone):
        super(EC2NodeLocation, self).__init__(id, name, country, driver)
        self.availability_zone = availability_zone

    def __repr__(self):
        return (('<EC2NodeLocation: id=%s, name=%s, country=%s, '
                 'availability_zone=%s driver=%s>')
                % (self.id, self.name, self.country,
                   self.availability_zone.name, self.driver.name))

class EC2Response(Response):
    """
    EC2 specific response parsing and error handling.
    """
    def parse_body(self):
        if not self.body:
            return None
        try:
          body = ET.XML(self.body)
        except:
          raise MalformedResponseError("Failed to parse XML", body=self.body, driver=EC2NodeDriver)
        return body

    def parse_error(self):
        err_list = []
        # Okay, so for Eucalyptus, you can get a 403, with no body,
        # if you are using the wrong user/password.
        msg = "Failure: 403 Forbidden"
        if self.status == 403 and self.body[:len(msg)] == msg:
            raise InvalidCredsError(msg)

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML", body=self.body, driver=EC2NodeDriver)

        for err in body.findall('Errors/Error'):
            code, message = err.getchildren()
            err_list.append("%s: %s" % (code.text, message.text))
            if code.text == "InvalidClientTokenId":
                raise InvalidCredsError(err_list[-1])
            if code.text == "SignatureDoesNotMatch":
                raise InvalidCredsError(err_list[-1])
            if code.text == "AuthFailure":
                raise InvalidCredsError(err_list[-1])
            if code.text == "OptInRequired":
                raise InvalidCredsError(err_list[-1])
            if code.text == "IdempotentParameterMismatch":
                raise IdempotentParamError(err_list[-1])
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

class ExEC2AvailabilityZone(object):
    """
    Extension class which stores information about an EC2 availability zone.

    Note: This class is EC2 specific.
    """
    def __init__(self, name, zone_state, region_name):
        self.name = name
        self.zone_state = zone_state
        self.region_name = region_name

    def __repr__(self):
        return (('<ExEC2AvailabilityZone: name=%s, zone_state=%s, '
                 'region_name=%s>')
                % (self.name, self.zone_state, self.region_name))

class EC2NodeDriver(NodeDriver):
    """
    Amazon EC2 node driver
    """

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2 (us-east-1)'
    friendly_name = 'Amazon US N. Virginia'
    country = 'US'
    region_name = 'us-east-1'
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
                'clienttoken' : self._findattr(element, "clientToken"),
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

    def list_locations(self):
        locations = []
        for index, availability_zone in enumerate(self.ex_list_availability_zones()):
            locations.append(EC2NodeLocation(index,
                                             self.friendly_name,
                                             self.country,
                                             self,
                                             availability_zone))
        return locations

    def ex_create_keypair(self, name):
        """Creates a new keypair

        @note: This is a non-standard extension API, and
               only works for EC2.

        @type name: C{str}
        @param name: The name of the keypair to Create. This must be
                     unique, otherwise an InvalidKeyPair.Duplicate
                     exception is raised.
        """
        params = {
            'Action': 'CreateKeyPair',
            'KeyName': name,
        }
        response = self.connection.request(self.path, params=params).object
        key_material = self._findtext(response, 'keyMaterial')
        key_fingerprint = self._findtext(response, 'keyFingerprint')
        return {
            'keyMaterial': key_material,
            'keyFingerprint': key_fingerprint,
        }

    def ex_import_keypair(self, name, keyfile):
        """imports a new public key

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the public key to import. This must be unique,
                     otherwise an InvalidKeyPair.Duplicate exception is raised.

        @type keyfile: C{str}
        @param keyfile: The filename with path of the public key to import.

        """

        base64key = base64.b64encode(open(os.path.expanduser(keyfile)).read())

        params = {'Action': 'ImportKeyPair',
                  'KeyName': name,
                  'PublicKeyMaterial': base64key
        }

        response = self.connection.request(self.path, params=params).object
        key_name = self._findtext(response, 'keyName')
        key_fingerprint = self._findtext(response, 'keyFingerprint')
        return {
                'keyName': key_name,
                'keyFingerprint': key_fingerprint,
        }

    def ex_describe_keypairs(self, name):
        """Describes a keypiar by name

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the keypair to describe.

        """

        params = {'Action': 'DescribeKeyPairs',
                  'KeyName.1': name
        }

        response = self.connection.request(self.path, params=params).object
        key_name = self._findattr(response, 'keySet/item/keyName')
        return {
                'keyName': key_name
        }

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

    def ex_list_availability_zones(self, only_available=True):
        """
        Return a list of L{ExEC2AvailabilityZone} objects for the
        current region.

        Note: This is an extension method and is only available for EC2
        driver.

        @keyword  only_available: If true, return only availability zones
                                  with state 'available'
        @type     only_available: C{string}
        """
        params = {'Action': 'DescribeAvailabilityZones'}

        if only_available:
            params.update({'Filter.0.Name': 'state'})
            params.update({'Filter.0.Value.0': 'available'})

        params.update({'Filter.1.Name': 'region-name'})
        params.update({'Filter.1.Value.0': self.region_name})

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        availability_zones = []
        for element in self._findall(result, 'availabilityZoneInfo/item'):
            name = self._findtext(element, 'zoneName')
            zone_state = self._findtext(element, 'zoneState')
            region_name = self._findtext(element, 'regionName')

            availability_zone = ExEC2AvailabilityZone(
                name=name,
                zone_state=zone_state,
                region_name=region_name
            )
            availability_zones.append(availability_zone)

        return availability_zones

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

        @keyword    ex_clienttoken: Unique identifier to ensure idempotency
        @type       ex_clienttoken: C{str}
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

        if 'location' in kwargs:
            availability_zone = getattr(kwargs['location'], 'availability_zone',
                                        None)
            if availability_zone:
                if availability_zone.region_name != self.region_name:
                    raise AttributeError('Invalid availability zone: %s'
                                         % (availability_zone.name))
                params['Placement.AvailabilityZone'] = availability_zone.name

        if 'ex_keyname' in kwargs:
            params['KeyName'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            params['UserData'] = base64.b64encode(kwargs['ex_userdata'])

        if 'ex_clienttoken' in kwargs:
            params['ClientToken'] = kwargs['ex_clienttoken']

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

class IdempotentParamError(LibcloudError):
    """
    Request used the same client token as a previous, but non-identical request.
    """
    def __str__(self):
        return repr(self.value)

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
    friendly_name = 'Amazon Europe Ireland'
    country = 'IE'
    region_name = 'eu-west-1'
    connectionCls = EC2EUConnection
    _instance_types = EC2_EU_WEST_INSTANCE_TYPES

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
    friendly_name = 'Amazon US N. California'
    country = 'US'
    region_name = 'us-west-1'
    connectionCls = EC2USWestConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES

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
    friendly_name = 'Amazon Asia-Pacific Singapore'
    country = 'SG'
    region_name = 'ap-southeast-1'
    connectionCls = EC2APSEConnection
    _instance_types = EC2_AP_SOUTHEAST_INSTANCE_TYPES

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
