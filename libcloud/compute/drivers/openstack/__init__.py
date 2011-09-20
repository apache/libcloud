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
OpenStack Nova driver base class and factory.
"""

try:
    import simplejson as json
except ImportError:
    import json

import sys
import httplib

from libcloud.common.types import MalformedResponseError
from libcloud.common.base import Response
from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.compute.types import Provider
from libcloud.compute.base import NodeState, NodeDriver


class OpenStackResponse(Response):

    def success(self):
        status = int(self.status)
        return status >= 200 and status <= 299

    def has_content_type(self, content_type):
        content_type_value = self.headers.get('content-type') or ''
        content_type_value = content_type_value.lower()
        return content_type_value.find(content_type.lower()) > -1

    def parse_body(self):
        if not self.body or self.status == httplib.NO_CONTENT:
            return None

        try:
            if not self.has_content_type('application/json'):
                raise ValueError
            return json.loads(self.body)
        except ValueError:
            raise MalformedResponseError('Invalid JSON Response', body=self.body, driver=self.connection.driver)

    def parse_error(self):
        return '%s %s; %s' % (
            self.status,
            self.error,
            ';'.join([fault_data['message'] for fault_data in self.parse_body().values()]),
        )


class OpenStackConnection(OpenStackBaseConnection):
    # Unhappy naming - this class, named per the pattern in compute drivers,
    # is inheriting from a common (non-service-specific) base class.

    responseCls = OpenStackResponse
    _url_key = "server_url"
    content_type = 'application/json; charset=UTF-8'

    def encode_data(self, data):
        return json.dumps(data)


class OpenStackNodeDriver(NodeDriver):

    connectionCls = OpenStackConnection
    name = 'OpenStack'
    api_name = 'openstack'
    type = Provider.OPENSTACK
    _auth_url = None
    _tenant_id = None
    features = {
        'create_node': ['generates_password'],
    }

    NODE_STATE_MAP = {
        'BUILD': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'SUSPENDED': NodeState.TERMINATED,
        'QUEUE_RESIZE': NodeState.PENDING,
        'PREP_RESIZE': NodeState.PENDING,
        'VERIFY_RESIZE': NodeState.RUNNING,
        'PASSWORD': NodeState.PENDING,
        'RESCUE': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'REBOOT': NodeState.REBOOTING,
        'HARD_REBOOT': NodeState.REBOOTING,
        'SHARE_IP': NodeState.PENDING,
        'SHARE_IP_NO_CONFIG': NodeState.PENDING,
        'DELETE_IP': NodeState.PENDING,
        'UNKNOWN': NodeState.UNKNOWN,
    }

    def __new__(cls, *args, **kwargs):

        if cls is OpenStackNodeDriver:
            # This base class is a factory.

            version = kwargs.get('version', None) # TODO: Would it be unwise to have a default version?

            if not version:
                raise TypeError('An OpenStack "version" keyword argument is required.')

            ver_mod_name = 'libcloud.compute.drivers.openstack.v%s' % (version.replace('.', '_'),)
            try:
                __import__(ver_mod_name)
            except ImportError:
                raise NotImplementedError(
                    'API version %s is not supported by this OpenStack driver' % (version,)
                )

            ver_mod = sys.modules[ver_mod_name]
            cls = ver_mod.OpenStackNodeDriver

        return object.__new__(cls)

    def __init__(self, username, api_key, auth_url=None, tenant_id=None, ex_force_base_url=None, version=None):
        # version is there because the sig must be compatible with __new__, but it's ignored.
        if auth_url:
            self._auth_url = auth_url
        if tenant_id:
            self._tenant_id = tenant_id
        self._ex_force_base_url = ex_force_base_url
        NodeDriver.__init__(self, username, secret=api_key)

    def _ex_connection_class_kwargs(self):
        kwargs = {}
        if self._auth_url:
            kwargs['auth_url'] = self._auth_url
        if self._tenant_id:
            kwargs['tenant_id'] = self._tenant_id
        if self._ex_force_base_url:
            kwargs['ex_force_base_url'] = self._ex_force_base_url
        return kwargs
