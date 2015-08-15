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
RunAbove driver
"""
from libcloud.common.runabove import API_ROOT, RunAboveConnection
from libcloud.compute.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.compute.base import NodeImage, StorageVolume
from libcloud.compute.types import Provider, StorageVolumeState
from libcloud.compute.drivers.openstack import OpenStackNodeDriver
from libcloud.compute.drivers.openstack import OpenStackKeyPair


class RunAboveNodeDriver(NodeDriver):
    """
    Libcloud driver for the RunAbove API

    For more information on the RunAbove API, read the official reference:

        https://api.runabove.com/console/
    """
    type = Provider.RUNABOVE
    name = "RunAbove"
    website = 'https://www.runabove.com/'
    connectionCls = RunAboveConnection
    features = {'create_node': ['ssh_key']}
    api_name = 'runabove'

    NODE_STATE_MAP = OpenStackNodeDriver.NODE_STATE_MAP
    VOLUME_STATE_MAP = OpenStackNodeDriver.VOLUME_STATE_MAP

    def __init__(self, key, secret, ex_consumer_key=None):
        """
        Instantiate the driver with the given API credentials.

        :param key: Your application key (required)
        :type key: ``str``

        :param secret: Your application secret (required)
        :type secret: ``str``

        :param ex_consumer_key: Your consumer key (required)
        :type ex_consumer_key: ``str``

        :rtype: ``None``
        """
        self.datacenter = None
        self.consumer_key = ex_consumer_key
        NodeDriver.__init__(self, key, secret, ex_consumer_key=ex_consumer_key)

    def list_nodes(self, location=None):
        """
        List all nodes.

        :keyword location: Location (region) used as filter
        :type    location: :class:`NodeLocation`

        :return: List of node objects
        :rtype: ``list`` of :class:`Node`
        """
        action = API_ROOT + '/instance'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_nodes(response.object)

    def ex_get_node(self, node_id):
        """
        Get a individual node.

        :keyword node_id: Node's ID
        :type    node_id: ``str``

        :return: Created node
        :rtype  : :class:`Node`
        """
        action = API_ROOT + '/instance/' + node_id
        response = self.connection.request(action, method='GET')
        return self._to_node(response.object)

    def create_node(self, name, image, size, location, ex_keyname=None):
        """
        Create a new node

        :keyword name: Name of created node
        :type    name: ``str``

        :keyword image: Image used for node
        :type    image: :class:`NodeImage`

        :keyword size: Size (flavor) used for node
        :type    size: :class:`NodeSize`

        :keyword location: Location (region) where to create node
        :type    location: :class:`NodeLocation`

        :keyword ex_keyname: Name of SSH key used
        :type    ex_keyname: ``str``

        :retunrs: Created node
        :rtype  : :class:`Node`
        """
        action = API_ROOT + '/instance'
        data = {
            'name': name,
            'imageId': image.id,
            'flavorId': size.id,
            'region': location.id,
        }
        if ex_keyname is not None:
            data['sshKeyName'] = ex_keyname
        response = self.connection.request(action, data=data, method='POST')
        return self._to_node(response.object)

    def destroy_node(self, node):
        action = API_ROOT + '/instance/' + node.id
        self.connection.request(action, method='DELETE')
        return True

    def list_sizes(self, location=None):
        action = API_ROOT + '/flavor'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_sizes(response.object)

    def ex_get_size(self, size_id):
        """
        Get an individual size (flavor).

        :keyword size_id: Size's ID
        :type    size_id: ``str``

        :return: Size
        :rtype: :class:`NodeSize`
        """
        action = API_ROOT + '/flavor/' + size_id
        response = self.connection.request(action)
        return self._to_size(response.object)

    def list_images(self, location=None, ex_size=None):
        """
        List available images

        :keyword location: Location (region) used as filter
        :type    location: :class:`NodeLocation`

        :keyword ex_size: Exclude images which are uncompatible with given size
        :type    ex_size: :class:`NodeImage`

        :return: List of images
        :rtype  : ``list`` of :class:`NodeImage`
        """
        action = API_ROOT + '/image'
        data = {}
        if location:
            data['region'] = location.id
        if ex_size:
            data['flavorId'] = ex_size.id
        response = self.connection.request(action, data=data)
        return self._to_images(response.object)

    def get_image(self, image_id):
        action = API_ROOT + '/image/' + image_id
        response = self.connection.request(action)
        return self._to_image(response.object)

    def list_locations(self):
        action = API_ROOT + '/region'
        data = self.connection.request(action)
        return self._to_locations(data.object)

    def list_key_pairs(self, location=None):
        """
        List available SSH public keys.

        :keyword location: Location (region) used as filter
        :type    location: :class:`NodeLocation`

        :return: Public keys
        :rtype: ``list``of :class:`KeyPair`
        """
        action = API_ROOT + '/ssh'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_key_pairs(response.object)

    def get_key_pair(self, name, location):
        """
        Get an individual SSH public key by its name and location.

        :keyword name: SSH key name
        :type name: str

        :keyword location: Key's region
        :type location: :class:`NodeLocation`

        :return: Public key
        :rtype: :class:`KeyPair`
        """
        action = API_ROOT + '/ssh/' + name
        data = {'region': location.id}
        response = self.connection.request(action, data=data)
        return self._to_key_pair(response.object)

    def import_key_pair_from_string(self, name, key_material, location):
        """
        Import a new public key from string.

        :param name: Key pair name.
        :type name: ``str``

        :param key_material: Public key material.
        :type key_material: ``str``

        :return: Imported key pair object.
        :rtype: :class:`KeyPair`
        """
        action = API_ROOT + '/ssh'
        data = {'name': name, 'publicKey': key_material, 'region': location.id}
        response = self.connection.request(action, data=data, method='POST')
        return self._to_key_pair(response.object)

    def delete_key_pair(self, name, location):
        """
        Delete an existing key pair.

        :param name: Key pair name.
        :type name: ``str``

        :keyword location: Key's region
        :type location: :class:`NodeLocation`

        :return:   True of False based on success of Keypair deletion
        :rtype:    ``bool``
        """
        action = API_ROOT + '/ssh/' + name
        data = {'name': name, 'region': location.id}
        self.connection.request(action, data=data, method='DELETE')
        return True

    def create_volume(self, size, location, name=None,
                      ex_volume_type='classic', ex_description=None):
        """
        Create a volume.

        :param size: Size of volume to create (in GB).
        :type size: ``int``

        :param name: Name of volume to create
        :type name: ``str``

        :keyword location: Location to create the volume in
        :type location: :class:`NodeLocation` or ``None``

        :keyword ex_volume_type: ``'classic'`` or ``'high-speed'``
        :type ex_volume_type: ``str``

        :keyword ex_description: Optionnal description of volume
        :type ex_description: str

        :return:  Storage Volume object
        :rtype:   :class:`StorageVolume`
        """
        action = API_ROOT + '/volume'
        data = {
            'region': location.id,
            'size': str(size),
            'type': ex_volume_type,
        }
        if name:
            data['name'] = name
        if ex_description:
            data['description'] = ex_description
        response = self.connection.request(action, data=data, method='POST')
        return self._to_volume(response.object)

    def destroy_volume(self, volume):
        action = API_ROOT + '/volume/' + volume.id
        self.connection.request(action, method='DELETE')
        return True

    def list_volumes(self, location=None):
        """
        Return a list of volumes.

        :keyword location: Location use for filter
        :type location: :class:`NodeLocation` or ``None``

        :return: A list of volume objects.
        :rtype: ``list`` of :class:`StorageVolume`
        """
        action = API_ROOT + '/volume'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_volumes(response.object)

    def ex_get_volume(self, volume_id):
        """
        Return a Volume object based on a volume ID.

        :param  volume_id: The ID of the volume
        :type   volume_id: ``int``

        :return:  A StorageVolume object for the volume
        :rtype:   :class:`StorageVolume`
        """
        action = API_ROOT + '/volume/' + volume_id
        response = self.connection.request(action)
        return self._to_volume(response.object)

    def attach_volume(self, node, volume, device=None):
        """
        Attach a volume to a node.

        :param node: Node where to attach volume
        :type node: :class:`Node`

        :param volume: The ID of the volume
        :type volume: :class:`StorageVolume`

        :param device: Unsed parameter

        :return: True or False representing operation successful
        :rtype:   ``bool``
        """
        action = '%s/volume/%s/attach' % (API_ROOT, volume.id)
        data = {'instanceId': node.id}
        self.connection.request(action, data=data, method='POST')
        return True

    def detach_volume(self, volume, ex_node=None):
        """
        Detach a volume to a node.

        :param volume: The ID of the volume
        :type volume: :class:`StorageVolume`

        :param ex_node: Node to detach from (optionnal if volume is attached
                        to only one node)
        :type ex_node: :class:`Node`

        :return: True or False representing operation successful
        :rtype:   ``bool``

        :raises: Exception: If ``ex_node`` is not provided and more than one
                            node is attached to the volume
        """
        action = '%s/volume/%s/detach' % (API_ROOT, volume.id)
        if ex_node is None:
            if len(volume.extra['attachedTo']) != 1:
                err_msg = "Volume '%s' has more or less than one attached \
                    nodes, you must specify one."
                raise Exception(err_msg)
            ex_node = self.ex_get_node(volume.extra['attachedTo'][0])
        data = {'instanceId': ex_node.id}
        self.connection.request(action, data=data, method='POST')
        return True

    def _to_volume(self, obj):
        extra = obj.copy()
        extra.pop('id')
        extra.pop('name')
        extra.pop('size')
        state = self.VOLUME_STATE_MAP.get(obj.pop('status', None),
                                          StorageVolumeState.UNKNOWN)
        return StorageVolume(id=obj['id'], name=obj['name'], size=obj['size'],
                             state=state, extra=extra, driver=self)

    def _to_volumes(self, objs):
        return [self._to_volume(obj) for obj in objs]

    def _to_location(self, obj):
        location = self.connection.LOCATIONS[obj]
        return NodeLocation(driver=self, **location)

    def _to_locations(self, objs):
        return [self._to_location(obj) for obj in objs]

    def _to_node(self, obj):
        extra = obj.copy()
        if 'flavorId' in extra:
            public_ips = [obj.pop('ip')]
        else:
            ip = extra.pop('ipv4')
            public_ips = [ip] if ip else []
        del extra['instanceId']
        del extra['name']
        return Node(id=obj['instanceId'], name=obj['name'],
                    state=self.NODE_STATE_MAP[obj['status']],
                    public_ips=public_ips, private_ips=[], driver=self,
                    extra=extra)

    def _to_nodes(self, objs):
        return [self._to_node(obj) for obj in objs]

    def _to_size(self, obj):
        extra = {'vcpus': obj['vcpus'], 'type': obj['type'],
                 'region': obj['region']}
        return NodeSize(id=obj['id'], name=obj['name'], ram=obj['ram'],
                        disk=obj['disk'], bandwidth=None, price=None,
                        driver=self, extra=extra)

    def _to_sizes(self, objs):
        return [self._to_size(obj) for obj in objs]

    def _to_image(self, obj):
        extra = {'region': obj['region'], 'visibility': obj['visibility'],
                 'deprecated': obj['deprecated']}
        return NodeImage(id=obj['id'], name=obj['name'], driver=self,
                         extra=extra)

    def _to_images(self, objs):
        return [self._to_image(obj) for obj in objs]

    def _to_key_pair(self, obj):
        extra = {'region': obj['region']}
        return OpenStackKeyPair(name=obj['name'], public_key=obj['publicKey'],
                                driver=self, fingerprint=obj['fingerPrint'],
                                extra=extra)

    def _to_key_pairs(self, objs):
        return [self._to_key_pair(obj) for obj in objs]

    def _ex_connection_class_kwargs(self):
        return {'ex_consumer_key': self.consumer_key}

    def _add_required_headers(self, headers, method, action, data, timestamp):
        timestamp = self.connection.get_timestamp()
        signature = self.connection.make_signature(method, action, data,
                                                   str(timestamp))
        headers.update({
            'X-Ra-Timestamp': timestamp,
            'X-Ra-Signature': signature
        })
