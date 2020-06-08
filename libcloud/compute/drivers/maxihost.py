
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

import json
import re
import hashlib
import json

from libcloud.compute.base import Node, NodeDriver, NodeLocation
from libcloud.compute.base import NodeSize, NodeImage
from libcloud.compute.base import KeyPair
from libcloud.common.maxihost import MaxihostConnection
from libcloud.compute.types import Provider, NodeState

from  libcloud.common.exceptions import BaseHTTPError

from libcloud.utils.py3 import httplib

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

    def _paginated_request(self, url, obj):
        """
        Perform multiple calls in order to have a full list of elements when
        the API responses are paginated.

        :param url: API endpoint
        :type url: ``str``

        :param obj: Result object key
        :type obj: ``str``

        :return: ``list`` of API response objects
        :rtype: ``list``
        """
        params = {}
        data = self.connection.request(url)
        try:
            pages = data.object['meta']['pages']['total']
            values = data.object[obj]
            for page in range(2, int(pages) + 1):
                params.update({'page': page})
                new_data = self.connection.request(url, params=params)

                for value in new_data.object[obj]:
                    values.append(value)
            data = values
        except KeyError:  # No pages.
            data = data.object[obj]
        return data


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

        node = Node(id=res.object['service_id'], name='dummy', private_ips=[],
                    public_ips=[], driver=self, state='unknown', extra={})
        return node


    def start_node(self, node):
        """
        Start a node.
        """
        params = {"type": "power_on"}
        res = self.connection.request('/devices/%s/actions' % node.id, params=params, method='PUT')

        return res.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def stop_node(self, node):
        """
        Stop a node.
        """
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
        data = self._paginated_request('/devices', 'devices')
        nodes = [self._to_node(host) for host in data]
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

        if data['status'] in ['On']:
            state = NodeState.RUNNING
        else:
            state = NodeState.STOPPED

        for key in data:
            extra[key] = data[key]

        name = data['description']
        _id = data['service_id'] or hashlib.sha1(name.encode()).hexdigest()
        node = Node(id=_id, name=name, state=state,
                    private_ips=private_ips, public_ips=public_ips,
                    driver=self, extra=extra)
        return node

    def list_locations(self, available=True):
        """
        List locations

        If available is True, show only locations which are available
        """
        locations = []
        data = self._paginated_request('/regions', 'regions')
        for location in data:
            if available:
                if location.get('available'):
                    locations.append(self._to_location(location))
            else:
                locations.append(self._to_location(location))
        return locations
    
    def _to_location(self, data):
        name = data.get('name')
        country = data.get('location').get('country', '')
        return NodeLocation(id=data['slug'], name=name, country=None,
                            driver=self)

    def list_sizes(self):
        """
        List sizes
        """
        sizes = []
        data = self._paginated_request('/plans', 'servers')
        for size in data:
            if size.get('deploy_type', '') in ['automated']:
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
        data = self._paginated_request('/plans/operating-systems', 'operating-systems')
        for image in data:
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
        keys = []
        data = self._paginated_request('/account/keys', 'ssh_keys')
        for key in data:
            keys.append(key)
        return list(map(self._to_key_pair, keys))


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

    def ex_start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.start_node(node=node)

    def ex_stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.stop_node(node=node)
