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
from libcloud.common.aws import SignedAWSConnection
from libcloud.storage.drivers.s3 import BaseS3Connection
from libcloud.storage.drivers.s3 import BaseS3StorageDriver
from libcloud.storage.drivers.s3 import API_VERSION

__all__ = [
    "ScalewayStorageDriver"
]


class ScalewayConnectionAWS4(SignedAWSConnection, BaseS3Connection):
    service_name = 's3'
    version = API_VERSION

    def __init__(self, user_id, key, secure=True, host=None, port=None,
                 url=None, timeout=None, proxy_url=None, token=None,
                 retry_delay=None, backoff=None, **kwargs):

        super(ScalewayConnectionAWS4, self).__init__(user_id, key,
                                                  secure, host,
                                                  port, url,
                                                  timeout,
                                                  proxy_url, token,
                                                  retry_delay,
                                                  backoff,
                                                  4) # force aws4


class ScalewayStorageDriver(BaseS3StorageDriver):
    name = 'Scaleway Storage Driver'
    website = 'https://www.scaleway.com/en/object-storage/'
    connectionCls = ScalewayConnectionAWS4
    region_name = "fr-par"

    def __init__(self, key, secret=None, secure=True, host=None, port=None, url=None):
        if host is None:
            raise LibcloudError('host argument is required', driver=self)

        self.connectionCls.host = host

        super(ScalewayStorageDriver, self).__init__(key=key,
                                                 secret=secret,
                                                 secure=secure,
                                                 host=host,
                                                 port=port,
                                                 url=url)


class ScalewayFRParConnection(ScalewayConnectionAWS4):
    host = "s3.fr-par.scw.cloud"


class ScalewayFRParStorageDriver(ScalewayStorageDriver):
    name = 'Scaleway Storage Driver (fr-par)'
    connectionCls = ScalewayFRParConnection
    region_name = "fr-par"


class ScalewayNLAmsConnection(ScalewayConnectionAWS4):
    host = "s3.nl-ams.scw.cloud"


class ScalewayNLAmsStorageDriver(ScalewayStorageDriver):
    name = 'Scaleway Storage Driver (nl-ams)'
    connectionCls = ScalewayNLAmsConnection
    region_name = "nl-ams"


class ScalewayPLWawConnection(ScalewayConnectionAWS4):
    host = "s3.pl-waw.scw.cloud"


class ScalewayPLWawStorageDriver(ScalewayStorageDriver):
    name = 'Scaleway Storage Driver (pl-waw)'
    connectionCls = ScalewayPLWawConnection
    region_name = "pl-waw"
