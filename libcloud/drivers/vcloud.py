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
import time
from urlparse import urlparse
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

#From vcloud api "The VirtualQuantity element defines the number of MB of memory. This should be either 512 or a multiple of 1024 (1 GB)."
VIRTUAL_MEMORY_VALS = [512] + [1024 * i for i in range(1,9)] 

def get_url_path(url):
    return urlparse(url.strip()).path

def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e) for e in xpath.split("/")])
    return fixed_xpath

class InstantiateVAppXML(object):
    
    def __init__(self, name, template, net_href, cpus, memory, password=None, row=None, group=None):
        self.name = name
        self.template = template
        self.net_href = net_href
        self.cpus = cpus
        self.memory = memory
        self.password = password
        self.row = row
        self.group = group

        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)
    
    def _build_xmltree(self):
        self.root = self._make_instantiation_root()

        self._add_vapp_template(self.root)
        instantionation_params = ET.SubElement(self.root, 
                                               "InstantiationParams")

        product = self._make_product_section(instantionation_params)
        virtual_hardware = self._make_virtual_hardware(instantionation_params)
        network_config_section = ET.SubElement(instantionation_params,
                                               "NetworkConfigSection")

        network_config = ET.SubElement(network_config_section,
                                       "NetworkConfig")
        self._add_network_association(network_config)

    def _make_instantiation_root(self):
        return ET.Element(
            "InstantiateVAppTemplateParams", 
            {'name': self.name,
             'xml:lang': 'en',
             'xmlns': "http://www.vmware.com/vcloud/v1",
             'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"}
        )

    def _add_vapp_template(self, parent):
        return ET.SubElement(
            parent, 
            "VAppTemplate",
            {'href': self.template}
        )

    def _make_product_section(self, parent):
        prod_section = ET.SubElement(
            parent,
            "ProductSection",
            {'xmlns:q1': "http://www.vmware.com/vcloud/v1",
             'xmlns:ovf': "http://schemas.dmtf.org/ovf/envelope/1"}
        )

        if self.password:
            self._add_property(prod_section, 'password', self.password)

        if self.row:
            self._add_property(prod_section, 'row', self.row)

        if self.group:
            self._add_property(prod_section, 'group', self.group)

        return prod_section

    def _add_property(self, parent, ovfkey, ovfvalue):
        return ET.SubElement(
            parent, 
            "Property",
            {'xmlns': 'http://schemas.dmtf.org/ovf/envelope/1',
             'ovf:key': ovfkey,
             'ovf:value': ovfvalue}
        )
    
    def _make_virtual_hardware(self, parent):
        vh = ET.SubElement(
            parent,
            "VirtualHardwareSection",
            {'xmlns:q1': "http://www.vmware.com/vcloud/v1"}
        )

        self._add_cpu(vh)
        self._add_memory(vh)

        return vh

    def _add_cpu(self, parent):
        cpu_item = ET.SubElement(
            parent,
            "Item",
            {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"}
        )
        self._add_instance_id(cpu_item, '1')
        self._add_resource_type(cpu_item, '3')
        self._add_virtual_quantity(cpu_item, self.cpus)

        return cpu_item

    def _add_memory(self, parent):
        mem_item = ET.SubElement(
            parent,
            "Item",
            {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"}
        )
        self._add_instance_id(mem_item, '2')
        self._add_resource_type(mem_item, '4')
        self._add_virtual_quantity(mem_item, self.memory)

        return mem_item

    def _add_instance_id(self, parent, id):
        elm = ET.SubElement(
            parent, 
            "InstanceID",
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = id
        return elm

    def _add_resource_type(self, parent, type):
        elm = ET.SubElement(
            parent,
            "ResourceType",
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = type
        return elm

    def _add_virtual_quantity(self, parent, amount):
       elm = ET.SubElement(
            parent,
            "VirtualQuantity",
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
       elm.text = amount
       return elm

    def _add_network_association(self, parent):
        return ET.SubElement(
            parent,
            "NetworkAssociation",
            {'href': self.net_href}
        )

class VCloudResponse(Response):

    def parse_body(self):
        if not self.body:
            return None
        try:
            return ET.XML(self.body)
        except ExpatError, e:
            raise Exception("%s: %s" % (e, self.parse_error()))

    def parse_error(self):
        return self.error

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

    @property
    def networks(self):
        networks = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            networks.extend(
                [network for network in res.findall(fixxpath(res, "AvailableNetworks/Network"))]
            )

        return networks

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, name, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        public_ips = [ip.text for ip in elm.findall(fixxpath(elm, 'NetworkConnectionSection/NetworkConnection/IPAddress'))]

        # Following code to find private IPs works for Terremark
        sections = elm.findall('{http://schemas.dmtf.org/ovf/envelope/1}Section')
        network_connection_section = None
        for section in sections:
          section_type = section.get('{http://www.w3.org/2001/XMLSchema-instance}type')
          if section_type == 'q1:NetworkConnectionSectionType':
            network_connection_section = section
        
        if network_connection_section:
          private_ips = [ip.text for ip in network_connection_section.findall(fixxpath(elm, 'NetworkConnection/IpAddress'))]
        else:
          private_ips = []

        node = Node(id=elm.get('href'),
                    name=name,
                    state=state,
                    public_ip=public_ips,
                    private_ip=private_ips,
                    driver=self.connection.driver)

        return node

    def _get_catalog_hrefs(self):
        res = self.connection.request(self.org)
        catalogs = [get_url_path(i.get('href'))
                    for i in res.object.findall(fixxpath(res.object, "Link"))
                    if i.get('type') == 'application/vnd.vmware.vcloud.catalog+xml']

        return catalogs

    def destroy_node(self, node):
        node_path = get_url_path(node.id)
        # blindly poweroff node, it will throw an exception if already off
        try:
            self.connection.request('%s/power/action/poweroff' % node_path,
                                    method='POST') 
        except Exception, e: 
            pass

        try:
            res = self.connection.request('%s/action/undeploy' % node_path,
                                          method='POST')
        except ExpatError: # the undeploy response is malformed XML atm. We can remove this whent he providers fix the problem.
            pass
        except Exception, e: # some vendors don't implement undeploy at all yet, so catch this and move on.
            pass

        res = self.connection.request(node_path, method='DELETE')
        return res.status == 202

    def reboot_node(self, node):
        res = self.connection.request('%s/power/action/reset' % get_url_path(node.id),
                                      method='POST') 
        return res.status == 202 or res.status == 204

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

    def _to_size(self, ram):
        ns = NodeSize(
            id=None,
            name="%s Ram" % ram,
            ram=ram,
            disk=None,
            bandwidth=None,
            price=None,
            driver=self.connection.driver
        )

        return ns
        
    def list_sizes(self):
        sizes = [self._to_size(i) for i in VIRTUAL_MEMORY_VALS]
        return sizes

    def _get_catalogitems_hrefs(self, catalog):
        """Given a catalog href returns contained catalog item hrefs"""
        res = self.connection.request(
            catalog,
            headers={'Content-Type': 'application/vnd.vmware.vcloud.catalog+xml'}
        ).object

        cat_items = res.findall(fixxpath(res, "CatalogItems/CatalogItem"))
        cat_item_hrefs = [i.get('href')
                          for i in cat_items
                          if i.get('type') == 'application/vnd.vmware.vcloud.catalogItem+xml']

        return cat_item_hrefs

    def _get_catalogitem(self, catalog_item):
        """Given a catalog item href returns elementree"""
        res = self.connection.request(
            catalog_item,
            headers={'Content-Type': 'application/vnd.vmware.vcloud.catalogItem+xml'}
        ).object

        return res
        
    def list_images(self):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            res_ents = res.findall(fixxpath(res, "ResourceEntities/ResourceEntity"))
            images += [self._to_image(i) 
                       for i in res_ents 
                       if i.get('type') == 'application/vnd.vmware.vcloud.vAppTemplate+xml']
        
        for catalog in self._get_catalog_hrefs():
            for cat_item in self._get_catalogitems_hrefs(catalog):
                res = self._get_catalogitem(cat_item) 
                res_ents = res.findall(fixxpath(res, 'Entity'))
                images += [self._to_image(i)
                           for i in res_ents
                           if i.get('type') ==  'application/vnd.vmware.vcloud.vAppTemplate+xml']

        return images

    def create_node(self, name, image, size, **kwargs):
        """Creates and returns node.

           Non-standard optional keyword arguments:
           network -- link to a "Network" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/network/7"
           vdc -- link to a "VDC" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/vdc/1"
           cpus -- number of virtual cpus (limit depends on provider)
           password
           row
           group 
        """
        # Some providers don't require a network link
        try:
            network = kwargs.get('network', self.networks[0].get('href'))
        except IndexError:
            network = ''

        instantiate_xml = InstantiateVAppXML(
            name=name, 
            template=image.id, 
            net_href=network,
            cpus=str(kwargs.get('cpus', 1)),
            memory=str(size.ram),
            password=kwargs.get('password', None),
            row=kwargs.get('row', None),
            group=kwargs.get('group', None)
        )

        # Instantiate VM and get identifier.
        res = self.connection.request('%s/action/instantiateVAppTemplate' % kwargs.get('vdc', self.vdcs[0]),
                                      data=instantiate_xml.tostring(),
                                      method='POST',
                                      headers={'Content-Type': 'application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml'})
        vapp_name = res.object.get('name')
        vapp_href = get_url_path(res.object.get('href'))

        # Deploy the VM from the identifier.
        res = self.connection.request('%s/action/deploy' % vapp_href,
                                      method='POST')
        
        deploy_task_href = get_url_path(res.object.get('href'))
        res = self.connection.request(deploy_task_href)
        status = res.object.get('status')
        while status != 'success':
          # TODO: fail if status is error or cancelled
          time.sleep(5)
          res = self.connection.request(deploy_task_href)
          status = res.object.get('status')
        
        # Power on the VM.
        res = self.connection.request('%s/power/action/powerOn' % vapp_href,
                                      method='POST')

        res = self.connection.request(vapp_href)
        node = self._to_node(vapp_name, res.object)

        return node

class HostingComConnection(VCloudConnection):
    host = "vcloud.safesecureweb.com" 
    
    def _get_auth_headers(self):
        """hosting.com doesn't follow the standard vCloud authentication API"""
        return {'Authentication': base64.b64encode('%s:%s' % (self.user_id, self.key)),
                   'Content-Length': 0} 


class HostingComDriver(VCloudNodeDriver):
    connectionCls = HostingComConnection

class TerremarkConnection(VCloudConnection):
    host = "services.vcloudexpress.terremark.com"

class TerremarkDriver(VCloudNodeDriver):
    connectionCls = TerremarkConnection
