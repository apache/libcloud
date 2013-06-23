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
from libcloud.compute.types import Provider, LibcloudError
from libcloud.compute.base import NodeLocation
from libcloud.compute.drivers.openstack import OpenStack_1_0_Connection,\
    OpenStack_1_0_NodeDriver, OpenStack_1_0_Response

from libcloud.common.rackspace import AUTH_URL_US, AUTH_URL_UK


class RackspaceConnection(OpenStack_1_0_Connection):
    """
    Connection class for the Rackspace driver
    """

    responseCls = OpenStack_1_0_Response
    auth_url = AUTH_URL_US
    XML_NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'

    def get_endpoint(self):
        ep = {}

        if '2.0' in self._auth_version:
            ep = self.service_catalog.get_endpoint(service_type='compute',
                                                   name='cloudServers')
        elif ('1.1' in self._auth_version) or ('1.0' in self._auth_version):
            ep = self.service_catalog.get_endpoint(name='cloudServers')

        public_url = ep.get('publicURL', None)

        if not public_url:
            raise LibcloudError('Could not find specified endpoint')

        return public_url


class RackspaceNodeDriver(OpenStack_1_0_NodeDriver):
    name = 'Rackspace'
    website = 'http://www.rackspace.com/'
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    api_name = 'rackspace'

    def list_locations(self):
        """Lists available locations

        Locations cannot be set or retrieved via the API, but currently
        there are two locations, DFW and ORD.

        @inherits: L{OpenStack_1_0_NodeDriver.list_locations}
        """
        return [NodeLocation(0, "Rackspace DFW1/ORD1", 'US', self)]


class RackspaceUKConnection(RackspaceConnection):
    """
    Connection class for the Rackspace UK driver
    """
    auth_url = AUTH_URL_UK
    _auth_version = '2.0'

    def get_endpoint(self):
        ep = self.service_catalog.get_endpoint(service_type='compute',
                                               name='cloudServers')

        public_url = ep.get('publicURL', None)

        if not public_url:
            raise LibcloudError('Could not find specified endpoint')

        # Hack which is required because of how global auth works (old
        # US accounts work with the lon endpoint, but don't have it in
        # the service catalog)
        public_url = public_url.replace('https://servers.api',
                                        'https://lon.servers.api')

        return public_url


class RackspaceUKNodeDriver(RackspaceNodeDriver):
    """
    Driver for Rackspace in the UK (London)
    """

    name = 'Rackspace (UK)'
    connectionCls = RackspaceUKConnection

    def list_locations(self):
        return [NodeLocation(0, 'Rackspace UK London', 'UK', self)]


class RackspaceAUConnection(RackspaceConnection):
    """
    Connection class for the Rackspace Sydney datacenter
    """

    auth_url = AUTH_URL_US
    _auth_version = '2.0'

    def get_endpoint(self):
        ep = self.service_catalog.get_endpoint(service_type='compute',
                                               name='cloudServersOpenStack',
                                               region='SYD')

        if 'publicURL' in ep:
            return ep['publicURL']

        raise LibcloudError('Could not find specified endpoint')


class RackspaceAUNodeDriver(RackspaceNodeDriver):
    """Driver for Rackspace in the UK (London)
    """

    name = 'Rackspace (Sydney, Australia)'
    connectionCls = RackspaceAUConnection

    def list_locations(self):
        return [NodeLocation(0, 'Rackspace Sydney, Australia', 'AU', self)]
