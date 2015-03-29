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

from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionUserAndKey, ConnectionKey
from libcloud.common.base import JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, KeyPair

__all__ = [
    'DigitalOceanNodeDriver',
    'DigitalOcean_v1_NodeDriver',
    'DigitalOcean_v1_NodeDriver'
]


class DigitalOceanNodeDriver(NodeDriver):
    """
    DigitalOcean NodeDriver defaulting to using APIv2.

    :keyword    api_version: Specifies the API version to use. ``v1`` and
                             ``v2`` are the only valid options. Defaults to
                             using ``v2`` (optional)
    :type       api_version: ``str``
    """
    type = Provider.DIGITAL_OCEAN
    name = 'DigitalOcean'
    website = 'https://www.digitalocean.com'

    def __new__(cls, key, secret=None, api_version='v2', **kwargs):
        if cls is DigitalOceanNodeDriver:
            if api_version == 'v1':
                cls = DigitalOcean_v1_NodeDriver
            elif api_version == 'v2':
                cls = DigitalOcean_v2_NodeDriver
            else:
                raise NotImplementedError('Unsupported API version: %s' %
                                          (api_version))
        return super(DigitalOceanNodeDriver, cls).__new__(cls, **kwargs)


class DigitalOcean_v1_Response(JsonResponse):
    def parse_error(self):
        if self.status == httplib.FOUND and '/api/error' in self.body:
            # Hacky, but DigitalOcean error responses are awful
            raise InvalidCredsError(self.body)
        elif self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()

            if 'error_message' in body:
                error = '%s (code: %s)' % (body['error_message'], self.status)
            else:
                error = body
            return error


class DigitalOcean_v2_Response(JsonResponse):
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


class SSHKey(object):
    def __init__(self, id, name, pub_key):
        self.id = id
        self.name = name
        self.pub_key = pub_key

    def __repr__(self):
        return (('<SSHKey: id=%s, name=%s, pub_key=%s>') %
                (self.id, self.name, self.pub_key))


class DigitalOcean_v1_Connection(ConnectionUserAndKey):
    """
    Connection class for the DigitalOcean (v1) driver.
    """

    host = 'api.digitalocean.com'
    responseCls = DigitalOcean_v1_Response

    def add_default_params(self, params):
        """
        Add parameters that are necessary for every request

        This method adds ``client_id`` and ``api_key`` to
        the request.
        """
        params['client_id'] = self.user_id
        params['api_key'] = self.key
        return params


