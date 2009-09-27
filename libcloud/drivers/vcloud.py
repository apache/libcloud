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
from libcloud.base import Node, Response, ConnectionKey, NodeDriver, NodeSize, NodeImage

import base64
from xml.etree import ElementTree as ET


NAMESPACE = "http://www.vmware.com/vcloud1/vl"

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        return self.body

class VCloudConnection(ConnectionKey):
    host = None
    responseCls = VCloudResponse
    token = None
    hostingid = None

    __host = None

    @property
    def host(self):
        if not self.__host:
            headers = {'Authentication': base64.b64encode(self.key),
                       'Content-Length': 0} 

            conn = self.conn_classes[self.secure](self.api_host, self.port[self.secure])
            conn.request(method='POST', url='/api/v0.8/login', headers=headers)

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            body = resp.read()
            print body

            try:
                self.token = headers['set-cookie']
                print
                print body.strip()
                print 
                print ET.XML(body)
            except KeyError:
                raise InvalidCredsException()
            
            self.__host = True
            
        return self.api_host

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudDriver(NodeDriver):
    type = Provider.VCLOUD

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def list_images(self):
        headers = {'Content-Type': 'application/vnd.vmware.vcloud.catalog+xml'}
        images = self.connection.request('/catalog/1', headers=headers).object
        print images.getchildren()
        print images.findall(self._fixxpath("CatalogItems/CatalogItem"))[0].attrib

class HostingComConnection(VCloudConnection):
    api_host = "vcloud.safesecureweb.com" 

class HostingComDriver(VCloudDriver):
    connectionCls = HostingComConnection
