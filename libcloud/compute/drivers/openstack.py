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

    QUOTA_TYPES = [
        'cores',
        'floating_ips',
        'gigabytes',
        'injected_file_content_bytes',
        'injected_files',
        'instances',
        'metadata_items',
        'ram',
        'volumes',
    ]

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

        self.REBOOT_HARD = version_module.servers.REBOOT_HARD
        self.REBOOT_SOFT = version_module.servers.REBOOT_SOFT
        self.client = version_module.client.Client(username, api_key, project_id, auth_url, timeout)

    def list_nodes(self):
        return self._to_nodes(self.client.servers.list())

    def list_sizes(self):
        return self._to_sizes(self.client.flavors.list())

    def list_images(self):
        return self._to_images(self.client.images.findall(status='ACTIVE'))

    def create_node(self, name, size, image, metadata=None, files=None):
        return self._to_node(self.client.servers.create(
            name,
            image.id,
            size.id,
            meta=metadata,
            files=files,
        ))

    def destroy_node(self, node):
        self.client.servers.delete(node.id)

    def reboot_node(self, node, hard=False):
        reboot_type = (self.REBOOT_SOFT, self.REBOOT_HARD)[hard]
        self.client.servers.reboot(node.id, reboot_type)

    def ex_get_node(self, node_id):
        return self._to_node(self.client.servers.get(node_id))

    def ex_set_password(self, node, password):
        self.client.servers.change_password(node.id, password)
        node.extra['password'] = password

    def ex_set_server_name(self, node, name):
        self.client.servers.update(node.id, name=name)
        node.name = name

    def ex_resize(self, node, size):
        # Old RS driver returned False for failure instead of raising an exception.
        # Should we fix that behavior and use exception handling instead (like the
        # non-ex operations do)? Exceptions cleaner for now - await feedback.
        self.client.servers.resize(node.id, size.id)

    def ex_confirm_resize(self, node):
        self.client.servers.confirm_resize(node.id)

    def ex_revert_resize(self, node):
        self.client.servers.revert_resize(node.id)

    def ex_rebuild(self, node, size, password=None):
        # TODO: Oddly, you can set password during rebuild but not during create.
        # This should be brought up with OpenStack devs.
        node = self._to_node(
            self.client.servers.rebuild(node.id, size.id, password=password)
        )

        if password is not None:
            node.extra['password'] = password

        return node

    def ex_save_image(self, node, name, metadata=None):
        self.client.servers.create_image(node.id, name, metadata)

    def ex_list_floating_ips(self):
        return self._to_floating_ips(self.client.floating_ips.list())

    def ex_create_floating_ip(self):
        return self._to_floating_ip(self.client.floating_ips.create())

    def ex_delete_floating_ip(self, floating_ip):
        self.client.floating_ips.delete(floating_ip.id)

    def ex_add_floating_ip(self, node, floating_ip):
        self.client.servers.add_floating_ip(node.id, floating_ip.address)

    def ex_remove_floating_ip(self, node, floating_ip):
        self.client.servers.remove_floating_ip(node.id, floating_ip.address)

    def ex_quotas(self, project_id=None):
        if project_id is None:
            project_id = self.client.client.projectid
        nova_quotas = self.client.quotas.get(project_id)

        quotas_dict = {}
        for quota_type in self.QUOTA_TYPES:
            quotas_dict[quota_type] = getattr(nova_quotas, quota_type, None)
        return quotas_dict

    # TODO: Things to consider with libcloud devs:
    #    - Should we expose SSH keypair management the API provides?
    #    - Ditto for security groups?
    #    - How about zones? OS-side implementation seems incomplete, at
    #      least in novaclient.
    #    - There appears to be no way to get the initial password after node
    #      creation.

    def _to_nodes(self, nova_nodes):
        return [self._to_node(nova_node) for nova_node in nova_nodes]

    def _to_node(self, nova_node):
        public_ip = nova_node.networks.get('public')
        private_ip = nova_node.networks.get('private')

        return Node(
            id=nova_node.id,
            name=nova_node.name,
            state=self.NODE_STATE_MAP.get(nova_node.status, NodeState.UNKNOWN),
            public_ip=public_ip,
            private_ip=private_ip,
            driver=self,
            extra=dict(
                hostId=nova_node.hostId,
                imageId=nova_node.image['id'],
                flavorId=nova_node.flavor['id'],
                uri=[link['href'] for link in nova_node.links if link['rel'] == 'self'][0],
                metadata=nova_node.metadata,
            ),
        )

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

    def _to_floating_ips(self, nova_floating_ips):
        return [
            self._to_floating_ip(nova_floating_ip)
            for nova_floating_ip in nova_floating_ips
        ]

    def _to_floating_ip(self, nova_floating_ip):
        # Wraps instantiation so subclasses can override easily if needed, as
        # well as to match pattern elsewhere.
        # TODO: Fix init args when structure is known. See the class for more.
        return OpenStackFloatingIP(
            address=nova_floating_ip.address,
        )


class OpenStackFloatingIP(object):
    # TODO: Though the admin guide describes FloatingIPs, the API docs don't
    # describe their data at this time, nor does novaclient's class implement
    # any details. When we know more, this object and instantiations need to
    # be fleshed out. Even the "address" part is an assumption.

    def __init__(self, address):
        self.address = address
