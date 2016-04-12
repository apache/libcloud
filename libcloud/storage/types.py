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

from libcloud.common.types import LibcloudError

__all__ = [
    'Provider',
    'ContainerError',
    'ObjectError',
    'ContainerAlreadyExistsError',
    'ContainerDoesNotExistError',
    'ContainerIsNotEmptyError',
    'ObjectDoesNotExistError',
    'ObjectHashMismatchError',
    'InvalidContainerNameError',

    'OLD_CONSTANT_TO_NEW_MAPPING'
]


class Provider(object):
    """
    Defines for each of the supported providers

    :cvar DUMMY: Example provider
    :cvar CLOUDFILES: CloudFiles
    :cvar S3: Amazon S3 US
    :cvar S3_US_WEST: Amazon S3 US West (Northern California)
    :cvar S3_EU_WEST: Amazon S3 EU West (Ireland)
    :cvar S3_AP_SOUTHEAST_HOST: Amazon S3 Asia South East (Singapore)
    :cvar S3_AP_NORTHEAST_HOST: Amazon S3 Asia South East (Tokyo)
    :cvar S3_RGW_OUTSCALE: OUTSCALE RGW S3
    :cvar NINEFOLD: Ninefold
    :cvar GOOGLE_STORAGE Google Storage
    :cvar S3_US_WEST_OREGON: Amazon S3 US West 2 (Oregon)
    :cvar NIMBUS: Nimbus.io driver
    :cvar LOCAL: Local storage driver
    :cvar AURORAOBJECTS: AuroraObjects storage driver
    :cvar ALIYUN_OSS: Aliyun OSS storage driver
    """
    DUMMY = 'dummy'
    S3 = 's3'
    S3_US_WEST = 's3_us_west'
    S3_EU_WEST = 's3_eu_west'
    S3_AP_SOUTHEAST = 's3_ap_southeast'
    S3_AP_NORTHEAST = 's3_ap_northeast'
    S3_AP_NORTHEAST1 = 's3_ap_northeast_1'
    S3_AP_NORTHEAST2 = 's3_ap_northeast_2'
    S3_SA_EAST = 's3_sa_east'
    S3_RGW_OUTSCALE = 's3_rgw_outscale'
    NINEFOLD = 'ninefold'
    GOOGLE_STORAGE = 'google_storage'
    S3_US_WEST_OREGON = 's3_us_west_oregon'
    NIMBUS = 'nimbus'
    LOCAL = 'local'
    OPENSTACK_SWIFT = 'openstack_swift'
    CLOUDFILES = 'cloudfiles'
    AZURE_BLOBS = 'azure_blobs'
    KTUCLOUD = 'ktucloud'
    AURORAOBJECTS = 'auroraobjects'
    BACKBLAZE_B2 = 'backblaze_b2'
    ALIYUN_OSS = 'aliyun_oss'

    # Deperecated
    CLOUDFILES_US = 'cloudfiles_us'
    CLOUDFILES_UK = 'cloudfiles_uk'
    CLOUDFILES_SWIFT = 'cloudfiles_swift'


OLD_CONSTANT_TO_NEW_MAPPING = {
    # CloudFiles
    Provider.CLOUDFILES_US: Provider.CLOUDFILES,
    Provider.CLOUDFILES_UK: Provider.CLOUDFILES_UK,
    Provider.CLOUDFILES_SWIFT: Provider.OPENSTACK_SWIFT
}


class ContainerError(LibcloudError):
    error_type = 'ContainerError'

    def __init__(self, value, driver, container_name):
        self.container_name = container_name
        super(ContainerError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return ('<%s in %s, container=%s, value=%s>' %
                (self.error_type, repr(self.driver),
                 self.container_name, self.value))


class ObjectError(LibcloudError):
    error_type = 'ContainerError'

    def __init__(self, value, driver, object_name):
        self.object_name = object_name
        super(ObjectError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<%s in %s, value=%s, object = %s>' % (self.error_type,
                                                      repr(self.driver),
                                                      self.value,
                                                      self.object_name)


class ContainerAlreadyExistsError(ContainerError):
    error_type = 'ContainerAlreadyExistsError'


class ContainerDoesNotExistError(ContainerError):
    error_type = 'ContainerDoesNotExistError'


class ContainerIsNotEmptyError(ContainerError):
    error_type = 'ContainerIsNotEmptyError'


class ObjectDoesNotExistError(ObjectError):
    error_type = 'ObjectDoesNotExistError'


class ObjectHashMismatchError(ObjectError):
    error_type = 'ObjectHashMismatchError'


class InvalidContainerNameError(ContainerError):
    error_type = 'InvalidContainerNameError'
