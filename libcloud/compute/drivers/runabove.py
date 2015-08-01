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

from libcloud.common.runabove import API_ROOT, RunAboveConnection
from libcloud.compute.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.compute.base import NodeImage
from libcloud.compute.types import Provider
from libcloud.compute.drivers.openstack import OpenStackNodeDriver
from libcloud.compute.drivers.openstack import OpenStackKeyPair


class RunAboveNodeDriver(NodeDriver):
    """libcloud driver for the RunAbove API

    Rough mapping of which is which:

        list_nodes              linode.list
        reboot_node             linode.reboot
        destroy_node            linode.delete
        create_node             linode.create, linode.update,
                                linode.disk.createfromdistribution,
                                linode.disk.create, linode.config.create,
                                linode.ip.addprivate, linode.boot
        list_sizes              avail.linodeplans
        list_images             avail.distributions
        list_locations          avail.datacenters
        list_volumes            linode.disk.list
        destroy_volume          linode.disk.delete

    For more information on the Linode API, be sure to read the reference:

        http://www.linode.com/api/
    """
    type = Provider.RUNABOVE
    name = "RunAbove"
    website = 'https://www.runabove.com/'
    connectionCls = RunAboveConnection
    features = {'create_node': ['ssh_key']}
    api_name = 'runabove'

    NODE_STATE_MAP = OpenStackNodeDriver.NODE_STATE_MAP

    def __init__(self, key, secret, ex_consumer_key=None):
        """Instantiate the driver with the given API key

        :param   key: the API key to use (required)
        :type    key: ``str``

        :rtype: ``None``
        """
        self.datacenter = None
        self.consumer_key = ex_consumer_key
        NodeDriver.__init__(self, key, secret, ex_consumer_key=ex_consumer_key)

    def _ex_connection_class_kwargs(self):
        return {'ex_consumer_key': self.consumer_key}

    def _add_required_headers(self, headers, method, action, data, timestamp):
        timestamp = self.connection.get_timestamp()
        signature = self.connection.make_signature(method, action, data,
                                                   str(timestamp))
        headers.update({
            "X-Ra-Timestamp": timestamp,
            "X-Ra-Signature": signature
        })

    def list_nodes(self, location=None):
        """
        List all Linodes that the API key can access

        This call will return all Linodes that the API key in use has access
         to.
        If a node is in this list, rebooting will work; however, creation and
        destruction are a separate grant.

        :return: List of node objects that the API key can access
        :rtype: ``list`` of :class:`Node`
        """
        action = API_ROOT + '/instance'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_nodes(response.object)

    def ex_get_node(self, node_id):
        action = API_ROOT + '/instance/' + node_id
        response = self.connection.request(action, method='GET')
        return self._to_node(response.object)

    def reboot_node(self, node):
        raise NotImplementedError(
            "reboot_node not implemented for this driver")

    def create_node(self, **kwargs):
        action = API_ROOT + '/instance'
        data = {
            'name': kwargs["name"],
            'imageId': kwargs["image"].id,
            'flavorId': kwargs["size"].id,
            'region': kwargs["location"].id,
        }
        if kwargs.get('ex_keyname'):
            data['sshKeyName'] = kwargs['ex_keyname']
        response = self.connection.request(action, data=data, method='POST')
        return self._to_node(response.object)

    def destroy_node(self, node):
        action = API_ROOT + '/instance/' + node.id
        self.connection.request(action, method='DELETE')
        return True

    def list_sizes(self, location=None):
        """
        List available RunAbove flavors.

        :keyword location: the facility to retrieve plans in
        :type    location: :class:`NodeLocation`

        :rtype: ``list`` of :class:`NodeSize`
        """
        action = API_ROOT + '/flavor'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_sizes(response.object)

    def ex_get_size(self, size_id):
        action = API_ROOT + '/flavor/' + size_id
        response = self.connection.request(action)
        return self._to_size(response.object)

    def list_images(self, location=None, size=None):
        """
        List available Linux distributions

        Retrieve all Linux distributions that can be deployed to a Linode.

        :rtype: ``list`` of :class:`NodeImage`
        """
        action = API_ROOT + '/image'
        data = {}
        if location:
            data['region'] = location.id
        if size:
            data['flavorId'] = size.id
        response = self.connection.request(action, data=data)
        return self._to_images(response.object)

    def get_image(self, image_id):
        action = API_ROOT + '/image/' + image_id
        response = self.connection.request(action)
        return self._to_image(response.object)

    def list_locations(self):
        """
        List available facilities for deployment

        Retrieve all facilities that a Linode can be deployed in.

        :rtype: ``list`` of :class:`NodeLocation`
        """
        action = API_ROOT + '/region'
        data = self.connection.request(action)
        return self._to_locations(data.object)

    def list_key_pairs(self, location=None):
        action = API_ROOT + '/ssh'
        data = {}
        if location:
            data['region'] = location.id
        response = self.connection.request(action, data=data)
        return self._to_key_pairs(response.object)

    def get_key_pair(self, name, location):
        action = API_ROOT + '/ssh/' + name
        data = {'region': location.id}
        response = self.connection.request(action, data=data)
        return self._to_key_pair(response.object)

    def import_key_pair_from_string(self, name, key_material, location):
        """
        Import a new public key.

        :param name: Key pair name.
        :type name: ``str``

        :param key_material: Public key material.
        :type key_material: ``str``

        :return: Imported key pair object.
        :rtype: :class:`.KeyPair`
        """
        action = API_ROOT + '/ssh'
        data = {'name': name, 'publicKey': key_material, 'region': location.id}
        response = self.connection.request(action, data=data, method='POST')
        return self._to_key_pair(response.object)

    def delete_key_pair(self, name, location):
        """
        Delete an existing key pair.

        :param key_pair: Key pair object or ID.
        :type key_pair: :class.KeyPair` or ``int``

        :return:   True of False based on success of Keypair deletion
        :rtype:    ``bool``
        """
        action = API_ROOT + '/ssh/' + name
        data = {'name': name, 'region': location.id}
        self.connection.request(action, data=data, method='DELETE')
        return True

    def create_volume(self, size, name):
        raise NotImplementedError(
            "create_volume not implemented for this driver")

    def destroy_volume(self, volume):
        raise NotImplementedError(
            "destroy_volume not implemented for this driver")

    def ex_list_volumes(self, node, disk_id=None):
        raise NotImplementedError(
            "list_volumes not implemented for this driver")

    def _to_volume(self, obj):
        pass

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
