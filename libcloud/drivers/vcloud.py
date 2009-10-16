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

from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize, NodeImage

import base64
import httplib
from xml.etree import ElementTree as ET

def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e) for e in xpath.split("/")])
    return fixed_xpath

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        return self.body

    def success(self):
        return self.status in (httplib.OK, httplib.CREATED, 
                               httplib.NO_CONTENT, httplib.ACCEPTED)

class VCloudConnection(ConnectionUserAndKey):

    responseCls = VCloudResponse
    token = None
    host = None

    @property
    def hostingid(self):
        return self.user_id.split('@')[1]

    def request(self, *args, **kwargs):
        self._get_auth_token()
        return super(VCloudConnection, self).request(*args, **kwargs)

    def _get_auth_token(self):
        if not self.token:
            headers = {'Authentication': base64.b64encode('%s:%s' % (self.user_id, self.key)),
                       'Content-Length': 0} 

            conn = self.conn_classes[self.secure](self.host, 
                                                  self.port[self.secure])
            conn.request(method='POST', url='/api/v0.8/login', headers=headers)

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            try:
                self.token = headers['set-cookie']
            except KeyError:
                raise InvalidCredsException()

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudNodeDriver(NodeDriver):
    type = Provider.VCLOUD
    name = "vCloud"
    connectionCls = VCloudConnection

    NODE_STATE_MAP = {'0': NodeState.PENDING,
                      '1': NodeState.PENDING,
                      '2': NodeState.PENDING,
                      '3': NodeState.PENDING,
                      '4': NodeState.RUNNING}

    @property
    def hostingid(self):
        return self.connection.hostingid

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, name, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        public_ips = [ip.text for ip in elm.findall(fixxpath(elm, 'NetworkConnectionSection/NetworkConnection/IPAddress'))]

        node = Node(id=name,
                    name=name,
                    state=state,
                    public_ip=public_ips,
                    private_ip=None,
                    driver=self.connection.driver)

        return node

    def reboot_node(self, node):
        res = self.connection.request('/vapp/%s/power/action/reset' % node.id,
                                      method='POST') 
        return res.status == 204

    def list_nodes(self):
        res = self.connection.request('/vdc/%s' % self.hostingid) 
        elms = res.object.findall(fixxpath(res.object, "ResourceEntities/ResourceEntity"))
        vapps = [i.get('name') 
                    for i in elms
                        if i.get('type') == 'application/vnd.vmware.vcloud.vApp+xml' and 
                           i.get('name')]
        nodes = []
        for vapp in vapps:
            res = self.connection.request('/vApp/%s' % vapp)
            nodes.append(self._to_node(vapp, res.object))

        return nodes

    def list_images(self):
        images = self.connection.request('/vdc/%s' % self.hostingid).object
        res_ents = images.findall(fixxpath(images, "ResourceEntities/ResourceEntity"))
        images = [self._to_image(i) 
                    for i in res_ents 
                        if i.get('type') == 'application/vnd.vmware.vcloud.vAppTemplate+xml']
        return images

class HostingComConnection(VCloudConnection):
    host = "vcloud.safesecureweb.com" 

class HostingComDriver(VCloudNodeDriver):
    connectionCls = HostingComConnection
