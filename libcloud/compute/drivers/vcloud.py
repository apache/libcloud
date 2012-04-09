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
VMware vCloud driver.
"""
import base64
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import b

urlparse = urlparse.urlparse

import time
import collections

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from libcloud.common.base import XmlResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation
from libcloud.compute.base import NodeSize, NodeImage, NodeAuthPassword

"""
From vcloud api "The VirtualQuantity element defines the number of MB
of memory. This should be either 512 or a multiple of 1024 (1 GB)."
"""
VIRTUAL_MEMORY_VALS = [512] + [1024 * i for i in range(1, 9)]

DEFAULT_TASK_COMPLETION_TIMEOUT = 600


def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e)
                            for e in xpath.split("/")])
    return fixed_xpath


def get_url_path(url):
    return urlparse(url.strip()).path


class InstantiateVAppXML(object):

    def __init__(self, name, template, net_href, cpus, memory,
                 password=None, row=None, group=None):
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

        # product and virtual hardware
        self._make_product_section(instantionation_params)
        self._make_virtual_hardware(instantionation_params)

    def _make_instantiation_root(self):
        return ET.Element(
            "InstantiateVAppTemplateParams",
            {'name': self.name,
             'xml:lang': 'en',
             'xmlns': "http://www.vmware.com/vcloud/v0.8",
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
            {'xmlns:q1': "http://www.vmware.com/vcloud/v0.8",
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
            {'xmlns:q1': "http://www.vmware.com/vcloud/v0.8"}
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
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResreourceAllocationSettingData'}
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

class VCloudResponse(XmlResponse):


    def success(self):
        return self.status in (httplib.OK, httplib.CREATED,
                               httplib.NO_CONTENT, httplib.ACCEPTED)


class Vdc(object):
    """vCloud Datacenter
    """

    def __init__(self, **kwargs):

        self.name = kwargs["name"]
        self.href = kwargs["href"]
        self.profile = kwargs["profile"]
        self.networks = kwargs["networks"]

    @classmethod
    def get_vdc(self, vdc, conn, org):
        res = conn.request(org)
        vdcs = res.object.findall(fixxpath(res.object, "Link"))
        for i in vdcs:
            if vdc in i.get('name'):
                #Find the Name, Type and Available Networks for a vdc

                vdc_name = i.get('name')
                vdc_href = get_url_path(i.get('href'))
                v = conn.request(vdc_href)
                desc = v.object.findall(fixxpath(v.object, "Description"))[0] 
                vdc_profile = desc.text.split(';')[0].split('=')[1].strip()
                ns = v.object.findall(fixxpath(v.object, "AvailableNetworks"))
                if not ns:
                    raise Exception("No Available Networks found")
                n = ns[0]
                networks = n.findall(fixxpath(n, "Network"))
                vdc_networks = [ i.get("name") for i in networks]
    
                return Vdc(name=vdc_name, href=vdc_href, profile=vdc_profile, networks=vdc_networks)

        raise ValueError("Cannot find VDC: %s" %vdc)
 

class VCloudConnection(ConnectionUserAndKey):
    """
    Connection class for the vCloud driver
    """

    responseCls = VCloudResponse
    token = None
    host = None
    login_url = '/api/v0.8/login'

    def request(self, *args, **kwargs):
        self._get_auth_token()
        return super(VCloudConnection, self).request(*args, **kwargs)

    def check_org(self):
        # the only way to get our org is by logging in.
        self._get_auth_token()

    def _get_auth_headers(self):
        """Some providers need different headers than others"""
        return {
            'Authorization':
                "Basic %s"
                % base64.b64encode(b('%s:%s' % (self.user_id, self.key))),
            'Content-Length': 0
        }

    def _get_auth_token(self):
        if not self.token:
            conn = self.conn_classes[self.secure](self.host,
                                                  self.port)
            conn.request(method='POST', url=self.login_url,
                         headers=self._get_auth_headers())

            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            body = ET.XML(resp.read())

            try:
                self.token = headers['set-cookie']
            except KeyError:
                raise InvalidCredsError()

            self.driver.org = get_url_path(
                body.find(fixxpath(body, 'Org')).get('href')
            )

    def add_default_headers(self, headers):
        headers['Cookie'] = self.token
        return headers

class VCloudNodeDriver(NodeDriver):
    """
    vCloud node driver
    """

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
            self._vdcs = [
                get_url_path(i.get('href'))
                for i
                in res.object.findall(fixxpath(res.object, "Link"))
                if i.get('type') == 'application/vnd.vmware.vcloud.vdc+xml'
            ]

        return self._vdcs

    @property
    def networks(self):
        networks = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            networks.extend(
                [network
                 for network in res.findall(
                     fixxpath(res, "AvailableNetworks/Network")
                 )]
            )

        return networks

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, name, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        public_ips = []
        private_ips = []

        # Following code to find private IPs works for Terremark
        connections = elm.findall('{http://schemas.dmtf.org/ovf/envelope/1}NetworkConnectionSection/{http://www.vmware.com/vcloud/v0.8}NetworkConnection')
        for connection in connections:
            ips = [ip.text
                   for ip
                   in connection.findall(fixxpath(elm, "IpAddress"))]
            if connection.get('Network') == 'Internal':
                private_ips.extend(ips)
            else:
                public_ips.extend(ips)

        node = Node(id=elm.get('href'),
                    name=name,
                    state=state,
                    public_ips=public_ips,
                    private_ips=private_ips,
                    driver=self.connection.driver)

        return node

    def _get_catalog_hrefs(self):
        res = self.connection.request(self.org)
        catalogs = [
            get_url_path(i.get('href'))
            for i in res.object.findall(fixxpath(res.object, "Link"))
            if i.get('type') == 'application/vnd.vmware.vcloud.catalog+xml'
        ]

        return catalogs

    def _fetch_task_info(self, task_href):
        res = self.connection.request(task_href)
        return res.object

    def _wait_for_task_completion(self, task_href,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        start_time = time.time()
        task = self._fetch_task_info(task_href)
        print "Task Href %s Task Status: %s" %(task_href, task.get("status"))
        status = task.get('status')
        while status != 'success':
            if status == 'error':
                raise Exception("Error status returned by task %s."
                                % task_href)
            if status == 'canceled':
                raise Exception("Canceled status returned by task %s."
                                % task_href)
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout while waiting for task %s."
                                % task_href)
            time.sleep(5)
            task = self._fetch_task_info(task_href)
            print "Task Href %s Task Status: %s" %(task_href, task.get("status"))
            status = task.get('status')

    def destroy_node(self, node):
        node_path = get_url_path(node.id)
        # blindly poweroff node, it will throw an exception if already off
        try:
            res = self.connection.request('%s/power/action/poweroff'
                                          % node_path,
                                          method='POST')
            self._wait_for_task_completion(res.object.get('href'))
        except Exception:
            pass

        try:
            res = self.connection.request('%s/action/undeploy' % node_path,
                                          method='POST')
            self._wait_for_task_completion(res.object.get('href'))
        except ExpatError:
            # The undeploy response is malformed XML atm.
            # We can remove this whent he providers fix the problem.
            pass
        except Exception:
            # Some vendors don't implement undeploy at all yet,
            # so catch this and move on.
            pass

        res = self.connection.request(node_path, method='DELETE')
        return res.status == 202

    def reboot_node(self, node):
        res = self.connection.request('%s/power/action/reset'
                                      % get_url_path(node.id),
                                      method='POST')
        return res.status == 202 or res.status == 204

    def list_nodes(self):
        nodes = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc)
            elms = res.object.findall(fixxpath(
                res.object, "ResourceEntities/ResourceEntity")
            )
            vapps = [
                (i.get('name'), get_url_path(i.get('href')))
                for i in elms
                if i.get('type')
                    == 'application/vnd.vmware.vcloud.vApp+xml'
                    and i.get('name')
            ]

            for vapp_name, vapp_href in vapps:
                res = self.connection.request(
                    vapp_href,
                    headers={
                        'Content-Type':
                            'application/vnd.vmware.vcloud.vApp+xml'
                    }
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

    def list_sizes(self, location=None):
        sizes = [self._to_size(i) for i in VIRTUAL_MEMORY_VALS]
        return sizes

    def _get_catalogitems_hrefs(self, catalog):
        """Given a catalog href returns contained catalog item hrefs"""
        res = self.connection.request(
            catalog,
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.catalog+xml'
            }
        ).object

        cat_items = res.findall(fixxpath(res, "CatalogItems/CatalogItem"))
        cat_item_hrefs = [i.get('href')
                          for i in cat_items
                          if i.get('type') ==
                              'application/vnd.vmware.vcloud.catalogItem+xml']

        return cat_item_hrefs

    def _get_catalogitem(self, catalog_item):
        """Given a catalog item href returns elementree"""
        res = self.connection.request(
            catalog_item,
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.catalogItem+xml'
            }
        ).object

        return res

    def list_images(self, location=None):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc).object
            res_ents = res.findall(fixxpath(
                res, "ResourceEntities/ResourceEntity")
            )
            images += [
                self._to_image(i)
                for i in res_ents
                if i.get('type') ==
                    'application/vnd.vmware.vcloud.vAppTemplate+xml'
            ]

        for catalog in self._get_catalog_hrefs():
            for cat_item in self._get_catalogitems_hrefs(catalog):
                res = self._get_catalogitem(cat_item)
                res_ents = res.findall(fixxpath(res, 'Entity'))
                images += [
                    self._to_image(i)
                    for i in res_ents
                    if i.get('type') ==
                        'application/vnd.vmware.vcloud.vAppTemplate+xml'
                ]

        return images

    def create_node(self, **kwargs):
        """Creates and returns node.


        See L{NodeDriver.create_node} for more keyword args.

        Non-standard optional keyword arguments:
        @keyword    ex_network: link to a "Network" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/network/7"
        @type       ex_network: C{string}

        @keyword    ex_vdc: link to a "VDC" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/vdc/1"
        @type       ex_vdc: C{string}

        @keyword    ex_cpus: number of virtual cpus (limit depends on provider)
        @type       ex_cpus: C{int}

        @keyword    row: ????
        @type       row: C{????}

        @keyword    group: ????
        @type       group: C{????}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']

        # Some providers don't require a network link
        try:
            network = kwargs.get('ex_network', self.networks[0].get('href'))
        except IndexError:
            network = ''

        password = None
        if 'auth' in kwargs:
            auth = kwargs['auth']
            if isinstance(auth, NodeAuthPassword):
                password = auth.password
            else:
                raise ValueError('auth must be of NodeAuthPassword type')

        instantiate_xml = InstantiateVAppXML(
            name=name,
            template=image.id,
            net_href=network,
            cpus=str(kwargs.get('ex_cpus', 1)),
            memory=str(size.ram),
            password=password,
            row=kwargs.get('ex_row', None),
            group=kwargs.get('ex_group', None)
        )

        # Instantiate VM and get identifier.
        res = self.connection.request(
            '%s/action/instantiateVAppTemplate'
                % kwargs.get('vdc', self.vdcs[0]),
            data=instantiate_xml.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml'
            }
        )
        vapp_name = res.object.get('name')
        vapp_href = get_url_path(res.object.get('href'))

        # Deploy the VM from the identifier.
        res = self.connection.request('%s/action/deploy' % vapp_href,
                                      method='POST')

        self._wait_for_task_completion(res.object.get('href'))

        # Power on the VM.
        res = self.connection.request('%s/power/action/powerOn' % vapp_href,
                                      method='POST')

        res = self.connection.request(vapp_href)
        node = self._to_node(vapp_name, res.object)

        return node

    features = {"create_node": ["password"]}

