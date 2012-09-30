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


ENDPOINT_ARGS_MAP = {
    'us': {
        'dfw':  {'service_type': 'compute',
                  'name': 'cloudServersOpenStack',
                  'region': 'DFW'},
        'ord':  {'service_type': 'compute',
                  'name': 'cloudServersOpenStack',
                  'region': 'ORD'}
    },
    'uk': {
        'default':  {'service_type': 'compute',
                     'name': 'cloudServersOpenStack',
                     'region': 'LON'}
    },
    'beta': {
        'dfw':  {'service_type': 'compute',
                 'name': 'cloudServersPreprod',
                 'region': 'DFW'}
    }
}


class RackspaceConnection(OpenStack_1_1_Connection):
    get_endpoint_args = {}

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
    name = 'Rackspace Cloud'
    website = 'http://www.rackspace.com'
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    api_name = None # todo

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 region='us', datacenter='dfw', **kwargs):
        if region not in ['us', 'uk']:
            raise ValueError('Invalid region: %s' % (region))

        if region == 'us' and datacenter not in ['dfw', 'ord']:
            raise ValueError('Invalid datacenter: %s' % (datacenter))
        elif region in ['uk']:
            datacenter = 'default'

        self.connectionCls.get_endpoint_args = \
                ENDPOINT_ARGS_MAP[region][datacenter]

        self.region = region
        self.datacenter = datacenter

        super(RackspaceNodeDriver, self).__init__(key=key, secret=secret,
                       secure=secure, host=host, port=port, **kwargs)
