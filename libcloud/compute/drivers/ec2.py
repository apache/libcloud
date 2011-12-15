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
from __future__ import with_statement

import sys
import base64
import hmac
import os
import time
import copy

from hashlib import sha256
from xml.etree import ElementTree as ET

from libcloud.utils.py3 import urlquote
from libcloud.utils.py3 import b

from libcloud.utils.xml import fixxpath, findtext, findattr, findall
from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.aws import AWSBaseResponse
from libcloud.common.types import (InvalidCredsError, MalformedResponseError,
                                   LibcloudError)
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage

EC2_US_EAST_HOST = 'ec2.us-east-1.amazonaws.com'
EC2_US_WEST_HOST = 'ec2.us-west-1.amazonaws.com'
EC2_US_WEST_OREGON_HOST = 'ec2.us-west-2.amazonaws.com'
EC2_EU_WEST_HOST = 'ec2.eu-west-1.amazonaws.com'
EC2_AP_SOUTHEAST_HOST = 'ec2.ap-southeast-1.amazonaws.com'
EC2_AP_NORTHEAST_HOST = 'ec2.ap-northeast-1.amazonaws.com'
EC2_SA_EAST_HOST = 'ec2.sa-east-1.amazonaws.com'

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
    'cg1.4xlarge': {
        'id': 'cg1.4xlarge',
        'name': 'Cluster GPU Quadruple Extra Large Instance',
        'ram': 22528,
        'disk': 1690,
        'bandwidth': None
    },
    'cc1.4xlarge': {
        'id': 'cc1.4xlarge',
        'name': 'Cluster Compute Quadruple Extra Large Instance',
        'ram': 23552,
        'disk': 1690,
        'bandwidth': None
    },
    'cc2.8xlarge': {
        'id': 'cc2.8xlarge',
        'name': 'Cluster Compute Eight Extra Large Instance',
        'ram': 63488,
        'disk': 3370,
        'bandwidth': None
    }
}

CLUSTER_INSTANCES_IDS = ['cg1.4xlarge', 'cc1.4xlarge', 'cc2.8xlarge']

EC2_US_EAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_US_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_EU_WEST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_AP_SOUTHEAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_AP_NORTHEAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_US_WEST_OREGON_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)
EC2_SA_EAST_INSTANCE_TYPES = dict(EC2_INSTANCE_TYPES)


class EC2NodeLocation(NodeLocation):
    def __init__(self, id, name, country, driver, availability_zone):
        super(EC2NodeLocation, self).__init__(id, name, country, driver)
        self.availability_zone = availability_zone

    def __repr__(self):
        return (('<EC2NodeLocation: id=%s, name=%s, country=%s, '
                 'availability_zone=%s driver=%s>')
                % (self.id, self.name, self.country,
                   self.availability_zone.name, self.driver.name))


