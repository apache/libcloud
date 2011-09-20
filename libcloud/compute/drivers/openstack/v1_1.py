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
'''
OpenStack Nova 1.1 driver
'''

from libcloud.compute.base import Node, NodeState, NodeSize, NodeImage
from libcloud.compute.drivers.openstack import OpenStackNodeDriverBase


class OpenStackNodeDriver(OpenStackNodeDriverBase):

    def list_nodes(self):
        return [
            self._to_node(api_server)
            for api_server in self.connection.request('/servers/detail').object['servers']
        ]

    def list_sizes(self):
        return [
            self._to_size(api_flavor)
            for api_flavor in self.connection.request('/flavors/detail').object['flavors']
        ]

    def list_images(self):
        return [
            self._to_image(api_image)
            for api_image
            in self.connection.request('/images/detail?status=ACTIVE').object['images']
        ]

    def create_node(self, name, size, image, metadata=None, files=None):
        # TODO: should we ref images and flavors by link instead of id? It
        # opens up the theoretical possibility of remote images and such.
        # TODO: "personality" support.
        # TODO: "reservation_id" support.
        # TODO: "security_groups" support.
        server_params = dict(
            name=name,
            flavorRef=str(size.id),
            imageRef=str(image.id),
        )
        if metadata:
            server_params['metadata'] = metadata
        if files:
            server_params['files'] = files

        return self._to_node(
            self.connection.request(
                '/servers', method='POST', data=dict(server=server_params)
            ).object['server']
        )

    def destroy_node(self, node):
        self.connection.request('/servers/%s' % (node.id,), method='DELETE')

    def reboot_node(self, node, hard=False):
        self._node_action(node, 'reboot', type=('SOFT', 'HARD')[hard])

    def ex_set_password(self, node, password):
        self._node_action(node, 'changePassword', adminPass=password)
        node.extra['password'] = password

    def ex_rebuild(self, node, image, name=None, metadata=None):
        # TODO: "personality" support.        
        optional_params = {}
        if name:
            optional_params['name'] = name
        if metadata:
            optional_params['metadata'] = metadata

        # Note: At this time, the docs say this should be "image={'id': image.id}".
        # Educating guessing turned up the actual working syntax here.
        self._node_action(node, 'rebuild', imageRef=image.id, **optional_params)

    def ex_resize(self, node, size):
        # Note: At this time, the docs say this should be "flavor={'id': image.id}".
        # Educating guessing turned up the actual working syntax here.
        self._node_action(node, 'resize', flavorRef=size.id)

    def ex_confirm_resize(self, node):
        self._node_action(node, 'confirmResize')

    def ex_revert_resize(self, node):
        self._node_action(node, 'revertResize')

    def ex_save_image(self, node, name, metadata=None):
        optional_params = {}
        if metadata:
            optional_params['metadata'] = metadata
        self._node_action(node, 'createImage', name=name, **optional_params)

    def ex_update_node(self, node, **node_updates):
        # At this time, only name is supported, but this signature covers the future.
        self.connection.request(
            '/servers/%s' % (node.id,), method='PUT', data=dict(server=node_updates)
        )

    def ex_get_node(self, node_id):
        return self._to_node(self.connection.request('/servers/%s' % (node_id,)).object['server'])

    def ex_get_size(self, size_id):
        return self._to_size(self.connection.request('/flavors/%s' % (size_id,)).object['flavor'])

    def ex_get_image(self, image_id):
        return self._to_image(self.connection.request('/images/%s' % (image_id,)).object['image'])

    def ex_delete_image(self, image):
        self.connection.request('/images/%s' % (image.id,), method='DELETE')

    def ex_quotas(self, tenant_id=None):
        if tenant_id is None:
            tenant_id = self.connection.tenant_id

        return self.connection.request('/os-quota-sets/%s' % (tenant_id,)).object['quota_set']

    def _node_action(self, node, action, **params):
        params = params or None
        self.connection.request('/servers/%s/action' % (node.id,), method='POST', data={action: params})

    def _to_node(self, api_node):
        return Node(
            id=api_node['id'],
            name=api_node['name'],
            state=self.NODE_STATE_MAP.get(api_node['status'], NodeState.UNKNOWN),
            public_ip=[addr_desc['addr'] for addr_desc in api_node['addresses'].get('public', [])],
            private_ip=[addr_desc['addr'] for addr_desc in api_node['addresses'].get('private', [])],
            driver=self,
            extra=dict(
                hostId=api_node['hostId'],
                # Docs says "tenantId", but actual is "tenant_id". *sigh* Best handle both.
                tenantId=api_node.get('tenant_id') or api_node['tenantId'],
                imageId=api_node['image']['id'],
                flavorId=api_node['flavor']['id'],
                uri=(link['href'] for link in api_node['links'] if link['rel'] == 'self').next(),
                metadata=api_node['metadata'],
                password=api_node.get('adminPass'),
            ),
        )

    def _to_size(self, api_flavor, price=None, bandwidth=None):
        # if provider-specific subclasses can get better values for
        # price/bandwidth, then can pass them in when they super().
        return NodeSize(
            id=api_flavor['id'],
            name=api_flavor['name'],
            ram=api_flavor['ram'],
            disk=api_flavor['disk'],
            bandwidth=bandwidth,
            price=price,
            driver=self,
        )

    def _to_image(self, api_image):
        return NodeImage(
            id=api_image['id'],
            name=api_image['name'],
            driver=self,
            extra=dict(
                updated=api_image['updated'],
                created=api_image['created'],
                status=api_image['status'],
                progress=api_image['progress'],
                metadata=api_image.get('metadata'),
            ),
        )
