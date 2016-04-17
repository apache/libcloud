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
Scaleway Driver
"""

import copy
try:
    import simplejson as json
except:
    import json

from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.base import NodeDriver, NodeImage, Node, NodeSize
from libcloud.compute.base import StorageVolume, VolumeSnapshot
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState, VolumeSnapshotState
from libcloud.utils.iso8601 import parse_date
from libcloud.utils.py3 import httplib

__all__ = [
    'ScalewayResponse',
    'ScalewayConnection',
    'ScalewayNodeDriver'
]

# 'api.scaleway.com' works only with this
# libcloud.security.VERIFY_SSL_CERT = False
SCALEWAY_API_HOST = 'api.cloud.online.net'

# The API doesn't currently expose all of the required values for libcloud,
# so we simply list what's available right now, along with all of the various
# attributes that are needed by libcloud.
SCALEWAY_INSTANCE_TYPES = [
    {
        'id': 'C1',
        'name': 'C1',
        'ram': 2048,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.006
    },
    {
        'id': 'C2S',
        'name': 'C2S',
        'ram': 8192,
        'disk': 50,
        'bandwidth': 300,
        'price': 0.024
    },
    {
        'id': 'C2M',
        'name': 'C2M',
        'ram': 16384,
        'disk': 50,
        'bandwidth': 500,
        'price': 0.036
    },
    {
        'id': 'C2L',
        'name': 'C2L',
        'ram': 32768,
        'disk': 50,
        'bandwidth': 800,
        'price': 0.048
    },
    {
        'id': 'VC1S',
        'name': 'VC1S',
        'ram': 2048,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.006
    },
    {
        'id': 'VC1M',
        'name': 'VC1M',
        'ram': 4096,
        'disk': 100,
        'bandwidth': 200,
        'price': 0.012},
    {
        'id': 'VC1L',
        'name': 'VC1L',
        'ram': 8192,
        'disk': 200,
        'bandwidth': 200,
        'price': 0.02
    },
]


class ScalewayResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED,
                            httplib.CREATED, httplib.NO_CONTENT]

    def parse_error(self):
        return super(ScalewayResponse, self).parse_error()['message']

    def success(self):
        return self.status in self.valid_response_codes


class ScalewayConnection(ConnectionUserAndKey):
    """
    Connection class for the Scaleway driver.
    """

    host = SCALEWAY_API_HOST
    allow_insecure = False
    responseCls = ScalewayResponse

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request
        """
        headers['X-Auth-Token'] = self.key
        headers['Content-Type'] = 'application/json'
        return headers


def _kb_to_mb(size):
    return int(size / 1000 / 1000 / 1000)


def _mb_to_kb(size):
    return int(size * 1000 * 1000 * 1000)


class ScalewayNodeDriver(NodeDriver):
    """
    Scaleway NodeDriver
    """

    type = Provider.SCALEWAY
    connectionCls = ScalewayConnection
    name = 'Scaleway'
    website = 'https://www.scaleway.com/'

    SNAPSHOT_STATE_MAP = {  # TODO map all states
        'snapshotting': VolumeSnapshotState.CREATING
    }

    def list_sizes(self):
        return [NodeSize(driver=self, **copy.deepcopy(size))
                for size in SCALEWAY_INSTANCE_TYPES]

    def list_images(self):
        response = self.connection.request('/images')
        images = response.object['images']
        return [NodeImage(id=image['id'],
                          name=image['name'],
                          driver=self,
                          extra={'arch': image['arch']})
                for image in images]

    def create_image(self, node, name, description=None):
        data = {
            'organization': self.key,
            'name': name,
            'arch': node.extra['arch'],
            'root_volume': node.extra['volumes']['0']['id']  # TODO check this
        }
        response = self.connection.request('/images', data=json.dumps(data),
                                           method='POST')
        image = response.object['image']
        return NodeImage(id=image['id'], name=image['name'], driver=self)

    def delete_image(self, node_image):
        return self.connection.request('/images/%s' % node_image.id,
                                       method='DELETE').success()

    def get_image(self, image_id):
        response = self.connection.request('/images/%s' % image_id)
        image = response.object['image']
        return NodeImage(id=image['id'], name=image['name'], driver=self)

    def list_nodes(self):
        response = self.connection.request('/servers')
        servers = response.object['servers']
        return [self._to_node(server) for server in servers]

    def _to_node(self, server):
        public_ip = server['public_ip']
        private_ip = server['private_ip']
        return Node(id=server['id'],
                    name=server['name'],
                    state=NodeState.fromstring(server['state']),
                    public_ips=[public_ip['address']] if public_ip else [],
                    private_ips=[private_ip['address']] if private_ip else [],
                    driver=self,
                    extra={'volumes': server['volumes']},
                    created_at=parse_date(server['creation_date']))

    def create_node(self, name, size, image, ex_volumes=None, ex_tags=None):
        data = {
            'name': name,
            'organization': self.key,
            'image': image.id,
            'volumes': ex_volumes or {},
            'commercial_type': size.id,
            'tags': ex_tags or []
        }

        response = self.connection.request('/servers', data=json.dumps(data),
                                           method='POST')
        server = response.object['server']
        node = self._to_node(server)

        # Scaleway doesn't start servers by default, let's do it
        self._action(node.id, 'poweron')

        return node

    def _action(self, server_id, action):
        return self.connection.request('/servers/%s/action' % server_id,
                                       data=json.dumps({'action': action}),
                                       method='POST').success()

    def reboot_node(self, node):
        return self._action(node.id, 'reboot')

    def destroy_node(self, node):
        return self._action(node.id, 'terminate')

    def list_volumes(self):
        response = self.connection.request('/volumes')
        volumes = response.object['volumes']
        return [self._to_volume(volume) for volume in volumes]

    def _to_volume(self, volume):
        return StorageVolume(id=volume['id'],
                             name=volume['name'],
                             size=_kb_to_mb(volume['size']),
                             driver=self)

    def list_volume_snapshots(self, volume):
        response = self.connection.request('/snapshots')
        snapshots = filter(lambda s: s['base_volume']['id'] == volume.id,
                           response.object['snapshots'])
        return [self._to_snapshot(snapshot) for snapshot in snapshots]

    def _to_snapshot(self, snapshot):
        state = self.SNAPSHOT_STATE_MAP.get(snapshot['state'],
                                            VolumeSnapshotState.UNKNOWN)
        return VolumeSnapshot(id=snapshot['id'],
                              driver=self,
                              size=_kb_to_mb(snapshot['size']),
                              created=parse_date(snapshot['creation_date']),
                              state=state)

    def create_volume(self, size, name):
        data = {
            'name': name,
            'organization': self.key,
            'volume_type': 'l_ssd',
            'size': _mb_to_kb(size)
        }
        response = self.connection.request('/volumes',
                                           data=json.dumps(data),
                                           method='POST')
        volume = response.object['volume']
        return self._to_volume(volume)

    def create_volume_snapshot(self, volume, name):
        data = {
            'name': name,
            'organization': self.key,
            'volume_id': volume.id
        }
        response = self.connection.request('/snapshots',
                                           data=json.dumps(data),
                                           method='POST')
        snapshot = response.object['snapshot']
        return self._to_snapshot(snapshot)

    def destroy_volume(self, volume):
        return self.connection.request('/volumes/%s' % volume.id,
                                       method='DELETE').success()

    def destroy_volume_snapshot(self, snapshot):
        return self.connection.request('/snapshots//%s' % snapshot.id,
                                       method='DELETE').success()
