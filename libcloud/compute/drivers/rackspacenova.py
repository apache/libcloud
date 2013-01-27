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
Rackspace driver
"""
from libcloud.compute.providers import Provider
from libcloud.compute.drivers.openstack import OpenStack_1_1_Connection,\
    OpenStack_1_1_NodeDriver
from libcloud.common.types import LibcloudError


class RackspaceNovaConnection(OpenStack_1_1_Connection):
    get_endpoint_args = {}

    def get_endpoint(self):
        if not self.get_endpoint_args:
            raise LibcloudError(
                'RackspaceNovaConnection must have get_endpoint_args set')

        # Only support auth 2.0_*
        if '2.0' in self._auth_version:
            ep = self.service_catalog.get_endpoint(**self.get_endpoint_args)
        else:
            raise LibcloudError(
                'Auth version "%s" not supported' % (self._auth_version))

        # It's possible to authenticate but the service catalog not have
        # the correct endpoint for this driver, so we throw here.
        if 'publicURL' in ep:
            return ep['publicURL']
        else:
            raise LibcloudError('Could not find specified endpoint')


class RackspaceNovaBetaConnection(RackspaceNovaConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'cloudServersPreprod',
                         'region': 'DFW'}


class RackspaceNovaDfwConnection(RackspaceNovaConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'cloudServersOpenStack',
                         'region': 'DFW'}


class RackspaceNovaLonConnection(RackspaceNovaConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'cloudServersOpenStack',
                         'region': 'LON'}


class RackspaceNovaDfwNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'RackspaceNovadfw'
    website = 'http://www.rackspace.com/'
    connectionCls = RackspaceNovaDfwConnection
    type = Provider.RACKSPACE_NOVA_DFW
    api_name = 'rackspacenovaus'


class RackspaceNovaOrdConnection(RackspaceNovaConnection):

    get_endpoint_args = {'service_type': 'compute',
                         'name': 'cloudServersOpenStack',
                         'region': 'ORD'}


class RackspaceNovaOrdNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'RackspaceNovaord'
    website = 'http://www.rackspace.com/'
    connectionCls = RackspaceNovaOrdConnection
    type = Provider.RACKSPACE_NOVA_ORD
    api_name = 'rackspacenovaus'


class RackspaceNovaLonNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'RackspaceNovalon'
    website = 'http://www.rackspace.com/'
    connectionCls = RackspaceNovaLonConnection
    type = Provider.RACKSPACE_NOVA_LON
    api_name = 'rackspacenovauk'


class RackspaceNovaBetaNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'RackspaceNovaBeta'
    website = 'http://www.rackspace.com/'
    connectionCls = RackspaceNovaBetaConnection
    type = Provider.RACKSPACE_NOVA_BETA
    api_name = 'rackspacenovabeta'
