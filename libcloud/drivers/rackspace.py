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
from libcloud.base import ConnectionUserAndKey, Response, NodeDriver, Node, NodeSize, NodeImage
from libcloud.interface import INodeDriver

from zope.interface import implements

import urlparse

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'

class RackspaceResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        # TODO: fixup, Rackspace only uses response codes really!
        try:
            object = ET.XML(self.body)
            return "; ".join([ err.text
                               for err in
                               object.findall('error') ])
        except ExpatError:
            return self.body


class RackspaceConnection(ConnectionUserAndKey):
    api_version = 'v1.0'
    auth_host = 'auth.api.rackspacecloud.com'
    __host = None
    path = None
    token = None

    responseCls = RackspaceResponse

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.token;
        headers['Accept'] = 'application/xml'
        return headers

    @property
    def host(self):
        """
        Rackspace uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.

        TODO: Fixup for when our token expires (!!!)
        """
        if not self.__host:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](self.auth_host, self.port[self.secure])
            conn.request(method='GET', url='/%s' % self.api_version,
                                           headers={'X-Auth-User': self.user_id,
                                                    'X-Auth-Key': self.key})
            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            try:
                self.token = headers['x-auth-token']
                endpoint = headers['x-server-management-url']
            except KeyError:
                raise InvalidCredsException()

            scheme, server, self.path, param, query, fragment = (
                urlparse.urlparse(endpoint)
            )
            if scheme is "https" and self.secure is not 1:
                # TODO: Custom exception (?)
                raise InvalidCredsException()

            # Set host to where we want to make further requests to; close auth conn
            self.__host = server
            conn.close()

        return self.__host

    def request(self, action, params={}, data='', headers={}, method='GET'):
        # Due to first-run authentication request, we may not have a path
        if self.path:
            action = self.path + action
        if method == "POST":
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        return super(RackspaceConnection, self).request(action=action,
                                                        params=params, data=data,
                                                        method=method, headers=headers)
        

class RackspaceNodeDriver(NodeDriver):

    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    name = 'Rackspace'

    NODE_STATE_MAP = {  'BUILD': NodeState.PENDING,
                        'ACTIVE': NodeState.RUNNING,
                        'SUSPENDED': NodeState.TERMINATED,
                        'QUEUE_RESIZE': NodeState.PENDING,
                        'PREP_RESIZE': NodeState.PENDING,
                        'RESCUE': NodeState.PENDING,
                        'REBUILD': NodeState.PENDING,
                        'REBOOT': NodeState.REBOOTING,
                        'HARD_REBOOT': NodeState.REBOOTING}

    def list_nodes(self):
        return self.to_nodes(self.connection.request('/servers/detail').object)

    def list_sizes(self):
        return self.to_sizes(self.connection.request('/flavors/detail').object)

    def list_images(self):
        return self.to_images(self.connection.request('/images/detail').object)

    def create_node(self, name, image, size, **kwargs):
        body = """<server   xmlns="%s"
                            name="%s"
                            imageId="%s"
                            flavorId="%s">
                </server>
                """ % (NAMESPACE, name, image.id, size.id)
        resp = self.connection.request("/servers", method='POST', data=body)
        return self._to_node(resp.object)

    def reboot_node(self, node):
        # TODO: Hard Reboots should be supported too!
        resp = self._node_action(node, ['reboot', ('type', 'SOFT')])
        return resp.status == 202

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 202

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1]) for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def to_nodes(self, object):
        node_elements = self._findall(object, 'server')
        return [ self._to_node(el) for el in node_elements ]

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]
        
        public_ip = get_ips(self._findall(el, 
                                          'addresses/public/ip'))
        private_ip = get_ips(self._findall(el, 
                                          'addresses/private/ip'))
        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=el.get('status'),
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver)
        return n

    def to_sizes(self, object):
        elements = self._findall(object, 'flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, el):
        s = NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     bandwidth=None, # XXX: needs hardcode
                     price=None, # XXX: needs hardcode,
                     driver=self.connection.driver)
        return s

    def to_images(self, object):
        elements = self._findall(object, "image")
        return [ self._to_image(el) for el in elements if el.get('status') == 'ACTIVE']

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                     name=el.get('name'),
                     driver=self.connection.driver)
        return i
