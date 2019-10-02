from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize, NodeImage
from libcloud.compute.base import KeyPair
from libcloud.common.maxihost import MaxihostConnection
from libcloud.compute.types import Provider, NodeState

from  libcloud.common.exceptions import BaseHTTPError

from libcloud.utils.py3 import httplib


import json


__all__ = [
    "MaxihostNodeDriver"
]

class MaxihostNodeDriver(NodeDriver):
    """
    Base Maxihost node driver.
    """

    connectionCls = MaxihostConnection
    type = Provider.MAXIHOST
    name = 'Maxihost'

    def create_node(self, name, size, image, location,
                    ex_ssh_key_ids=None):
        """
        Create a node.
        :return: The newly created node.
        :rtype: :class:`Node`
        """
        attr = {'hostname': name, 'plan': size.id,
                'operating_system': image.id,
                'facility': location.id.lower(), 'billing_cycle': 'monthly'}

        if ex_ssh_key_ids:
            attr['ssh_keys'] = ex_ssh_key_ids

        try:
            res = self.connection.request('/devices',
                                          data=json.dumps(attr), method='POST')
        except BaseHTTPError as exc:
            error_message = exc.message.get('error_messages', '')
            raise ValueError('Failed to create node: %s' % (error_message))

        node = Node(id=0, name='dummy', private_ips=[], public_ips=[], driver=self, state='unknown', extra={})
        return node


    def ex_start_node(self, node):
        params = {"type": "power_on"}
        res = self.connection.request('/devices/%s/actions' % node.id, params=params, method='PUT')

        return res.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]


    def ex_stop_node(self, node):
        params = {"type": "power_off"}
        res = self.connection.request('/devices/%s/actions' % node.id, params=params, method='PUT')

        return res.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def destroy_node(self, node):
        """
        Destroy a node.
        """
        try:
            res = self.connection.request('/devices/%s' % node.id,
                                        method='DELETE')
        except BaseHTTPError as exc:
            error_message = exc.message.get('error_messages', '')
            raise ValueError('Failed to destroy node: %s' % (error_message))

        return res.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]


    def reboot_node(self, node):
        params = {"type": "power_cycle"}
        res = self.connection.request('/devices/%s/actions' % node.id, params=params, method='PUT')

        return res.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]


    def list_nodes(self):
        """
        List nodes

        :rtype: ``list`` of :class:`MaxihostNode`
        """
        response = self.connection.request('/devices', method='GET')
        nodes = [self._to_node(host)
                 for host in response.object['devices']]
        return nodes


    def _to_node(self, data):
        extra = {}
        private_ips = []
        public_ips = []
        for ip in data['ips']:
            if 'Private' in ip['ip_description']:
                private_ips.append(ip['ip_address'])
            else:
                public_ips.append(ip['ip_address'])

        if data['power_status']:
            state = NodeState.RUNNING
        else:
            state = NodeState.STOPPED

        for key in data:
            extra[key] = data[key]

        node = Node(id=data['id'], name=data['description'], state=state,
                    private_ips=private_ips, public_ips=public_ips,
                    driver=self, extra=extra)
        return node
        
    def list_locations(self, available=True):
        """
        List locations

        If available is True, show only locations which are available
        """
        locations = []
        data = self.connection.request('/regions')
        for location in data.object['regions']:
            if available:
                if location.get('available'):
                    locations.append(self._to_location(location))
            else:
                locations.append(self._to_location(location))
        return locations
    
    def _to_location(self, data):
        name = data.get('location').get('city', '')
        country = data.get('location').get('country', '')
        return NodeLocation(id=data['slug'], name=name, country=None,
                            driver=self)

    def list_sizes(self):
        """
        List sizes
        """
        sizes = []
        data = self.connection.request('/plans')
        for size in data.object['servers']:
                sizes.append(self._to_size(size))
        return sizes

    def _to_size(self, data):
        regions = []
        for region in data['regions']:
            if region.get('in_stock'):
                regions.append(region.get('code'))
        extra = {'specs': data['specs'],
                 'regions': regions}
        return NodeSize(id=data['slug'], name=data['name'], ram=data['specs']['memory']['total'],
                        disk=None, bandwidth=None,
                        price=None, driver=self, extra=extra)

    def list_images(self):
        """
        List images
        """
        images = []
        data = self.connection.request('/plans/operating-systems')
        for image in data.object['operating-systems']:
                images.append(self._to_image(image))
        return images

    def _to_image(self, data):
        extra = {'operating_system': data['operating_system'],
                 'distro': data['distro'],
                 'version': data['version'],
                 'pricing': data['pricing']}
        return NodeImage(id=data['slug'], name=data['name'], driver=self,
                         extra=extra)


    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`KeyPair`
        """
        data = self.connection.request('/account/keys')
        return list(map(self._to_key_pair, data.object['ssh_keys']))


    def create_key_pair(self, name, public_key):
        """
        Create a new SSH key.

        :param name: Key name (required)
        :type name: ``str``

        :param public_key: Valid public key string (required)
        :type  public_key: ``str``
        """
        attr = {'name': name, 'public_key': public_key}
        res = self.connection.request('/account/keys', method='POST',
                                      data=json.dumps(attr))

        return self._to_key_pair(res.object)


    def _to_key_pair(self, data):
        extra = {'id': data['id']}
        return KeyPair(name=data['name'],
                       fingerprint=data['fingerprint'],
                       public_key=data['public_key'],
                       private_key=None,
                       driver=self,
                       extra=extra)
