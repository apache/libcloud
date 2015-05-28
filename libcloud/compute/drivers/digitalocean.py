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
import json
import warnings

from libcloud.utils.py3 import httplib

from libcloud.common.digitalocean import DigitalOcean_v1_BaseDriver
from libcloud.common.digitalocean import DigitalOcean_v2_BaseDriver
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, KeyPair

__all__ = [
    'DigitalOceanNodeDriver',
    'DigitalOcean_v1_NodeDriver',
    'DigitalOcean_v2_NodeDriver'
]


class DigitalOceanNodeDriver(NodeDriver):
    """
    DigitalOcean NodeDriver defaulting to using APIv2.

    :keyword    key: Required for authentication. Used in both ``v1`` and
                     ``v2`` implementations.
    :type       key: ``str``

    :keyword    secret: Used in driver authentication with key. Defaults to
                        None and when set, will cause driver to use ``v1`` for
                        connection and response. (optional)
    :type       secret: ``str``

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
            if api_version == 'v1' or secret is not None:
                if secret is None:
                    raise InvalidCredsError(
                        'secret missing for v1 authentication')
                if secret is not None and api_version == 'v2':
                    raise InvalidCredsError(
                        'secret not accepted for v2 authentication')
                cls = DigitalOcean_v1_NodeDriver
            elif api_version == 'v2':
                cls = DigitalOcean_v2_NodeDriver
            else:
                raise NotImplementedError('Unsupported API version: %s' %
                                          (api_version))
        return super(DigitalOceanNodeDriver, cls).__new__(cls, **kwargs)


# TODO Implement v1 driver using KeyPair
class SSHKey(object):
    def __init__(self, id, name, pub_key):
        self.id = id
        self.name = name
        self.pub_key = pub_key

    def __repr__(self):
        return (('<SSHKey: id=%s, name=%s, pub_key=%s>') %
                (self.id, self.name, self.pub_key))


class DigitalOcean_v1_NodeDriver(DigitalOcean_v1_BaseDriver,
                                 DigitalOceanNodeDriver):
    """
    DigitalOcean NodeDriver using v1 of the API.
    """

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

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`KeyPair`
        """
        data = self.connection.request('/v1/ssh_keys').object['ssh_keys']
        return list(map(self._to_key_pair, data))

    def ex_list_ssh_keys(self):
        """
        List all the available SSH keys.
        :return: Available SSH keys.
        :rtype: ``list`` of :class:`SSHKey`
        """
        warnings.warn("This method has been deprecated in "
                      "favor of the list_key_pairs method")

        data = self.connection.request('/v1/ssh_keys').object['ssh_keys']
        return list(map(self._to_ssh_key, data))

    def get_key_pair(self, name):
        """
        Retrieve a single key pair.

        :param name: Name of the key pair to retrieve.
        :type name: ``str``

        :rtype: :class:`.KeyPair`
        """
        qkey = [k for k in self.list_key_pairs() if k.name == name][0]
        data = self.connection.request('/v1/ssh_keys/%s' %
                                       qkey.extra['id']).object['ssh_key']
        return self._to_key_pair(data=data)

    # TODO: This adds the ssh_key_pub parameter. This puts the burden of making
    #      it within the function or on the API. The KeyPair API needs work.
    def create_key_pair(self, name, ssh_key_pub):
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
        # TODO: libcloud.compute.base.KeyPair.create_key_pair doesn't specify
        #      a return value. This looks like it should return a KeyPair
        return self._to_key_pair(data=data['ssh_key'])

    def ex_create_ssh_key(self, name, ssh_key_pub):
        """
        Create a new SSH key.
        :param      name: Key name (required)
        :type       name: ``str``
        :param      name: Valid public key string (required)
        :type       name: ``str``
        """
        warnings.warn("This method has been deprecated in "
                      "favor of the create_key_pair method")

        params = {'name': name, 'ssh_pub_key': ssh_key_pub}
        data = self.connection.request('/v1/ssh_keys/new/', method='GET',
                                       params=params).object
        assert 'ssh_key' in data
        return self._to_ssh_key(data=data['ssh_key'])

    def delete_key_pair(self, key_pair):
        """
        Delete an existing key pair.

        :param key_pair: Key pair object.
        :type key_pair: :class:`.KeyPair`
        """
        res = self.connection.request('/v1/ssh_keys/%s/destroy/' %
                                      key_pair.extra['id'])
        # TODO: This looks like it should return bool like the other delete_*
        return res.status == httplib.OK

    def ex_destroy_ssh_key(self, key_id):
        """
        Delete an existing SSH key.
        :param      key_id: SSH key id (required)
        :type       key_id: ``str``
        """
        warnings.warn(
            "This method has been deprecated in "
            "favor of the delete_key_pair method")

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

    def _to_key_pair(self, data):
        try:
            pubkey = data['ssh_pub_key']
        except KeyError:
            pubkey = None
        return KeyPair(data['name'], public_key=pubkey, fingerprint=None,
                       driver=self, private_key=None, extra={'id': data['id']})

    def _to_ssh_key(self, data):
        return SSHKey(id=data['id'], name=data['name'],
                      pub_key=data.get('ssh_pub_key', None))


class DigitalOcean_v2_NodeDriver(DigitalOcean_v2_BaseDriver,
                                 DigitalOceanNodeDriver):
    """
    DigitalOcean NodeDriver using v2 of the API.
    """

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
        attr = {'name': name, 'size': size.name, 'image': image.id,
                'region': location.id}

        if ex_ssh_key_ids:
            attr['ssh_keys'] = ex_ssh_key_ids

        res = self.connection.request('/v2/droplets',
                                      data=json.dumps(attr), method='POST')

        data = res.object['droplet']
        # TODO: Handle this in the response class
        status = res.object.get('status', 'OK')
        if status == 'ERROR':
            message = res.object.get('message', None)
            error_message = res.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))

        return self._to_node(data=data)

    def reboot_node(self, node):
        attr = {'type': 'reboot'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
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
        attr = {'type': 'snapshot', 'name': name}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
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
        attr = {'type': 'rename', 'name': name}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
        return res.status == httplib.CREATED

    def ex_shutdown_node(self, node):
        attr = {'type': 'shutdown'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
        return res.status == httplib.CREATED

    def ex_power_on_node(self, node):
        attr = {'type': 'power_on'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
        return res.status == httplib.CREATED

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`KeyPair`
        """
        data = self._paginated_request('/v2/account/keys', 'ssh_keys')
        return list(map(self._to_key_pair, data))

    def get_key_pair(self, name):
        """
        Retrieve a single key pair.

        :param name: Name of the key pair to retrieve.
        :type name: ``str``

        :rtype: :class:`.KeyPair`
        """
        qkey = [k for k in self.list_key_pairs() if k.name == name][0]
        data = self.connection.request('/v2/account/keys/%s' %
                                       qkey.extra['id']).object['ssh_key']
        return self._to_key_pair(data=data)

    def create_key_pair(self, name, public_key):
        """
        Create a new SSH key.

        :param      name: Key name (required)
        :type       name: ``str``

        :param      public_key: Valid public key string (required)
        :type       public_key: ``str``
        """
        attr = {'name': name, 'public_key': public_key}
        res = self.connection.request('/v2/account/keys', method='POST',
                                      data=json.dumps(attr))

        data = res.object['ssh_key']

        return self._to_key_pair(data=data)

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

    def _to_key_pair(self, data):
        extra = {'id': data['id']}
        return KeyPair(name=data['name'],
                       fingerprint=data['fingerprint'],
                       public_key=data['public_key'],
                       private_key=None,
                       driver=self,
                       extra=extra)
