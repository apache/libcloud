# Licensed to libcloud.org under one or more
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

from libcloud.types import NodeState, InvalidCredsException, Provider
from libcloud.base import ConnectionKey, Response, NodeDriver, Node, NodeSize, NodeImage
import base64
import httplib
import struct
import socket
import hashlib
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

class SlicehostResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        try:
            object = ET.XML(self.body)
            return "; ".join([ err.text
                               for err in
                               object.findall('error') ])
        except ExpatError:
            return self.body
    

class SlicehostConnection(ConnectionKey):

    host = 'api.slicehost.com'
    responseCls = SlicehostResponse

    def add_default_headers(self, headers):
        headers['Authorization'] = ('Basic %s'
                              % (base64.b64encode('%s:' % self.key)))
        return headers
    

class SlicehostNodeDriver(NodeDriver):

    connectionCls = SlicehostConnection

    type = Provider.SLICEHOST
    name = 'Slicehost'

    NODE_STATE_MAP = { 'active': NodeState.RUNNING,
                       'build': NodeState.PENDING,
                       'reboot': NodeState.REBOOTING,
                       'hard_reboot': NodeState.REBOOTING,
                       'terminated': NodeState.TERMINATED }

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/slices.xml').object)

    def list_sizes(self):
        return self._to_sizes(self.connection.request('/flavors.xml').object)

    def list_images(self):
        return self._to_images(self.connection.request('/images.xml').object)

    def create_node(self, name, image, size, **kwargs):
        uri = '/slices.xml'

        # create a slice obj
        root = ET.Element('slice')
        el_name = ET.SubElement(root, 'name')
        el_name.text = name
        flavor_id = ET.SubElement(root, 'flavor-id')
        flavor_id.text = str(size.id)
        image_id = ET.SubElement(root, 'image-id')
        image_id.text = str(image.id)
        xml = ET.tostring(root)

        node = self._to_nodes(
                  self.connection.request(uri, method='POST', 
                            data=xml, headers={'Content-Type': 'application/xml'}
                      ).object)[0]
        return node

    def reboot_node(self, node):
        """Reboot the node by passing in the node object"""

        # 'hard' could bubble up as kwarg depending on how reboot_node 
        # turns out. Defaulting to soft reboot.
        #hard = False
        #reboot = self.api.hard_reboot if hard else self.api.reboot
        #expected_status = 'hard_reboot' if hard else 'reboot'

        uri = '/slices/%s/reboot.xml' % (node.id)
        node = self._to_nodes(self.connection.request(uri, method='PUT').object)[0]
        return node.state == NodeState.REBOOTING

    def destroy_node(self, node):
        """Destroys the node

        Requires 'Allow Slices to be deleted or rebuilt from the API' to be
        ticked at https://manage.slicehost.com/api, otherwise returns:

        <errors>
          <error>You must enable slice deletes in the SliceManager</error>
          <error>Permission denied</error>
        </errors>
        """
        uri = '/slices/%s/destroy.xml' % (node.id)
        ret = self.connection.request(uri, method='PUT')
        return True

    def _to_nodes(self, object):
        if object.tag == 'slice':
            return [ self._to_node(object) ]
        node_elements = object.findall('slice')
        return [ self._to_node(el) for el in node_elements ]

    def _to_node(self, element):

        attrs = [ 'name', 'image-id', 'progress', 'id', 'bw-out', 'bw-in', 
                  'flavor-id', 'status', 'ip-address' ]

        node_attrs = {}
        for attr in attrs:
            node_attrs[attr] = element.findtext(attr)

        # slicehost does not determine between public and private, so we 
        # have to figure it out
        public_ip = element.findtext('ip-address')
        private_ip = None
        for addr in element.findall('addresses/address'):
            ip = addr.text
            try:
                socket.inet_aton(ip)
            except socket.error:
                # not a valid ip
                continue
            if self._is_private_subnet(ip):
                private_ip = ip
            else:
                public_ip = ip
                
        try:
            state = self.NODE_STATE_MAP[element.findtext('status')]
        except:
            state = NodeState.UNKNOWN

        n = Node(id=element.findtext('id'),
                 name=element.findtext('name'),
                 state=state,
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver)
        return n

    def _to_sizes(self, object):
        if object.tag == 'flavor':
            return [ self._to_size(object) ]
        elements = object.findall('flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, element):
        s = NodeSize(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     ram=int(element.findtext('ram')),
                     disk=None, # XXX: needs hardcode
                     bandwidth=None, # XXX: needs hardcode
                     price=float(element.findtext('price'))/(100*24*30),
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        if object.tag == 'image':
            return [ self._to_image(object) ]
        elements = object.findall('image')
        return [ self._to_image(el) for el in elements ]

    def _to_image(self, element):
        i = NodeImage(id=int(element.findtext('id')),
                     name=str(element.findtext('name')),
                     driver=self.connection.driver)
        return i


    def _is_private_subnet(self, ip):
        priv_subnets = [ {'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                         {'subnet': '172.16.0.0', 'mask': '172.16.0.0'},
                         {'subnet': '192.168.0.0', 'mask': '192.168.0.0'} ]

        ip = struct.unpack('I',socket.inet_aton(ip))[0]

        for network in priv_subnets:
            subnet = struct.unpack('I',socket.inet_aton(network['subnet']))[0]
            mask = struct.unpack('I',socket.inet_aton(network['mask']))[0]

            if (ip & mask) == (subnet & mask):
                return True
            
        return False