class EC2Response(AWSBaseResponse):
    """
    EC2 specific response parsing and error handling.
    """

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
            raise MalformedResponseError("Failed to parse XML",
                                         body=self.body, driver=EC2NodeDriver)

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
    Represents a single connection to the EC2 Endpoint
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
        params['Signature'] = self._get_aws_auth_param(params, self.key,
                                                       self.action)
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
        keys = list(params.keys())
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urlquote(key, safe='') + '=' +
                         urlquote(params[key], safe='-_~'))

        qs = '&'.join(pairs)

        hostname = self.host
        if (self.secure and self.port != 443) or \
           (not self.secure and self.port != 80):
            hostname += ":" + str(self.port)

        string_to_sign = '\n'.join(('GET', hostname, path, qs))

        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key), b(string_to_sign), digestmod=sha256).digest()
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
    api_name = 'ec2_us_east'
    name = 'Amazon EC2 (us-east-1)'
    friendly_name = 'Amazon US N. Virginia'
    country = 'US'
    region_name = 'us-east-1'
    path = '/'

    _instance_types = EC2_US_EAST_INSTANCE_TYPES
    features = {'create_node': ['ssh_key']}

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'shutting-down': NodeState.TERMINATED,
        'terminated': NodeState.TERMINATED
    }

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

    def _get_state_boolean(self, element):
        """
        Checks for the instances's state
        """
        state = findall(element=element,
                        xpath='instancesSet/item/currentState/name',
                        namespace=NAMESPACE)[0].text

        return state in ('stopping', 'pending', 'starting')

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([term_status == status
                    for term_status
                    in ('shutting-down', 'terminated')])

    def _to_nodes(self, object, xpath, groups=None):
        return [self._to_node(el, groups=groups)
                for el in object.findall(fixxpath(xpath=xpath,
                                                  namespace=NAMESPACE))]

    def _to_node(self, element, groups=None):
        try:
            state = self.NODE_STATE_MAP[
                    findattr(element=element, xpath="instanceState/name",
                             namespace=NAMESPACE)
            ]
        except KeyError:
            state = NodeState.UNKNOWN

        instance_id = findtext(element=element, xpath='instanceId',
                               namespace=NAMESPACE)
        tags = dict((findtext(element=item, xpath='key', namespace=NAMESPACE),
                     findtext(element=item, xpath='value',
                              namespace=NAMESPACE))
        for item in findall(element=element, xpath='tagSet/item',
                            namespace=NAMESPACE))

        name = tags.get('Name', instance_id)

        public_ip = findtext(element=element, xpath='ipAddress',
                              namespace=NAMESPACE)
        public_ips = [public_ip] if public_ip else []
        private_ip = findtext(element=element, xpath='privateIpAddress',
                                 namespace=NAMESPACE)
        private_ips = [private_ip] if private_ip else []

        n = Node(
            id=findtext(element=element, xpath='instanceId',
                        namespace=NAMESPACE),
            name=name,
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra={
                'dns_name': findattr(element=element, xpath="dnsName",
                                     namespace=NAMESPACE),
                'instanceId': findattr(element=element, xpath="instanceId",
                                       namespace=NAMESPACE),
                'imageId': findattr(element=element, xpath="imageId",
                                    namespace=NAMESPACE),
                'private_dns': findattr(element=element,
                                        xpath="privateDnsName",
                                        namespace=NAMESPACE),
                'status': findattr(element=element, xpath="instanceState/name",
                                   namespace=NAMESPACE),
                'keyname': findattr(element=element, xpath="keyName",
                                    namespace=NAMESPACE),
                'launchindex': findattr(element=element,
                                        xpath="amiLaunchIndex",
                                        namespace=NAMESPACE),
                'productcode':
                    [p.text for p in findall(element=element,
                                    xpath="productCodesSet/item/productCode",
                                    namespace=NAMESPACE
                    )],
                'instancetype': findattr(element=element, xpath="instanceType",
                                         namespace=NAMESPACE),
                'launchdatetime': findattr(element=element, xpath="launchTime",
                                           namespace=NAMESPACE),
                'availability': findattr(element,
                                         xpath="placement/availabilityZone",
                                         namespace=NAMESPACE),
                'kernelid': findattr(element=element, xpath="kernelId",
                                     namespace=NAMESPACE),
                'ramdiskid': findattr(element=element, xpath="ramdiskId",
                                      namespace=NAMESPACE),
                'clienttoken': findattr(element=element, xpath="clientToken",
                                        namespace=NAMESPACE),
                'groups': groups,
                'tags': tags
            }
        )
        return n

    def _to_images(self, object):
        return [self._to_image(el)
                for el in object.findall(
            fixxpath(xpath='imagesSet/item', namespace=NAMESPACE)
        )]

    def _to_image(self, element):
        n = NodeImage(id=findtext(element=element, xpath='imageId',
                                  namespace=NAMESPACE),
                      name=findtext(element=element, xpath='imageLocation',
                                    namespace=NAMESPACE),
                      driver=self.connection.driver,
                      extra={
                          'state': findattr(element=element,
                                            xpath="imageState",
                                            namespace=NAMESPACE),
                          'ownerid': findattr(element=element,
                                        xpath="imageOwnerId",
                                        namespace=NAMESPACE),
                          'owneralias': findattr(element=element,
                                        xpath="imageOwnerAlias",
                                        namespace=NAMESPACE),
                          'ispublic': findattr(element=element,
                                        xpath="isPublic",
                                        namespace=NAMESPACE),
                          'architecture': findattr(element=element,
                                        xpath="architecture",
                                        namespace=NAMESPACE),
                          'imagetype': findattr(element=element,
                                        xpath="imageType",
                                        namespace=NAMESPACE),
                          'platform': findattr(element=element,
                                        xpath="platform",
                                        namespace=NAMESPACE),
                          'rootdevicetype': findattr(element=element,
                                        xpath="rootDeviceType",
                                        namespace=NAMESPACE),
                          'virtualizationtype': findattr(element=element,
                                        xpath="virtualizationType",
                                        namespace=NAMESPACE),
                          'hypervisor': findattr(element=element,
                                        xpath="hypervisor",
                                        namespace=NAMESPACE)
                      }
        )
        return n

    def list_nodes(self, ex_node_ids=None):
        """
        @type node.id: C{list}
        @param ex_node_ids: List of C{node.id}
        This parameter is used to filter the list of
        nodes that should be returned. Only the nodes
        with the corresponding node ids will be returned.
        """
        params = {'Action': 'DescribeInstances'}
        if ex_node_ids:
            params.update(self._pathlist('InstanceId', ex_node_ids))
        elem = self.connection.request(self.path, params=params).object
        nodes = []
        for rs in findall(element=elem, xpath='reservationSet/item',
                          namespace=NAMESPACE):
            groups = [g.findtext('')
                      for g in findall(element=rs,
                                       xpath='groupSet/item/groupId',
                                       namespace=NAMESPACE)]
            nodes += self._to_nodes(rs, 'instancesSet/item', groups)

        nodes_elastic_ips_mappings = self.ex_describe_addresses(nodes)
        for node in nodes:
            ips = nodes_elastic_ips_mappings[node.id]
            node.public_ips.extend(ips)
        return nodes

    def list_sizes(self, location=None):
        # Cluster instances are currently only available
        # in the US - N. Virginia Region
        include_ci = self.region_name == 'us-east-1'
        sizes = self._get_sizes(include_cluser_instances=include_ci)
        return sizes

    def _get_sizes(self, include_cluser_instances=False):
        sizes = []
        for key, values in self._instance_types.items():
            if not include_cluser_instances and\
               key in CLUSTER_INSTANCES_IDS:
                continue
            attributes = copy.deepcopy(values)
            attributes.update({'price': self._get_size_price(size_id=key)})
            sizes.append(NodeSize(driver=self, **attributes))
        return sizes

    def list_images(self, location=None):
        params = {'Action': 'DescribeImages'}
        images = self._to_images(
            self.connection.request(self.path, params=params).object
        )
        return images

    def list_locations(self):
        locations = []
        for index, availability_zone in \
            enumerate(self.ex_list_availability_zones()):
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
        key_material = findtext(element=response, xpath='keyMaterial',
                                namespace=NAMESPACE)
        key_fingerprint = findtext(element=response, xpath='keyFingerprint',
                                   namespace=NAMESPACE)
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
        with open(os.path.expanduser(keyfile)) as fh:
            content = fh.read()

        base64key = base64.b64encode(content)

        params = {'Action': 'ImportKeyPair',
                  'KeyName': name,
                  'PublicKeyMaterial': base64key
        }

        response = self.connection.request(self.path, params=params).object
        key_name = findtext(element=response, xpath='keyName',
                            namespace=NAMESPACE)
        key_fingerprint = findtext(element=response, xpath='keyFingerprint',
                                   namespace=NAMESPACE)
        return {
            'keyName': key_name,
            'keyFingerprint': key_fingerprint,
            }

    def ex_describe_keypairs(self, name):
        """Describes a keypair by name

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the keypair to describe.

        """

        params = {'Action': 'DescribeKeyPairs',
                  'KeyName.1': name
        }

        response = self.connection.request(self.path, params=params).object
        key_name = findattr(element=response, xpath='keySet/item/keyName',
                            namespace=NAMESPACE)
        return {
            'keyName': key_name
        }

    def ex_create_security_group(self, name, description):
        """Creates a new Security Group

        @note: This is a non-standard extension API, and only works for EC2.

        @type name: C{str}
        @param name: The name of the security group to Create.
                     This must be unique.

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
        except Exception:
            e = sys.exc_info()[1]
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e
        params['IpProtocol'] = 'udp'

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception:
            e = sys.exc_info()[1]
            if e.args[0].find("InvalidPermission.Duplicate") == -1:
                raise e

        params.update({'IpProtocol': 'icmp', 'FromPort': '-1', 'ToPort': '-1'})

        try:
            results.append(
                self.connection.request(self.path, params=params.copy()).object
            )
        except Exception:
            e = sys.exc_info()[1]

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
        for element in findall(element=result,
                               xpath='availabilityZoneInfo/item',
                               namespace=NAMESPACE):
            name = findtext(element=element, xpath='zoneName',
                            namespace=NAMESPACE)
            zone_state = findtext(element=element, xpath='zoneState',
                                  namespace=NAMESPACE)
            region_name = findtext(element=element, xpath='regionName',
                                   namespace=NAMESPACE)

            availability_zone = ExEC2AvailabilityZone(
                name=name,
                zone_state=zone_state,
                region_name=region_name
            )
            availability_zones.append(availability_zone)

        return availability_zones

    def ex_describe_tags(self, node):
        """
        Return a dictionary of tags for this instance.

        @type node: C{Node}
        @param node: Node instance

        @return dict Node tags
        """
        params = {'Action': 'DescribeTags',
                  'Filter.0.Name': 'resource-id',
                  'Filter.0.Value.0': node.id,
                  'Filter.1.Name': 'resource-type',
                  'Filter.1.Value.0': 'instance',
                  }

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        tags = {}
        for element in findall(element=result, xpath='tagSet/item',
                               namespace=NAMESPACE):
            key = findtext(element=element, xpath='key', namespace=NAMESPACE)
            value = findtext(element=element,
                             xpath='value', namespace=NAMESPACE)

            tags[key] = value
        return tags

    def ex_create_tags(self, node, tags):
        """
        Create tags for an instance.

        @type node: C{Node}
        @param node: Node instance
        @param tags: A dictionary or other mapping of strings to strings,
                     associating tag names with tag values.
        """
        if not tags:
            return

        params = {'Action': 'CreateTags',
                  'ResourceId.0': node.id}
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        self.connection.request(self.path,
                                params=params.copy()).object

    def ex_delete_tags(self, node, tags):
        """
        Delete tags from an instance.

        @type node: C{Node}
        @param node: Node instance
        @param tags: A dictionary or other mapping of strings to strings,
                     specifying the tag names and tag values to be deleted.
        """
        if not tags:
            return

        params = {'Action': 'DeleteTags',
                  'ResourceId.0': node.id}
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        self.connection.request(self.path,
                                params=params.copy()).object

    def _add_instance_filter(self, params, node):
        """
        Add instance filter to the provided params dictionary.
        """
        params.update({
            'Filter.0.Name': 'instance-id',
            'Filter.0.Value.0': node.id
        })

    def ex_describe_all_addresses(self, only_allocated=False):
        """
        Return all the Elastic IP addresses for this account
        optionally, return only the allocated addresses

        @keyword  only_allocated: If true, return only those addresses
                                  that are associated with an instance
        @type     only_allocated: C{string}

        @return   list list of elastic ips for this particular account.
        """
        params = {'Action': 'DescribeAddresses'}

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        # the list which we return
        elastic_ip_addresses = []
        for element in findall(element=result, xpath='addressesSet/item',
                               namespace=NAMESPACE):
            instance_id = findtext(element=element, xpath='instanceId',
                                   namespace=NAMESPACE)

            # if only allocated addresses are requested
            if only_allocated and not instance_id:
                continue

            ip_address = findtext(element=element, xpath='publicIp',
                                  namespace=NAMESPACE)

            elastic_ip_addresses.append(ip_address)

        return elastic_ip_addresses

    def ex_associate_addresses(self, node, elastic_ip_address):
        """
        Associate an IP address with a particular node.

        @type node: C{Node}
        @param node: Node instance

        """
        params = {'Action': 'AssociateAddress'}

        params.update(self._pathlist('InstanceId', [node.id]))
        params.update({'PublicIp': elastic_ip_address})
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def ex_describe_addresses(self, nodes):
        """
        Return Elastic IP addresses for all the nodes in the provided list.

        @type nodes: C{list}
        @param nodes: List of C{Node} instances

        @return dict Dictionary where a key is a node ID and the value is a
                     list with the Elastic IP addresses associated with
                     this node.
        """
        if not nodes:
            return {}

        params = {'Action': 'DescribeAddresses'}

        if len(nodes) == 1:
            self._add_instance_filter(params, nodes[0])

        result = self.connection.request(self.path,
                                         params=params.copy()).object

        node_instance_ids = [node.id for node in nodes]
        nodes_elastic_ip_mappings = {}

        for node_id in node_instance_ids:
            nodes_elastic_ip_mappings.setdefault(node_id, [])
        for element in findall(element=result, xpath='addressesSet/item',
                               namespace=NAMESPACE):
            instance_id = findtext(element=element, xpath='instanceId',
                                   namespace=NAMESPACE)
            ip_address = findtext(element=element, xpath='publicIp',
                                  namespace=NAMESPACE)

            if instance_id not in node_instance_ids:
                continue

            nodes_elastic_ip_mappings[instance_id].append(ip_address)
        return nodes_elastic_ip_mappings

    def ex_describe_addresses_for_node(self, node):
        """
        Return a list of Elastic IP addresses associated with this node.

        @type node: C{Node}
        @param node: Node instance

        @return list Elastic IP addresses attached to this node.
        """
        node_elastic_ips = self.ex_describe_addresses([node])
        return node_elastic_ips[node.id]

    def ex_modify_instance_attribute(self, node, attributes):
        """
        Modify node attributes.
        A list of valid attributes can be found at http://goo.gl/gxcj8

        @type node: C{Node}
        @param node: Node instance

        @type attributes: C{dict}
        @param attributes: Dictionary with node attributes

        @return bool True on success, False otherwise.
        """
        attributes = attributes or {}
        attributes.update({'InstanceId': node.id})

        params = {'Action': 'ModifyInstanceAttribute'}
        params.update(attributes)

        result = self.connection.request(self.path,
                                         params=params.copy()).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

    def ex_change_node_size(self, node, new_size):
        """
        Change the node size.
        Note: Node must be turned of before changing the size.

        @type node: C{Node}
        @param node: Node instance

        @type new_size: C{NodeSize}
        @param new_size: NodeSize intance

        @return bool True on success, False otherwise.
        """
        if 'instancetype' in node.extra:
            current_instance_type = node.extra['instancetype']

            if current_instance_type == new_size.id:
                raise ValueError('New instance size is the same as' +
                                 'the current one')

        attributes = {'InstanceType.Value': new_size.id}
        return self.ex_modify_instance_attribute(node, attributes)

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
            'MinCount': kwargs.get('ex_mincount', '1'),
            'MaxCount': kwargs.get('ex_maxcount', '1'),
            'InstanceType': size.id
        }

        if 'ex_securitygroup' in kwargs:
            if not isinstance(kwargs['ex_securitygroup'], list):
                kwargs['ex_securitygroup'] = [kwargs['ex_securitygroup']]
            for sig in range(len(kwargs['ex_securitygroup'])):
                params['SecurityGroup.%d' % (sig + 1,)] = \
                            kwargs['ex_securitygroup'][sig]

        if 'location' in kwargs:
            availability_zone = getattr(kwargs['location'],
                                        'availability_zone', None)
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

        for node in nodes:
            tags = {'Name': kwargs['name']}

            try:
                self.ex_create_tags(node=node, tags=tags)
            except Exception:
                continue

            node.name = kwargs['name']
            node.extra.update({'tags': tags})

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

    def ex_start_node(self, node):
        """
        Start the node by passing in the node object, does not work with
        instance store backed instances
        """
        params = {'Action': 'StartInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_state_boolean(res)

    def ex_stop_node(self, node):
        """
        Stop the node by passing in the node object, does not work with
        instance store backed instances
        """
        params = {'Action': 'StopInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_state_boolean(res)

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
    Request used the same client token as a previous,
    but non-identical request.
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

    api_name = 'ec2_eu_west'
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

    api_name = 'ec2_us_west'
    name = 'Amazon EC2 (us-west-1)'
    friendly_name = 'Amazon US N. California'
    country = 'US'
    region_name = 'us-west-1'
    connectionCls = EC2USWestConnection
    _instance_types = EC2_US_WEST_INSTANCE_TYPES


class EC2USWestOregonConnection(EC2Connection):
    """
    Connection class for EC2 in the Western US Region (Oregon).
    """

    host = EC2_US_WEST_OREGON_HOST


class EC2USWestOregonNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the US West Oregon region.
    """

    api_name = 'ec2_us_west_oregon'
    name = 'Amazon EC2 (us-west-2)'
    friendly_name = 'Amazon US West - Oregon'
    country = 'US'
    region_name = 'us-west-2'
    connectionCls = EC2USWestOregonConnection
    _instance_types = EC2_US_WEST_OREGON_INSTANCE_TYPES


