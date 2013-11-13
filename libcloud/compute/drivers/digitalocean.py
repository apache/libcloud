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
Digital Ocean Driver
"""

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation


class DigitalOceanResponse(JsonResponse):
    def parse_error(self):
        if self.status == httplib.FOUND and '/api/error' in self.body:
            # Hacky, but DigitalOcean error responses are awful
            raise InvalidCredsError(self.body)
        elif self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        if type(self.body) == str:
            return json.loads(self.body).get('message')
        elif type(self.body) == dict:
            return self.body.get('message')


class SSHKey(object):
    def __init__(self, id, name, pub_key):
        self.id = id
        self.name = name
        self.pub_key = pub_key

    def __repr__(self):
        return (('<SSHKey: id=%s, name=%s, pub_key=%s>') %
                (self.id, self.name, self.pub_key))


class DigitalOceanConnection(ConnectionUserAndKey):
    """
    Connection class for the DigitalOcean driver.
    """

    host = 'api.digitalocean.com'
    responseCls = DigitalOceanResponse

    def add_default_params(self, params):
        """
        Add parameters that are necessary for every request

        This method adds ``client_id`` and ``api_key`` to
        the request.
        """
        params['client_id'] = self.user_id
        params['api_key'] = self.key
        return params


class DigitalOceanNodeDriver(NodeDriver):
    """
    DigitalOceanNode node driver.
    """

    connectionCls = DigitalOceanConnection

    type = Provider.DIGITAL_OCEAN
    name = 'Digital Ocean'
    website = 'https://www.digitalocean.com'

    NODE_STATE_MAP = {'new': NodeState.PENDING,
                      'off': NodeState.UNKNOWN,
                      'active': NodeState.RUNNING}

    def list_nodes(self):
        data = self.connection.request('/droplets').object['droplets']
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/regions').object['regions']
        return list(map(self._to_location, data))

    def list_images(self):
        data = self.connection.request('/images').object['images']
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/sizes').object['sizes']
        return list(map(self._to_size, data))

    def create_node(self, name, size, image, location, ex_ssh_key_ids=None,
                    **kwargs):
        """
        Create a node.

        :keyword    ex_ssh_key_ids: A list of ssh key ids which will be added
                                   to the server. (optional)
        :type       ex_ssh_key_ids: ``list`` of ``str``

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        params = {'name': name, 'size_id': size.id, 'image_id': image.id,
                  'region_id': location.id}

        if ex_ssh_key_ids:
            params['ssh_key_ids'] = ','.join(ex_ssh_key_ids)
        private_networking = kwargs.get('private_networking', False)
        params['private_networking'] = private_networking
        data = self.connection.request('/droplets/new', params=params).object
        if data.get('status') == 'ERROR':
            raise Exception(data.get('message'))

        return self._to_node(data=data['droplet'])

    def ex_start_node(self, node):
        res = self.connection.request('/droplets/%s/power_on/' % (node.id))
        return res.status == httplib.OK

    def ex_stop_node(self, node):
        res = self.connection.request('/droplets/%s/power_off/' % (node.id))
        return res.status == httplib.OK

    def reboot_node(self, node):
        res = self.connection.request('/droplets/%s/reboot/' % (node.id))
        return res.status == httplib.OK

    def destroy_node(self, node):
        res = self.connection.request('/droplets/%s/destroy/' % (node.id))
        return res.status == httplib.OK

    def ex_list_ssh_keys(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`SSHKey`
        """
        data = self.connection.request('/ssh_keys').object['ssh_keys']
        return list(map(self._to_ssh_key, data))

    def ex_create_ssh_key(self, name, ssh_key_pub):
        """
        Create a new SSH key.

        :param      name: Key name (required)
        :type       name: ``str``

        :param      name: Valid public key string (required)
        :type       name: ``str``
        """
        params = {'name': name, 'ssh_pub_key': ssh_key_pub}
        data = self.connection.request('/ssh_keys/new/', method='GET',
                                       params=params).object
        assert 'ssh_key' in data
        return self._to_ssh_key(data=data['ssh_key'])

    def ex_destroy_ssh_key(self, key_id):
        """
        Delete an existing SSH key.

        :param      key_id: SSH key id (required)
        :type       key_id: ``str``
        """
        res = self.connection.request('/ssh_keys/%s/destroy/' % (key_id))
        return res.status == httplib.OK

    def _to_node(self, data):
        extra_keys = ['image_id', 'backups_active', 'region_id']
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        if 'ip_address' in data and data['ip_address'] is not None:
            public_ips = [data['ip_address']]
        else:
            public_ips = []

        if 'private_ip_address' in data \
            and data['private_ip_address'] is not None:
            private_ips = [data['private_ip_address']]
        else:
            private_ips = []

        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'],
                    name=data['name'],
                    state=state,
                    public_ips=public_ips,
                    private_ips=private_ips,
                    extra=extra,
                    driver=self)
        return node

    def _to_image(self, data):
        extra = {'distribution': data['distribution']}
        return NodeImage(id=data['id'], name=data['name'], extra=extra,
                         driver=self)

    def _to_location(self, data):
        return NodeLocation(id=data['id'], name=data['name'], country=None,
                            driver=self)

    def _to_size(self, data):
        ram = data['name'].lower()

        if 'mb' in ram:
            ram = int(ram.replace('mb', ''))
        elif 'gb' in ram:
            ram = int(ram.replace('gb', '')) * 1024
        price = "$%s/hour, $%s/month" % \
               (data.get('cost_per_hour'), data.get('cost_per_month'))
        disk = "%sGB SSD" % data.get('disk')
        return NodeSize(id=data['id'], name=data['name'], ram=ram, disk=disk,
                        bandwidth=0, price=price, driver=self)

    def _to_ssh_key(self, data):
        return SSHKey(id=data['id'], name=data['name'],
                      pub_key=data.get('ssh_pub_key', None))