class HostingComConnection(VCloudConnection):
    """
    vCloud connection subclass for Hosting.com
    """

    host = "vcloud.safesecureweb.com"

    def _get_auth_headers(self):
        """hosting.com doesn't follow the standard vCloud authentication API"""
        return {
            'Authentication':
                base64.b64encode(b('%s:%s' % (self.user_id, self.key))),
            'Content-Length': 0
        }

class HostingComDriver(VCloudNodeDriver):
    """
    vCloud node driver for Hosting.com
    """
    connectionCls = HostingComConnection

class TerremarkConnection(VCloudConnection):
    """
    vCloud connection subclass for Terremark
    """

    host = "services.vcloudexpress.terremark.com"

class TerremarkDriver(VCloudNodeDriver):
    """
    vCloud node driver for Terremark
    """

    connectionCls = TerremarkConnection

    def list_locations(self):
        return [NodeLocation(0, "Terremark Texas", 'US', self)]


class SavvisConnection(VCloudConnection):
    """
    vCloud connection subclass for Savvis
    """

    host = "api.savvis.net"
    login_url = '/vpdc/v1.0/login'

    def _get_auth_headers(self):
        """Some providers need different headers than others"""
        return {
            'Authorization':
                "Basic %s"
                % base64.b64encode(b('%s:%s' % (self.user_id, self.key))),
            'Content-Length': 0,
            'Content-type': 'application/x-www-form-urlencoded' 
        }

