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

    def __init__(self, response):
        self.parsed = None
        super(BlueboxResponse, self).__init__(response)

    def parse_body(self):
        if not self.body:
            return None
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        return self.parsed

    def parse_error(self):
        err_list = []
        if not self.body:
            return None
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        for err in self.parsed.findall('err'):
            code = err.get('code')
            err_list.append("(%s) %s" % (code, err.get('msg')))
            # From voxel docs:
            # 1: Invalid login or password
            # 9: Permission denied: user lacks access rights for this method
            if code == "1" or code == "9":
                # sucks, but only way to detect
                # bad authentication tokens so far
                raise InvalidCredsError(err_list[-1])
        return "\n".join(err_list)

    def success(self):
        if not self.parsed:
            self.parsed = ET.XML(self.body)
        stat = self.parsed.get('stat')
        if stat != "ok":
            return False
        return True

class BlueboxConnection(ConnectionUserAndKey):
    """
    Connection class for the Bluebox driver
    """

    host = BLUEBOX_API_HOST
    responseCls = BlueboxResponse

    def add_default_params(self, params):
        params["key"] = self.user_id
        params["timestamp"] = datetime.datetime.utcnow().isoformat()+"+0000"

        for param in params.keys():
            if params[param] is None:
                del params[param]

        keys = params.keys()
        keys.sort()

        md5 = hashlib.md5()
        md5.update(self.key)
        for key in keys:
            if params[key]:
                if not params[key] is None:
                    md5.update("%s%s"% (key, params[key]))
                else:
                    md5.update(key)
        params['api_sig'] = md5.hexdigest()
        return params

BLUEBOX_INSTANCE_TYPES = {}
RAM_PER_CPU = 2048

NODE_STATE_MAP = { 'IN_PROGRESS': NodeState.PENDING,
                   'SUCCEEDED': NodeState.RUNNING,
                   'shutting-down': NodeState.TERMINATED,
                   'terminated': NodeState.TERMINATED }

class BlueboxNodeDriver(NodeDriver):
    """
    Bluebox Blocks node driver
    """

    connectionCls = BlueboxConnection
    type = Provider.BLUEBOX
    name = 'Bluebox Blocks'

    def list_nodes(self):
        result = self.connection.request('/api/blocks.xml').object
        return self._to_nodes(result)

    def list_sizes(self, location=None):
        return [ NodeSize(driver=self.connection.driver, **i)
                    for i in BLUEBOX_INSTANCE_TYPES.values() ]

    def list_images(self, location=None):
        result = self.connection.request('/api/block_templates.xml').object
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

        object = self.connection.request('/api/blocks.xml', params=params, method='POST').object

        if self._getstatus(object):
            return Node(
                id = object.findtext("device/id"),
                name = kwargs["name"],
                state = NODE_STATE_MAP[object.findtext("devices/status")],
                public_ip = kwargs.get("publicip", None),
                private_ip = kwargs.get("privateip", None),
                driver = self.connection.driver
            )
        else:
            return None

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'method': 'voxel.devices.power',
                  'device_id': node.id,
                  'power_action': 'reboot'}
        return self._getstatus(self.connection.request('/', params=params).object)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'method': 'voxel.voxcloud.delete',
                  'device_id': node.id}
        return self._getstatus(self.connection.request('/', params=params).object)

    def list_locations(self):
        params = {"method": "voxel.voxcloud.facilities.list"}
        result = self.connection.request('/', params=params).object
        nodes = self._to_locations(result)
        return nodes

    def _getstatus(self, element):
        status = element.attrib["stat"]
        return status == "ok"


    def _to_locations(self, object):
        return [NodeLocation(element.attrib["label"],
                             element.findtext("description"),
                             element.findtext("description"),
                             self)
                for element in object.findall('facilities/facility')]

    def _to_nodes(self, object):
        nodes = []
        for element in object.findall('devices/device'):
            if element.findtext("type") == "Virtual Server":
                try:
                    state = self.NODE_STATE_MAP[element.attrib['status']]
                except KeyError:
                    state = NodeState.UNKNOWN

                public_ip = private_ip = None
                ipassignments = element.findall("ipassignments/ipassignment")
                for ip in ipassignments:
                    if ip.attrib["type"] =="frontend":
                        public_ip = ip.text
                    elif ip.attrib["type"] == "backend":
                        private_ip = ip.text

                nodes.append(Node(id= element.attrib['id'],
                                 name=element.attrib['label'],
                                 state=state,
                                 public_ip= public_ip,
                                 private_ip= private_ip,
                                 driver=self.connection.driver))
        return nodes

    def _to_images(self, object):
        images = []
        for element in object.findall("images/image"):
            images.append(NodeImage(id = element.attrib["id"],
                                    name = element.attrib["summary"],
                                    driver = self.connection.driver))
        return images
