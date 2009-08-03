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

from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.base import ConnectionKey, Response, NodeDriver
from libcloud.interface import INodeDriver
from zope.interface import implements
import base64
import httplib
import struct
import socket
import hashlib
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

class SlicehostResponse(Response):

    NODE_STATE_MAP = { 'active': NodeState.RUNNING,
                       'build': NodeState.PENDING,
                       'reboot': NodeState.REBOOTING,
                       'hard_reboot': NodeState.REBOOTING,
                       'terminated': NodeState.TERMINATED }

    def parse_body(self, body):
        if not body:
            return None
        return ET.XML(self.body)

    def get_uuid(self, field):
        # XXX find way to define this as slice.id and Provider.SLICEHOST
        return hashlib.sha1("%s:%d" % (field,3)).hexdigest()

    def to_node(self):
        if self.tree.tag == 'slice':
          return self._to_node(self.tree)
        node_elements = self.tree.findall('slice')
        return [ self._to_node(el) for el in node_elements ]

    def _to_node(self, element):

        attrs = [ 'name', 'image-id', 'progress', 'id', 'bw-out', 'bw-in', 
                  'flavor-id', 'status', 'ip-address' ]

        node_attrs = {}
        for attr in attrs:
            node_attrs[attr] = element.findtext(attr)

        ipaddress = element.findtext('ip-address')
        if self._is_private_subnet(ipaddress):
            # sometimes slicehost gives us a private address in ip-address
            for addr in element.findall('addresses/address'):
                ip = addr.text
                try:
                    socket.inet_aton(ip)
                except socket.error:
                    # not a valid ip
                    continue
                if not self._is_private_subnet(ip):
                    ipaddress = ip
                    break
        try:
            state = self.NODE_STATE_MAP[element.findtext('status')]
        except:
            state = NodeState.UNKNOWN

        n = Node(uuid=self.get_uuid(element.findtext('id')),
                 name=element.findtext('name'),
                 state=state,
                 ipaddress=ipaddress,
                 attrs=node_attrs)
        return n

    def parse_error(self, body):
        try:
            tree = ET.XML(body)
            return "; ".join([ err.text
                               for err in
                               tree.findall('error') ])
        except ExpatError:
            return body
    
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

class SlicehostConnection(ConnectionKey):

    host = 'api.slicehost.com'
    responseCls = SlicehostResponse

    @property
    def default_headers(self):
        return {
            'Authorization': ('Basic %s'
                              % (base64.b64encode('%s:' % self.key))),
        }
    
class SlicehostNodeDriver(NodeDriver):

    connectionCls = SlicehostConnection

    def list_nodes(self):
        return self.connection.request('/slices.xml').to_node()

    def reboot_node(self, node):
        """Reboot the node by passing in the node object"""

        # 'hard' could bubble up as kwarg depending on how reboot_node 
        # turns out. Defaulting to soft reboot.
        #hard = False
        #reboot = self.api.hard_reboot if hard else self.api.reboot
        #expected_status = 'hard_reboot' if hard else 'reboot'

        uri = '/slices/%s/reboot.xml' % (node.attrs['id'])
        node = self.connection.request(uri, method='PUT').to_node()
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
        uri = '/slices/%s/destroy.xml' % (node.attrs['id'])
        ret = self.connection.request(uri, method='PUT')
        return True
