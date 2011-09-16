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
from libcloud.compute.base import (
    Node, NodeState, NodeSize, NodeDriver, NodeImage
)

url_version_pattern = re.compile(r'\/v(\d+(?:\.\d+)+)\/?$')


class OpenStackNodeDriver(NodeDriver):

    name = 'OpenStack'
    type = Provider.OPENSTACK
    api_version = None
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
        if not api_version and not self.api_version:
            # If not specified in call or class, try to guess from URL.
            match = url_version_pattern.search(auth_url)
            if match:
                api_version = match.groups()[0]

        if api_version:
            self.api_version = api_version

        if not self.api_version:
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

    def list_sizes(self):
        return self._to_sizes(self.client.flavors.list())

    def list_images(self):
        return self._to_images(self.client.images.findall(status='ACTIVE'))

    def ex_set_password(self, node, password):
        self._to_nova_node(node).change_password(password)
        node.extra['password'] = password

    def _to_nodes(self, nova_nodes):
        return [self._to_node(nova_node) for nova_node in nova_nodes]

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

    def _to_nova_node(self, node):
        return self.client.servers.get(node.id)

    def _to_sizes(self, nova_flavors):
        return [self._to_size(nova_flavor) for nova_flavor in nova_flavors]

    def _to_size(self, nova_flavor, price=None, bandwidth=None):
        # if provider-specific subclasses can get better values for
        # price/bandwidth, then can pass them in when they super().
        return NodeSize(
            id=nova_flavor.id,
            name=nova_flavor.name,
            ram=nova_flavor.ram,
            disk=nova_flavor.disk,
            bandwidth=bandwidth,
            price=price,
            driver=self,
        )

    def _to_images(self, nova_images):
        return [self._to_image(nova_image) for nova_image in nova_images]

    def _to_image(self, nova_image):
        return NodeImage(
            id=nova_image.id,
            name=nova_image.name,
            driver=self,
            extra=dict(
                updated=nova_image.updated,
                created=nova_image.created,
                status=nova_image.status,
                progress=nova_image.progress,
                metadata=nova_image.metadata,
            ),
        )