class DigitalOcean_v2_Connection(ConnectionKey):
    """
    Connection class for the DigitalOcean (v2) driver.
    """

    host = 'api.digitalocean.com'
    responseCls = DigitalOcean_v2_Response

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` to the request.
        """
        headers['Authorization'] = 'Bearer %s' % (self.key)
        headers['Content-Type'] = 'application/json'
        return headers


class DigitalOcean_v1_NodeDriver(DigitalOceanNodeDriver):
    """
    DigitalOcean NodeDriver using v1 of the API.
    """

    connectionCls = DigitalOcean_v1_Connection

    NODE_STATE_MAP = {'new': NodeState.PENDING,
                      'off': NodeState.REBOOTING,
                      'active': NodeState.RUNNING}

    def list_nodes(self):
        data = self.connection.request('/v1/droplets').object['droplets']
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/v1/regions').object['regions']
        return list(map(self._to_location, data))

    def list_images(self):
        data = self.connection.request('/v1/images').object['images']
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/v1/sizes').object['sizes']
        return list(map(self._to_size, data))

    def create_node(self, name, size, image, location, ex_ssh_key_ids=None):
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

        data = self.connection.request('/v1/droplets/new', params=params)

        # TODO: Handle this in the response class
        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))

        return self._to_node(data=data.object['droplet'])

    def reboot_node(self, node):
        res = self.connection.request('/v1/droplets/%s/reboot/' % (node.id))
        return res.status == httplib.OK

    def destroy_node(self, node):
        params = {'scrub_data': '1'}
        res = self.connection.request('/v1/droplets/%s/destroy/' % (node.id),
                                      params=params)
        return res.status == httplib.OK

    def ex_rename_node(self, node, name):
        params = {'name': name}
        res = self.connection.request('/v1/droplets/%s/rename/' % (node.id),
                                      params=params)
        return res.status == httplib.OK

    def ex_list_ssh_keys(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`SSHKey`
        """
        data = self.connection.request('/v1/ssh_keys').object['ssh_keys']
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
        data = self.connection.request('/v1/ssh_keys/new/', method='GET',
                                       params=params).object
        assert 'ssh_key' in data
        return self._to_ssh_key(data=data['ssh_key'])

    def ex_destroy_ssh_key(self, key_id):
        """
        Delete an existing SSH key.

        :param      key_id: SSH key id (required)
        :type       key_id: ``str``
        """
        res = self.connection.request('/v1/ssh_keys/%s/destroy/' % (key_id))
        return res.status == httplib.OK

    def _to_node(self, data):
        extra_keys = ['backups_active', 'region_id', 'image_id', 'size_id']
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        if 'ip_address' in data and data['ip_address'] is not None:
            public_ips = [data['ip_address']]
        else:
            public_ips = []

        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'], name=data['name'], state=state,
                    public_ips=public_ips, private_ips=None, extra=extra,
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

        return NodeSize(id=data['id'], name=data['name'], ram=ram, disk=0,
                        bandwidth=0, price=0, driver=self)

    def _to_ssh_key(self, data):
        return SSHKey(id=data['id'], name=data['name'],
                      pub_key=data.get('ssh_pub_key', None))


class DigitalOcean_v2_NodeDriver(DigitalOceanNodeDriver):
    """
    DigitalOcean NodeDriver using v2 of the API.
    """

    connectionCls = DigitalOcean_v2_Connection

    NODE_STATE_MAP = {'new': NodeState.PENDING,
                      'off': NodeState.STOPPED,
                      'active': NodeState.RUNNING,
                      'archive': NodeState.TERMINATED}

    def list_nodes(self):
        data = self._paginated_request('/v2/droplets', 'droplets')
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/v2/regions').object['regions']
        return list(map(self._to_location, data))

    def list_images(self):
        data = self._paginated_request('/v2/images', 'images')
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/v2/sizes').object['sizes']
        return list(map(self._to_size, data))

    def create_node(self, name, size, image, location, ex_ssh_key_ids=None):
        """
        Create a node.

        :keyword    ex_ssh_key_ids: A list of ssh key ids which will be added
                                   to the server. (optional)
        :type       ex_ssh_key_ids: ``list`` of ``str``

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        params = {'name': name, 'size': size.name, 'image': image.id,
                  'region': location.id}

        if ex_ssh_key_ids:
            params['ssh_key_ids'] = ','.join(ex_ssh_key_ids)

        data = self.connection.request('/v2/droplets',
                                       params=params, method='POST').object

        # TODO: Handle this in the response class
        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))

        return self._to_node(data=data['droplet'])

    def reboot_node(self, node):
        params = {'type': 'reboot'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.CREATED

    def destroy_node(self, node):
        res = self.connection.request('/v2/droplets/%s' % (node.id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def get_image(self, image_id):
        """
        Get an image based on an image_id

        @inherits: :class:`NodeDriver.get_image`

        :param image_id: Image identifier
        :type image_id: ``int``

        :return: A NodeImage object
        :rtype: :class:`NodeImage`
        """
        res = self.connection.request('/v2/images/%s' % (image_id))
        data = res.object['image']
        return self._to_image(data)

    def create_image(self, node, name):
        """
        Create an image fron a Node.

        @inherits: :class:`NodeDriver.create_image`

        :param node: Node to use as base for image
        :type node: :class:`Node`

        :param node: Name for image
        :type node: ``str``

        :rtype: ``bool``
        """
        params = {'type': 'snapshot', 'name': name}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.CREATED

    def delete_image(self, image):
        """Delete an image for node.

        @inherits: :class:`NodeDriver.delete_image`

        :param      image: the image to be deleted
        :type       image: :class:`NodeImage`

        :rtype: ``bool``
        """
        res = self.connection.request('/v2/images/%s' % (image.id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def ex_rename_node(self, node, name):
        params = {'type': 'rename', 'name': name}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.CREATED

    def ex_shutdown_node(self, node):
        params = {'type': 'shutdown'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.CREATED

    def ex_power_on_node(self, node):
        params = {'type': 'power_on'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.CREATED

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`KeyPair`
        """
        data = self.connection.request('/v2/account/keys').object['ssh_keys']
        return list(map(self._to_key_pairs, data))

    def create_key_pair(self, name, public_key):
        """
        Create a new SSH key.

        :param      name: Key name (required)
        :type       name: ``str``

        :param      public_key: Valid public key string (required)
        :type       public_key: ``str``
        """
        params = {'name': name, 'public_key': public_key}
        data = self.connection.request('/v2/account/keys', method='POST',
                                       params=params).object['ssh_key']
        return self._to_key_pairs(data=data)

    def delete_key_pair(self, key):
        """
        Delete an existing SSH key.

        :param      key: SSH key (required)
        :type       key: :class:`KeyPair`
        """
        key_id = key.extra['id']
        res = self.connection.request('/v2/account/keys/%s' % (key_id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def _paginated_request(self, url, obj):
        """
            Perform multiple calls in order to have a full list of elements
            when the API are paginated.
        """
        params = {}
        data = self.connection.request(url)
        try:
            pages = data.object['links']['pages']['last'].split('=')[-1]
            values = data.object[obj]
            for page in range(2, int(pages) + 1):
                params.update({'page': page})
                new_data = self.connection.request(url, params=params)

                more_values = new_data.object[obj]
                for value in more_values:
                    values.append(value)
            data = values
        except KeyError:  # No pages.
            data = data.object[obj]

        return data

    def _to_node(self, data):
        extra_keys = ['memory', 'vcpus', 'disk', 'region', 'image',
                      'size_slug', 'locked', 'created_at', 'networks',
                      'kernel', 'backup_ids', 'snapshot_ids', 'features']
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        networks = data['networks']
        private_ips = []
        public_ips = []
        if networks:
            for net in networks['v4']:
                if net['type'] == 'private':
                    private_ips = [net['ip_address']]
                if net['type'] == 'public':
                    public_ips = [net['ip_address']]

        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'], name=data['name'], state=state,
                    public_ips=public_ips, private_ips=private_ips,
                    extra=extra, driver=self)
        return node

    def _to_image(self, data):
        extra = {'distribution': data['distribution'],
                 'public': data['public'],
                 'slug': data['slug'],
                 'regions': data['regions'],
                 'min_disk_size': data['min_disk_size'],
                 'created_at': data['created_at']}
        return NodeImage(id=data['id'], name=data['name'], extra=extra,
                         driver=self)

    def _to_location(self, data):
        return NodeLocation(id=data['slug'], name=data['name'], country=None,
                            driver=self)

    def _to_size(self, data):
        extra = {'vcpus': data['vcpus'],
                 'regions': data['regions']}
        return NodeSize(id=data['slug'], name=data['slug'], ram=data['memory'],
                        disk=data['disk'], bandwidth=data['transfer'],
                        price=data['price_hourly'], driver=self, extra=extra)

    def _to_key_pairs(self, data):
        extra = {'id': data['id']}
        return KeyPair(name=data['name'],
                       fingerprint=data['fingerprint'],
                       public_key=data['public_key'],
                       private_key=None,
                       driver=self,
                       extra=extra)
