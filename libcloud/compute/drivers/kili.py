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
HP Public cloud driver which is essentially just a small wrapper around
OpenStack driver.
"""

from libcloud.compute.types import Provider, LibcloudError
from libcloud.compute.drivers.openstack import OpenStack_1_1_Connection
from libcloud.compute.drivers.openstack import OpenStack_1_1_NodeDriver

__all__ = [
    'KiliCloudNodeDriver'
]

ENDPOINT_ARGS = {
    'service_type': 'compute',
    'name': 'nova',
    'region': 'RegionOne'
}

AUTH_URL = 'https://api.kili.io/keystone/v2.0/tokens'


class KiliCloudConnection(OpenStack_1_1_Connection):
    _auth_version = '2.0_password'

    def __init__(self, *args, **kwargs):
        self.region = kwargs.pop('region', None)
        self.get_endpoint_args = kwargs.pop('get_endpoint_args', None)
        super(KiliCloudConnection, self).__init__(*args, **kwargs)
        self._auth_version = KiliCloudConnection._auth_version

    def get_endpoint(self):
        if not self.get_endpoint_args:
            raise LibcloudError(
                'KiliCloudConnection must have get_endpoint_args set')

        if '2.0_password' in self._auth_version:
            ep = self.service_catalog.get_endpoint(**self.get_endpoint_args)
        else:
            raise LibcloudError(
                'Auth version "%s" not supported' % (self._auth_version))

        public_url = ep.url

        if not public_url:
            raise LibcloudError('Could not find specified endpoint')

        return public_url


class KiliCloudNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'Kili Public Cloud'
    website = 'http://kili.io/'
    connectionCls = KiliCloudConnection
    type = Provider.HPCLOUD

    def __init__(self, key, secret, tenant_name, secure=True,
                 host=None, port=None, **kwargs):
        """
        Note: tenant_name argument is required for Kili cloud.
        """
        self.tenant_name = tenant_name
        super(KiliCloudNodeDriver, self).__init__(key=key, secret=secret,
                                                  secure=secure, host=host,
                                                  port=port,
                                                  **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = self.openstack_connection_kwargs()
        kwargs['get_endpoint_args'] = ENDPOINT_ARGS
        kwargs['ex_force_auth_url'] = AUTH_URL
        kwargs['ex_tenant_name'] = self.tenant_name

        return kwargs