class EC2APSEConnection(EC2Connection):
    """
    Connection class for EC2 in the Southeast Asia Pacific Region
    """

    host = EC2_AP_SOUTHEAST_HOST


class EC2APNEConnection(EC2Connection):
    """
    Connection class for EC2 in the Northeast Asia Pacific Region
    """

    host = EC2_AP_NORTHEAST_HOST


class EC2APSENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region
    """

    api_name = 'ec2_ap_southeast'
    name = 'Amazon EC2 (ap-southeast-1)'
    friendly_name = 'Amazon Asia-Pacific Singapore'
    country = 'SG'
    region_name = 'ap-southeast-1'
    connectionCls = EC2APSEConnection
    _instance_types = EC2_AP_SOUTHEAST_INSTANCE_TYPES


class EC2APNENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Northeast Asia Pacific Region
    """

    api_name = 'ec2_ap_northeast'
    name = 'Amazon EC2 (ap-northeast-1)'
    friendly_name = 'Amazon Asia-Pacific Tokyo'
    country = 'JP'
    region_name = 'ap-northeast-1'
    connectionCls = EC2APNEConnection
    _instance_types = EC2_AP_NORTHEAST_INSTANCE_TYPES


class EC2SAEastConnection(EC2Connection):
    """
    Connection class for EC2 in the South America (Sao Paulo) Region
    """

    host = EC2_SA_EAST_HOST


