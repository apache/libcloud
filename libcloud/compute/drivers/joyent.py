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
Joyent Cloud (http://www.joyentcloud.com) driver.
"""

import base64

try:
    import simplejson as json
except:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.types import LibcloudError
from libcloud.compute.providers import Provider
from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.compute.base import is_private_subnet
from libcloud.compute.types import NodeState, InvalidCredsError
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeSize

API_HOST_SUFFIX = '.api.joyentcloud.com'
API_VERSION = '~6.5'


NODE_STATE_MAP = {
    'provisioning': NodeState.PENDING,
    'running': NodeState.RUNNING,
    'stopping': NodeState.TERMINATED,
    'stopped': NodeState.TERMINATED,
    'deleted': NodeState.TERMINATED
}

LOCATIONS = ['us-east-1', 'us-west-1', 'us-sw-1', 'eu-ams-1']
DEFAULT_LOCATION = LOCATIONS[0]


class JoyentResponse(JsonResponse):
    """
    Joyent response class.
    """

    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_error(self):
        if self.status == 401:
            data = self.parse_body()
            raise InvalidCredsError(data['code'] + ': ' + data['message'])
        return self.body

    def success(self):
        return self.status in self.valid_response_codes


class JoyentConnection(ConnectionUserAndKey):
    """
    Joyent connection class.
    """

    responseCls = JoyentResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json; charset=UTF-8'
        headers['X-Api-Version'] = API_VERSION

        user_b64 = base64.b64encode(b('%s:%s' % (self.user_id, self.key)))
        headers['Authorization'] = 'Basic %s' % (user_b64.decode('utf-8'))
        return headers


class JoyentNodeDriver(NodeDriver):
    """
    Joyent node driver class.
    """

    type = Provider.JOYENT
    name = 'Joyent'
    website = 'http://www.joyentcloud.com'
    connectionCls = JoyentConnection
    features = {'create_node': ['generates_password']}

    def __init__(self, *args, **kwargs):
        """
        @inherits: L{NodeDriver.__init__}

        @keyword    location: Location which should be used
        @type       location: C{str}
        """
        if 'location' in kwargs:
            if kwargs['location'] not in LOCATIONS:
                msg = 'Invalid location: "%s". Valid locations: %s'
                raise LibcloudError(msg % (kwargs['location'],
                                    ', '.join(LOCATIONS)), driver=self)
        else:
            kwargs['location'] = DEFAULT_LOCATION

        super(JoyentNodeDriver, self).__init__(*args, **kwargs)
        self.connection.host = kwargs['location'] + API_HOST_SUFFIX

    def list_images(self):
        result = self.connection.request('/my/datasets').object

        images = []
        for value in result:
            extra = {'type': value['type'], 'urn': value['urn'],
                     'os': value['os'], 'default': value['default']}
            image = NodeImage(id=value['id'], name=value['name'],
                              driver=self.connection.driver, extra=extra)
            images.append(image)

        return images

    def list_sizes(self):
        result = self.connection.request('/my/packages').object

        sizes = []
        for value in result:
            size = NodeSize(id=value['name'], name=value['name'],
                            ram=value['memory'], disk=value['disk'],
                            bandwidth=None, price=0.0,
                            driver=self.connection.driver)
            sizes.append(size)

        return sizes

    def list_nodes(self):
        result = self.connection.request('/my/machines').object

        nodes = []
        for value in result:
            node = self._to_node(value)
            nodes.append(node)

        return nodes

    def reboot_node(self, node):
        data = json.dumps({'action': 'reboot'})
        result = self.connection.request('/my/machines/%s' % (node.id),
                                         data=data, method='POST')
        return result.status == httplib.ACCEPTED

    def destroy_node(self, node):
        result = self.connection.request('/my/machines/%s' % (node.id),
                                         method='DELETE')
        return result.status == httplib.NO_CONTENT

    def create_node(self, **kwargs):
        name = kwargs['name']
        size = kwargs['size']
        image = kwargs['image']

        data = json.dumps({'name': name, 'package': size.id,
                           'dataset': image.id})
        result = self.connection.request('/my/machines', data=data,
                                         method='POST')
        return self._to_node(result.object)

    def ex_stop_node(self, node):
        """
        Stop node

        @param  node: The node to be stopped
        @type   node: L{Node}

        @rtype: C{bool}
        """
        data = json.dumps({'action': 'stop'})
        result = self.connection.request('/my/machines/%s' % (node.id),
                                         data=data, method='POST')
        return result.status == httplib.ACCEPTED

    def ex_start_node(self, node):
        """
        Start node

        @param  node: The node to be stopped
        @type   node: L{Node}

        @rtype: C{bool}
        """
        data = json.dumps({'action': 'start'})
        result = self.connection.request('/my/machines/%s' % (node.id),
                                         data=data, method='POST')
        return result.status == httplib.ACCEPTED

    def _to_node(self, data):
        state = NODE_STATE_MAP[data['state']]
        public_ips = []
        private_ips = []
        extra = {}

        for ip in data['ips']:
            if is_private_subnet(ip):
                private_ips.append(ip)
            else:
                public_ips.append(ip)

        if 'credentials' in data['metadata']:
            extra['password'] = data['metadata']['credentials']['root']

        node = Node(id=data['id'], name=data['name'], state=state,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self.connection.driver, extra=extra)
        return node