OSType = collections.namedtuple('OSType', 'id type name desc storage arch')

class AddVAppXML(object):

    OS_TYPES = {
        '77' : OSType('77', 'Windows', 'winLonghorn64Guest', 'MS Windows Server 2008 (Enterprise 64-bit)', [50, 25], 'x86_64'),
        '79' : OSType('79', 'Linux', 'rhel5Guest', 'RedHat Enterprise Linux 5.x 32-bit', [25, 25], 'i686'),
        '80' : OSType('80', 'Linux', 'rhel5_64Guest', 'RedHat Enterprise Linux 5.x 32-bit', [50, 25], 'x86_64'),
        '103' : OSType('103', 'Windows', 'Windows7Server64Guest', 'MS Windows Server 2008 (Enterprise 64-bit)', [50, 25], 'x86_64'),
    }

    def __init__(self, name, os, network, cpus, memory):
        self.name = name
        self.os = os
        self.network = network
        self.cpus = cpus
        self.memory = memory

        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)

    def _build_xmltree(self):
        self.root = self._make_vapp_root()

        self._add_os_section(self.root)

        # product and virtual hardware
        self._make_virtual_hardware(self.root)

    def _make_vapp_root(self):
        return ET.Element(
            "vApp:VApp",
            {
                "xmlns:common":"http://schemas.dmtf.org/wbem/wscim/1/common",
                "xmlns:vApp":"http://www.vmware.com/vcloud/v0.8",
                "xmlns:rasd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData",
                "xmlns:vssd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData",
                "xmlns:ovf":"http://schemas.dmtf.org/ovf/envelope/1", 
                "name": self.name,
                "type":"application/vnd.vmware.vcloud.vApp+xml", 
                "href":""
            }
        )

    def _add_os_section(self, parent):
        os_section = ET.SubElement(
            parent,
            "ovf:OperatingSystemSection",
            {'ovf:id': self.os}
        )
        ET.SubElement(os_section, "ovf:Info").text='Specifies the operating system installed'
        ET.SubElement(os_section, "ovf:Description").text= self.OS_TYPES[self.os].desc
        return os_section

    def _make_virtual_hardware(self, parent):
        vh = ET.SubElement(
            parent,
            "ovf:VirtualHardwareSection",
        )
        instance_id = 1
        self._add_system(vh, instance_id)
        instance_id += 1
        self._add_cpu(vh, instance_id)
        instance_id += 1
        self._add_memory(vh, instance_id)
        instance_id += 1
        self._add_network(vh, instance_id, self.network)
        instance_id += 1
        self._add_boot_disk(vh, instance_id, self.OS_TYPES[self.os].storage[0])
        instance_id += 1
        self._add_storage_disk(vh, instance_id, self.OS_TYPES[self.os].storage[1])
        #XXX Add support to store more than 2 disks

        return vh

    def _add_storage_disk(self, parent, instance_id, size):
        return self._add_disk(
                parent = parent,
                element = '/data',
                host_resource = 'data',
                instance_id = instance_id,
                res_type = '26',
                size = size
        )
