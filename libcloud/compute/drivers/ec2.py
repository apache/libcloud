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

import re
import sys
import base64
import copy
import warnings

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
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume, VolumeSnapshot
from libcloud.compute.base import KeyPair
from libcloud.compute.types import NodeState, KeyPairDoesNotExistError

__all__ = [
    'API_VERSION',
    'NAMESPACE',
    'INSTANCE_TYPES',

    'EC2NodeDriver',
    'BaseEC2NodeDriver',

    'NimbusNodeDriver',
    'EucNodeDriver',

    'EC2NodeLocation',
    'EC2ReservedNode',
    'EC2Network',
    'EC2NetworkSubnet',
    'EC2NetworkInterface',
    'ExEC2AvailabilityZone',

    'IdempotentParamError'
]

API_VERSION = '2013-10-15'
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
    },
    # i2 instances have up to eight SSD drives
    'i2.xlarge': {
        'id': 'i2.xlarge',
        'name': 'High Storage Optimized Extra Large Instance',
        'ram': 31232,
        'disk': 800,
        'bandwidth': None
    },
    'i2.2xlarge': {
        'id': 'i2.2xlarge',
        'name': 'High Storage Optimized Double Extra Large Instance',
        'ram': 62464,
        'disk': 1600,
        'bandwidth': None
    },
    'i2.4xlarge': {
        'id': 'i2.4xlarge',
        'name': 'High Storage Optimized Quadruple Large Instance',
        'ram': 124928,
        'disk': 3200,
        'bandwidth': None
    },
    'i2.8xlarge': {
        'id': 'i2.8xlarge',
        'name': 'High Storage Optimized Eight Extra Large Instance',
        'ram': 249856,
        'disk': 6400,
        'bandwidth': None
    },
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
            'hs1.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'c1.xlarge',
            'c3.large',
            'c3.xlarge',
            'c3.2xlarge',
            'c3.4xlarge',
            'c3.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'cc2.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'cc2.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'hs1.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'c3.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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
            'hs1.8xlarge',
            'i2.xlarge',
            'i2.2xlarge',
            'i2.4xlarge',
            'i2.8xlarge',
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

