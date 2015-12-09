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
Packet Driver
"""

from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import KeyPair

PACKET_ENDPOINT = "api.packet.net"


class PacketResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body['message'], self.status)
            else:
                error = body
            return error

    def success(self):
        return self.status in self.valid_response_codes


class PacketConnection(ConnectionKey):
    """
    Connection class for the Packet driver.
    """

    host = PACKET_ENDPOINT
    responseCls = PacketResponse

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request
        """
        headers['Content-Type'] = 'application/json'
        headers['X-Auth-Token'] = self.key
        headers['X-Consumer-Token'] = \
            'kcrhMn7hwG8Ceo2hAhGFa2qpxLBvVHxEjS9ue8iqmsNkeeB2iQgMq4dNc1893pYu'
        return headers


class PacketNodeDriver(NodeDriver):
    """
    Packet NodeDriver
    """

    connectionCls = PacketConnection
    type = Provider.PACKET
    name = 'Packet'
    website = 'http://www.packet.net/'

    NODE_STATE_MAP = {'queued': NodeState.PENDING,
                      'provisioning': NodeState.PENDING,
                      'rebuilding': NodeState.PENDING,
                      'powering_on': NodeState.REBOOTING,
                      'powering_off': NodeState.REBOOTING,
                      'rebooting': NodeState.REBOOTING,
                      'inactive': NodeState.STOPPED,
                      'deleted': NodeState.TERMINATED,
                      'deprovisioning': NodeState.TERMINATED,
                      'failed': NodeState.ERROR,
                      'active': NodeState.RUNNING}

    def list_nodes(self, ex_project_id):
        data = self.connection.request('/projects/%s/devices' %
                                       (ex_project_id),
                                       params={'include': 'plan'}
                                       ).object['devices']
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/facilities')\
            .object['facilities']
        return list(map(self._to_location, data))

    def list_images(self):
        data = self.connection.request('/operating-systems')\
            .object['operating_systems']
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/plans').object['plans']
        return list(map(self._to_size, data))

    def create_node(self, name, size, image, location, ex_project_id):
        """
        Create a node.

        :return: The newly created node.
        :rtype: :class:`Node`
        """

        params = {'hostname': name, 'plan': size.id,
                  'operating_system': image.id, 'facility': location.id,
                  'include': 'plan', 'billing_cycle': 'hourly'}

        data = self.connection.request('/projects/%s/devices' %
                                       (ex_project_id),
                                       params=params, method='POST')

        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))
        return self._to_node(data=data.object)

    def reboot_node(self, node):
        params = {'type': 'reboot'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def destroy_node(self, node):
        res = self.connection.request('/devices/%s' % (node.id),
                                      method='DELETE')
        return res.status == httplib.OK

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`.KeyPair` objects
        """
        data = self.connection.request('/ssh-keys').object['ssh_keys']
        return list(map(self._to_key_pairs, data))

    def create_key_pair(self, name, public_key):
        """
        Create a new SSH key.

        :param      name: Key name (required)
        :type       name: ``str``

        :param      public_key: Valid public key string (required)
        :type       public_key: ``str``
        """
        params = {'label': name, 'key': public_key}
        data = self.connection.request('/ssh-keys', method='POST',
                                       params=params).object
        return self._to_key_pairs(data)

    def delete_key_pair(self, key):
        """
        Delete an existing SSH key.

        :param      key: SSH key (required)
        :type       key: :class:`KeyPair`
        """
        key_id = key.name
        res = self.connection.request('/ssh-keys/%s' % (key_id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def _to_node(self, data):
        extra_keys = ['created_at', 'updated_at',
                      'userdata', 'billing_cycle', 'locked']
        if 'state' in data:
            state = self.NODE_STATE_MAP.get(data['state'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        if 'ip_addresses' in data and data['ip_addresses'] is not None:
            ips = self._parse_ips(data['ip_addresses'])

        if 'operating_system' in data and data['operating_system'] is not None:
            image = self._to_image(data['operating_system'])

        if 'plan' in data and data['plan'] is not None:
            size = self._to_size(data['plan'])

        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'], name=data['hostname'], state=state,
                    image=image, size=size,
                    public_ips=ips['public'], private_ips=ips['private'],
                    extra=extra, driver=self)
        return node

    def _to_image(self, data):
        extra = {'distro': data['distro'], 'version': data['version']}
        return NodeImage(id=data['slug'], name=data['name'], extra=extra,
                         driver=self)

    def _to_location(self, data):
        return NodeLocation(id=data['code'], name=data['name'], country=None,
                            driver=self)

    def _to_size(self, data):
        extra = {'description': data['description'], 'line': data['line']}

        ram = data['specs']['memory']['total'].lower()
        if 'mb' in ram:
            ram = int(ram.replace('mb', ''))
        elif 'gb' in ram:
            ram = int(ram.replace('gb', '')) * 1024

        disk = 0
        for disks in data['specs']['drives']:
            disk += disks['count'] * int(disks['size'].replace('GB', ''))

        price = data['pricing']['hourly']

        return NodeSize(id=data['slug'], name=data['name'], ram=ram, disk=disk,
                        bandwidth=0, price=price, extra=extra, driver=self)

    def _to_key_pairs(self, data):
        extra = {'label': data['label'],
                 'created_at': data['created_at'],
                 'updated_at': data['updated_at']}
        return KeyPair(name=data['id'],
                       fingerprint=data['fingerprint'],
                       public_key=data['key'],
                       private_key=None,
                       driver=self,
                       extra=extra)

    def _parse_ips(self, data):
        public_ips = []
        private_ips = []
        for address in data:
            if 'address' in address and address['address'] is not None:
                if 'public' in address and address['public'] is True:
                    public_ips.append(address['address'])
                else:
                    private_ips.append(address['address'])
        return {'public': public_ips, 'private': private_ips}