##
#        sd = ET.SubElement(
#            parent,
#            "ovf:Item"
#        )
#        ET.SubElement(sd, "rasd:AllocationUnits").text='Gigabytes'
#        ET.SubElement(sd, "rasd:Caption").text=''
#        ET.SubElement(sd, "rasd:Description").text='Hard Disk'
#        ET.SubElement(sd, "rasd:ElementName").text='/data'
#        ET.SubElement(sd, "rasd:HostResource").text='data'
#        ET.SubElement(sd, "rasd:InstanceID").text=str(instance_id)
#        ET.SubElement(sd, "rasd:ResourceType").text='26'
#        ET.SubElement(sd, "rasd:VirtualQuantity").text = str(size)
#        return sd
#

    def _add_boot_disk(self, parent, instance_id, size):
        return self._add_disk(
                parent = parent,
                element = '/',
                host_resource = 'boot',
                instance_id = instance_id,
                res_type = '27',
                size = size
        )
#        sd = ET.SubElement(
#            parent,
#            "ovf:Item"
#        )
#        ET.SubElement(sd, "rasd:AllocationUnits").text='Gigabytes'
#        ET.SubElement(sd, "rasd:Caption").text=''
#        ET.SubElement(sd, "rasd:Description").text='Hard Disk'
#        ET.SubElement(sd, "rasd:ElementName").text='/'
#        ET.SubElement(sd, "rasd:HostResource").text='boot'
#        ET.SubElement(sd, "rasd:InstanceID").text=str(instance_id)
#        ET.SubElement(sd, "rasd:ResourceType").text='27'
#        ET.SubElement(sd, "rasd:VirtualQuantity").text = str(size)
#        return sd
#
    def _add_disk(self, parent, element, host_resource, instance_id, res_type, size):
        sd = ET.SubElement(
            parent,
            "ovf:Item"
        )
        ET.SubElement(sd, "rasd:AllocationUnits").text='Gigabytes'
        ET.SubElement(sd, "rasd:Caption").text=''
        ET.SubElement(sd, "rasd:Description").text='Hard Disk'
        ET.SubElement(sd, "rasd:ElementName").text=element
        ET.SubElement(sd, "rasd:HostResource").text=host_resource
        ET.SubElement(sd, "rasd:InstanceID").text=str(instance_id)
        ET.SubElement(sd, "rasd:ResourceType").text=res_type
        ET.SubElement(sd, "rasd:VirtualQuantity").text = str(size)
        return sd




    def _add_network(self, parent, instance_id, network_type):

        network = ET.SubElement(
            parent,
            "ovf:Item",
        )
        ET.SubElement(network,"rasd:Caption").text="Nat1to1:true"
        ET.SubElement(network, "rasd:Connection").text=network_type
        ET.SubElement(network, "rasd:ElementName").text="Network"
        ET.SubElement(network, "rasd:InstanceID").text=str(instance_id)
        ET.SubElement(network, "rasd:ResourceType").text='10'
        ET.SubElement(network, "rasd:VirtualQuantity").text='1'
        return network


    def _add_system(self, parent, instance_id):

        ET.SubElement(parent, "ovf:Info").text = "Virtual hardware"
        system = ET.SubElement(parent, "ovf:System")
        ET.SubElement(system,"vssd:Description").text = "Virtual Hardware Family"
        ET.SubElement(system,"vssd:ElementName").text = self.name
        ET.SubElement(system,"vssd:InstanceID").text = str(instance_id)
        ET.SubElement(system,"vssd:VirtualSystemIdentifier").text = self.name
        return system
    
    def _add_cpu(self, parent, instance_id):
        cpu_item = ET.SubElement(
            parent,
            "ovf:Item",
        )
        speed = str(3 * float(self.cpus))  #3 GHz
        ET.SubElement(cpu_item, "rasd:AllocationUnits").text = "%s GHz" %speed
        ET.SubElement(cpu_item, "rasd:Description").text = "Number of Virtual CPUs"
        ET.SubElement(cpu_item, "rasd:ElementName").text= "%s CPU" %self.cpus
        self._add_instance_id(cpu_item, str(instance_id))
        self._add_resource_type(cpu_item, '3')
        self._add_virtual_quantity(cpu_item, '%s' %self.cpus)

        return cpu_item

    def _add_memory(self, parent, instance_id):
        mem_item = ET.SubElement(
            parent,
            "ovf:Item",
        )

        ET.SubElement(mem_item, "rasd:AllocationUnits").text = "Gigabytes"
        ET.SubElement(mem_item, "rasd:Description").text = "Memory Size"
        ET.SubElement(mem_item, "rasd:ElementName").text="Memory"
        self._add_instance_id(mem_item, str(instance_id))
        self._add_resource_type(mem_item, '4')
        self._add_virtual_quantity(mem_item,'%s' %self.memory)

        return mem_item

    def _add_instance_id(self, parent, id):
        elm = ET.SubElement(
            parent,
            "rasd:InstanceID",
        )
        elm.text = id
        return elm

    def _add_resource_type(self, parent, type):
        elm = ET.SubElement(
            parent,
            "rasd:ResourceType",
        )
        elm.text = type
        return elm

    def _add_virtual_quantity(self, parent, amount):
        elm = ET.SubElement(
             parent,
            "rasd:VirtualQuantity",
         )
        elm.text = amount
        return elm

