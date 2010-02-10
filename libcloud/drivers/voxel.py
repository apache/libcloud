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
Voxel VoxCloud driver
"""
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize, NodeImage, NodeLocation
import datetime
import hashlib
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

VOXEL_API_HOST = "api.voxel.net"

class VoxelResponse(Response):

   def parse_body(self):
       if not self.body:
           return None
       return ET.XML(self.body)

   def parse_error(self):
       try:
           err_list = []
           for err in ET.XML(self.body).findall('err'):
               code = err.attrib["code"]
               message = err.attrib["msg"]
               err_list.append("%s: %s" % (code.text, message.text))
           return "\n".join(err_list)
       except ExpatError:
           return self.body

class VoxelConnection(ConnectionUserAndKey):

   host = VOXEL_API_HOST
   responseCls = VoxelResponse
 
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

VOXEL_INSTANCE_TYPES = {}
RAM_PER_CPU = 2048

NODE_STATE_MAP = { 'IN_PROGRESS': NodeState.PENDING,
                  'SUCCEEDED': NodeState.RUNNING,
                  'shutting-down': NodeState.TERMINATED,
                  'terminated': NodeState.TERMINATED }

class VoxelNodeDriver(NodeDriver):

   connectionCls = VoxelConnection
   type = Provider.VOXEL
   name = 'Voxel VoxCLOUD'

   def initialize_instance_types():
       for cpus in range(1,14):
           if cpus == 1:
               name = "Single CPU"
           else:
               name = "%d CPUs" % cpus
           id = "%dcpu" % cpus
           ram = cpus * RAM_PER_CPU

           VOXEL_INSTANCE_TYPES[id]= { 
                        'id': id,
                        'name': name,
                        'ram': ram,
                        'disk': None,
                        'bandwidth': None,
                        'price': None}
   
   features = {"create_node": [],
               "list_sizes":  ["variable_disk"]}

   initialize_instance_types()

   def list_nodes(self):
       params = {"method": "voxel.devices.list"}
       result = self.connection.request('', params=params).object        
       return self._to_nodes(result)

   def list_sizes(self, location=None):
       return [ NodeSize(driver=self.connection.driver, **i) 
                   for i in VOXEL_INSTANCE_TYPES.values() ]

   def list_images(self, location=None):
       params = {"method": "voxel.images.list"}
       result = self.connection.request('', params=params).object
       return self._to_images(result)

   def create_node(self, **kwargs):
       size = kwargs["size"]
       cores = size.ram / RAM_PER_CPU
       params = {'method':           'voxel.voxcloud.create',
                 'hostname':         kwargs["name"],
                 'disk_size':        int(kwargs["disk"])/1024,
                 'processing_cores': cores,
                 'facility':         kwargs["location"].id,
                 'image_id':         kwargs["image"],
                 'backend_ip':       kwargs.get("privateip", None),
                 'frontend_ip':      kwargs.get("publicip", None),
                 'admin_password':   kwargs.get("rootpass", None),
                 'console_password': kwargs.get("consolepass", None),
                 'ssh_username':     kwargs.get("sshuser", None),
                 'ssh_password':     kwargs.get("sshpass", None),
                 'voxel_access':     kwargs.get("voxel_access", None)}

       object = self.connection.request('', params=params).object

       if self._getstatus(object):
           return Node(id = object.findtext("device/id"),
                       name = kwargs["name"],
                       state = NODE_STATE_MAP[object.findtext("devices/status")],
                       public_ip = public_ip,
                       private_ip = private_ip,
                       driver = self.connection.driver)
       else:
         return None

   def reboot_node(self, node):
       """
       Reboot the node by passing in the node object
       """
       params = {'method': 'voxel.devices.power',
                 'device_id': node.id,
                 'power_action': 'reboot'}
       return _getstatus(self.connection.request('', params=params).object)

   def destroy_node(self, node):
       """
       Destroy node by passing in the node object
       """
       params = {'method': 'voxel.voxcloud.delete',
                 'device_id': node.id}
       return _getstatus(self.connection.request('', params=params).object)

   def list_locations(self):
       params = {"method": "voxel.voxcloud.facilities.list"}
       result = self.connection.request('', params=params).object        
       nodes = self._to_locations(result)
       return nodes

   def _getstatus(self, element):
     status = element.attrib["stat"]
     return status == "ok"


   def _to_locations(self, object):
       return [NodeLocation(element.attrib["label"],
                            element.findtext("description"),
                            element.findtext("description"),
                            self) for element in object.findall('facilities/facility')]

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

