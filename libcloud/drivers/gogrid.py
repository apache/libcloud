# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
GoGrid driver
"""
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, ConnectionUserAndKey, Response, NodeDriver, NodeSize, NodeImage, NodeLocation
from libcloud.interface import INodeDriver
from zope.interface import implements
import httplib
import time
import urllib
import md5, hashlib

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json

HOST = 'api.gogrid.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
API_VERSION = '1.3'

STATE = {
    "Starting": NodeState.PENDING,
    "On": NodeState.RUNNING,
    "Off": NodeState.PENDING,
    "Restarting": NodeState.REBOOTING,
    "Saving": NodeState.PENDING,
    "Restoring": NodeState.PENDING,
}

GOGRID_INSTANCE_TYPES = {'512MB': {'id': '512MB',
                       'name': '512MB',
                       'ram': 512,
                       'disk': 30,
                       'bandwidth': None,
                       'price':0.095},
        '1GB': {'id': '1GB',
                       'name': '1GB',
                       'ram': 1024,
                       'disk': 60,
                       'bandwidth': None,
                       'price':0.19},
        '2GB': {'id': '2GB',
                       'name': '2GB',
                       'ram': 2048,
                       'disk': 120,
                       'bandwidth': None,
                       'price':0.38},
        '4GB': {'id': '4GB',
                       'name': '4GB',
                       'ram': 4096,
                       'disk': 240,
                       'bandwidth': None,
                       'price':0.76},
        '8GB': {'id': '8GB',
                       'name': '8GB',
                       'ram': 8192,
                       'disk': 480,
                       'bandwidth': None,
                       'price':1.52}}


class GoGridResponse(Response):
    def success(self):
        if not self.body:
            return None
        return json.loads(self.body)['status'] == 'success'

    def parse_body(self):
        if not self.body:
            return None
        return json.loads(self.body)

    def parse_error(self):
        if not self.object:
            return None
        return self.object['message']

class GoGridConnection(ConnectionUserAndKey):

    host = HOST
    responseCls = GoGridResponse

    def add_default_params(self, params):
        params["api_key"] = self.user_id
        params["v"] = API_VERSION
        params["format"] = 'json'
        params["sig"] = self.get_signature(self.user_id, self.key)

        return params
        
    def get_signature(self, key, secret):
        """ create sig from md5 of key + secret + time """
        m = md5.new(key+secret+str(int(time.time())))
        return m.hexdigest()

class GoGridNode(Node):
    # Generating uuid based on public ip to get around missing id on create_node in gogrid api
    # Used public ip since it is not mutable and specified at create time, so uuid of node should not change after add is completed
    def get_uuid(self):
        return hashlib.sha1("%s:%d" % (self.public_ip,self.driver.type)).hexdigest()

class GoGridNodeDriver(NodeDriver):

    connectionCls = GoGridConnection
    type = Provider.GOGRID
    name = 'GoGrid API'

    _instance_types = GOGRID_INSTANCE_TYPES

    def get_state(self, element):
        try:
            return STATE[element['state']['name']]
        except:
            pass
        return NodeState.UNKNOWN

    def get_ip(self, element):
        return element['ip']['ip']

    def get_id(self,element):
        return element.get('id',None)

    def _to_node(self, element):
        state = self.get_state(element)
        ip = self.get_ip(element)
        id = self.get_id(element)
        n = GoGridNode(id=id,
                 name=element['name'],
                 state=state,
                 public_ip=ip,
                 private_ip=ip,
                 driver=self.connection.driver)
        return n

    def _to_image(self, element):
        n = NodeImage(id=element['id'],
                      name=element['friendlyName'],
                      driver=self.connection.driver)
        return n

    def _to_images(self, object):
        return [ self._to_image(el)
                 for el in object['list'] ]

    def list_images(self):
        images = self._to_images(
                    self.connection.request('/api/grid/image/list').object)
        return images

    def get_uuid(self, field):
        uuid_str = "%s:%s" % (field,self.connection.user_id)
        return hashlib.sha1(uuid_str).hexdigest()

    def list_nodes(self):
        res = self.server_list()
        return [ self._to_node(el)
                 for el
                 in res['list'] ]

    def reboot_node(self, node):
        id = node.id
        power = 'restart'
        res = self.server_power(id, power)
        if not res.success():
            raise Exception(res.parse_error())
        return True

    def destroy_node(self, node):
        id = node.attrs['id']
        res = self.server_delete(id)
        if not res.success():
            raise Exception(res.parse_error())
        return True

    def server_list(self):
        return self.connection.request('/api/grid/server/list').object

    def server_power(self, id, power):
        # power in ['start', 'stop', 'restart']
        params = {'id': id, 'power': power}
        return self.connection.request("/api/grid/server/power", params)

    def server_delete(self, id):
        params = {'id': id}
        return self.connection.request("/api/grid/server/delete", params).object

    def get_first_ip(self):
        params = {'ip.state': 'Unassigned', 'ip.type':'public'}
        object = self.connection.request("/api/grid/ip/list", params).object
        return object['list'][0]['ip']

    def list_sizes(self):
        return [ NodeSize(driver=self.connection.driver, **i) 
                    for i in self._instance_types.values() ]

    def list_locations(self):
        return [NodeLocation(0, "GoGrid Los Angeles", 'US', self)]

    def create_node(self, **kwargs):
        name = kwargs['name']
        image = kwargs['iamge']
        size = kwargs['size']
        first_ip = self.get_first_ip()
        params = {'name': name,
                  'image': image.id,
                  'description': kwargs.get('description',''),
                  'server.ram': size.id,
                  'ip':first_ip}

        object = self.connection.request('/api/grid/server/add', params=params).object
        node = self._to_node(object['list'][0])

        return node