class AddFirewallRuleXML(object):           
    def __init__(self, port, proto, src, dest):
        self.port = port
        self.proto = proto
        self.src = src
        self.dest = dest

        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)

    def _build_xmltree(self):
        self.root = self._make_pfw_root() 
        
        self._add_pfw_rule()
        print "PFW Rule:%s" %self.tostring()
        return
   
    def _add_pfw_rule(self):
        rule = ET.SubElement(self.root, "svvs:FirewallRule")
        ET.SubElement(rule, "svvs:Description").text = "Perimeter Firewall Rule"
        ET.SubElement(rule, "svvs:Type").text = "PERIMETER_FIREWALL"
        ET.SubElement(rule, "svvs:Log").text = "no"
        ET.SubElement(rule, "svvs:Policy").text = "allow"
        proto = ET.SubElement(rule, "svvs:Protocols")
        if "tcp" in self.proto.lower():
            ET.SubElement(proto, "svvs:Tcp").text = "true"
        else:
            ET.SubElement(proto, "svvs:Udp").text = "true"

        ET.SubElement(rule, "svvs:Port").text = str(self.port)
        ET.SubElement(rule, "svvs:Destination").text = self.dest
        ET.SubElement(rule, "svvs:Source").text = self.src
        return rule
         
    def _make_pfw_root(self):
        return ET.Element(
            "svvs:FirewallService",
            {
                "xmlns:common":"http://schemas.dmtf.org/wbem/wscim/1/common",
                "xmlns:vApp":"http://www.vmware.com/vcloud/v0.8",
                "xmlns:rasd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData",
                "xmlns:vssd":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData",
                "xmlns:ovf":"http://schemas.dmtf.org/ovf/envelope/1",
                "xmlns:svvs":"http://schemas.api.sandbox.symphonyVPDC.savvis.net/vpdci"
            })


