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
Bluebox Blocks driver
"""
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsError
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver
from libcloud.base import NodeSize, NodeImage, NodeLocation
from libcloud.base import NodeAuthPassword, NodeAuthSSHKey
import datetime
import hashlib
import urllib
import base64

try: import json
except: import simplejson as json

BLUEBOX_API_HOST = "boxpanel.blueboxgrp.com"

# Since Bluebox doesn't provide a list of available VPS types through their
# API, we list them explicitly here.

BLUEBOX_INSTANCE_TYPES = {
  '1gb': {
    'id': '94fd37a7-2606-47f7-84d5-9000deda52ae',
    'name': 'Block 1GB Virtual Server',
    'ram': 1024,
    'disk': 20,
    'cpu': 0.5,
    'price': 0.15
  },
  '2gb': {
    'id': 'b412f354-5056-4bf0-a42f-6ddd998aa092',
    'name': 'Block 2GB Virtual Server',
    'ram': 2048,
    'disk': 25,
    'cpu': 1,
    'price': 0.25
  },
  '4gb': {
    'id': '0cd183d3-0287-4b1a-8288-b3ea8302ed58',
    'name': 'Block 4GB Virtual Server',
    'ram': 4096,
    'disk': 50,
    'cpu': 2,
    'price': 0.35
  },
  '8gb': {
    'id': 'b9b87a5b-2885-4a2e-b434-44a163ca6251',
    'name': 'Block 8GB Virtual Server',
    'ram': 8192,
    'disk': 100,
    'cpu': 4,
    'price': 0.45
  }
}

class BlueboxResponse(Response):

#    def __init__(self, response):
#        self.parsed = None
#        super(BlueboxResponse, self).__init__(response)

    def parse_body(self):
        try:
            js = json.loads(self.body)
            return js
        except ValueError:
            return self.body

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)
        return self.body

class BlueboxNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, disk, price, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.price = price
        self.driver = driver

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s, disk=%s, price=%s, driver=%s ...>')
               % (self.id, self.name, self.cpu, self.ram, self.disk, self.price, self.driver.name))

class BlueboxConnection(ConnectionUserAndKey):
    """
    Connection class for the Bluebox driver
    """

    host = BLUEBOX_API_HOST
    secure = True
    responseCls = BlueboxResponse

    def add_default_headers(self, headers):
        user_b64 = base64.b64encode('%s:%s' % (self.user_id, self.key))
        headers['Authorization'] = 'Basic %s' % (user_b64)
        return headers

RAM_PER_CPU = 2048

NODE_STATE_MAP = { 'queued': NodeState.PENDING,
                   'building': NodeState.PENDING,
                   'running': NodeState.RUNNING,
                   'error': NodeState.TERMINATED,
                   'unknown': NodeState.UNKNOWN }

class BlueboxNodeDriver(NodeDriver):
    """
    Bluebox Blocks node driver
    """

    connectionCls = BlueboxConnection
    type = Provider.BLUEBOX
    name = 'Bluebox Blocks'

    def list_nodes(self):
        result = self.connection.request('/api/blocks.json')
        return [self._to_node(i) for i in result.object]

    def list_sizes(self, location=None):
        return [ BlueboxNodeSize(driver=self.connection.driver, **i)
                    for i in BLUEBOX_INSTANCE_TYPES.values() ]

    def list_images(self, location=None):
        result = self.connection.request('/api/block_templates.json')
        images = []
        for image in result.object:
          images.extend([self._to_image(image)])
          
        return images

    def create_node(self, **kwargs):
        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        size = kwargs["size"]
        cores = size.ram / RAM_PER_CPU

        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        auth = kwargs['auth']
        
        data = {
            'hostname': name,
            'product': size.id,
            'template': image.id
        }

        ssh = None
        password = None

        if isinstance(auth, NodeAuthSSHKey):
            ssh = auth.pubkey
            data.update(ssh_public_key=ssh)
        elif isinstance(auth, NodeAuthPassword):
            password = auth.password
            data.update(password=password)

        if "ex_username" in kwargs:
            data.update(username=kwargs["ex_username"])

        if not ssh and not password:
            raise Exception("SSH public key or password required.")

        params = urllib.urlencode(data)
        result = self.connection.request('/api/blocks.json', headers=headers, data=params, method='POST')
        node = self._to_node(result.object)
        return node

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        url = '/api/blocks/%s.json' % (node.id)
        result = self.connection.request(url, method='DELETE')

        return result.status == 200

    def list_locations(self):
        return [NodeLocation(0, "Blue Box Seattle US", 'US', self)]

    def reboot_node(self, node):
        url = '/api/blocks/%s/reboot.json' % (node.id)
        result = self.connection.request(url, method="PUT")
        node = self._to_node(result.object)
        return result.status == 200

    def _to_node(self, vm):
        try:
            state = NODE_STATE_MAP[vm['status']]
        except KeyError:
            state = NodeState.UNKNOWN
        n = Node(id=vm['id'],
                 name=vm['hostname'],
                 state=state,
                 public_ip=[ ip['address'] for ip in vm['ips'] ],
                 private_ip=[],
                 extra={'storage':vm['storage'], 'cpu':vm['cpu']},
                 driver=self.connection.driver)
        return n

    def _to_image(self, image):
        image = NodeImage(id=image['id'],
                          name=image['description'],
                          driver=self.connection.driver)
        return image
