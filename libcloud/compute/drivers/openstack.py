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
OpenStack Nova driver
"""

import re

import novaclient
from novaclient import v1_0, v1_1  # Populates attributes of novaclient module
v1_0, v1_1  # Silence pyflakes

from libcloud.compute.types import Provider
from libcloud.compute.base import Node, NodeState, NodeDriver

url_version_pattern = re.compile(r'\/v(\d+(?:\.\d+)+)\/?$')


class OpenStackNodeDriver(NodeDriver):

    name = 'OpenStack'
    type = Provider.OPENSTACK
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

    def __init__(self, username, api_key, project_id, auth_url, timeout=None, api_version=None):
        if not api_version:
            match = url_version_pattern.search(auth_url)
            if match:
                api_version = match.groups()[0]

        if not api_version:
            raise RuntimeError('Unable to determine OpenStack API version')

        try:
            version_module = getattr(novaclient, 'v' + api_version.replace('.', '_'))
        except AttributeError:
            raise NotImplementedError(
                'API version %s is not supported by this OpenStack driver' % (api_version,)
            )

        self.client = version_module.client.Client(username, api_key, project_id, auth_url, timeout)

    def list_nodes(self):
        return self._to_nodes(self.client.servers.list())

    def _to_nodes(self, nova_nodes):
        return [self._to_node(nova_node) for nova_node in self.client.servers.list()]

    def _to_node(self, nova_node):
        return Node(
            id=nova_node.id,
            name=nova_node.name,
            state=self.NODE_STATE_MAP.get(nova_node.status, NodeState.UNKNOWN),
            public_ip=nova_node.networks['public'],
            private_ip=nova_node.networks['private'],
            driver=self,
            extra=dict(
                hostId=nova_node.hostId,
                imageId=nova_node.image['id'],
                flavorId=nova_node.flavor['id'],
                uri=[link['href'] for link in nova_node.links if link['rel'] == 'self'][0],
                metadata=nova_node.metadata,
            ),
        )