class SavvisNodeDriver(VCloudNodeDriver):
    """
    vCloud node driver for Savvis
    """
    connectionCls = SavvisConnection
    type = Provider.VCLOUD

    def list_locations(self):
        return [NodeLocation(0, "US EAST", 'US', self)]

    def _fetch_task_info(self, task_href):
        res = self.connection.request(task_href)
        task = res.object.findall(fixxpath(res.object, "Task"))[0]
        return task

    def _to_node(self, name, elm):
        state = elm.get('status')
        public_ips = None
        href = elm.get('href')
        print "Vapp href : %s" %href
        sections = elm.findall('{http://schemas.dmtf.org/ovf/envelope/1}Section')
        for section in sections:
            network = section if section.get('Network') else None
            
            if network.findall('{http://www.vmware.com/vcloud/v0.8}IpAddress'):
                ip_addr = network.findall('{http://www.vmware.com/vcloud/v0.8}IpAddress')
                if ip_addr:
                    private_ips = [ip_addr[0].text]

            elif network.findall('{http://www.vmware.com/vcloud/v0.8}NetworkConfig'):
                networkconfig = network.findall('{http://www.vmware.com/vcloud/v0.8}NetworkConfig')
                [features] = networkconfig[0].findall('{http://www.vmware.com/vcloud/v0.8}Features')
                nat = features.findall('{http://www.vmware.com/vcloud/v0.8}Nat')
                if nat:
                    [nat_rule] = nat[0].findall('{http://www.vmware.com/vcloud/v0.8}NatRule')
            
                    private_ips = [nat_rule.get('internalIP')]
                    if nat_rule.get('externalIP') == '0.0.0.0':
                        public_ips = private_ips
                    else:
                        public_ips = [nat_rule.get('externalIP')]

        if not public_ips:
            public_ips = private_ips
        node = Node(
                    id=elm.get('href'),
                    name=name,
                    state=state,
                    public_ips=public_ips,
                    private_ips=private_ips,
                    driver=self.connection.driver
                    )

        return node


    def destroy_node(self, node):
        node_path = get_url_path(node.id)
        res = self.connection.request(node_path, method='DELETE')
        return res.status == 200

    def create_node(self, **kwargs):
        """Creates and returns node.


        See L{NodeDriver.create_node} for more keyword args.

        Non-standard optional keyword arguments:
        @keyword    ex_network: link to a "Network" e.g., "VM Tier01, VM Tier02, VM Tier03"
        @type       ex_network: C{string}

        @keyword    ex_vdc: link to a "VDC" e.g., "https://services.vcloudexpress.terremark.com/api/v0.8/vdc/1"
        @type       ex_vdc: C{string}

        @keyword    ex_cpus: number of virtual cpus (limit depends on provider)
        @type       ex_cpus: C{int}

        """
        name = kwargs['name']
        os = kwargs['ex_os']
        cpus = kwargs['ex_cpus']
        network = kwargs['network']
        size = kwargs['size']
        vpdc = kwargs['ex_vpdc']
        memory = str(size.ram/1024)
        #Check ORG is available
        self.connection.check_org()
        vdc = Vdc.get_vdc(vpdc, self.connection, self.org)

        if network not in vdc.networks:
            raise ValueError("%s not available. Available Networks are:%s" %(network, vdc.network))

        vapp_xml = AddVAppXML(
                        name = name, 
                        os = os, 
                        network = network, 
                        cpus = cpus, 
                        memory = memory
                    )

        print "VApp XML: %s" %vapp_xml.tostring()

        # Instantiate VM and get identifier.
        res = self.connection.request(
            '%s/vApp' %vdc.href,
            data=vapp_xml.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/xml'
            }
        )
        #Fetch the associate Task
        task = res.object.findall(fixxpath(res.object, "Task"))[0]
        if not task.get('href'):
            error = task.findall(fixxpath(task, "Error"))
            raise Exception("Failed to Create Server : Error %s" %error[0].get('message'))

        self._wait_for_task_completion(task.get('href'),timeout=7200)

        #If task succeeds, fetch vapp information
        task = self._fetch_task_info(task.get('href'))
        result = task.findall(fixxpath(task, "Result"))
        vapp_href = result[0].get('href')

        vapp =self.connection.request(vapp_href)
        vapp_name = vapp.object.get('name')
        node = self._to_node(vapp_name, vapp.object)

        return node

    def ex_create_pf_rule(self, vpdc, port, proto, src, dest):

        #Check ORG is available
        self.connection.check_org()

        vdc = Vdc.get_vdc(vpdc, self.connection, self.org)
        #vdc profile example: Balanced(Provisioning)

        if 'Essential' not in vdc.profile:
            #Open the SSH Port on the perimeter Firewall
            firewall_xml = AddFirewallRuleXML(
                                port = port, 
                                proto = proto, 
                                src = src, 
                                dest = dest
                            )
        
        res = self.connection.request(
                        '%s/FirewallService' %vdc.href,
                        data=firewall_xml.tostring(),
                        method='PUT',
                        headers={'Content-Type':'application/xml'}
            )   
        task = res.object.findall(fixxpath(res.object, "Task"))[0]
        if not task.get('href'):
            error = task.findall(fixxpath(task, "Error"))
            raise Exception("Failed to Create Firewall Rule : Error %s" %error[0].get('message'))

        self._wait_for_task_completion(task.get('href'), timeout=3600)

    
