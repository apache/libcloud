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
Brightbox Driver
"""
from libcloud.utils.py3 import httplib
import base64

from libcloud.utils.py3 import b

from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

try:
    import simplejson as json
except ImportError:
    import json

API_VERSION = '1.0'


class BrightboxResponse(JsonResponse):
    def success(self):
        return self.status >= 200 and self.status < 400

    def parse_body(self):
        if self.headers['content-type'].split('; ')[0] == 'application/json':
            return super(BrightboxResponse, self).parse_body()
        else:
            return self.body

    def parse_error(self):
        return super(BrightboxResponse, self).parse_body()['error']


class BrightboxConnection(ConnectionUserAndKey):
    """
    Connection class for the Brightbox driver
    """

    host = 'api.gb1.brightbox.com'
    responseCls = BrightboxResponse

    def _fetch_oauth_token(self):
        body = json.dumps({'client_id': self.user_id, 'grant_type': 'none'})

        authorization = 'Basic ' + str(base64.encodestring(b('%s:%s' %
                                        (self.user_id, self.key)))).rstrip()

        self.connect()

        response = self.connection.request(method='POST', url='/token', body=body, headers={
            'Host': self.host,
            'User-Agent': self._user_agent(),
            'Authorization': authorization,
            'Content-Type': 'application/json',
            'Content-Length': str(len(body))
        })

        response = self.connection.getresponse()

        if response.status == 200:
            return json.loads(response.read())['access_token']
        else:
            message = '%s (%s)' % (json.loads(response.read())['error'], response.status)

            raise InvalidCredsError(message)

    def add_default_headers(self, headers):
        try:
            headers['Authorization'] = 'OAuth ' + self.token
        except AttributeError:
            self.token = self._fetch_oauth_token()

            headers['Authorization'] = 'OAuth ' + self.token

        return headers

    def encode_data(self, data):
        return json.dumps(data)


class BrightboxNodeDriver(NodeDriver):
    """
    Brightbox node driver
    """

    connectionCls = BrightboxConnection

    type = Provider.BRIGHTBOX
    name = 'Brightbox'

    NODE_STATE_MAP = { 'creating': NodeState.PENDING,
                       'active': NodeState.RUNNING,
                       'inactive': NodeState.UNKNOWN,
                       'deleting': NodeState.UNKNOWN,
                       'deleted': NodeState.TERMINATED,
                       'failed': NodeState.UNKNOWN,
                       'unavailable': NodeState.UNKNOWN }

    def _to_node(self, data):
        return Node(
            id = data['id'],
            name = data['name'],
            state = self.NODE_STATE_MAP[data['status']],
            public_ips = list(map(lambda cloud_ip: cloud_ip['public_ip'],
                                                   data['cloud_ips'])),
            private_ips = list(map(lambda interface: interface['ipv4_address'],
                                                     data['interfaces'])),
            driver = self.connection.driver,
            extra = {
                'status': data['status'],
                'interfaces': data['interfaces']
            }
        )

    def _to_image(self, data):
        return NodeImage(
            id = data['id'],
            name = data['name'],
            driver = self,
            extra = {
                'description': data['description'],
                'arch': data['arch']
            }
        )

    def _to_size(self, data):
        return NodeSize(
            id = data['id'],
            name = data['name'],
            ram = data['ram'],
            disk = data['disk_size'],
            bandwidth = 0,
            price = 0,
            driver = self
        )

    def _to_location(self, data):
        return NodeLocation(
            id = data['id'],
            name = data['handle'],
            country = 'GB',
            driver = self
        )

    def _post(self, path, data={}):
        headers = {'Content-Type': 'application/json'}

        return self.connection.request(path, data=data, headers=headers, method='POST')

    def create_node(self, **kwargs):
        data = {
            'name': kwargs['name'],
            'server_type': kwargs['size'].id,
            'image': kwargs['image'].id,
            'user_data': ''
        }

        if 'location' in kwargs:
            data['zone'] = kwargs['location'].id
        else:
            data['zone'] = ''

        data = self._post('/%s/servers' % API_VERSION, data).object

        return self._to_node(data)

    def destroy_node(self, node):
        response = self.connection.request('/%s/servers/%s' % (API_VERSION, node.id), method='DELETE')

        return response.status == httplib.ACCEPTED

    def list_nodes(self):
        data = self.connection.request('/%s/servers' % API_VERSION).object

        return list(map(self._to_node, data))

    def list_images(self):
        data = self.connection.request('/%s/images' % API_VERSION).object

        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/%s/server_types' % API_VERSION).object

        return list(map(self._to_size, data))

    def list_locations(self):
        data = self.connection.request('/%s/zones' % API_VERSION).object

        return list(map(self._to_location, data))

    def ex_list_cloud_ips(self):
        return self.connection.request('/%s/cloud_ips' % API_VERSION).object

    def ex_create_cloud_ip(self):
        return self._post('/%s/cloud_ips' % API_VERSION).object

    def ex_map_cloud_ip(self, cloud_ip_id, interface_id):
        response = self._post('/%s/cloud_ips/%s/map' % (API_VERSION, cloud_ip_id), {'interface': interface_id})

        return response.status == httplib.ACCEPTED

    def ex_unmap_cloud_ip(self, cloud_ip_id):
        response = self._post('/%s/cloud_ips/%s/unmap' % (API_VERSION, cloud_ip_id))

        return response.status == httplib.ACCEPTED

    def ex_destroy_cloud_ip(self, cloud_ip_id):
        response = self.connection.request('/%s/cloud_ips/%s' % (API_VERSION, cloud_ip_id), method='DELETE')

        return response.status == httplib.OK
