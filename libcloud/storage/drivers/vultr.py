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

from libcloud.utils.py3 import httplib

from libcloud.common.types import LibcloudError

from libcloud.storage.providers import Provider
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.drivers.s3 import BaseS3StorageDriver, BaseS3Connection

__all__ = [
    'VultrObjectStorageDriver'
]

VULTR_OBJECT_STORAGE_US_HOST = 'ewr1.vultrobjects.com'


class BaseVultrObjectConnection(BaseS3Connection):
    host = VULTR_OBJECT_STORAGE_US_HOST


class BaseVultrObjectStorageDriver(BaseS3StorageDriver):
    type = Provider.VULTR
    name = 'Vultr Object Storage'
    website = 'https://www.vultr.com/products/object-storage/'
    supports_s3_multipart_upload = False


class VultrObjectStorageDriver(BaseVultrObjectStorageDriver):
    connectionCls = BaseVultrObjectConnection

    def get_container_cdn_url(self, container):
        if self.connection.secure:
            protocol = 'https'
        else:
            protocol = 'http'

        cdn_host = self.connection.host
        cdn_path = self._get_container_path(container)

        cdn_url = '%s://%s%s/' % (protocol, cdn_host, cdn_path)

        response = self.connection.request(cdn_path, method='HEAD')

        if response.status == httplib.OK:
            return cdn_url
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(value='',
                                             container_name=container.name,
                                             driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_object_cdn_url(self, obj):
        container_cdn_url = self.get_container_cdn_url(container=obj.container)

        cdn_path = self._get_object_path(obj.container, obj.name)

        cdn_url = container_cdn_url + obj.name

        response = self.connection.request(cdn_path, method='HEAD')

        if response.status == httplib.OK:
            return cdn_url
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(value='',
                                          object_name=obj.name,
                                          driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status))
