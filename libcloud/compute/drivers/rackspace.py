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
from libcloud.compute.drivers.openstack import OpenStack_1_1_Connection,\
    OpenStack_1_1_NodeDriver

from libcloud.common.rackspace import AUTH_URL_US, AUTH_URL_UK


ENDPOINT_ARGS_MAP = {
    'dfw': {'service_type': 'compute',
            'name': 'cloudServersOpenStack',
            'region': 'DFW'},
    'ord': {'service_type': 'compute',
            'name': 'cloudServersOpenStack',
            'region': 'ORD'},
    'iad': {'service_type': 'compute',
            'name': 'cloudServersOpenStack',
            'region': 'IAD'},
    'lon': {'service_type': 'compute',
            'name': 'cloudServersOpenStack',
            'region': 'LON'},
    'syd': {'service_type': 'compute',
            'name': 'cloudServersOpenStack',
            'region': 'SYD'},
}


class RackspaceFirstGenConnection(OpenStack_1_0_Connection):
    """
    Connection class for the Rackspace first-gen driver.
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

        if 'publicURL' in ep:
            return ep['publicURL']

        raise LibcloudError('Could not find specified endpoint')


class RackspaceFirstGenNodeDriver(OpenStack_1_0_NodeDriver):
    name = 'Rackspace Cloud (First Gen)'
    website = 'http://www.rackspace.com'
    connectionCls = RackspaceFirstGenConnection
    type = Provider.RACKSPACE_FIRST_GEN
    api_name = 'rackspace'

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 region='us', **kwargs):
        """
        @inherits:  :class:`NodeDriver.__init__`

        :param region: Region ID which should be used
        :type region: ``str``
        """
        if region not in ['us', 'uk']:
            raise ValueError('Invalid region: %s' % (region))

        super(RackspaceFirstGenNodeDriver, self).__init__(key=key,
                                                          secret=secret,
                                                          secure=secure,
                                                          host=host,
                                                          port=port,
                                                          region=region,
                                                          **kwargs)

    def list_locations(self):
        """
        Lists available locations

        Locations cannot be set or retrieved via the API, but currently
        there are two locations, DFW and ORD.

        @inherits: :class:`OpenStack_1_0_NodeDriver.list_locations`
        """
        if self.region == 'us':
            locations = [NodeLocation(0, "Rackspace DFW1/ORD1", 'US', self)]
        elif self.region == 'uk':
            locations = [NodeLocation(0, 'Rackspace UK London', 'UK', self)]

        return locations

    def _ex_connection_class_kwargs(self):
        kwargs = self.openstack_connection_kwargs()

        if self.region == 'us':
            auth_url = AUTH_URL_US
        elif self.region == 'uk':
            auth_url = AUTH_URL_UK

        # 'ex_force_auth_url' has precedence over 'region' argument
        ex_force_auth_url = kwargs.get('ex_force_auth_url', auth_url)
        kwargs['ex_force_auth_url'] = ex_force_auth_url
        return kwargs


class RackspaceConnection(OpenStack_1_1_Connection):
    """
    Connection class for the Rackspace next-gen OpenStack base driver.
    """
    def __init__(self, *args, **kwargs):
        self.get_endpoint_args = kwargs.pop('get_endpoint_args', None)
        super(RackspaceConnection, self).__init__(*args, **kwargs)

    def get_endpoint(self):
        if not self.get_endpoint_args:
            raise LibcloudError(
                'RackspaceConnection must have get_endpoint_args set')

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


class RackspaceNodeDriver(OpenStack_1_1_NodeDriver):
    name = 'Rackspace Cloud (Next Gen)'
    website = 'http://www.rackspace.com'
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE

    _networks_url_prefix = '/os-networksv2'

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 region='dfw', **kwargs):
        """
        @inherits:  :class:`NodeDriver.__init__`

        :param region: ID of the region which should be used.
        :type region: ``str``
        """
        valid_regions = ENDPOINT_ARGS_MAP.keys()

        if region not in valid_regions:
            raise ValueError('Invalid region: %s' % (region))

        if region == 'lon':
            self.api_name = 'rackspacenovalon'
        elif region == 'syd':
            self.api_name = 'rackspacenovasyd'
        else:
            self.api_name = 'rackspacenovaus'

        super(RackspaceNodeDriver, self).__init__(key=key, secret=secret,
                                                  secure=secure, host=host,
                                                  port=port,
                                                  region=region,
                                                  **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = self.openstack_connection_kwargs()

        if self.region == 'lon':
            auth_url = AUTH_URL_UK
        else:
            auth_url = AUTH_URL_US

        # 'ex_force_auth_url' has precedence over 'region' argument
        ex_force_auth_url = kwargs.get('ex_force_auth_url', auth_url)

        # ex_force_auth_version has precedence is not set
        ex_force_auth_version = kwargs.get('ex_force_auth_version', '2.0')

        kwargs['ex_force_auth_url'] = ex_force_auth_url
        kwargs['ex_force_auth_version'] = ex_force_auth_version
        kwargs['get_endpoint_args'] = ENDPOINT_ARGS_MAP[self.region]
        return kwargs
