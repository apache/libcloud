# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.	You may obtain a copy of the License at
#
#	  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
libcloud driver for the Host Virtual Inc. (VR) API
Home page http://www.vr.org/
"""

try:
    import simplejson as json
except ImportError:
    import json


from libcloud.utils.py3 import httplib

from libcloud.common.types import LibcloudError
from libcloud.compute.providers import Provider
from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.compute.types import NodeState, InvalidCredsError
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import NodeAuthSSHKey, NodeAuthPassword

API_HOST = 'www.vr.org'
API_ROOT = '/vapi'

#API_VERSION = '0.1'
NODE_STATE_MAP = {
    'BUILDING': NodeState.PENDING,
    'PENDING': NodeState.PENDING,
    'RUNNING': NodeState.RUNNING,  # server is powered up
    'STOPPING': NodeState.REBOOTING,
    'REBOOTING': NodeState.REBOOTING,
    'STARTING': NodeState.REBOOTING,
    'TERMINATED': NodeState.TERMINATED  # server is powered down
}


class HostVirtualException(LibcloudError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<HostVirtualException in %d : %s>" % (self.code, self.message)


class HostVirtualResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_body(self):
        if not self.body:
            return None

        data = json.loads(self.body)
        return data

    def parse_error(self):
        if self.status == 401:
            data = self.parse_body()
            raise InvalidCredsError(
                data['error']['code'] + ': ' + data['error']['message'])
        elif self.status == 412:
            data = self.parse_body()
            raise HostVirtualException(
                data['error']['code'], data['error']['message'])
        elif self.status == 404:
            data = self.parse_body()
            raise HostVirtualException(
                data['error']['code'], data['error']['message'])
        else:
            return self.body

    def success(self):
        return self.status in self.valid_response_codes


class HostVirtualConnection(ConnectionKey):
    host = API_HOST
    responseCls = HostVirtualResponse

    def add_default_params(self, params):
        params["key"] = self.key
        return params


class HostVirtualNodeDriver(NodeDriver):
    type = Provider.HOSTVIRTUAL
    name = 'HostVirtual'
    website = 'http://www.vr.org'
    connectionCls = HostVirtualConnection

    def __init__(self, key):
        self.location = None
        NodeDriver.__init__(self, key)

    def _to_node(self, data):
        state = NODE_STATE_MAP[data['status']]
        public_ips = []
        private_ips = []
        extra = {}

        public_ips.append(data['ip'])

        node = Node(id=data['mbpkgid'], name=data['fqdn'], state=state,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self.connection.driver, extra=extra)
        return node

    def list_locations(self):
        result = self.connection.request(API_ROOT + '/cloud/locations/').object
        locations = []
        for dc in result:
            locations.append(NodeLocation(
                dc["id"],
                dc["name"],
                dc["name"].split(',')[1].replace(" ", ""),  # country
                self))
        return locations

    def list_sizes(self, location=None):
        params = {}
        if location:
            params = {'location': location.id}
        result = self.connection.request(
            API_ROOT + '/cloud/sizes/',
            data=json.dumps(params)).object
        sizes = []
        for size in result:
            n = NodeSize(id=size['plan'],
                         name=size['plan'],
                         ram=size['ram'],
                         disk=size['disk'],
                         bandwidth=size['transfer'],
                         price=size['price'],
                         driver=self.connection.driver)
            sizes.append(n)
        return sizes

    def list_images(self):
        result = self.connection.request(API_ROOT + '/cloud/images/').object
        images = []
        for image in result:
            i = NodeImage(id=image["id"],
                          name=image["os"],
                          driver=self.connection.driver,
                          extra={
                              'hypervisor': image['tech'],
                              'arch': image['bits']})
            images.append(i)
        return images

    def list_nodes(self):
        result = self.connection.request(API_ROOT + '/cloud/servers/').object
        nodes = []
        for value in result:
            node = self._to_node(value)
            nodes.append(node)
        return nodes

    def create_node(self, **kwargs):
        name = kwargs['name']  # expects fqdn ex: test.com
        size = kwargs['size']
        image = kwargs['image']
        auth = kwargs['auth']
        dc = None

        if "location" in kwargs:
            dc = kwargs["location"].id
        else:
            dc = '3'

        params = {'fqdn': name,
                  'plan': size.id,
                  'image': image.id,
                  'location': dc
                  }

        ssh_key = None
        password = None
        if isinstance(auth, NodeAuthSSHKey):
            ssh_key = auth.pubkey
            params['ssh_key'] = ssh_key
        elif isinstance(auth, NodeAuthPassword):
            password = auth.password
            params['password'] = password

        if not ssh_key and not password:
            raise HostVirtualException(500, "Need SSH key or root password")

        if password is None:
            raise HostVirtualException(500, "Root password cannot be empty")

        result = self.connection.request(API_ROOT + '/cloud/buy_build',
                                         data=json.dumps(params),
                                         method='POST').object
        return self._to_node(result)

    def reboot_node(self, node):
        params = {'force': 0, 'mbpkgid': node.id}
        result = self.connection.request(
            API_ROOT + '/cloud/server/reboot',
            data=json.dumps(params),
            method='POST').object
        if result:
            return True

    def destroy_node(self, node):
        params = {'mbpkgid': node.id}
        result = self.connection.request(
            API_ROOT + '/cloud/cancel', data=json.dumps(params),
            method='POST').object
        if result:
            return True

    def ex_stop_node(self, node):
        params = {'force': 0, 'mbpkgid': node.id}
        result = self.connection.request(
            API_ROOT + '/cloud/server/stop',
            data=json.dumps(params),
            method='POST').object
        if result:
            return True

    def ex_start_node(self, node):
        params = {'mbpkgid': node.id}
        result = self.connection.request(
            API_ROOT + '/cloud/server/start',
            data=json.dumps(params),
            method='POST').object
        if result:
            return True
