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
from urlparse import urlparse
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

def get_url_path(url):
    return urlparse(url.strip()).path

def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e) for e in xpath.split("/")])
    return fixed_xpath

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        try:
            return ET.XML(self.body)
        except ExpatError, e:
            raise Exception("%s: %s" % (e, self.parse_error()))

    def parse_error(self):
        return self.body

    def success(self):
        return self.status in (httplib.OK, httplib.CREATED, 
                               httplib.NO_CONTENT, httplib.ACCEPTED)

class VCloudConnection(ConnectionUserAndKey):

    responseCls = VCloudResponse
    token = None
    host = None

    def request(self, *args, **kwargs):
        self._get_auth_token()
        return super(VCloudConnection, self).request(*args, **kwargs)

    def check_org(self):
        self._get_auth_token() # the only way to get our org is by logging in.

    def _get_auth_headers(self):
        """Some providers need different headers than others"""
        return {'Authorization': "Basic %s" % base64.b64encode('%s:%s' % (self.user_id, self.key)),
                'Content-Length': 0}

    def _get_auth_token(self):
        if not self.token:
            conn = self.conn_classes[self.secure](self.host, 
                                                  self.port[self.secure])
            conn.request(method='POST', url='/api/v0.8/login', headers=self._get_auth_headers())

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            body = ET.XML(resp.read())

            try:
                self.token = headers['set-cookie']
            except KeyError:
                raise InvalidCredsException()

            self.driver.org = get_url_path(body.find(fixxpath(body, 'Org')).get('href'))

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudNodeDriver(NodeDriver):
    type = Provider.VCLOUD
    name = "vCloud"
    connectionCls = VCloudConnection
    org = None
    _vdcs = None

    NODE_STATE_MAP = {'0': NodeState.PENDING,
                      '1': NodeState.PENDING,
                      '2': NodeState.PENDING,
                      '3': NodeState.PENDING,
                      '4': NodeState.RUNNING}

    @property
    def vdcs(self):
        if not self._vdcs:
            self.connection.check_org() # make sure the org is set.
            res = self.connection.request(self.org)
            self._vdcs = [get_url_path(i.get('href'))
                          for i in res.object.findall(fixxpath(res.object, "Link"))
                          if i.get('type') == 'application/vnd.vmware.vcloud.vdc+xml']
            
        return self._vdcs

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

    def _get_catalog_hrefs(self):
        res = self.connection.request(self.org)
        catalogs = [get_url_path(i.get('href'))
                    for i in res.object.findall(fixxpath(res.object, "Link"))
                    if i.get('type') == 'application/vnd.vmware.vcloud.catalog+xml']

        return catalogs

    def destroy_node(self, node):
        self.connection.request('/vapp/%s/power/action/poweroff' % node.id,
                                method='POST') 
        try:
            res = self.connection.request('/vapp/%s/action/undeploy' % node.id,
                                          method='POST')
        except ExpatError: # the undeploy response is malformed XML atm. We can remove this whent he providers fix the problem.
            return True
        return res.status == 202

    def reboot_node(self, node):
        res = self.connection.request('/vapp/%s/power/action/reset' % node.id,
                                      method='POST') 
        return res.status == 204

    def list_nodes(self):
        nodes = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc) 
            elms = res.object.findall(fixxpath(res.object, "ResourceEntities/ResourceEntity"))
            vapps = [(i.get('name'), get_url_path(i.get('href')))
                        for i in elms
                            if i.get('type') == 'application/vnd.vmware.vcloud.vApp+xml' and 
                               i.get('name')]

            for vapp_name, vapp_href in vapps:
                res = self.connection.request(
                    vapp_href,
                    headers={'Content-Type': 'application/vnd.vmware.vcloud.vApp+xml'}
                )
                nodes.append(self._to_node(vapp_name, res.object))

        return nodes

    def list_images(self):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            res_ents = res.findall(fixxpath(res, "ResourceEntities/ResourceEntity"))
            images += [self._to_image(i) 
                       for i in res_ents 
                       if i.get('type') == 'application/vnd.vmware.vcloud.vAppTemplate+xml']
        
        for catalog in self._get_catalog_hrefs():
            res = self.connection.request(
                catalog,
                headers={'Content-Type': 'application/vnd.vmware.vcloud.catalog+xml'}
            ).object

            cat_items = res.findall(fixxpath(res, "CatalogItems/CatalogItem"))
            cat_item_hrefs = [i.get('href')
                              for i in cat_items
                              if i.get('type') == 'application/vnd.vmware.vcloud.catalogItem+xml']

            for cat_item in cat_item_hrefs:
                res = self.connection.request(
                    cat_item,
                    headers={'Content-Type': 'application/vnd.vmware.vcloud.catalogItem+xml'}
                ).object
                res_ents = res.findall(fixxpath(res, 'Entity'))
                images += [self._to_image(i)
                           for i in res_ents
                           if i.get('type') ==  'application/vnd.vmware.vcloud.vAppTemplate+xml']

        return images

class HostingComConnection(VCloudConnection):
    host = "vcloud.safesecureweb.com" 
    
    def _get_auth_headers(self):
        """hosting.com doesn't follow the standard vCloud authentication API"""
        return {'Authentication': base64.b64encode('%s:%s' % (self.user_id, self.key)),
                   'Content-Length': 0} 


class HostingComDriver(VCloudNodeDriver):
    connectionCls = HostingComConnection
