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
HPCloud driver
"""
from libcloud.compute.providers import Provider
from libcloud.compute.drivers.openstack import (OpenStack_1_1_Connection,
                                                OpenStack_1_1_NodeDriver)
from libcloud.common.types import LibcloudError
from libcloud.compute.base import NodeAuthSSHKey

try:
        import simplejson as json
except ImportError:
        import json

class HPCloudConnection(OpenStack_1_1_Connection):
    get_endpoint_args = {}

    def get_endpoint(self):

        if not self.get_endpoint_args:
            raise LibcloudError(
                'HPCloudConnection must have get_endpoint_args set')

        # Only support auth 2.0_*
        if '2.0' in self._auth_version:
            ep = self.service_catalog.get_endpoint(**self.get_endpoint_args)
        else:
            raise LibcloudError(
                'Auth version "%s" not supported' % (self._auth_version))

        # It's possible to authenticate but the service catalog not have
        #the correct endpoint for this driver, so we throw here.
        if 'publicURL' in ep:
            return ep['publicURL']
        else:
            raise LibcloudError('Could not find specified endpoint')

class HPCloudAZ1Connection(HPCloudConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'Compute',
                         'region': 'az-1.region-a.geo-1'}


class HPCloudAZ2Connection(HPCloudConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'Compute',
                         'region': 'az-2.region-a.geo-1'}

class HPCloudNodeDriver(OpenStack_1_1_NodeDriver):
    website = 'http://www.hpcloud.com/'
    api_name = 'Compute'

    def ex_create_keypair(self, name):
        """ Non-standard API Extension
        """
        data = {'keypair': {'name': name}}
        uri = '/os-keypairs'
        resp = self.connection.request(uri, method='POST', data=data)
        body = json.loads(resp.body)
        return body

    def ex_delete_keypair(self, name):
        """ Non-standard API Extension
        """
        uri = '/os-keypairs/%s' % (name)
        return self.connection.request(uri, method='DELETE')

    def ex_list_keypairs(self):
        """ Non-standard API Extension
        """
        uri = '/os-keypairs'
        resp = self.connection.request(uri, method='GET')
        keys = json.loads(resp.body)["keypairs"]
        keypairs = [NodeAuthSSHKey(key["keypair"]["name"]) for key in keys]
        return keypairs

class HPCloudAZ1NodeDriver(HPCloudNodeDriver):
    name = 'HPCloudAZ1'
    connectionCls = HPCloudAZ1Connection
    type = Provider.HPCLOUD_AZ1

class HPCloudAZ2NodeDriver(HPCloudNodeDriver):
    name = 'HPCloudAZ2'
    connectionCls = HPCloudAZ2Connection
    type = Provider.HPCLOUD_AZ2