class EC2SAEastNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the South America (Sao Paulo) Region
    """

    api_name = 'ec2_sa_east'
    name = 'Amazon EC2 (sa-east-1)'
    friendly_name = 'Amazon South America Sao Paulo'
    country = 'BR'
    region_name = 'sa-east-1'
    connectionCls = EC2SAEastConnection
    _instance_types = EC2_SA_EAST_INSTANCE_TYPES


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

    def __init__(self, key, secret=None, secure=True, host=None,
                 path=None, port=None):
        super(EucNodeDriver, self).__init__(key, secret, secure, host, port)
        if path is None:
            path = "/services/Eucalyptus"
        self.path = path

    def list_locations(self):
        raise NotImplementedError(
                'list_locations not implemented for this driver')

    def _add_instance_filter(self, params, node):
        """
        Eucalyptus driver doesn't support filtering on instance id so this is a
        no-op.
        """
        pass

# Nimbus clouds have 3 EC2-style instance types but their particular RAM
# allocations are configured by the admin
NIMBUS_INSTANCE_TYPES = {
    'm1.small': {
        'id': 'm1.small',
        'name': 'Small Instance',
        'ram': None,
        'disk': None,
        'bandwidth': None,
        },
    'm1.large': {
        'id': 'm1.large',
        'name': 'Large Instance',
        'ram': None,
        'disk': None,
        'bandwidth': None,
        },
    'm1.xlarge': {
        'id': 'm1.xlarge',
        'name': 'Extra Large Instance',
        'ram': None,
        'disk': None,
        'bandwidth': None,
        },
    }


class NimbusConnection(EC2Connection):
    """
    Connection class for Nimbus
    """

    host = None


class NimbusNodeDriver(EC2NodeDriver):
    """
    Driver class for Nimbus
    """

    type = Provider.NIMBUS
    name = 'Nimbus'
    api_name = 'nimbus'
    region_name = 'nimbus'
    friendly_name = 'Nimbus Private Cloud'
    connectionCls = NimbusConnection
    _instance_types = NIMBUS_INSTANCE_TYPES

    def ex_describe_addresses(self, nodes):
        """
        Nimbus doesn't support elastic IPs, so this is a passthrough
        """
        nodes_elastic_ip_mappings = {}
        for node in nodes:
            # empty list per node
            nodes_elastic_ip_mappings[node.id] = []
        return nodes_elastic_ip_mappings

    def ex_create_tags(self, node, tags):
        """
        Nimbus doesn't support creating tags, so this is a passthrough
        """
        pass
