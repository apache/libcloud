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

__all__ = ['Provider',
           'ContainerError',
           'ObjectError',
           'ContainerAlreadyExistsError',
           'ContainerDoesNotExistError',
           'ContainerIsNotEmptyError',
           'ObjectDoesNotExistError',
           'ObjectHashMismatchError',
           'InvalidContainerNameError']

class Provider(object):
    """
    Defines for each of the supported providers

    @cvar DUMMY: Example provider
    @cvar CLOUDFILES_US: CloudFiles US
    @cvar CLOUDFILES_UK: CloudFiles UK
    @cvar S3: Amazon S3 US
    @cvar S3_US_WEST: Amazon S3 US West (Northern California)
    @cvar S3_EU_WEST: Amazon S3 EU West (Ireland)
    @cvar S3_AP_SOUTHEAST_HOST: Amazon S3 Asia South East (Singapore)
    @cvar S3_AP_NORTHEAST_HOST: Amazon S3 Asia South East (Tokyo)
    @cvar NINEFOLD: Ninefold
    @cvar GOOGLE_STORAGE Google Storage
    @cvar: S3_US_WEST_OREGON: Amazon S3 US West 2 (Oregon)
    """
    DUMMY = 0
    CLOUDFILES_US = 1
    CLOUDFILES_UK = 2
    S3 = 3
    S3_US_WEST = 4
    S3_EU_WEST = 5
    S3_AP_SOUTHEAST = 6
    S3_AP_NORTHEAST = 7
    NINEFOLD = 8
    GOOGLE_STORAGE = 9
    S3_US_WEST_OREGON = 10

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
        return '<%s in %s, value=%s, object = %s>' % (self.error_type, repr(self.driver),
                                                      self.value, self.object_name)

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
