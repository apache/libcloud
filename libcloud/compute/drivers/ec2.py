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
Amazon EC2, Eucalyptus and Nimbus drivers.
"""

from __future__ import with_statement

import sys
import base64
import os
import copy

from xml.etree import ElementTree as ET

from libcloud.utils.py3 import b, basestring

from libcloud.utils.xml import fixxpath, findtext, findattr, findall
from libcloud.utils.publickey import get_pubkey_ssh2_fingerprint
from libcloud.utils.publickey import get_pubkey_comment
from libcloud.utils.iso8601 import parse_date
from libcloud.common.aws import AWSBaseResponse, SignedAWSConnection
from libcloud.common.types import (InvalidCredsError, MalformedResponseError,
                                   LibcloudError)
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume, VolumeSnapshot

API_VERSION = '2010-08-31'
NAMESPACE = 'http://ec2.amazonaws.com/doc/%s/' % (API_VERSION)

"""
Sizes must be hardcoded, because Amazon doesn't provide an API to fetch them.
From http://aws.amazon.com/ec2/instance-types/
"""
INSTANCE_TYPES = {
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
    'm1.medium': {
        'id': 'm1.medium',
        'name': 'Medium Instance',
        'ram': 3700,
        'disk': 410,
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
    'm3.xlarge': {
        'id': 'm3.xlarge',
        'name': 'Extra Large Instance',
        'ram': 15360,
        'disk': None,
        'bandwidth': None
    },
    'm3.2xlarge': {
        'id': 'm3.2xlarge',
        'name': 'Double Extra Large Instance',
        'ram': 30720,
        'disk': None,
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
    },
    # c3 instances have 2 SSDs of the specified disk size
    'c3.large': {
        'id': 'c3.large',
        'name': 'Compute Optimized Large Instance',
        'ram': 3750,
        'disk': 16,
        'bandwidth': None
    },
    'c3.xlarge': {
        'id': 'c3.xlarge',
        'name': 'Compute Optimized Extra Large Instance',
        'ram': 7000,
        'disk': 40,
        'bandwidth': None
    },
    'c3.2xlarge': {
        'id': 'c3.2xlarge',
        'name': 'Compute Optimized Double Extra Large Instance',
        'ram': 15000,
        'disk': 80,
        'bandwidth': None
    },
    'c3.4xlarge': {
        'id': 'c3.4xlarge',
        'name': 'Compute Optimized Quadruple Extra Large Instance',
        'ram': 30000,
        'disk': 160,
        'bandwidth': None
    },
    'c3.8xlarge': {
        'id': 'c3.8xlarge',
        'name': 'Compute Optimized Eight Extra Large Instance',
        'ram': 60000,
        'disk': 320,
        'bandwidth': None
    },
    'cr1.8xlarge': {
        'id': 'cr1.8xlarge',
        'name': 'High Memory Cluster Eight Extra Large',
        'ram': 244000,
        'disk': 240,
        'bandwidth': None
    },
    'hs1.8xlarge': {
        'id': 'hs1.8xlarge',
        'name': 'High Storage Eight Extra Large Instance',
        'ram': 119808,
        'disk': 48000,
        'bandwidth': None
    }
}

REGION_DETAILS = {
    'us-east-1': {
        'endpoint': 'ec2.us-east-1.amazonaws.com',
        'api_name': 'ec2_us_east',
        'country': 'USA',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge',
            'cc1.4xlarge',
            'cc2.8xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'cg1.4xlarge',
            'cr1.8xlarge',
            'hs1.8xlarge'
        ]
    },
    'us-west-1': {
        'endpoint': 'ec2.us-west-1.amazonaws.com',
        'api_name': 'ec2_us_west',
        'country': 'USA',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge'
        ]
    },
    'us-west-2': {
        'endpoint': 'ec2.us-west-2.amazonaws.com',
        'api_name': 'ec2_us_west_oregon',
        'country': 'US',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'c1.medium',
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'cc2.8xlarge'
        ]
    },
    'eu-west-1': {
        'endpoint': 'ec2.eu-west-1.amazonaws.com',
        'api_name': 'ec2_eu_west',
        'country': 'Ireland',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'cc2.8xlarge'
        ]
    },
    'ap-southeast-1': {
        'endpoint': 'ec2.ap-southeast-1.amazonaws.com',
        'api_name': 'ec2_ap_southeast',
        'country': 'Singapore',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'hs1.8xlarge'
        ]
    },
    'ap-northeast-1': {
        'endpoint': 'ec2.ap-northeast-1.amazonaws.com',
        'api_name': 'ec2_ap_northeast',
        'country': 'Japan',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge'
        ]
    },
    'sa-east-1': {
        'endpoint': 'ec2.sa-east-1.amazonaws.com',
        'api_name': 'ec2_sa_east',
        'country': 'Brazil',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge'

        ]
    },
    'ap-southeast-2': {
        'endpoint': 'ec2.ap-southeast-2.amazonaws.com',
        'api_name': 'ec2_ap_southeast_2',
        'country': 'Australia',
        'instance_types': [
            't1.micro',
            'm1.small',
            'm1.medium',
            'm1.large',
            'm1.xlarge',
            'm2.xlarge',
            'm2.2xlarge',
            'm2.4xlarge',
            'm3.xlarge',
            'm3.2xlarge',
            'c1.medium',
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'hs1.8xlarge'
        ]
    },
    'nimbus': {
        # Nimbus clouds have 3 EC2-style instance types but their particular
        # RAM allocations are configured by the admin
        'country': 'custom',
        'instance_types': [
            'm1.small',
            'm1.large',
            'm1.xlarge'
        ]
    }
}

VALID_EC2_REGIONS = REGION_DETAILS.keys()
VALID_EC2_REGIONS = [r for r in VALID_EC2_REGIONS if r != 'nimbus']


class EC2NodeLocation(NodeLocation):
    def __init__(self, id, name, country, driver, availability_zone):
        super(EC2NodeLocation, self).__init__(id, name, country, driver)
        self.availability_zone = availability_zone

    def __repr__(self):
        return (('<EC2NodeLocation: id=%s, name=%s, country=%s, '
                 'availability_zone=%s driver=%s>')
                % (self.id, self.name, self.country,
                   self.availability_zone, self.driver.name))


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


class EC2Connection(SignedAWSConnection):
    """
    Represents a single connection to the EC2 Endpoint.
    """

    version = API_VERSION
    host = REGION_DETAILS['us-east-1']['endpoint']
    responseCls = EC2Response


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


class BaseEC2NodeDriver(NodeDriver):
    """
    Base Amazon EC2 node driver.

    Used for main EC2 and other derivate driver classes to inherit from it.
    """

    connectionCls = EC2Connection
    features = {'create_node': ['ssh_key']}
    path = '/'

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'shutting-down': NodeState.UNKNOWN,
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
            state = self.NODE_STATE_MAP[findattr(element=element,
                                                 xpath="instanceState/name",
                                                 namespace=NAMESPACE)
                                        ]
        except KeyError:
            state = NodeState.UNKNOWN

        instance_id = findtext(element=element, xpath='instanceId',
                               namespace=NAMESPACE)
        tags = dict((findtext(element=item, xpath='key', namespace=NAMESPACE),
                     findtext(element=item, xpath='value',
                              namespace=NAMESPACE))
                    for item in findall(element=element,
                                        xpath='tagSet/item',
                                        namespace=NAMESPACE)
                    )

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
                'productcode': [
                    p.text for p in findall(
                        element=element,
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
                'tags': tags,
                'iam_profile': findattr(element, xpath="iamInstanceProfile/id",
                                        namespace=NAMESPACE)
            }
        )
        return n

    def _to_images(self, object):
        return [self._to_image(el) for el in object.findall(
            fixxpath(xpath='imagesSet/item', namespace=NAMESPACE))
        ]

    def _to_image(self, element):
        n = NodeImage(
            id=findtext(element=element, xpath='imageId', namespace=NAMESPACE),
            name=findtext(element=element, xpath='imageLocation',
                          namespace=NAMESPACE),
            driver=self.connection.driver,
            extra={
                'state': findattr(element=element, xpath="imageState",
                                  namespace=NAMESPACE),
                'ownerid': findattr(element=element, xpath="imageOwnerId",
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
                'virtualizationtype': findattr(
                    element=element, xpath="virtualizationType",
                    namespace=NAMESPACE),
                'hypervisor': findattr(element=element,
                                       xpath="hypervisor",
                                       namespace=NAMESPACE)
            }
        )
        return n

    def _to_volume(self, element, name):
        volId = findtext(element=element, xpath='volumeId',
                         namespace=NAMESPACE)
        size = findtext(element=element, xpath='size', namespace=NAMESPACE)
        state = findtext(element=element, xpath='status', namespace=NAMESPACE)
        create_time = findtext(element=element, xpath='createTime',
                               namespace=NAMESPACE)
        device = findtext(element=element, xpath='attachmentSet/item/device',
                          namespace=NAMESPACE)

        return StorageVolume(id=volId,
                             name=name,
                             size=int(size),
                             driver=self,
                             extra={'state': state,
                                    'device': device,
                                    'create-time': parse_date(create_time)})

    def _to_snapshots(self, response):
        return [self._to_snapshot(el) for el in response.findall(
            fixxpath(xpath='snapshotSet/item', namespace=NAMESPACE))
        ]

    def _to_snapshot(self, element):
        snapId = findtext(element=element, xpath='snapshotId',
                          namespace=NAMESPACE)
        volId = findtext(element=element, xpath='volumeId',
                         namespace=NAMESPACE)
        size = findtext(element=element, xpath='volumeSize',
                        namespace=NAMESPACE)
        state = findtext(element=element, xpath='status',
                         namespace=NAMESPACE)
        description = findtext(element=element, xpath='description',
                               namespace=NAMESPACE)
        return VolumeSnapshot(snapId, size=int(size), driver=self,
                              extra={'volume_id': volId,
                                     'description': description,
                                     'state': state})

    def list_nodes(self, ex_node_ids=None):
        """
        List all nodes

        Ex_node_ids parameter is used to filter the list of
        nodes that should be returned. Only the nodes
        with the corresponding node ids will be returned.

        :param      ex_node_ids: List of ``node.id``
        :type       ex_node_ids: ``list`` of ``str``

        :rtype: ``list`` of :class:`Node`
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
        available_types = REGION_DETAILS[self.region_name]['instance_types']
        sizes = []

        for instance_type in available_types:
            attributes = INSTANCE_TYPES[instance_type]
            attributes = copy.deepcopy(attributes)
            price = self._get_size_price(size_id=instance_type)
            attributes.update({'price': price})
            sizes.append(NodeSize(driver=self, **attributes))
        return sizes

    def list_images(self, location=None, ex_image_ids=None, ex_owner=None):
        """
        List all images

        Ex_image_ids parameter is used to filter the list of
        images that should be returned. Only the images
        with the corresponding image ids will be returned.

        Ex_owner parameter is used to filter the list of
        images that should be returned. Only the images
        with the corresponding owner will be returned.
        Valid values: amazon|aws-marketplace|self|all|aws id

        :param      ex_image_ids: List of ``NodeImage.id``
        :type       ex_image_ids: ``list`` of ``str``

        :param      ex_owner: Owner name
        :type       ex_image_ids: ``str``

        :rtype: ``list`` of :class:`NodeImage`
        """
        params = {'Action': 'DescribeImages'}

        if ex_owner:
            params.update({'Owner.1': ex_owner})

        if ex_image_ids:
            params.update(self._pathlist('ImageId', ex_image_ids))

        images = self._to_images(
            self.connection.request(self.path, params=params).object
        )
        return images

    def list_locations(self):
        locations = []
        for index, availability_zone in \
                enumerate(self.ex_list_availability_zones()):
                    locations.append(EC2NodeLocation(
                        index, availability_zone.name, self.country, self,
                        availability_zone)
                    )
        return locations

    def list_volumes(self, node=None):
        params = {
            'Action': 'DescribeVolumes',
        }
        if node:
            params.update({
                'Filter.1.Name': 'attachment.instance-id',
                'Filter.1.Value': node.id,
            })
        response = self.connection.request(self.path, params=params).object
        volumes = [self._to_volume(el, '') for el in response.findall(
            fixxpath(xpath='volumeSet/item', namespace=NAMESPACE))
        ]
        return volumes

    def create_volume(self, size, name, location=None, snapshot=None):
        """
        :param location: Datacenter in which to create a volume in.
        :type location: :class:`ExEC2AvailabilityZone`
        """
        params = {
            'Action': 'CreateVolume',
            'Size': str(size)}

        if location is not None:
            params['AvailabilityZone'] = location.availability_zone.name

        volume = self._to_volume(
            self.connection.request(self.path, params=params).object,
            name=name)
        self.ex_create_tags(volume, {'Name': name})
        return volume

    def destroy_volume(self, volume):
        params = {
            'Action': 'DeleteVolume',
            'VolumeId': volume.id}
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def attach_volume(self, node, volume, device):
        params = {
            'Action': 'AttachVolume',
            'VolumeId': volume.id,
            'InstanceId': node.id,
            'Device': device}

        self.connection.request(self.path, params=params)
        return True

    def detach_volume(self, volume):
        params = {
            'Action': 'DetachVolume',
            'VolumeId': volume.id}

        self.connection.request(self.path, params=params)
        return True

    def create_volume_snapshot(self, volume, name=None):
        """
        Create snapshot from volume

        :param      volume: Instance of ``StorageVolume``
        :type       volume: ``StorageVolume``

        :param      name: Description for snapshot
        :type       name: ``str``

        :rtype: :class:`VolumeSnapshot`
        """
        params = {
            'Action': 'CreateSnapshot',
            'VolumeId': volume.id,
        }
        if name:
            params.update({
                'Description': name,
            })
        response = self.connection.request(self.path, params=params).object
        snapshot = self._to_snapshot(response)
        return snapshot

    def list_volume_snapshots(self, snapshot):
        return self.list_snapshots(snapshot)

    def list_snapshots(self, snapshot=None, owner=None):
        """
        Describe all snapshots.

        :param snapshot: If provided, only return snapshot information for the
                         provided snapshot.

        :param owner: Owner for snapshot: self|amazon|ID
        :type owner: ``str``

        :rtype: ``list`` of :class:`VolumeSnapshot`
        """
        params = {
            'Action': 'DescribeSnapshots',
        }
        if snapshot:
            params.update({
                'SnapshotId.1': snapshot.id,
            })
        if owner:
            params.update({
                'Owner.1': owner,
            })
        response = self.connection.request(self.path, params=params).object
        snapshots = self._to_snapshots(response)
        return snapshots

    def destroy_volume_snapshot(self, snapshot):
        params = {
            'Action': 'DeleteSnapshot',
            'SnapshotId': snapshot.id
        }
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def ex_destroy_image(self, image):
        params = {
            'Action': 'DeregisterImage',
            'ImageId': image.id
        }
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def ex_create_keypair(self, name):
        """Creates a new keypair

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the keypair to Create. This must be
            unique, otherwise an InvalidKeyPair.Duplicate exception is raised.
        :type       name: ``str``

        :rtype: ``dict``
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

    def ex_delete_keypair(self, keypair):
        """
        Delete a key pair by name.

        @note: This is a non-standard extension API, and only works with EC2.

        :param      keypair: The name of the keypair to delete.
        :type       keypair: ``str``

        :rtype: ``bool``
        """
        params = {
            'Action': 'DeleteKeyPair',
            'KeyName': keypair
        }
        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

    def ex_import_keypair_from_string(self, name, key_material):
        """
        imports a new public key where the public key is passed in as a string

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the public key to import. This must be
         unique, otherwise an InvalidKeyPair.Duplicate exception is raised.
        :type       name: ``str``

        :param     key_material: The contents of a public key file.
        :type      key_material: ``str``

        :rtype: ``dict``
        """
        base64key = base64.b64encode(b(key_material))

        params = {
            'Action': 'ImportKeyPair',
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

    def ex_import_keypair(self, name, keyfile):
        """
        imports a new public key where the public key is passed via a filename

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the public key to import. This must be
         unique, otherwise an InvalidKeyPair.Duplicate exception is raised.
        :type       name: ``str``

        :param     keyfile: The filename with path of the public key to import.
        :type      keyfile: ``str``

        :rtype: ``dict``
        """
        with open(os.path.expanduser(keyfile)) as fh:
            content = fh.read()
        return self.ex_import_keypair_from_string(name, content)

    def ex_find_or_import_keypair_by_key_material(self, pubkey):
        """
        Given a public key, look it up in the EC2 KeyPair database. If it
        exists, return any information we have about it. Otherwise, create it.

        Keys that are created are named based on their comment and fingerprint.
        """
        key_fingerprint = get_pubkey_ssh2_fingerprint(pubkey)
        key_comment = get_pubkey_comment(pubkey, default='unnamed')
        key_name = "%s-%s" % (key_comment, key_fingerprint)

        for keypair in self.ex_list_keypairs():
            if keypair['keyFingerprint'] == key_fingerprint:
                return keypair

        return self.ex_import_keypair_from_string(key_name, pubkey)

    def ex_list_keypairs(self):
        """
        Lists all the keypair names and fingerprints.

        :rtype: ``list`` of ``dict``
        """
        params = {
            'Action': 'DescribeKeyPairs'
        }

        response = self.connection.request(self.path, params=params).object
        keypairs = []
        for elem in findall(element=response, xpath='keySet/item',
                            namespace=NAMESPACE):
            keypair = {
                'keyName': findtext(element=elem, xpath='keyName',
                                    namespace=NAMESPACE),
                'keyFingerprint': findtext(element=elem,
                                           xpath='keyFingerprint',
                                           namespace=NAMESPACE).strip(),
            }
            keypairs.append(keypair)

        return keypairs

    def ex_describe_all_keypairs(self):
        """
        Describes all keypairs. This is here for backward compatibilty.

        @note: This is a non-standard extension API, and only works for EC2.

        :rtype: ``list`` of ``str``
        """
        return [k['keyName'] for k in self.ex_list_keypairs()]

    def ex_describe_keypairs(self, name):
        """
        Here for backward compatibility.
        """
        return self.ex_describe_keypair(name=name)

    def ex_describe_keypair(self, name):
        """
        Describes a keypair by name.

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the keypair to describe.
        :type       name: ``str``

        :rtype: ``dict``
        """

        params = {
            'Action': 'DescribeKeyPairs',
            'KeyName.1': name
        }

        response = self.connection.request(self.path, params=params).object
        key_name = findattr(element=response, xpath='keySet/item/keyName',
                            namespace=NAMESPACE)
        fingerprint = findattr(element=response,
                               xpath='keySet/item/keyFingerprint',
                               namespace=NAMESPACE).strip()
        return {
            'keyName': key_name,
            'keyFingerprint': fingerprint
        }

    def ex_list_security_groups(self):
        """
        List existing Security Groups.

        @note: This is a non-standard extension API, and only works for EC2.

        :rtype: ``list`` of ``str``
        """
        params = {'Action': 'DescribeSecurityGroups'}
        response = self.connection.request(self.path, params=params).object

        groups = []
        for group in findall(element=response, xpath='securityGroupInfo/item',
                             namespace=NAMESPACE):
            name = findtext(element=group, xpath='groupName',
                            namespace=NAMESPACE)
            groups.append(name)

        return groups

    def ex_create_security_group(self, name, description):
        """
        Creates a new Security Group

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the security group to Create.
                          This must be unique.
        :type       name: ``str``

        :param      description: Human readable description of a Security
        Group.
        :type       description: ``str``

        :rtype: ``str``
        """
        params = {'Action': 'CreateSecurityGroup',
                  'GroupName': name,
                  'GroupDescription': description}
        return self.connection.request(self.path, params=params).object

    def ex_authorize_security_group(self, name, from_port, to_port, cidr_ip,
                                    protocol='tcp'):
        """
        Edit a Security Group to allow specific traffic.

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the security group to edit
        :type       name: ``str``

        :param      from_port: The beginning of the port range to open
        :type       from_port: ``str``

        :param      to_port: The end of the port range to open
        :type       to_port: ``str``

        :param      cidr_ip: The ip to allow traffic for.
        :type       cidr_ip: ``str``

        :param      protocol: tcp/udp/icmp
        :type       protocol: ``str``

        :rtype: ``bool``
        """

        params = {'Action': 'AuthorizeSecurityGroupIngress',
                  'GroupName': name,
                  'IpProtocol': protocol,
                  'FromPort': str(from_port),
                  'ToPort': str(to_port),
                  'CidrIp': cidr_ip}
        try:
            resp = self.connection.request(
                self.path, params=params.copy()).object
            return bool(findtext(element=resp, xpath='return',
                                 namespace=NAMESPACE))
        except Exception:
            e = sys.exc_info()[1]
            if e.args[0].find('InvalidPermission.Duplicate') == -1:
                raise e

    def ex_authorize_security_group_permissive(self, name):
        """
        Edit a Security Group to allow all traffic.

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the security group to edit
        :type       name: ``str``

        :rtype: ``list`` of ``str``
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
        Return a list of :class:`ExEC2AvailabilityZone` objects for the
        current region.

        Note: This is an extension method and is only available for EC2
        driver.

        :keyword  only_available: If true, return only availability zones
                                  with state 'available'
        :type     only_available: ``str``

        :rtype: ``list`` of :class:`ExEC2AvailabilityZone`
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

    def ex_describe_tags(self, resource):
        """
        Return a dictionary of tags for a resource (Node or StorageVolume).

        :param  resource: resource which should be used
        :type   resource: :class:`Node` or :class:`StorageVolume`

        :return: dict Node tags
        :rtype: ``dict``
        """
        params = {'Action': 'DescribeTags',
                  'Filter.0.Name': 'resource-id',
                  'Filter.0.Value.0': resource.id,
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

    def ex_create_tags(self, resource, tags):
        """
        Create tags for a resource (Node or StorageVolume).

        :param resource: Resource to be tagged
        :type resource: :class:`Node` or :class:`StorageVolume`

        :param tags: A dictionary or other mapping of strings to strings,
                     associating tag names with tag values.
        :type tags: ``dict``

        :rtype: ``bool``
        """
        if not tags:
            return

        params = {'Action': 'CreateTags',
                  'ResourceId.0': resource.id}
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        result = self.connection.request(self.path,
                                         params=params.copy()).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

    def ex_delete_tags(self, resource, tags):
        """
        Delete tags from a resource.

        :param resource: Resource to be tagged
        :type resource: :class:`Node` or :class:`StorageVolume`

        :param tags: A dictionary or other mapping of strings to strings,
                     specifying the tag names and tag values to be deleted.
        :type tags: ``dict``

        :rtype: ``bool``
        """
        if not tags:
            return

        params = {'Action': 'DeleteTags',
                  'ResourceId.0': resource.id}
        for i, key in enumerate(tags):
            params['Tag.%d.Key' % i] = key
            params['Tag.%d.Value' % i] = tags[key]

        result = self.connection.request(self.path,
                                         params=params.copy()).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

    def ex_get_metadata_for_node(self, node):
        """
        Return the metadata associated with the node.

        :param      node: Node instance
        :type       node: :class:`Node`

        :return: A dictionary or other mapping of strings to strings,
                 associating tag names with tag values.
        :rtype tags: ``dict``
        """
        return node.extra['tags']

    def _add_instance_filter(self, params, node):
        """
        Add instance filter to the provided params dictionary.
        """
        params.update({
            'Filter.0.Name': 'instance-id',
            'Filter.0.Value.0': node.id
        })

    def ex_allocate_address(self):
        """
        Allocate a new Elastic IP address

        :return: String representation of allocated IP address
        :rtype: ``str``
        """
        params = {'Action': 'AllocateAddress'}

        response = self.connection.request(self.path, params=params).object
        public_ip = findtext(element=response, xpath='publicIp',
                             namespace=NAMESPACE)
        return public_ip

    def ex_release_address(self, elastic_ip_address):
        """
        Release an Elastic IP address

        :param      elastic_ip_address: Elastic IP address which should be used
        :type       elastic_ip_address: ``str``

        :return: True on success, False otherwise.
        :rtype: ``bool``
        """
        params = {'Action': 'ReleaseAddress'}

        params.update({'PublicIp': elastic_ip_address})
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def ex_describe_all_addresses(self, only_allocated=False):
        """
        Return all the Elastic IP addresses for this account
        optionally, return only the allocated addresses

        :param    only_allocated: If true, return only those addresses
                                  that are associated with an instance
        :type     only_allocated: ``str``

        :return:   list list of elastic ips for this particular account.
        :rtype: ``list`` of ``str``
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

    def ex_associate_address_with_node(self, node, elastic_ip_address):
        """
        Associate an Elastic IP address with a particular node.

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      elastic_ip_address: IP address which should be used
        :type       elastic_ip_address: ``str``

        :return: True on success, False otherwise.
        :rtype: ``bool``
        """
        params = {'Action': 'AssociateAddress'}

        params.update({'InstanceId': node.id})
        params.update({'PublicIp': elastic_ip_address})
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def ex_associate_addresses(self, node, elastic_ip_address):
        """
        Note: This method has been deprecated in favor of
        the ex_associate_address_with_node method.
        """
        return self.ex_associate_address_with_node(node=node,
                                                   elastic_ip_address=
                                                   elastic_ip_address)

    def ex_disassociate_address(self, elastic_ip_address):
        """
        Disassociate an Elastic IP address

        :param      elastic_ip_address: Elastic IP address which should be used
        :type       elastic_ip_address: ``str``

        :return: True on success, False otherwise.
        :rtype: ``bool``
        """
        params = {'Action': 'DisassociateAddress'}

        params.update({'PublicIp': elastic_ip_address})
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def ex_describe_addresses(self, nodes):
        """
        Return Elastic IP addresses for all the nodes in the provided list.

        :param      nodes: List of :class:`Node` instances
        :type       nodes: ``list`` of :class:`Node`

        :return: Dictionary where a key is a node ID and the value is a
            list with the Elastic IP addresses associated with this node.
        :rtype: ``dict``
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

        :param      node: Node instance
        :type       node: :class:`Node`

        :return: list Elastic IP addresses attached to this node.
        :rtype: ``list`` of ``str``
        """
        node_elastic_ips = self.ex_describe_addresses([node])
        return node_elastic_ips[node.id]

    def ex_modify_instance_attribute(self, node, attributes):
        """
        Modify node attributes.
        A list of valid attributes can be found at http://goo.gl/gxcj8

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      attributes: Dictionary with node attributes
        :type       attributes: ``dict``

        :return: True on success, False otherwise.
        :rtype: ``bool``
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

    def ex_modify_image_attribute(self, image, attributes):
        """
        Modify image attributes.

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      attributes: Dictionary with node attributes
        :type       attributes: ``dict``

        :return: True on success, False otherwise.
        :rtype: ``bool``
        """
        attributes = attributes or {}
        attributes.update({'ImageId': image.id})

        params = {'Action': 'ModifyImageAttribute'}
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

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      new_size: NodeSize intance
        :type       new_size: :class:`NodeSize`

        :return: True on success, False otherwise.
        :rtype: ``bool``
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

        Reference: http://bit.ly/8ZyPSy [docs.amazonwebservices.com]

        @inherits: :class:`NodeDriver.create_node`

        :keyword    ex_keyname: The name of the key pair
        :type       ex_keyname: ``str``

        :keyword    ex_userdata: User data
        :type       ex_userdata: ``str``

        :keyword    ex_security_groups: A list of names of security groups to
                                        assign to the node.
        :type       ex_security_groups:   ``list``

        :keyword    ex_metadata: Key/Value metadata to associate with a node
        :type       ex_metadata: ``dict``

        :keyword    ex_mincount: Minimum number of instances to launch
        :type       ex_mincount: ``int``

        :keyword    ex_maxcount: Maximum number of instances to launch
        :type       ex_maxcount: ``int``

        :keyword    ex_clienttoken: Unique identifier to ensure idempotency
        :type       ex_clienttoken: ``str``

        :keyword    ex_blockdevicemappings: ``list`` of ``dict`` block device
                    mappings. Example:
                    [{'DeviceName': '/dev/sda1', 'Ebs.VolumeSize': 10},
                     {'DeviceName': '/dev/sdb', 'VirtualName': 'ephemeral0'}]
        :type       ex_blockdevicemappings: ``list`` of ``dict``

        :keyword    ex_iamprofile: Name or ARN of IAM profile
        :type       ex_iamprofile: ``str``
        """
        image = kwargs["image"]
        size = kwargs["size"]
        params = {
            'Action': 'RunInstances',
            'ImageId': image.id,
            'MinCount': str(kwargs.get('ex_mincount', '1')),
            'MaxCount': str(kwargs.get('ex_maxcount', '1')),
            'InstanceType': size.id
        }

        if 'ex_security_groups' in kwargs and 'ex_securitygroup' in kwargs:
            raise ValueError('You can only supply ex_security_groups or'
                             ' ex_securitygroup')

        # ex_securitygroup is here for backward compatibility
        ex_security_groups = kwargs.get('ex_security_groups', None)
        ex_securitygroup = kwargs.get('ex_securitygroup', None)
        security_groups = ex_security_groups or ex_securitygroup

        if security_groups:
            if not isinstance(security_groups, (tuple, list)):
                security_groups = [security_groups]

            for sig in range(len(security_groups)):
                params['SecurityGroup.%d' % (sig + 1,)] =\
                    security_groups[sig]

        if 'location' in kwargs:
            availability_zone = getattr(kwargs['location'],
                                        'availability_zone', None)
            if availability_zone:
                if availability_zone.region_name != self.region_name:
                    raise AttributeError('Invalid availability zone: %s'
                                         % (availability_zone.name))
                params['Placement.AvailabilityZone'] = availability_zone.name

        if 'auth' in kwargs and 'ex_keyname' in kwargs:
            raise AttributeError('Cannot specify auth and ex_keyname together')

        if 'auth' in kwargs:
            auth = self._get_and_check_auth(kwargs['auth'])
            params['KeyName'] = \
                self.ex_find_or_import_keypair_by_key_material(auth.pubkey)

        if 'ex_keyname' in kwargs:
            params['KeyName'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            params['UserData'] = base64.b64encode(b(kwargs['ex_userdata']))\
                .decode('utf-8')

        if 'ex_clienttoken' in kwargs:
            params['ClientToken'] = kwargs['ex_clienttoken']

        if 'ex_blockdevicemappings' in kwargs:
            if not isinstance(kwargs['ex_blockdevicemappings'], (list, tuple)):
                raise AttributeError(
                    'ex_blockdevicemappings not list or tuple')

            for idx, mapping in enumerate(kwargs['ex_blockdevicemappings']):
                idx += 1  # we want 1-based indexes
                if not isinstance(mapping, dict):
                    raise AttributeError(
                        'mapping %s in ex_blockdevicemappings '
                        'not a dict' % mapping)
                for k, v in mapping.items():
                    params['BlockDeviceMapping.%d.%s' % (idx, k)] = str(v)

        if 'ex_iamprofile' in kwargs:
            if not isinstance(kwargs['ex_iamprofile'], basestring):
                raise AttributeError('ex_iamprofile not string')

            if kwargs['ex_iamprofile'].startswith('arn:aws:iam:'):
                params['IamInstanceProfile.Arn'] = kwargs['ex_iamprofile']
            else:
                params['IamInstanceProfile.Name'] = kwargs['ex_iamprofile']

        object = self.connection.request(self.path, params=params).object
        nodes = self._to_nodes(object, 'instancesSet/item')

        for node in nodes:
            tags = {'Name': kwargs['name']}
            if 'ex_metadata' in kwargs:
                tags.update(kwargs['ex_metadata'])

            try:
                self.ex_create_tags(resource=node, tags=tags)
            except Exception:
                continue

            node.name = kwargs['name']
            node.extra.update({'tags': tags})

        if len(nodes) == 1:
            return nodes[0]
        else:
            return nodes

    def reboot_node(self, node):
        params = {'Action': 'RebootInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def ex_start_node(self, node):
        """
        Start the node by passing in the node object, does not work with
        instance store backed instances

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        params = {'Action': 'StartInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_state_boolean(res)

    def ex_stop_node(self, node):
        """
        Stop the node by passing in the node object, does not work with
        instance store backed instances

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        params = {'Action': 'StopInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_state_boolean(res)

    def destroy_node(self, node):
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_terminate_boolean(res)


class EC2NodeDriver(BaseEC2NodeDriver):
    """
    Amazon EC2 node driver.
    """

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2'
    website = 'http://aws.amazon.com/ec2/'
    path = '/'

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'shutting-down': NodeState.UNKNOWN,
        'terminated': NodeState.TERMINATED,
        'stopped': NodeState.STOPPED
    }

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 region='us-east-1', **kwargs):
        if hasattr(self, '_region'):
            region = self._region

        if region not in VALID_EC2_REGIONS:
            raise ValueError('Invalid region: %s' % (region))

        details = REGION_DETAILS[region]
        self.region_name = region
        self.api_name = details['api_name']
        self.country = details['country']

        self.connectionCls.host = details['endpoint']

        super(EC2NodeDriver, self).__init__(key=key, secret=secret,
                                            secure=secure, host=host,
                                            port=port, **kwargs)


class IdempotentParamError(LibcloudError):
    """
    Request used the same client token as a previous,
    but non-identical request.
    """

    def __str__(self):
        return repr(self.value)


class EC2EUNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western Europe Region.
    """
    name = 'Amazon EC2 (eu-west-1)'
    _region = 'eu-west-1'


class EC2USWestNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Western US Region
    """
    name = 'Amazon EC2 (us-west-1)'
    _region = 'us-west-1'


class EC2USWestOregonNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the US West Oregon region.
    """
    name = 'Amazon EC2 (us-west-2)'
    _region = 'us-west-2'


class EC2APSENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region.
    """
    name = 'Amazon EC2 (ap-southeast-1)'
    _region = 'ap-southeast-1'


class EC2APNENodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Northeast Asia Pacific Region.
    """
    name = 'Amazon EC2 (ap-northeast-1)'
    _region = 'ap-northeast-1'


class EC2SAEastNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the South America (Sao Paulo) Region.
    """
    name = 'Amazon EC2 (sa-east-1)'
    _region = 'sa-east-1'


class EC2APSESydneyNodeDriver(EC2NodeDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific (Sydney) Region.
    """
    name = 'Amazon EC2 (ap-southeast-2)'
    _region = 'ap-southeast-2'


class EucConnection(EC2Connection):
    """
    Connection class for Eucalyptus
    """

    host = None


class EucNodeDriver(BaseEC2NodeDriver):
    """
    Driver class for Eucalyptus
    """

    name = 'Eucalyptus'
    website = 'http://www.eucalyptus.com/'
    api_name = 'ec2_us_east'
    region_name = 'us-east-1'
    connectionCls = EucConnection

    def __init__(self, key, secret=None, secure=True, host=None,
                 path=None, port=None):
        """
        @inherits: :class:`EC2NodeDriver.__init__`

        :param    path: The host where the API can be reached.
        :type     path: ``str``
        """
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


class NimbusConnection(EC2Connection):
    """
    Connection class for Nimbus
    """

    host = None


class NimbusNodeDriver(BaseEC2NodeDriver):
    """
    Driver class for Nimbus
    """

    type = Provider.NIMBUS
    name = 'Nimbus'
    website = 'http://www.nimbusproject.org/'
    country = 'Private'
    api_name = 'nimbus'
    region_name = 'nimbus'
    friendly_name = 'Nimbus Private Cloud'
    connectionCls = NimbusConnection

    def ex_describe_addresses(self, nodes):
        """
        Nimbus doesn't support elastic IPs, so this is a passthrough.

        @inherits: :class:`EC2NodeDriver.ex_describe_addresses`
        """
        nodes_elastic_ip_mappings = {}
        for node in nodes:
            # empty list per node
            nodes_elastic_ip_mappings[node.id] = []
        return nodes_elastic_ip_mappings

    def ex_create_tags(self, resource, tags):
        """
        Nimbus doesn't support creating tags, so this is a passthrough.

        @inherits: :class:`EC2NodeDriver.ex_create_tags`
        """
        pass
