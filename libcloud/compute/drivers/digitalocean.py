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
DigitalOcean Driver
"""
import json
import warnings

from libcloud.utils.iso8601 import parse_date
from libcloud.utils.py3 import httplib

from libcloud.common.digitalocean import DigitalOcean_v1_Error
from libcloud.common.digitalocean import DigitalOcean_v2_BaseDriver
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, KeyPair
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import StorageVolume

__all__ = [
    'DigitalOceanNodeDriver',
    'DigitalOcean_v2_NodeDriver'
]


class DigitalOceanNodeDriver(NodeDriver):
    """
    DigitalOcean NodeDriver defaulting to using APIv2.

    :keyword    key: Personal Access Token required for authentication.
    :type       key: ``str``

    :keyword    secret: Previously used with API version ``v1``. (deprecated)
    :type       secret: ``str``

    :keyword    api_version: Specifies the API version to use. Defaults to
                             using ``v2``, currently the only valid option.
                             (optional)
    :type       api_version: ``str``
    """
    type = Provider.DIGITAL_OCEAN
    name = 'DigitalOcean'
    website = 'https://www.digitalocean.com'

    def __new__(cls, key, secret=None, api_version='v2', **kwargs):
        if cls is DigitalOceanNodeDriver:
            if api_version == 'v1' or secret is not None:
                if secret is not None and api_version == 'v2':
                    raise InvalidCredsError(
                        'secret not accepted for v2 authentication')
                raise DigitalOcean_v1_Error()
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


class DigitalOcean_v2_NodeDriver(DigitalOcean_v2_BaseDriver,
                                 DigitalOceanNodeDriver):
    """
    DigitalOcean NodeDriver using v2 of the API.
    """

    NODE_STATE_MAP = {'new': NodeState.PENDING,
                      'off': NodeState.STOPPED,
                      'active': NodeState.RUNNING,
                      'archive': NodeState.TERMINATED}

    EX_CREATE_ATTRIBUTES = ['backups',
                            'ipv6',
                            'private_networking',
                            'ssh_keys']

    def list_images(self):
        data = self._paginated_request('/v2/images', 'images')
        return list(map(self._to_image, data))

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`KeyPair`
        """
        data = self._paginated_request('/v2/account/keys', 'ssh_keys')
        return list(map(self._to_key_pair, data))

    def list_locations(self):
        data = self._paginated_request('/v2/regions', 'regions')
        return list(map(self._to_location, data))

    def list_nodes(self):
        data = self._paginated_request('/v2/droplets', 'droplets')
        return list(map(self._to_node, data))

    def list_sizes(self):
        data = self._paginated_request('/v2/sizes', 'sizes')
        return list(map(self._to_size, data))

    def list_volumes(self):
        data = self._paginated_request('/v2/volumes', 'volumes')
        return list(map(self._to_volume, data))

    def create_node(self, name, size, image, location, ex_create_attr=None,
                    ex_ssh_key_ids=None, ex_user_data=None):
        """
        Create a node.

        The `ex_create_attr` parameter can include the following dictionary
        key and value pairs:

        * `backups`: ``bool`` defaults to False
        * `ipv6`: ``bool`` defaults to False
        * `private_networking`: ``bool`` defaults to False
        * `user_data`: ``str`` for cloud-config data
        * `ssh_keys`: ``list`` of ``int`` key ids or ``str`` fingerprints

        `ex_create_attr['ssh_keys']` will override `ex_ssh_key_ids` assignment.

        :keyword ex_create_attr: A dictionary of optional attributes for
                                 droplet creation
        :type ex_create_attr: ``dict``

        :keyword ex_ssh_key_ids: A list of ssh key ids which will be added
                                 to the server. (optional)
        :type ex_ssh_key_ids: ``list`` of ``int`` key ids or ``str``
                              key fingerprints

        :keyword    ex_user_data:  User data to be added to the node on create.
                                     (optional)
        :type       ex_user_data:  ``str``

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        attr = {'name': name, 'size': size.name, 'image': image.id,
                'region': location.id, 'user_data': ex_user_data}

        if ex_ssh_key_ids:
            warnings.warn("The ex_ssh_key_ids parameter has been deprecated in"
                          " favor of the ex_create_attr parameter.")
            attr['ssh_keys'] = ex_ssh_key_ids

        ex_create_attr = ex_create_attr or {}
        for key in ex_create_attr.keys():
            if key in self.EX_CREATE_ATTRIBUTES:
                attr[key] = ex_create_attr[key]

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

    def destroy_node(self, node):
        res = self.connection.request('/v2/droplets/%s' % (node.id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def reboot_node(self, node):
        attr = {'type': 'reboot'}
        res = self.connection.request('/v2/droplets/%s/actions' % (node.id),
                                      data=json.dumps(attr), method='POST')
        return res.status == httplib.CREATED

    def create_image(self, node, name):
        """
        Create an image from a Node.

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

    def get_image(self, image_id):
        """
        Get an image based on an image_id

        @inherits: :class:`NodeDriver.get_image`

        :param image_id: Image identifier
        :type image_id: ``int``

        :return: A NodeImage object
        :rtype: :class:`NodeImage`
        """
        data = self._paginated_request('/v2/images/%s' % (image_id), 'image')
        return self._to_image(data)

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

    def create_key_pair(self, name, public_key=''):
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

    def create_volume(self, size, name, location=None, snapshot=None):
        """
        Create a new volume.

        :param size: Size of volume in gigabytes (required)
        :type size: ``int``

        :param name: Name of the volume to be created
        :type name: ``str``

        :param location: Which data center to create a volume in. If
                               empty, undefined behavior will be selected.
                               (optional)
        :type location: :class:`.NodeLocation`

        :param snapshot:  Snapshot from which to create the new
                          volume.  (optional)
        :type snapshot: :class:`.VolumeSnapshot`

        :return: The newly created volume.
        :rtype: :class:`StorageVolume`
        """
        attr = {'name': name, 'size_gigabytes': size, 'region': location.id}

        res = self.connection.request('/v2/volumes', data=json.dumps(attr),
                                      method='POST')
        data = res.object['volume']
        status = res.object.get('status', 'OK')
        if status == 'ERROR':
            message = res.object.get('message', None)
            error_message = res.object.get('error_message', message)
            raise ValueError('Failed to create volume: %s' % (error_message))

        return self._to_volume(data=data)

    def destroy_volume(self, volume):
        """
        Destroys a storage volume.

        :param volume: Volume to be destroyed
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """
        res = self.connection.request('/v2/volumes/%s' % volume.id,
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def attach_volume(self, node, volume, device=None):
        """
        Attaches volume to node.

        :param node: Node to attach volume to.
        :type node: :class:`.Node`

        :param volume: Volume to attach.
        :type volume: :class:`.StorageVolume`

        :param device: Where the device is exposed, e.g. '/dev/sdb'
        :type device: ``str``

        :rytpe: ``bool``
        """
        attr = {'type': 'attach', 'droplet_id': node.id,
                'volume_id': volume.id, 'region': volume.extra['region_slug']}

        res = self.connection.request('/v2/volumes/actions',
                                      data=json.dumps(attr), method='POST')

        return res.status == httplib.ACCEPTED

    def detach_volume(self, volume):
        """
        Detaches a volume from a node.

        :param volume: Volume to be detached
        :type volume: :class:`.StorageVolume`

        :rtype: ``bool``
        """
        attr = {'type': 'detach', 'volume_id': volume.id,
                'region': volume.extra['region_slug']}

        responses = []
        for droplet_id in volume.extra['droplet_ids']:
            attr['droplet_id'] = droplet_id
            res = self.connection.request('/v2/volumes/actions',
                                          data=json.dumps(attr), method='POST')
            responses.append(res)

        return all([r.status == httplib.ACCEPTED for r in responses])

    def _to_node(self, data):
        extra_keys = ['memory', 'vcpus', 'disk', 'region', 'image',
                      'size_slug', 'locked', 'created_at', 'networks',
                      'kernel', 'backup_ids', 'snapshot_ids', 'features']
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        created = parse_date(data['created_at'])
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
                    created_at=created, driver=self, extra=extra)
        return node

    def _to_image(self, data):
        extra = {'distribution': data['distribution'],
                 'public': data['public'],
                 'slug': data['slug'],
                 'regions': data['regions'],
                 'min_disk_size': data['min_disk_size'],
                 'created_at': data['created_at']}
        return NodeImage(id=data['id'], name=data['name'], driver=self,
                         extra=extra)

    def _to_volume(self, data):
        extra = {'created_at': data['created_at'],
                 'droplet_ids': data['droplet_ids'],
                 'region': data['region'],
                 'region_slug': data['region']['slug']}

        return StorageVolume(id=data['id'], name=data['name'],
                             size=data['size_gigabytes'], driver=self,
                             extra=extra)

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
