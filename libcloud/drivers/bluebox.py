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
import datetime
import hashlib
import base64
from xml.etree import ElementTree as ET

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
    'cost': 0.15
  },
  '2gb': {
    'id': 'b412f354-5056-4bf0-a42f-6ddd998aa092',
    'name': 'Block 2GB Virtual Server',
    'ram': 2048,
    'disk': 25,
    'cpu': 1,
    'cost': 0.25
  },
  '4gb': {
    'id': '0cd183d3-0287-4b1a-8288-b3ea8302ed58',
    'name': 'Block 4GB Virtual Server',
    'ram': 4096,
    'disk': 50,
    'cpu': 2,
    'cost': 0.35
  },
  '8gb': {
    'id': 'b9b87a5b-2885-4a2e-b434-44a163ca6251',
    'name': 'Block 8GB Virtual Server',
    'ram': 8192,
    'disk': 100,
    'cpu': 4,
    'cost': 0.45
  }
}

class BlueboxResponse(Response):

#    def __init__(self, response):
#        self.parsed = None
#        super(BlueboxResponse, self).__init__(response)

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)
        return self.body

    #def success(self):
    #    if not self.parsed:
    #        self.parsed = ET.XML(self.body)
    #    stat = self.parsed.get('stat')
    #    if stat != "ok":
    #        return False
    #    return True

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

BLUEBOX_INSTANCE_TYPES = {}
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
        result = self.connection.request('/api/blocks.xml', method='GET').object
        return self._to_nodes(result)

    def list_sizes(self, location=None):
        return [ NodeSize(driver=self.connection.driver, **i)
                    for i in BLUEBOX_INSTANCE_TYPES.values() ]

    def list_images(self, location=None):
        result = self.connection.request('/api/block_templates.xml', method='GET').object
        return self._to_images(result)

    def create_node(self, **kwargs):
        raise NotImplementedError, \
            'create_node not finished for voxel yet'
        size = kwargs["size"]
        cores = size.ram / RAM_PER_CPU
        params = {
                  'product':          kwargs["product"],
                  'template':         kwargs["template"],
                  'password':         kwargs["password"],
                  'ssh_key':          kwargs["ssh_key"],
                  'username':         kwargs["username"]
        }

        if params['username'] == "":
          params['username'] = "deploy"

        object = self.connection.request('/api/blocks.xml', method='POST').object

        if self._getstatus(object):
            return Node(
                id = object.findtext("hash/id"),
                hostname = object.findtext("hash/hostname"),
                state = NODE_STATE_MAP[object.findtext("hash/status")],
                public_ip = object.findtext("hash/ips/ip"),
                driver = self.connection.driver
            )
        else:
            return None

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        return self._getstatus(self.connection.request("/api/blocks/#{node.id}.xml", method='DELETE').object)

    def list_locations(self):
        raise NotImplementedError, \
          'list_locations not finished for bluebox yet'

    def _getstatus(self, element):
        status = element.attrib["stat"]
        return status == "ok"


#    def _to_locations(self, object):
#        return [NodeLocation(element.attrib["label"],
#                             element.findtext("description"),
#                             element.findtext("description"),
#                             self)
#                for element in object.findall('facilities/facility')]

    def _to_nodes(self, object):
        nodes = []
        for element in object.findall('records/record'):
            try:
                state = self.NODE_STATE_MAP[element.attrib['status']]
            except KeyError:
                state = NodeState.UNKNOWN

                public_ip = None
                ips = element.findall("ips")
                for ip in ips:
                    public_ip = ip.findtext("address")

                nodes.append(Node(id= element.attrib['id'],
                                 name=element.attrib['hostname'],
                                 state=state,
                                 public_ip= public_ip,
                                 driver=self.connection.driver))
        return nodes

    def _to_images(self, object):
        images = []
        for element in object.findall("records/record"):
            images.append(NodeImage(id = element.attrib["id"],
                                    name = element.attrib["description"],
                                    driver = self.connection.driver))
        return images