"""
Define the extra dictionary for specific resources
"""
RESOURCE_EXTRA_ATTRIBUTES_MAP = {
    'ebs_volume': {
        'snapshot_id': {
            'xpath': 'ebs/snapshotId',
            'transform_func': str
        },
        'volume_size': {
            'xpath': 'ebs/volumeSize',
            'transform_func': int
        },
        'delete': {
            'xpath': 'ebs/deleteOnTermination',
            'transform_func': str
        },
        'volume_type': {
            'xpath': 'ebs/volumeType',
            'transform_func': str
        },
        'iops': {
            'xpath': 'ebs/iops',
            'transform_func': int
        }
    },
    'elastic_ip': {
        'allocation_id': {
            'xpath': 'allocationId',
            'transform_func': str,
        },
        'association_id': {
            'xpath': 'associationId',
            'transform_func': str,
        },
        'interface_id': {
            'xpath': 'networkInterfaceId',
            'transform_func': str,
        },
        'owner_id': {
            'xpath': 'networkInterfaceOwnerId',
            'transform_func': str,
        },
        'private_ip': {
            'xpath': 'privateIp',
            'transform_func': str,
        }
    },
    'image': {
        'state': {
            'xpath': 'imageState',
            'transform_func': str
        },
        'owner_id': {
            'xpath': 'imageOwnerId',
            'transform_func': str
        },
        'owner_alias': {
            'xpath': 'imageOwnerAlias',
            'transform_func': str
        },
        'is_public': {
            'xpath': 'isPublic',
            'transform_func': str
        },
        'architecture': {
            'xpath': 'architecture',
            'transform_func': str
        },
        'image_type': {
            'xpath': 'imageType',
            'transform_func': str
        },
        'image_location': {
            'xpath': 'imageLocation',
            'transform_func': str
        },
        'platform': {
            'xpath': 'platform',
            'transform_func': str
        },
        'description': {
            'xpath': 'description',
            'transform_func': str
        },
        'root_device_type': {
            'xpath': 'rootDeviceType',
            'transform_func': str
        },
        'virtualization_type': {
            'xpath': 'virtualizationType',
            'transform_func': str
        },
        'hypervisor': {
            'xpath': 'hypervisor',
            'transform_func': str
        },
        'kernel_id': {
            'xpath': 'kernelId',
            'transform_func': str
        },
        'ramdisk_id': {
            'xpath': 'ramdisk_id',
            'transform_func': str
        }
    },
    'network': {
        'state': {
            'xpath': 'state',
            'transform_func': str
        },
        'dhcp_options_id': {
            'xpath': 'dhcpOptionsId',
            'transform_func': str
        },
        'instance_tenancy': {
            'xpath': 'instanceTenancy',
            'transform_func': str
        },
        'is_default': {
            'xpath': 'isDefault',
            'transform_func': str
        }
    },
    'network_interface': {
        'subnet_id': {
            'xpath': 'subnetId',
            'transform_func': str
        },
        'vpc_id': {
            'xpath': 'vpcId',
            'transform_func': str
        },
        'zone': {
            'xpath': 'availabilityZone',
            'transform_func': str
        },
        'description': {
            'xpath': 'description',
            'transform_func': str
        },
        'owner_id': {
            'xpath': 'ownerId',
            'transform_func': str
        },
        'mac_address': {
            'xpath': 'macAddress',
            'transform_func': str
        },
        'private_dns_name': {
            'xpath': 'privateIpAddressesSet/privateDnsName',
            'transform_func': str
        },
        'source_dest_check': {
            'xpath': 'sourceDestCheck',
            'transform_func': str
        }
    },
    'network_interface_attachment': {
        'attachment_id': {
            'xpath': 'attachment/attachmentId',
            'transform_func': str
        },
        'instance_id': {
            'xpath': 'attachment/instanceId',
            'transform_func': str
        },
        'owner_id': {
            'xpath': 'attachment/instanceOwnerId',
            'transform_func': str
        },
        'device_index': {
            'xpath': 'attachment/deviceIndex',
            'transform_func': int
        },
        'status': {
            'xpath': 'attachment/status',
            'transform_func': str
        },
        'attach_time': {
            'xpath': 'attachment/attachTime',
            'transform_func': parse_date
        },
        'delete': {
            'xpath': 'attachment/deleteOnTermination',
            'transform_func': str
        }
    },
    'node': {
        'availability': {
            'xpath': 'placement/availabilityZone',
            'transform_func': str
        },
        'architecture': {
            'xpath': 'architecture',
            'transform_func': str
        },
        'client_token': {
            'xpath': 'clientToken',
            'transform_func': str
        },
        'dns_name': {
            'xpath': 'dnsName',
            'transform_func': str
        },
        'hypervisor': {
            'xpath': 'hypervisor',
            'transform_func': str
        },
        'iam_profile': {
            'xpath': 'iamInstanceProfile/id',
            'transform_func': str
        },
        'image_id': {
            'xpath': 'imageId',
            'transform_func': str
        },
        'instance_id': {
            'xpath': 'instanceId',
            'transform_func': str
        },
        'instance_lifecycle': {
            'xpath': 'instanceLifecycle',
            'transform_func': str
        },
        'instance_tenancy': {
            'xpath': 'placement/tenancy',
            'transform_func': str
        },
        'instance_type': {
            'xpath': 'instanceType',
            'transform_func': str
        },
        'key_name': {
            'xpath': 'keyName',
            'transform_func': str
        },
        'launch_index': {
            'xpath': 'amiLaunchIndex',
            'transform_func': int
        },
        'launch_time': {
            'xpath': 'launchTime',
            'transform_func': str
        },
        'kernel_id': {
            'xpath': 'kernelId',
            'transform_func': str
        },
        'monitoring': {
            'xpath': 'monitoring/state',
            'transform_func': str
        },
        'platform': {
            'xpath': 'platform',
            'transform_func': str
        },
        'private_dns': {
            'xpath': 'privateDnsName',
            'transform_func': str
        },
        'ramdisk_id': {
            'xpath': 'ramdiskId',
            'transform_func': str
        },
        'root_device_type': {
            'xpath': 'rootDeviceType',
            'transform_func': str
        },
        'root_device_name': {
            'xpath': 'rootDeviceName',
            'transform_func': str
        },
        'reason': {
            'xpath': 'reason',
            'transform_func': str
        },
        'source_dest_check': {
            'xpath': 'sourceDestCheck',
            'transform_func': str
        },
        'status': {
            'xpath': 'instanceState/name',
            'transform_func': str
        },
        'subnet_id': {
            'xpath': 'subnetId',
            'transform_func': str
        },
        'virtualization_type': {
            'xpath': 'virtualizationType',
            'transform_func': str
        },
        'ebs_optimized': {
            'xpath': 'ebsOptimized',
            'transform_func': str
        },
        'vpc_id': {
            'xpath': 'vpcId',
            'transform_func': str
        }
    },
    'reserved_node': {
        'instance_type': {
            'xpath': 'instanceType',
            'transform_func': str
        },
        'availability': {
            'xpath': 'availabilityZone',
            'transform_func': str
        },
        'start': {
            'xpath': 'start',
            'transform_func': str
        },
        'duration': {
            'xpath': 'duration',
            'transform_func': int
        },
        'usage_price': {
            'xpath': 'usagePrice',
            'transform_func': float
        },
        'fixed_price': {
            'xpath': 'fixedPrice',
            'transform_func': float
        },
        'instance_count': {
            'xpath': 'instanceCount',
            'transform_func': int
        },
        'description': {
            'xpath': 'productDescription',
            'transform_func': str
        },
        'instance_tenancy': {
            'xpath': 'instanceTenancy',
            'transform_func': str
        },
        'currency_code': {
            'xpath': 'currencyCode',
            'transform_func': str
        },
        'offering_type': {
            'xpath': 'offeringType',
            'transform_func': str
        }
    },
    'snapshot': {
        'volume_id': {
            'xpath': 'volumeId',
            'transform_func': str
        },
        'state': {
            'xpath': 'status',
            'transform_func': str
        },
        'description': {
            'xpath': 'description',
            'transform_func': str
        },
        'progress': {
            'xpath': 'progress',
            'transform_func': str
        },
        'start_time': {
            'xpath': 'startTime',
            'transform_func': parse_date
        }
    },
    'subnet': {
        'cidr_block': {
            'xpath': 'cidrBlock',
            'transform_func': str
        },
        'available_ips': {
            'xpath': 'availableIpAddressCount',
            'transform_func': int
        },
        'zone': {
            'xpath': 'availabilityZone',
            'transform_func': str
        },
        'vpc_id': {
            'xpath': 'vpcId',
            'transform_func': str
        }
    },
    'volume': {
        'device': {
            'xpath': 'device',
            'transform_func': str
        },
        'iops': {
            'xpath': 'iops',
            'transform_func': int
        },
        'zone': {
            'xpath': 'availabilityZone',
            'transform_func': str
        },
        'create_time': {
            'xpath': 'createTime',
            'transform_func': parse_date
        },
        'state': {
            'xpath': 'status',
            'transform_func': str
        },
        'attach_time': {
            'xpath': 'attachmentSet/item/attachTime',
            'transform_func': parse_date
        },
        'attachment_status': {
            'xpath': 'attachmentSet/item/status',
            'transform_func': str
        },
        'instance_id': {
            'xpath': 'attachmentSet/item/instanceId',
            'transform_func': str
        },
        'delete': {
            'xpath': 'attachmentSet/item/deleteOnTermination',
            'transform_func': str
        }
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
            err_list.append('%s: %s' % (code.text, message.text))
            if code.text == 'InvalidClientTokenId':
                raise InvalidCredsError(err_list[-1])
            if code.text == 'SignatureDoesNotMatch':
                raise InvalidCredsError(err_list[-1])
            if code.text == 'AuthFailure':
                raise InvalidCredsError(err_list[-1])
            if code.text == 'OptInRequired':
                raise InvalidCredsError(err_list[-1])
            if code.text == 'IdempotentParameterMismatch':
                raise IdempotentParamError(err_list[-1])
            if code.text == 'InvalidKeyPair.NotFound':
                # TODO: Use connection context instead
                match = re.match(r'.*\'(.+?)\'.*', message.text)

                if match:
                    name = match.groups()[0]
                else:
                    name = None

                raise KeyPairDoesNotExistError(name=name,
                                               driver=self.connection.driver)
        return '\n'.join(err_list)


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


class EC2ReservedNode(Node):
    """
    Class which stores information about EC2 reserved instances/nodes
    Inherits from Node and passes in None for name and private/public IPs

    Note: This class is EC2 specific.
    """

    def __init__(self, id, state, driver, size=None, image=None, extra=None):
        super(EC2ReservedNode, self).__init__(id=id, name=None, state=state,
                                              public_ips=None,
                                              private_ips=None,
                                              driver=driver, extra=extra)

    def __repr__(self):
        return (('<EC2ReservedNode: id=%s>') % (self.id))


class EC2Network(object):
    """
    Represents information about a VPC (Virtual Private Cloud) network

    Note: This class is EC2 specific.
    """

    def __init__(self, id, name, cidr_block, extra=None):
        self.id = id
        self.name = name
        self.cidr_block = cidr_block
        self.extra = extra or {}

    def __repr__(self):
        return (('<EC2Network: id=%s, name=%s')
                % (self.id, self.name))


class EC2NetworkSubnet(object):
    """
    Represents information about a VPC (Virtual Private Cloud) subnet

    Note: This class is EC2 specific.
    """

    def __init__(self, id, name, state, extra=None):
        self.id = id
        self.name = name
        self.state = state
        self.extra = extra or {}

    def __repr__(self):
        return (('<EC2NetworkSubnet: id=%s, name=%s') % (self.id, self.name))


class EC2NetworkInterface(object):
    """
    Represents information about a VPC network interface

    Note: This class is EC2 specific. The state parameter denotes the current
    status of the interface. Valid values for state are attaching, attached,
    detaching and detached.
    """

    def __init__(self, id, name, state, extra=None):
        self.id = id
        self.name = name
        self.state = state
        self.extra = extra or {}

    def __repr__(self):
        return (('<EC2NetworkInterface: id=%s, name=%s')
                % (self.id, self.name))


class ElasticIP(object):
    """
    Represents information about an elastic IP adddress

    :param      ip: The elastic IP address
    :type       ip: ``str``

    :param      domain: The domain that the IP resides in (EC2-Classic/VPC).
                        EC2 classic is represented with standard and VPC
                        is represented with vpc.
    :type       domain: ``str``

    :param      instance_id: The identifier of the instance which currently
                             has the IP associated.
    :type       instance_id: ``str``

    Note: This class is used to support both EC2 and VPC IPs.
          For VPC specific attributes are stored in the extra
          dict to make promotion to the base API easier.
    """

    def __init__(self, ip, domain, instance_id, extra=None):
        self.ip = ip
        self.domain = domain
        self.instance_id = instance_id
        self.extra = extra or {}

    def __repr__(self):
        return (('<ElasticIP: ip=%s, domain=%s, instance_id=%s>')
                % (self.ip, self.domain, self.instance_id))


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
            nodes += self._to_nodes(rs, 'instancesSet/item')

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

    def list_images(self, location=None, ex_image_ids=None, ex_owner=None,
                    ex_executableby=None):
        """
        List all images

        Ex_image_ids parameter is used to filter the list of
        images that should be returned. Only the images
        with the corresponding image ids will be returned.

        Ex_owner parameter is used to filter the list of
        images that should be returned. Only the images
        with the corresponding owner will be returned.
        Valid values: amazon|aws-marketplace|self|all|aws id

        Ex_executableby parameter describes images for which
        the specified user has explicit launch permissions.
        The user can be an AWS account ID, self to return
        images for which the sender of the request has
        explicit launch permissions, or all to return
        images with public launch permissions.
        Valid values: all|self|aws id

        :param      ex_image_ids: List of ``NodeImage.id``
        :type       ex_image_ids: ``list`` of ``str``

        :param      ex_owner: Owner name
        :type       ex_owner: ``str``

        :param      ex_executableby: Executable by
        :type       ex_executableby: ``str``

        :rtype: ``list`` of :class:`NodeImage`
        """
        params = {'Action': 'DescribeImages'}

        if ex_owner:
            params.update({'Owner.1': ex_owner})

        if ex_executableby:
            params.update({'ExecutableBy.1': ex_executableby})

        if ex_image_ids:
            for index, image_id in enumerate(ex_image_ids):
                index += 1
                params.update({'ImageId.%s' % (index): image_id})

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
        volumes = [self._to_volume(el) for el in response.findall(
            fixxpath(xpath='volumeSet/item', namespace=NAMESPACE))
        ]
        return volumes

    def create_node(self, **kwargs):
        """
        Create a new EC2 node.

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
                    mappings.
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
            params.update(self._get_block_device_mapping_params(
                          kwargs['ex_blockdevicemappings']))

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

    def destroy_node(self, node):
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request(self.path, params=params).object
        return self._get_terminate_boolean(res)

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

    def destroy_volume(self, volume):
        params = {
            'Action': 'DeleteVolume',
            'VolumeId': volume.id}
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def create_volume_snapshot(self, volume, name=None):
        """
        Create snapshot from volume

        :param      volume: Instance of ``StorageVolume``
        :type       volume: ``StorageVolume``

        :param      name: Name of snapshot
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
        snapshot = self._to_snapshot(response, name)

        if name:
            self.ex_create_tags(snapshot, {'Name': name})

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

    # Key pair management methods

    def list_key_pairs(self):
        params = {
            'Action': 'DescribeKeyPairs'
        }

        response = self.connection.request(self.path, params=params)
        elems = findall(element=response.object, xpath='keySet/item',
                        namespace=NAMESPACE)

        key_pairs = self._to_key_pairs(elems=elems)
        return key_pairs

    def get_key_pair(self, name):
        params = {
            'Action': 'DescribeKeyPairs',
            'KeyName': name
        }

        response = self.connection.request(self.path, params=params)
        elems = findall(element=response.object, xpath='keySet/item',
                        namespace=NAMESPACE)

        key_pair = self._to_key_pairs(elems=elems)[0]
        return key_pair

    def create_key_pair(self, name):
        params = {
            'Action': 'CreateKeyPair',
            'KeyName': name
        }

        response = self.connection.request(self.path, params=params)
        elem = response.object
        key_pair = self._to_key_pair(elem=elem)
        return key_pair

    def import_key_pair_from_string(self, name, key_material):
        base64key = base64.b64encode(b(key_material))

        params = {
            'Action': 'ImportKeyPair',
            'KeyName': name,
            'PublicKeyMaterial': base64key
        }

        response = self.connection.request(self.path, params=params)
        elem = response.object
        key_pair = self._to_key_pair(elem=elem)
        return key_pair

    def delete_key_pair(self, key_pair):
        params = {
            'Action': 'DeleteKeyPair',
            'KeyName': key_pair.name
        }
        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

    def ex_copy_image(self, source_region, image, name=None, description=None):
        """
        Copy an Amazon Machine Image from the specified source region
        to the current region.

        :param      source_region: The region where the image resides
        :type       source_region: ``str``

        :param      image: Instance of class NodeImage
        :type       image: :class:`NodeImage`

        :param      name: The name of the new image
        :type       name: ``str``

        :param      description: The description of the new image
        :type       description: ``str``

        :return:    Instance of class ``NodeImage``
        :rtype:     :class:`NodeImage`
        """
        params = {'Action': 'CopyImage',
                  'SourceRegion': source_region,
                  'SourceImageId':    image.id}

        if name is not None:
            params['Name'] = name

        if description is not None:
            params['Description'] = description

        image = self._to_image(
            self.connection.request(self.path, params=params).object)

        return image

    def ex_create_image_from_node(self, node, name, block_device_mapping,
                                  reboot=False, description=None):
        """
        Create an Amazon Machine Image based off of an EBS-backed instance.

        :param      node: Instance of ``Node``
        :type       node: :class: `Node`

        :param      name: The name for the new image
        :type       name: ``str``

        :param      block_device_mapping: A dictionary of the disk layout
                                          An example of this dict is included
                                          below.
        :type       block_device_mapping: ``list`` of ``dict``

        :param      reboot: Whether or not to shutdown the instance before
                               creation. By default Amazon sets this to false
                               to ensure a clean image.
        :type       reboot: ``bool``

        :param      description: An optional description for the new image
        :type       description: ``str``

        An example block device mapping dictionary is included:

        mapping = [{'VirtualName': None,
                    'Ebs': {'VolumeSize': 10,
                            'VolumeType': 'standard',
                            'DeleteOnTermination': 'true'},
                            'DeviceName': '/dev/sda1'}]

        :return:    Instance of class ``NodeImage``
        :rtype:     :class:`NodeImage`
        """
        params = {'Action': 'CreateImage',
                  'InstanceId': node.id,
                  'Name': name,
                  'Reboot': reboot}

        if description is not None:
            params['Description'] = description

        params.update(self._get_block_device_mapping_params(
                      block_device_mapping))

        image = self._to_image(
            self.connection.request(self.path, params=params).object)

        return image

    def ex_destroy_image(self, image):
        params = {
            'Action': 'DeregisterImage',
            'ImageId': image.id
        }
        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def ex_list_networks(self):
        """
        Return a list of :class:`EC2Network` objects for the
        current region.

        :rtype:     ``list`` of :class:`EC2Network`
        """
        params = {'Action': 'DescribeVpcs'}

        return self._to_networks(
            self.connection.request(self.path, params=params).object
        )

    def ex_create_network(self, cidr_block, name=None,
                          instance_tenancy='default'):
        """
        Create a network/VPC

        :param      cidr_block: The CIDR block assigned to the network
        :type       cidr_block: ``str``

        :param      name: An optional name for the network
        :type       name: ``str``

        :param      instance_tenancy: The allowed tenancy of instances launched
                                      into the VPC.
                                      Valid values: default/dedicated
        :type       instance_tenancy: ``str``

        :return:    Dictionary of network properties
        :rtype:     ``dict``
        """
        params = {'Action': 'CreateVpc',
                  'CidrBlock': cidr_block,
                  'InstanceTenancy':  instance_tenancy}

        response = self.connection.request(self.path, params=params).object
        element = response.findall(fixxpath(xpath='vpc',
                                            namespace=NAMESPACE))[0]

        network = self._to_network(element)

        if name is not None:
            self.ex_create_tags(network, {'Name': name})

        return network

    def ex_delete_network(self, vpc):
        """
        Deletes a network/VPC.

        :param      vpc: VPC to delete.
        :type       vpc: :class:`.EC2Network`

        :rtype:     ``bool``
        """
        params = {'Action': 'DeleteVpc', 'VpcId': vpc.id}

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_list_subnets(self):
        """
        Return a list of :class:`EC2NetworkSubnet` objects for the
        current region.

        :rtype:     ``list`` of :class:`EC2NetworkSubnet`
        """
        params = {'Action': 'DescribeSubnets'}

        return self._to_subnets(
            self.connection.request(self.path, params=params).object
        )

    def ex_create_subnet(self, vpc_id, cidr_block,
                         availability_zone, name=None):
        """
        Create a network subnet within a VPC

        :param      vpc_id: The ID of the VPC that the subnet should be
                            associated with
        :type       vpc_id: ``str``

        :param      cidr_block: The CIDR block assigned to the subnet
        :type       cidr_block: ``str``

        :param      availability_zone: The availability zone where the subnet
                                       should reside
        :type       availability_zone: ``str``

        :param      name: An optional name for the network
        :type       name: ``str``

        :rtype:     :class: `EC2NetworkSubnet`
        """
        params = {'Action': 'CreateSubnet',
                  'VpcId': vpc_id,
                  'CidrBlock': cidr_block,
                  'AvailabilityZone': availability_zone}

        response = self.connection.request(self.path, params=params).object
        element = response.findall(fixxpath(xpath='subnet',
                                            namespace=NAMESPACE))[0]

        subnet = self._to_subnet(element)

        if name is not None:
            self.ex_create_tags(subnet, {'Name': name})

        return subnet

    def ex_delete_subnet(self, subnet):
        """
        Deletes a VPC subnet.

        :param      subnet: The subnet to delete
        :type       subnet: :class:`.EC2NetworkSubnet`

        :rtype:     ``bool``
        """
        params = {'Action': 'DeleteSubnet', 'SubnetId': subnet.id}

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result,
                           xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

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

    def ex_create_security_group(self, name, description, vpc_id=None):
        """
        Creates a new Security Group in EC2-Classic or a targetted VPC.

        :param      name:        The name of the security group to Create.
                                 This must be unique.
        :type       name:        ``str``

        :param      description: Human readable description of a Security
                                 Group.
        :type       description: ``str``

        :param      description: Optional identifier for VPC networks
        :type       description: ``str``

        :rtype: ``dict``
        """
        params = {'Action': 'CreateSecurityGroup',
                  'GroupName': name,
                  'GroupDescription': description}

        if vpc_id is not None:
            params['VpcId'] = vpc_id

        response = self.connection.request(self.path, params=params).object
        group_id = findattr(element=response, xpath='groupId',
                            namespace=NAMESPACE)
        return {
            'group_id': group_id
        }

    def ex_delete_security_group_by_id(self, group_id):
        """
        Deletes a new Security Group using the group id.

        :param      group_id: The ID of the security group
        :type       group_id: ``str``

        :rtype: ``bool``
        """
        params = {'Action': 'DeleteSecurityGroup', 'GroupId': group_id}

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_delete_security_group_by_name(self, group_name):
        """
        Deletes a new Security Group using the group name.

        :param      group_name: The name of the security group
        :type       group_name: ``str``

        :rtype: ``bool``
        """
        params = {'Action': 'DeleteSecurityGroup', 'GroupName': group_name}

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_delete_security_group(self, name):
        """
        Wrapper method which calls ex_delete_security_group_by_name.

        :param      name: The name of the security group
        :type       name: ``str``

        :rtype: ``bool``
        """
        return self.ex_delete_security_group_by_name(name)

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

    def ex_authorize_security_group_ingress(self, id, from_port, to_port,
                                            cidr_ips=None, group_pairs=None,
                                            protocol='tcp'):
        """
        Edit a Security Group to allow specific ingress traffic using
        CIDR blocks or either a group ID, group name or user ID (account).

        :param      id: The id of the security group to edit
        :type       id: ``str``

        :param      from_port: The beginning of the port range to open
        :type       from_port: ``int``

        :param      to_port: The end of the port range to open
        :type       to_port: ``int``

        :param      cidr_ips: The list of ip ranges to allow traffic for.
        :type       cidr_ips: ``list``

        :param      group_pairs: Source user/group pairs to allow traffic for.
                    More info can be found at http://goo.gl/stBHJF

                    EC2 Classic Example: To allow access from any system
                    associated with the default group on account 1234567890

                    [{'group_name': 'default', 'user_id': '1234567890'}]

                    VPC Example: Allow access from any system associated with
                    security group sg-47ad482e on your own account

                    [{'group_id': ' sg-47ad482e'}]
        :type       group_pairs: ``list`` of ``dict``

        :param      protocol: tcp/udp/icmp
        :type       protocol: ``str``

        :rtype: ``bool``
        """

        params = self._get_common_security_group_params(id,
                                                        protocol,
                                                        from_port,
                                                        to_port,
                                                        cidr_ips,
                                                        group_pairs)

        params["Action"] = 'AuthorizeSecurityGroupIngress'

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_authorize_security_group_egress(self, id, from_port, to_port,
                                           cidr_ips=None, group_pairs=None,
                                           protocol='tcp'):
        """
        Edit a Security Group to allow specific egress traffic using
        CIDR blocks or either a group ID, group name or user ID (account).
        This call is not supported for EC2 classic and only works for VPC
        groups.

        :param      id: The id of the security group to edit
        :type       id: ``str``

        :param      from_port: The beginning of the port range to open
        :type       from_port: ``int``

        :param      to_port: The end of the port range to open
        :type       to_port: ``int``

        :param      cidr_ips: The list of ip ranges to allow traffic for.
        :type       cidr_ips: ``list``

        :param      group_pairs: Source user/group pairs to allow traffic for.
                    More info can be found at http://goo.gl/stBHJF

                    EC2 Classic Example: To allow access from any system
                    associated with the default group on account 1234567890

                    [{'group_name': 'default', 'user_id': '1234567890'}]

                    VPC Example: Allow access from any system associated with
                    security group sg-47ad482e on your own account

                    [{'group_id': ' sg-47ad482e'}]
        :type       group_pairs: ``list`` of ``dict``

        :param      protocol: tcp/udp/icmp
        :type       protocol: ``str``

        :rtype: ``bool``
        """

        params = self._get_common_security_group_params(id,
                                                        protocol,
                                                        from_port,
                                                        to_port,
                                                        cidr_ips,
                                                        group_pairs)

        params["Action"] = 'AuthorizeSecurityGroupEgress'

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_revoke_security_group_ingress(self, id, from_port, to_port,
                                         cidr_ips=None, group_pairs=None,
                                         protocol='tcp'):
        """
        Edit a Security Group to revoke specific ingress traffic using
        CIDR blocks or either a group ID, group name or user ID (account).

        :param      id: The id of the security group to edit
        :type       id: ``str``

        :param      from_port: The beginning of the port range to open
        :type       from_port: ``int``

        :param      to_port: The end of the port range to open
        :type       to_port: ``int``

        :param      cidr_ips: The list of ip ranges to allow traffic for.
        :type       cidr_ips: ``list``

        :param      group_pairs: Source user/group pairs to allow traffic for.
                    More info can be found at http://goo.gl/stBHJF

                    EC2 Classic Example: To allow access from any system
                    associated with the default group on account 1234567890

                    [{'group_name': 'default', 'user_id': '1234567890'}]

                    VPC Example: Allow access from any system associated with
                    security group sg-47ad482e on your own account

                    [{'group_id': ' sg-47ad482e'}]
        :type       group_pairs: ``list`` of ``dict``

        :param      protocol: tcp/udp/icmp
        :type       protocol: ``str``

        :rtype: ``bool``
        """

        params = self._get_common_security_group_params(id,
                                                        protocol,
                                                        from_port,
                                                        to_port,
                                                        cidr_ips,
                                                        group_pairs)

        params["Action"] = 'RevokeSecurityGroupIngress'

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_revoke_security_group_egress(self, id, from_port, to_port,
                                        cidr_ips=None, group_pairs=None,
                                        protocol='tcp'):
        """
        Edit a Security Group to revoke specific egress traffic using
        CIDR blocks or either a group ID, group name or user ID (account).
        This call is not supported for EC2 classic and only works for
        VPC groups.

        :param      id: The id of the security group to edit
        :type       id: ``str``

        :param      from_port: The beginning of the port range to open
        :type       from_port: ``int``

        :param      to_port: The end of the port range to open
        :type       to_port: ``int``

        :param      cidr_ips: The list of ip ranges to allow traffic for.
        :type       cidr_ips: ``list``

        :param      group_pairs: Source user/group pairs to allow traffic for.
                    More info can be found at http://goo.gl/stBHJF

                    EC2 Classic Example: To allow access from any system
                    associated with the default group on account 1234567890

                    [{'group_name': 'default', 'user_id': '1234567890'}]

                    VPC Example: Allow access from any system associated with
                    security group sg-47ad482e on your own account

                    [{'group_id': ' sg-47ad482e'}]
        :type       group_pairs: ``list`` of ``dict``

        :param      protocol: tcp/udp/icmp
        :type       protocol: ``str``

        :rtype: ``bool``
        """

        params = self._get_common_security_group_params(id,
                                                        protocol,
                                                        from_port,
                                                        to_port,
                                                        cidr_ips,
                                                        group_pairs)

        params['Action'] = 'RevokeSecurityGroupEgress'

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

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

        result = self.connection.request(self.path, params=params).object

        return self._get_resource_tags(result)

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

    def ex_allocate_address(self, domain='standard'):
        """
        Allocate a new Elastic IP address for EC2 classic or VPC

        :param      domain: The domain to allocate the new address in
                            (standard/vpc)
        :type       domain: ``str``

        :return:    Instance of ElasticIP
        :rtype:     :class:`ElasticIP`
        """
        params = {'Action': 'AllocateAddress'}

        if domain == 'vpc':
            params['Domain'] = domain

        response = self.connection.request(self.path, params=params).object

        return self._to_address(response, only_associated=False)

    def ex_release_address(self, elastic_ip, domain=None):
        """
        Release an Elastic IP address using the IP (EC2-Classic) or
        using the allocation ID (VPC)

        :param      elastic_ip: Elastic IP instance
        :type       elastic_ip: :class:`ElasticIP`

        :param      domain: The domain where the IP resides (vpc only)
        :type       domain: ``str``

        :return:    True on success, False otherwise.
        :rtype:     ``bool``
        """
        params = {'Action': 'ReleaseAddress'}

        if domain is not None and domain != 'vpc':
            raise AttributeError('Domain can only be set to vpc')

        if domain is None:
            params['PublicIp'] = elastic_ip.ip
        else:
            params['AllocationId'] = elastic_ip.extra['allocation_id']

        response = self.connection.request(self.path, params=params).object
        return self._get_boolean(response)

    def ex_describe_all_addresses(self, only_associated=False):
        """
        Return all the Elastic IP addresses for this account
        optionally, return only addresses associated with nodes

        :param    only_associated: If true, return only those addresses
                                   that are associated with an instance.
        :type     only_associated: ``bool``

        :return:  List of ElasticIP instances.
        :rtype:   ``list`` of :class:`ElasticIP`
        """
        params = {'Action': 'DescribeAddresses'}

        response = self.connection.request(self.path, params=params).object

        # We will send our only_associated boolean over to
        # shape how the return data is sent back
        return self._to_addresses(response, only_associated)

    def ex_associate_address_with_node(self, node, elastic_ip, domain=None):
        """
        Associate an Elastic IP address with a particular node.

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      elastic_ip: Elastic IP instance
        :type       elastic_ip: :class:`ElasticIP`

        :param      domain: The domain where the IP resides (vpc only)
        :type       domain: ``str``

        :return:    A string representation of the association ID which is
                    required for VPC disassociation. EC2/standard
                    addresses return None
        :rtype:     ``None`` or ``str``
        """
        params = {'Action': 'AssociateAddress', 'InstanceId': node.id}

        if domain is not None and domain != 'vpc':
            raise AttributeError('Domain can only be set to vpc')

        if domain is None:
            params.update({'PublicIp': elastic_ip.ip})
        else:
            params.update({'AllocationId': elastic_ip.extra['allocation_id']})

        response = self.connection.request(self.path, params=params).object
        association_id = findtext(element=response,
                                  xpath='associationId',
                                  namespace=NAMESPACE)
        return association_id

    def ex_associate_addresses(self, node, elastic_ip, domain=None):
        """
        Note: This method has been deprecated in favor of
        the ex_associate_address_with_node method.
        """

        return self.ex_associate_address_with_node(node=node,
                                                   elastic_ip=elastic_ip,
                                                   domain=domain)

    def ex_disassociate_address(self, elastic_ip, domain=None):
        """
        Disassociate an Elastic IP address using the IP (EC2-Classic)
        or the association ID (VPC)

        :param      elastic_ip: ElasticIP instance
        :type       elastic_ip: :class:`ElasticIP`

        :param      domain: The domain where the IP resides (vpc only)
        :type       domain: ``str``

        :return:    True on success, False otherwise.
        :rtype:     ``bool``
        """
        params = {'Action': 'DisassociateAddress'}

        if domain is not None and domain != 'vpc':
            raise AttributeError('Domain can only be set to vpc')

        if domain is None:
            params['PublicIp'] = elastic_ip.ip

        else:
            params['AssociationId'] = elastic_ip.extra['association_id']

        res = self.connection.request(self.path, params=params).object
        return self._get_boolean(res)

    def ex_describe_addresses(self, nodes):
        """
        Return Elastic IP addresses for all the nodes in the provided list.

        :param      nodes: List of :class:`Node` instances
        :type       nodes: ``list`` of :class:`Node`

        :return:    Dictionary where a key is a node ID and the value is a
                    list with the Elastic IP addresses associated with
                    this node.
        :rtype:     ``dict``
        """
        if not nodes:
            return {}

        params = {'Action': 'DescribeAddresses'}

        if len(nodes) == 1:
            self._add_instance_filter(params, nodes[0])

        result = self.connection.request(self.path, params=params).object

        node_instance_ids = [node.id for node in nodes]
        nodes_elastic_ip_mappings = {}

        # We will set only_associated to True so that we only get back
        # IPs which are associated with instances
        only_associated = True

        for node_id in node_instance_ids:
            nodes_elastic_ip_mappings.setdefault(node_id, [])
            for addr in self._to_addresses(result,
                                           only_associated):

                instance_id = addr.instance_id

                if node_id == instance_id:
                    nodes_elastic_ip_mappings[instance_id].append(
                        addr.ip)

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

    # Network interface management methods

    def ex_list_network_interfaces(self):
        """
        Return all network interfaces

        :return:    List of EC2NetworkInterface instances
        :rtype:     ``list`` of :class `EC2NetworkInterface`
        """
        params = {'Action': 'DescribeNetworkInterfaces'}

        return self._to_interfaces(
            self.connection.request(self.path, params=params).object
        )

    def ex_create_network_interface(self, subnet, name=None,
                                    description=None,
                                    private_ip_address=None):
        """
        Create a network interface within a VPC subnet.

        :param      node: EC2NetworkSubnet instance
        :type       node: :class:`EC2NetworkSubnet`

        :param      name:  Optional name of the interface
        :type       name:  ``str``

        :param      description:  Optional description of the network interface
        :type       description:  ``str``

        :param      private_ip_address: Optional address to assign as the
                                        primary private IP address of the
                                        interface. If one is not provided then
                                        Amazon will automatically auto-assign
                                        an available IP. EC2 allows assignment
                                        of multiple IPs, but this will be
                                        the primary.
        :type       private_ip_address: ``str``

        :return:    EC2NetworkInterface instance
        :rtype:     :class `EC2NetworkInterface`
        """
        params = {'Action': 'CreateNetworkInterface',
                  'SubnetId': subnet.id}

        if description:
            params['Description'] = description

        if private_ip_address:
            params['PrivateIpAddress'] = private_ip_address

        response = self.connection.request(self.path, params=params).object

        element = response.findall(fixxpath(xpath='networkInterface',
                                            namespace=NAMESPACE))[0]

        interface = self._to_interface(element, name)

        if name is not None:
            tags = {'Name': name}
            self.ex_create_tags(resource=interface, tags=tags)

        return interface

    def ex_delete_network_interface(self, network_interface):
        """
        Deletes a network interface.

        :param      network_interface: EC2NetworkInterface instance
        :type       network_interface: :class:`EC2NetworkInterface`

        :rtype:     ``bool``
        """
        params = {'Action': 'DeleteNetworkInterface',
                  'NetworkInterfaceId': network_interface.id}

        result = self.connection.request(self.path, params=params).object
        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)

        return element == 'true'

    def ex_attach_network_interface_to_node(self, network_interface,
                                            node, device_index):
        """
        Attatch a network interface to an instance.

        :param      network_interface: EC2NetworkInterface instance
        :type       network_interface: :class:`EC2NetworkInterface`

        :param      node: Node instance
        :type       node: :class:`Node`

        :param      device_index: The interface device index
        :type       device_index: ``int``

        :return:    String representation of the attachment id.
                    This is required to detach the interface.
        :rtype:     ``str``
        """
        params = {'Action': 'AttachNetworkInterface',
                  'NetworkInterfaceId': network_interface.id,
                  'InstanceId': node.id,
                  'DeviceIndex': device_index}

        response = self.connection.request(self.path, params=params).object
        attachment_id = findattr(element=response, xpath='attachmentId',
                                 namespace=NAMESPACE)

        return attachment_id

    def ex_detach_network_interface(self, attachment_id, force=False):
        """
        Detatch a network interface from an instance.

        :param      attachment_id: The attachment ID associated with the
                                   interface
        :type       attachment_id: ``str``

        :param      force: Forces the detachment.
        :type       force: ``bool``

        :return:    ``True`` on successful detachment, ``False`` otherwise.
        :rtype:     ``bool``
        """
        params = {'Action': 'DetachNetworkInterface',
                  'AttachmentId': attachment_id}

        if force:
            params['Force'] = True

        result = self.connection.request(self.path, params=params).object

        element = findtext(element=result, xpath='return',
                           namespace=NAMESPACE)
        return element == 'true'

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

    def ex_get_console_output(self, node):
        """
        Get console output for the node.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :return:    Dictionary with the following keys:
                    - instance_id (``str``)
                    - timestamp (``datetime.datetime``) - ts of the last output
                    - output (``str``) - console output
        :rtype:     ``dict``
        """
        params = {
            'Action': 'GetConsoleOutput',
            'InstanceId': node.id
        }

        response = self.connection.request(self.path, params=params).object

        timestamp = findattr(element=response,
                             xpath='timestamp',
                             namespace=NAMESPACE)

        encoded_string = findattr(element=response,
                                  xpath='output',
                                  namespace=NAMESPACE)

        timestamp = parse_date(timestamp)
        output = base64.b64decode(b(encoded_string)).decode('utf-8')

        return {'instance_id': node.id,
                'timestamp': timestamp,
                'output': output}

    def ex_list_reserved_nodes(self):
        """
        List all reserved instances/nodes which can be purchased from Amazon
        for one or three year terms. Reservations are made at a region level
        and reduce the hourly charge for instances.

        More information can be found at http://goo.gl/ulXCC7.

        :rtype: ``list`` of :class:`.EC2ReservedNode`
        """
        params = {'Action': 'DescribeReservedInstances'}

        response = self.connection.request(self.path, params=params).object

        return self._to_reserved_nodes(response, 'reservedInstancesSet/item')

    # Account specific methods

    def ex_get_limits(self):
        """
        Retrieve account resource limits.

        :rtype: ``dict``
        """
        attributes = ['max-instances', 'max-elastic-ips',
                      'vpc-max-elastic-ips']
        params = {}
        params['Action'] = 'DescribeAccountAttributes'

        for index, attribute in enumerate(attributes):
            params['AttributeName.%s' % (index)] = attribute

        response = self.connection.request(self.path, params=params)
        data = response.object

        elems = data.findall(fixxpath(xpath='accountAttributeSet/item',
                                      namespace=NAMESPACE))

        result = {'resource': {}}

        for elem in elems:
            name = findtext(element=elem, xpath='attributeName',
                            namespace=NAMESPACE)
            value = findtext(element=elem,
                             xpath='attributeValueSet/item/attributeValue',
                             namespace=NAMESPACE)

            result['resource'][name] = int(value)

        return result

    # Deprecated extension methods

    def ex_list_keypairs(self):
        """
        Lists all the keypair names and fingerprints.

        :rtype: ``list`` of ``dict``
        """
        warnings.warn('This method has been deprecated in favor of '
                      'list_key_pairs method')

        key_pairs = self.list_key_pairs()

        result = []

        for key_pair in key_pairs:
            item = {
                'keyName': key_pair.name,
                'keyFingerprint': key_pair.fingerprint,
            }
            result.append(item)

        return result

    def ex_describe_all_keypairs(self):
        """
        Return names for all the available key pairs.

        @note: This is a non-standard extension API, and only works for EC2.

        :rtype: ``list`` of ``str``
        """
        names = [key_pair.name for key_pair in self.list_key_pairs()]
        return names

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

    def ex_create_keypair(self, name):
        """
        Creates a new keypair

        @note: This is a non-standard extension API, and only works for EC2.

        :param      name: The name of the keypair to Create. This must be
            unique, otherwise an InvalidKeyPair.Duplicate exception is raised.
        :type       name: ``str``

        :rtype: ``dict``
        """
        warnings.warn('This method has been deprecated in favor of '
                      'create_key_pair method')

        key_pair = self.create_key_pair(name=name)

        result = {
            'keyMaterial': key_pair.private_key,
            'keyFingerprint': key_pair.fingerprint
        }

        return result

    def ex_delete_keypair(self, keypair):
        """
        Delete a key pair by name.

        @note: This is a non-standard extension API, and only works with EC2.

        :param      keypair: The name of the keypair to delete.
        :type       keypair: ``str``

        :rtype: ``bool``
        """
        warnings.warn('This method has been deprecated in favor of '
                      'delete_key_pair method')

        keypair = KeyPair(name=keypair, public_key=None, fingerprint=None,
                          driver=self)

        return self.delete_key_pair(keypair)

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
        warnings.warn('This method has been deprecated in favor of '
                      'import_key_pair_from_string method')

        key_pair = self.import_key_pair_from_string(name=name,
                                                    key_material=key_material)

        result = {
            'keyName': key_pair.name,
            'keyFingerprint': key_pair.fingerprint
        }
        return result

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
        warnings.warn('This method has been deprecated in favor of '
                      'import_key_pair_from_file method')

        key_pair = self.import_key_pair_from_file(name=name,
                                                  key_file_path=keyfile)

        result = {
            'keyName': key_pair.name,
            'keyFingerprint': key_pair.fingerprint
        }
        return result

    def ex_find_or_import_keypair_by_key_material(self, pubkey):
        """
        Given a public key, look it up in the EC2 KeyPair database. If it
        exists, return any information we have about it. Otherwise, create it.

        Keys that are created are named based on their comment and fingerprint.

        :rtype: ``dict``
        """
        key_fingerprint = get_pubkey_ssh2_fingerprint(pubkey)
        key_comment = get_pubkey_comment(pubkey, default='unnamed')
        key_name = '%s-%s' % (key_comment, key_fingerprint)

        key_pairs = self.list_key_pairs()
        key_pairs = [key_pair for key_pair in key_pairs if
                     key_pair.fingerprint == key_fingerprint]

        if len(key_pairs) >= 1:
            key_pair = key_pairs[0]
            result = {
                'keyName': key_pair.name,
                'keyFingerprint': key_pair.fingerprint
            }
        else:
            result = self.ex_import_keypair_from_string(key_name, pubkey)

        return result

    def _to_nodes(self, object, xpath):
        return [self._to_node(el)
                for el in object.findall(fixxpath(xpath=xpath,
                                                  namespace=NAMESPACE))]

    def _to_node(self, element):
        try:
            state = self.NODE_STATE_MAP[findattr(element=element,
                                                 xpath="instanceState/name",
                                                 namespace=NAMESPACE)
                                        ]
        except KeyError:
            state = NodeState.UNKNOWN

        instance_id = findtext(element=element, xpath='instanceId',
                               namespace=NAMESPACE)
        public_ip = findtext(element=element, xpath='ipAddress',
                             namespace=NAMESPACE)
        public_ips = [public_ip] if public_ip else []
        private_ip = findtext(element=element, xpath='privateIpAddress',
                              namespace=NAMESPACE)
        private_ips = [private_ip] if private_ip else []
        product_codes = []
        for p in findall(element=element,
                         xpath="productCodesSet/item/productCode",
                         namespace=NAMESPACE):
            product_codes.append(p)

        # Get our tags
        tags = self._get_resource_tags(element)
        name = tags.get('Name', instance_id)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['node'])

        # Add additional properties to our extra dictionary
        extra['block_device_mapping'] = self._to_device_mappings(element)
        extra['groups'] = self._get_security_groups(element)
        extra['network_interfaces'] = self._to_interfaces(element)
        extra['product_codes'] = product_codes
        extra['tags'] = tags

        return Node(id=instance_id, name=name, state=state,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self.connection.driver, extra=extra)

    def _to_images(self, object):
        return [self._to_image(el) for el in object.findall(
            fixxpath(xpath='imagesSet/item', namespace=NAMESPACE))
        ]

    def _to_image(self, element):

        id = findtext(element=element, xpath='imageId', namespace=NAMESPACE)
        name = findtext(element=element, xpath='name', namespace=NAMESPACE)

        # Build block device mapping
        block_device_mapping = self._to_device_mappings(element)

        # Get our tags
        tags = self._get_resource_tags(element)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['image'])

        # Add our tags and block device mapping
        extra['tags'] = tags
        extra['block_device_mapping'] = block_device_mapping

        return NodeImage(id=id, name=name, driver=self, extra=extra)

    def _to_volume(self, element, name=None):
        """
        Parse the XML element and return a StorageVolume object.

        :param      name: An optional name for the volume. If not provided
                          then either tag with a key "Name" or volume ID
                          will be used (which ever is available first in that
                          order).
        :type       name: ``str``

        :rtype:     :class:`StorageVolume`
        """
        volId = findtext(element=element, xpath='volumeId',
                         namespace=NAMESPACE)
        size = findtext(element=element, xpath='size', namespace=NAMESPACE)

        # Get our tags
        tags = self._get_resource_tags(element)

        # If name was not passed into the method then
        # fall back then use the volume id
        name = name if name else tags.get('Name', volId)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['volume'])

        return StorageVolume(id=volId,
                             name=name,
                             size=int(size),
                             driver=self,
                             extra=extra)

    def _to_snapshots(self, response):
        return [self._to_snapshot(el) for el in response.findall(
            fixxpath(xpath='snapshotSet/item', namespace=NAMESPACE))
        ]

    def _to_snapshot(self, element, name=None):
        snapId = findtext(element=element, xpath='snapshotId',
                          namespace=NAMESPACE)
        size = findtext(element=element, xpath='volumeSize',
                        namespace=NAMESPACE)

        # Get our tags
        tags = self._get_resource_tags(element)

        # If name was not passed into the method then
        # fall back then use the snapshot id
        name = name if name else tags.get('Name', snapId)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['snapshot'])

        # Add tags and name to the extra dict
        extra['tags'] = tags
        extra['name'] = name

        return VolumeSnapshot(snapId, size=int(size),
                              driver=self, extra=extra)

    def _to_key_pairs(self, elems):
        key_pairs = [self._to_key_pair(elem=elem) for elem in elems]
        return key_pairs

    def _to_key_pair(self, elem):
        name = findtext(element=elem, xpath='keyName', namespace=NAMESPACE)
        fingerprint = findtext(element=elem, xpath='keyFingerprint',
                               namespace=NAMESPACE).strip()
        private_key = findtext(element=elem, xpath='keyMaterial',
                               namespace=NAMESPACE)

        key_pair = KeyPair(name=name,
                           public_key=None,
                           fingerprint=fingerprint,
                           private_key=private_key,
                           driver=self)
        return key_pair

    def _to_networks(self, response):
        return [self._to_network(el) for el in response.findall(
            fixxpath(xpath='vpcSet/item', namespace=NAMESPACE))
        ]

    def _to_network(self, element):
        # Get the network id
        vpc_id = findtext(element=element,
                          xpath='vpcId',
                          namespace=NAMESPACE)

        # Get our tags
        tags = self._get_resource_tags(element)

        # Set our name if the Name key/value if available
        # If we don't get anything back then use the vpc_id
        name = tags.get('Name', vpc_id)

        cidr_block = findtext(element=element,
                              xpath='cidrBlock',
                              namespace=NAMESPACE)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['network'])

        # Add tags to the extra dict
        extra['tags'] = tags

        return EC2Network(vpc_id, name, cidr_block, extra=extra)

    def _to_addresses(self, response, only_associated):
        """
        Builds a list of dictionaries containing elastic IP properties.

        :param    only_associated: If true, return only those addresses
                                   that are associated with an instance.
                                   If false, return all addresses.
        :type     only_associated: ``bool``

        :rtype:   ``list`` of :class:`ElasticIP`
        """
        addresses = []
        for el in response.findall(fixxpath(xpath='addressesSet/item',
                                            namespace=NAMESPACE)):
            addr = self._to_address(el, only_associated)
            if addr is not None:
                addresses.append(addr)

        return addresses

    def _to_address(self, element, only_associated):
        instance_id = findtext(element=element, xpath='instanceId',
                               namespace=NAMESPACE)

        public_ip = findtext(element=element,
                             xpath='publicIp',
                             namespace=NAMESPACE)

        domain = findtext(element=element,
                          xpath='domain',
                          namespace=NAMESPACE)

        # Build our extra dict
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['elastic_ip'])

        # Return NoneType if only associated IPs are requested
        if only_associated and not instance_id:
            return None

        return ElasticIP(public_ip, domain, instance_id, extra=extra)

    def _to_subnets(self, response):
        return [self._to_subnet(el) for el in response.findall(
            fixxpath(xpath='subnetSet/item', namespace=NAMESPACE))
        ]

    def _to_subnet(self, element):
        # Get the subnet ID
        subnet_id = findtext(element=element,
                             xpath='subnetId',
                             namespace=NAMESPACE)

        # Get our tags
        tags = self._get_resource_tags(element)

        # If we don't get anything back then use the subnet_id
        name = tags.get('Name', subnet_id)

        state = findtext(element=element,
                         xpath='state',
                         namespace=NAMESPACE)

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['subnet'])

        # Also include our tags
        extra['tags'] = tags

        return EC2NetworkSubnet(subnet_id, name, state, extra=extra)

    def _to_interfaces(self, response):
        return [self._to_interface(el) for el in response.findall(
            fixxpath(xpath='networkInterfaceSet/item', namespace=NAMESPACE))
        ]

    def _to_interface(self, element, name=None):
        """
        Parse the XML element and return a EC2NetworkInterface object.

        :param      name: An optional name for the interface. If not provided
                          then either tag with a key "Name" or the interface ID
                          will be used (whichever is available first in that
                          order).
        :type       name: ``str``

        :rtype:     :class: `EC2NetworkInterface`
        """

        interface_id = findtext(element=element,
                                xpath='networkInterfaceId',
                                namespace=NAMESPACE)

        state = findtext(element=element,
                         xpath='status',
                         namespace=NAMESPACE)

        # Get tags
        tags = self._get_resource_tags(element)

        name = name if name else tags.get('Name', interface_id)

        # Build security groups
        groups = self._get_security_groups(element)

        # Build private IPs
        priv_ips = []
        for item in findall(element=element,
                            xpath='privateIpAddressesSet/item',
                            namespace=NAMESPACE):

            priv_ips.append({'private_ip': findtext(element=item,
                                                    xpath='privateIpAddress',
                                                    namespace=NAMESPACE),
                            'private_dns': findtext(element=item,
                                                    xpath='privateDnsName',
                                                    namespace=NAMESPACE),
                            'primary': findtext(element=item,
                                                xpath='primary',
                                                namespace=NAMESPACE)})

        # Build our attachment dictionary which we will add into extra later
        attributes_map = \
            RESOURCE_EXTRA_ATTRIBUTES_MAP['network_interface_attachment']
        attachment = self._get_extra_dict(element, attributes_map)

        # Build our extra dict
        attributes_map = RESOURCE_EXTRA_ATTRIBUTES_MAP['network_interface']
        extra = self._get_extra_dict(element, attributes_map)

        # Include our previously built items as well
        extra['tags'] = tags
        extra['attachment'] = attachment
        extra['private_ips'] = priv_ips
        extra['groups'] = groups

        return EC2NetworkInterface(interface_id, name, state, extra=extra)

    def _to_reserved_nodes(self, object, xpath):
        return [self._to_reserved_node(el)
                for el in object.findall(fixxpath(xpath=xpath,
                                                  namespace=NAMESPACE))]

    def _to_reserved_node(self, element):
        """
        Build an EC2ReservedNode object using the reserved instance properties.
        Information on these properties can be found at http://goo.gl/ulXCC7.
        """

        # Get our extra dictionary
        extra = self._get_extra_dict(
            element, RESOURCE_EXTRA_ATTRIBUTES_MAP['reserved_node'])

        try:
            size = [size for size in self.list_sizes() if
                    size.id == extra['instance_type']][0]
        except IndexError:
            size = None

        return EC2ReservedNode(id=findtext(element=element,
                                           xpath='reservedInstancesId',
                                           namespace=NAMESPACE),
                               state=findattr(element=element,
                                              xpath='state',
                                              namespace=NAMESPACE),
                               driver=self,
                               size=size,
                               extra=extra)

    def _to_device_mappings(self, object):
        return [self._to_device_mapping(el) for el in object.findall(
            fixxpath(xpath='blockDeviceMapping/item', namespace=NAMESPACE))
        ]

    def _to_device_mapping(self, element):
        """
        Parse the XML element and return a dictionary of device properties.
        Additional information can be found at http://goo.gl/GjWYBf.

        @note: EBS volumes do not have a virtual name. Only ephemeral
               disks use this property.
        :rtype:     ``dict``
        """
        mapping = {}

        mapping['device_name'] = findattr(element=element,
                                          xpath='deviceName',
                                          namespace=NAMESPACE)

        mapping['virtual_name'] = findattr(element=element,
                                           xpath='virtualName',
                                           namespace=NAMESPACE)

        # If virtual name does not exist then this is an EBS volume.
        # Build the EBS dictionary leveraging the _get_extra_dict method.
        if mapping['virtual_name'] is None:
            mapping['ebs'] = self._get_extra_dict(
                element, RESOURCE_EXTRA_ATTRIBUTES_MAP['ebs_volume'])

        return mapping

    def _pathlist(self, key, arr):
        """
        Converts a key and an array of values into AWS query param format.
        """
        params = {}
        i = 0

        for value in arr:
            i += 1
            params['%s.%s' % (key, i)] = value

        return params

    def _get_boolean(self, element):
        tag = '{%s}%s' % (NAMESPACE, 'return')
        return element.findtext(tag) == 'true'

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([term_status == status
                    for term_status
                    in ('shutting-down', 'terminated')])

    def _add_instance_filter(self, params, node):
        """
        Add instance filter to the provided params dictionary.
        """
        params.update({
            'Filter.0.Name': 'instance-id',
            'Filter.0.Value.0': node.id
        })

        return params

    def _get_state_boolean(self, element):
        """
        Checks for the instances's state
        """
        state = findall(element=element,
                        xpath='instancesSet/item/currentState/name',
                        namespace=NAMESPACE)[0].text

        return state in ('stopping', 'pending', 'starting')

    def _get_extra_dict(self, element, mapping):
        """
        Extract attributes from the element based on rules provided in the
        mapping dictionary.

        :param      element: Element to parse the values from.
        :type       element: xml.etree.ElementTree.Element.

        :param      mapping: Dictionary with the extra layout
        :type       node: :class:`Node`

        :rtype: ``dict``
        """
        extra = {}
        for attribute, values in mapping.items():
            transform_func = values['transform_func']
            value = findattr(element=element,
                             xpath=values['xpath'],
                             namespace=NAMESPACE)

            if value is not None:
                extra[attribute] = transform_func(value)
            else:
                extra[attribute] = None

        return extra

    def _get_resource_tags(self, element):
        """
        Parse tags from the provided element and return a dictionary with
        key/value pairs.

        :rtype: ``dict``
        """
        tags = {}

        # Get our tag set by parsing the element
        tag_set = findall(element=element,
                          xpath='tagSet/item',
                          namespace=NAMESPACE)

        for tag in tag_set:
            key = findtext(element=tag,
                           xpath='key',
                           namespace=NAMESPACE)

            value = findtext(element=tag,
                             xpath='value',
                             namespace=NAMESPACE)

            tags[key] = value

        return tags

    def _get_block_device_mapping_params(self, block_device_mapping):
        """
        Return a list of dictionaries with query parameters for
        a valid block device mapping.

        :param      mapping: List of dictionaries with the drive layout
        :type       mapping: ``list`` or ``dict``

        :return:    Dictionary representation of the drive mapping
        :rtype:     ``dict``
        """

        if not isinstance(block_device_mapping, (list, tuple)):
            raise AttributeError(
                'block_device_mapping not list or tuple')

        params = {}

        for idx, mapping in enumerate(block_device_mapping):
            idx += 1  # We want 1-based indexes
            if not isinstance(mapping, dict):
                raise AttributeError(
                    'mapping %s in block_device_mapping '
                    'not a dict' % mapping)
            for k, v in mapping.items():
                if not isinstance(v, dict):
                    params['BlockDeviceMapping.%d.%s' % (idx, k)] = str(v)
                else:
                    for key, value in v.items():
                        params['BlockDeviceMapping.%d.%s.%s'
                               % (idx, k, key)] = str(value)
        return params

    def _get_common_security_group_params(self, group_id, protocol,
                                          from_port, to_port, cidr_ips,
                                          group_pairs):
        """
        Return a dictionary with common query parameters which are used when
        operating on security groups.

        :rtype: ``dict``
        """
        params = {'GroupId': id,
                  'IpPermissions.1.IpProtocol': protocol,
                  'IpPermissions.1.FromPort': from_port,
                  'IpPermissions.1.ToPort': to_port}

        if cidr_ips is not None:
            ip_ranges = {}
            for index, cidr_ip in enumerate(cidr_ips):
                index += 1

                ip_ranges['IpPermissions.1.IpRanges.%s.CidrIp'
                          % (index)] = cidr_ip

            params.update(ip_ranges)

        if group_pairs is not None:
            user_groups = {}
            for index, group_pair in enumerate(group_pairs):
                index += 1

                if 'group_id' in group_pair.keys():
                    user_groups['IpPermissions.1.Groups.%s.GroupId'
                                % (index)] = group_pair['group_id']

                if 'group_name' in group_pair.keys():
                    user_groups['IpPermissions.1.Groups.%s.GroupName'
                                % (index)] = group_pair['group_name']

                if 'user_id' in group_pair.keys():
                    user_groups['IpPermissions.1.Groups.%s.UserId'
                                % (index)] = group_pair['user_id']

            params.update(user_groups)

        return params

    def _get_security_groups(self, element):
        """
        Parse security groups from the provided element and return a
        list of security groups with the id ane name key/value pairs.

        :rtype: ``list`` of ``dict``
        """
        groups = []

        for item in findall(element=element,
                            xpath='groupSet/item',
                            namespace=NAMESPACE):
            groups.append({
                'group_id':   findtext(element=item,
                                       xpath='groupId',
                                       namespace=NAMESPACE),
                'group_name': findtext(element=item,
                                       xpath='groupName',
                                       namespace=NAMESPACE)
            })

        return groups


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
            path = '/services/Eucalyptus'
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
        Nimbus doesn't support elastic IPs, so this is a pass-through.

        @inherits: :class:`EC2NodeDriver.ex_describe_addresses`
        """
        nodes_elastic_ip_mappings = {}
        for node in nodes:
            # empty list per node
            nodes_elastic_ip_mappings[node.id] = []
        return nodes_elastic_ip_mappings

    def ex_create_tags(self, resource, tags):
        """
        Nimbus doesn't support creating tags, so this is a pass-through.

        @inherits: :class:`EC2NodeDriver.ex_create_tags`
        """
        pass
