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

from libcloud.storage.providers import Provider
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
