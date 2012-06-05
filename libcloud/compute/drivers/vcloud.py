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
import copy
import sys
import re
import base64
import os
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import b
from libcloud.utils.py3 import next

urlparse = urlparse.urlparse

import time
import collections

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import _ElementInterface
from xml.parsers.expat import ExpatError

from libcloud.common.base import XmlResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.base import Node, NodeDriver, NodeLocation
from libcloud.compute.base import NodeSize, NodeImage, NodeAuthPassword

"""
From vcloud api "The VirtualQuantity element defines the number of MB
of memory. This should be either 512 or a multiple of 1024 (1 GB)."
"""
VIRTUAL_MEMORY_VALS = [512] + [1024 * i for i in range(1, 9)]

DEFAULT_TASK_COMPLETION_TIMEOUT = 1200

DEFAULT_API_VERSION = '0.8'

"""
Valid vCloud API v1.5 input values.
"""
VIRTUAL_CPU_VALS_1_5 = [i for i in range(1, 9)]
VIRTUAL_MEMORY_VALS_1_5 = [2 ** i for i in range(2, 19)]
FENCE_MODE_VALS_1_5 = ['bridged', 'isolated', 'natRouted']
IP_MODE_VALS_1_5 = ['POOL', 'DHCP', 'MANUAL', 'NONE']


def fixxpath(root, xpath):
    """ElementTree wants namespaces in its xpaths, so here we add them."""
    namespace, root_tag = root.tag[1:].split("}", 1)
    fixed_xpath = "/".join(["{%s}%s" % (namespace, e)
                            for e in xpath.split("/")])
    return fixed_xpath


def get_url_path(url):
    return urlparse(url.strip()).path


class Vdc:
    """Virtual datacenter (vDC) representation"""
    def __init__(self, id, name, driver):
        self.id = id
        self.name = name
        self.driver = driver

    def __repr__(self):
        return (('<Vdc: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))


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


class SavvisVPDC(object):
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
    
                return SavvisVPDC(name=vdc_name, href=vdc_href, profile=vdc_profile, networks=vdc_networks)

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
            'Content-Length': 0,
            'Accept': 'application/*+xml'
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
        headers['Accept'] = 'application/*+xml'
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

    def __new__(cls, key, secret=None, secure=True, host=None, port=None,
                api_version=DEFAULT_API_VERSION, **kwargs):
        if cls is VCloudNodeDriver:
            if api_version == '0.8':
                cls = VCloudNodeDriver
            elif api_version == '1.5':
                cls = VCloud_1_5_NodeDriver
            else:
                raise NotImplementedError(
                    "No VCloudNodeDriver found for API version %s" %
                    (api_version))
        return super(VCloudNodeDriver, cls).__new__(cls)

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
            time.sleep(60)
            try:
                task = self._fetch_task_info(task_href)
                print "Task Href %s Task Status: %s" %(task_href, task.get("status"))
                status = task.get('status')
            except Exception as e:
                print "Exception in Waiting for task completion : %s" %e
                pass


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
            res = self.connection.request(vdc.id)
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
                try:
                    res = self.connection.request(
                        vapp_href,
                        headers={'Content-Type': 'application/vnd.vmware.vcloud.vApp+xml'}
                    )
                    nodes.append(self._to_node(res.object))
                except Exception:
                    # The vApp was probably removed since the previous vDC query, ignore
                    e = sys.exc_info()[1]
                    if not (isinstance(e.args[0], _ElementInterface) and
                            e.args[0].tag.endswith('Error') and
                            e.args[0].get('minorErrorCode') == 'ACCESS_TO_RESOURCE_IS_FORBIDDEN'):
                        raise e

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


    def request(self, *args, **kwargs):
        retry = 3
        while retry > 0:
            try:
                self._get_auth_token()
                return super(VCloudConnection, self).request(*args, **kwargs)
            except ParseError as err:
                if 'line 1, column 0' in err.msg:
                    #Indicates that the Savvis servers are overloaded atm. Retry again
                    retry -= 1
                    time.sleep(60)
                else:
                    raise err

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
        '80' : OSType('80', 'Linux', 'rhel5_64Guest', 'RedHat Enterprise Linux 5.x 32-bit', [25, 25], 'x86_64'),
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
        return [
                NodeLocation(0, "US_EAST", 'US', self),
                NodeLocation(1, "US_WEST", 'US', self),
                NodeLocation(2, "EMEA", 'US', self),
                NodeLocation(3, "ASIA", 'US', self),
        ]

    def _fetch_task_info(self, task_href):
        res = self.connection.request(task_href)
        task = res.object.findall(fixxpath(res.object, "Task"))[0]
        return task

    def get_vpdc_info(self, vpdc):
        self.connection.check_org()
        return SavvisVPDC.get_vdc(vpdc, self.connection, self.org)

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
        network = kwargs['ex_network']
        size = kwargs['size']
        vpdc = kwargs['ex_vpdc']
        memory = str(size.ram/1024)
        #Check ORG is available
        self.connection.check_org()
        vdc = SavvisVPDC.get_vdc(vpdc, self.connection, self.org)

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

        self._wait_for_task_completion(task.get('href'),timeout=14400)

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

        vdc = SavvisVPDC.get_vdc(vpdc, self.connection, self.org)
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

class VCloud_1_5_Connection(VCloudConnection):

    def _get_auth_token(self):
        if not self.token:
            # Log In
            conn = self.conn_classes[self.secure](self.host,
                                                  self.port)
            conn.request(method='POST', url='/api/sessions',
                         headers=self._get_auth_headers())

            resp = conn.getresponse()
            headers = dict(resp.getheaders())

            # Set authorization token
            try:
                self.token = headers['x-vcloud-authorization']
            except KeyError:
                raise InvalidCredsError()

            # Get the URL of the Organization
            body = ET.XML(resp.read())
            self.org_name = body.get('org')
            org_list_url = get_url_path(
                next((link for link in body.findall(fixxpath(body, 'Link'))
                    if link.get('type') == 'application/vnd.vmware.vcloud.orgList+xml')).get('href')
            )

            conn.request(method='GET', url=org_list_url,
                         headers=self.add_default_headers({}))
            body = ET.XML(conn.getresponse().read())
            self.driver.org = get_url_path(
                next((org for org in body.findall(fixxpath(body, 'Org'))
                    if org.get('name') == self.org_name)).get('href')
            )

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/*+xml;version=1.5'
        headers['x-vcloud-authorization'] = self.token
        return headers

class Instantiate_1_5_VAppXML(object):
    def __init__(self, name, template, network, vm_network=None, vm_fence=None):
        self.name = name
        self.template = template
        self.network = network
        self.vm_network = vm_network
        self.vm_fence = vm_fence
        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)

    def _build_xmltree(self):
        self.root = self._make_instantiation_root()

        if self.network:
            instantionation_params = ET.SubElement(self.root, "InstantiationParams")
            network_config_section = ET.SubElement(instantionation_params, "NetworkConfigSection")
            ET.SubElement(network_config_section, "Info", {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"})
            network_config = ET.SubElement(network_config_section, "NetworkConfig")
            self._add_network_association(network_config)

        self._add_vapp_template(self.root)

    def _make_instantiation_root(self):
        return ET.Element(
            "InstantiateVAppTemplateParams",
                {'name': self.name,
                 'deploy': 'false',
                 'powerOn': 'false',
                 'xml:lang': 'en',
                 'xmlns': "http://www.vmware.com/vcloud/v1.5",
                 'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"}
        )

    def _add_vapp_template(self, parent):
        return ET.SubElement(
            parent,
            "Source",
                {'href': self.template}
        )

    def _add_network_association(self, parent):
        if self.vm_network is None:
            # Don't set a custom vApp VM network name
            parent.set('networkName', self.network.get('name'))
        else:
            # Set a custom vApp VM network name
            parent.set('networkName', self.vm_network)
        configuration = ET.SubElement(parent, 'Configuration')
        ET.SubElement(configuration, 'ParentNetwork', {'href': self.network.get('href')})
        if self.vm_fence is None:
            fencemode = self.network.find(fixxpath(self.network, 'Configuration/FenceMode')).text
        else:
            fencemode = self.vm_fence
        ET.SubElement(configuration, 'FenceMode').text = fencemode




class VCloud_1_5_NodeDriver(VCloudNodeDriver):

    connectionCls = VCloud_1_5_Connection

    # Based on http://pubs.vmware.com/vcloud-api-1-5/api_prog/GUID-843BE3AD-5EF6-4442-B864-BCAE44A51867.html
    NODE_STATE_MAP = {'-1': NodeState.UNKNOWN,
                      '0': NodeState.PENDING,
                      '1': NodeState.PENDING,
                      '2': NodeState.PENDING,
                      '3': NodeState.PENDING,
                      '4': NodeState.RUNNING,
                      '5': NodeState.RUNNING,
                      '6': NodeState.UNKNOWN,
                      '7': NodeState.UNKNOWN,
                      '8': NodeState.TERMINATED,
                      '9': NodeState.UNKNOWN,
                      '10': NodeState.UNKNOWN}
    @property
    def vdcs(self):
        """
        vCloud virtual data centers (vDCs).
        @return: C{list} of L{Vdc} objects
        """
        if not self._vdcs:
            self.connection.check_org()  # make sure the org is set.  # pylint: disable-msg=E1101
            res = self.connection.request(self.org)
            self._vdcs = [
                Vdc(i.get('href'), i.get('name'), self)
                for i
                in res.object.findall(fixxpath(res.object, "Link"))
                if i.get('type') == 'application/vnd.vmware.vcloud.vdc+xml'
            ]
        return self._vdcs

    @property
    def networks(self):
        networks = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc.id).object
            networks.extend(
                [network
                 for network in res.findall(
                     fixxpath(res, 'AvailableNetworks/Network')
                 )]
            )

        return networks


    def _get_vdc(self, vdc_name):
        vdc = None
        if not vdc_name:
            # Return the first organisation VDC found
            vdc = self.vdcs[0]
        else:
            for v in self.vdcs:
                if v.name == vdc_name:
                    vdc = v
            if vdc is None:
                raise ValueError('%s virtual data centre could not be found', vdc_name)
        return vdc

    def list_images(self, location=None):
        images = []
        for vdc in self.vdcs:
            res = self.connection.request(vdc.id).object
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

        def idfun(image):
            return image.id
        return self._uniquer(images, idfun)

    def _uniquer(self, seq, idfun=None):
        if idfun is None:
            def idfun(x):
                return x
        seen = {}
        result = []
        for item in seq:
            marker = idfun(item)
            if marker in seen:
                continue
            seen[marker] = 1
            result.append(item)
        return result



    def list_locations(self):
        return [NodeLocation(id=self.connection.host, name=self.connection.host, country="N/A", driver=self)]

    def ex_find_node(self, node_name, vdcs=None):
        """
        Searches for node across specified vDCs. This is more effective than querying all nodes to get a single
        instance.

        @param node_name: The name of the node to search for
        @type node_name: C{string}

        @param vdcs: None, vDC or a list of vDCs to search in. If None all vDCs will be searched.
        @type node_name: L{Vdc}

        @return: C{Node} node instance or None if not found
        """
        if not vdcs:
            vdcs = self.vdcs
        if not getattr(vdcs, '__iter__', False):
            vdcs = [vdcs]
        for vdc in vdcs:
            res = self.connection.request(vdc.id)
            entity_elems = res.object.findall(fixxpath(res.object, "ResourceEntities/ResourceEntity"))
            for entity_elem in entity_elems:
                if entity_elem.get('type') == 'application/vnd.vmware.vcloud.vApp+xml' and entity_elem.get('name') == node_name:
                    res = self.connection.request(entity_elem.get('href'),
                                                  headers={'Content-Type': 'application/vnd.vmware.vcloud.vApp+xml'})
                    return self._to_node(res.object)
        return None

    def destroy_node(self, node):
        try:
            self.ex_undeploy_node(node)
        except Exception:
            # Some vendors don't implement undeploy at all yet,
            # so catch this and move on.
            pass

        res = self.connection.request(get_url_path(node.id), method='DELETE')
        return res.status == httplib.ACCEPTED

    def reboot_node(self, node):
        res = self.connection.request('%s/power/action/reset'
                                      % get_url_path(node.id),
                                      method='POST')
        if res.status in [httplib.ACCEPTED, httplib.NO_CONTENT]:
            self._wait_for_task_completion(res.object.get('href'))
            return True
        else:
            return False

    def ex_deploy_node(self, node):
        """
        Deploys existing node. Equal to vApp "start" operation.

        @param node: The node to be deployed
        @type node: L{Node}

        @return: C{Node} deployed node
        """
        deploy_xml = ET.Element('DeployVAppParams', {'powerOn': 'true',
                                                     'xmlns': 'http://www.vmware.com/vcloud/v1.5'})
        res = self.connection.request('%s/action/deploy' % get_url_path(node.id),
                                      data=ET.tostring(deploy_xml),
                                      method='POST',
                                      headers={
                                          'Content-Type': 'application/vnd.vmware.vcloud.deployVAppParams+xml'
                                      })
        self._wait_for_task_completion(res.object.get('href'))
        res = self.connection.request(get_url_path(node.id))
        return self._to_node(res.object)

    def ex_undeploy_node(self, node):
        """
        Undeploys existing node. Equal to vApp "stop" operation.

        @param node: The node to be deployed
        @type node: L{Node}

        @return: C{Node} undeployed node instance
        """
        undeploy_xml = ET.Element('UndeployVAppParams', {'xmlns': 'http://www.vmware.com/vcloud/v1.5'})
        undeploy_power_action_xml = ET.SubElement(undeploy_xml, 'UndeployPowerAction')
        undeploy_power_action_xml.text = 'shutdown'

        try:
            res = self.connection.request('%s/action/undeploy' % get_url_path(node.id),
                                          data=ET.tostring(undeploy_xml),
                                          method='POST',
                                          headers={
                                              'Content-Type': 'application/vnd.vmware.vcloud.undeployVAppParams+xml'
                                          })
            self._wait_for_task_completion(res.object.get('href'))
        except Exception:
            undeploy_power_action_xml.text = 'powerOff'
            res = self.connection.request('%s/action/undeploy' % get_url_path(node.id),
                                          data=ET.tostring(undeploy_xml),
                                          method='POST',
                                          headers={
                                              'Content-Type': 'application/vnd.vmware.vcloud.undeployVAppParams+xml'
                                          })
            self._wait_for_task_completion(res.object.get('href'))

        res = self.connection.request(get_url_path(node.id))
        return self._to_node(res.object)

    def create_node(self, **kwargs):
        """Creates and returns node. If the source image is:
           - vApp template - a new vApp is instantiated from template
           - existing vApp - a new vApp is cloned from the source vApp. Can not clone more vApps is parallel otherwise
                             resource busy error is raised.


        See L{NodeDriver.create_node} for more keyword args.

        @keyword    image:  OS Image to boot on node. (required). Can be a NodeImage or existing Node that will be
                            cloned.
        @type       image:  L{NodeImage} or L{Node}

        Non-standard optional keyword arguments:
        @keyword    ex_network: Organisation's network name for attaching vApp VMs to.
        @type       ex_network: C{string}

        @keyword    ex_vdc: Name of organisation's virtual data center where vApp VMs will be deployed.
        @type       ex_vdc: C{string}

        @keyword    ex_vm_names: list of names to be used as a VM and computer name. The name must be max. 15 characters
                                 long and follow the host name requirements.
        @type       ex_vm_names: C{list} of L{string}

        @keyword    ex_vm_cpu: number of virtual CPUs/cores to allocate for each vApp VM.
        @type       ex_vm_cpu: C{number}

        @keyword    ex_vm_memory: amount of memory in MB to allocate for each vApp VM.
        @type       ex_vm_memory: C{number}

        @keyword    ex_vm_script: full path to file containing guest customisation script for each vApp VM.
                                  Useful for creating users & pushing out public SSH keys etc.
        @type       ex_vm_script: C{string}

        @keyword    ex_vm_network: Override default vApp VM network name. Useful for when you've imported an OVF
                                   originating from outside of the vCloud.
        @type       ex_vm_network: C{string}

        @keyword    ex_vm_fence: Fence mode for connecting the vApp VM network (ex_vm_network) to the parent
                                 organisation network (ex_network).
        @type       ex_vm_fence: C{string}

        @keyword    ex_vm_ipmode: IP address allocation mode for all vApp VM network connections.
        @type       ex_vm_ipmode: C{string}

        @keyword    ex_deploy: set to False if the node shouldn't be deployed (started) after creation
        @type       ex_deploy: C{bool}
        """
        name = kwargs['name']
        image = kwargs['image']
        ex_vm_names = kwargs.get('ex_vm_names')
        ex_vm_cpu = kwargs.get('ex_vm_cpu')
        ex_vm_memory = kwargs.get('ex_vm_memory')
        ex_vm_script = kwargs.get('ex_vm_script')
        ex_vm_fence = kwargs.get('ex_vm_fence', None)
        ex_network = kwargs.get('ex_network', None)
        ex_vm_network = kwargs.get('ex_vm_network', None)
        ex_vm_ipmode = kwargs.get('ex_vm_ipmode', None)
        ex_deploy = kwargs.get('ex_deploy', True)
        ex_vdc = kwargs.get('ex_vdc', None)
        ex_org_network = kwargs.get('ex_org_network', None)
        self._validate_vm_names(ex_vm_names)
        self._validate_vm_cpu(ex_vm_cpu)
        self._validate_vm_memory(ex_vm_memory)
        self._validate_vm_fence(ex_vm_fence)
        self._validate_vm_ipmode(ex_vm_ipmode)
        ex_vm_script = self._validate_vm_script(ex_vm_script)

        # Some providers don't require a network link
        if ex_network:
            network_href = self._get_network_href(ex_network)
            network_elem = self.connection.request(network_href).object
        else:
            network_elem = None

        vdc = self._get_vdc(ex_vdc)

        if self._is_node(image):
            vapp_name, vapp_href = self._clone_node(name, image, vdc)
        else:
            vapp_name, vapp_href = self._instantiate_node(name, image, network_elem,
                                                          vdc, ex_vm_network, ex_vm_fence)

        self._change_vm_names(vapp_href, ex_vm_names)
        self._change_vm_cpu(vapp_href, ex_vm_cpu)
        self._change_vm_memory(vapp_href, ex_vm_memory)
        self._change_vm_script(vapp_href, ex_vm_script)
        self._change_vm_ipmode(vapp_href, ex_vm_ipmode)
        #Required for Bluelock vCD 1.5
        if ex_org_network:
            self._configure_vapp_org_network(vapp_href, ex_org_network)
        # Power on the VM.
        if ex_deploy:
            # Retry 3 times: when instantiating large number of VMs at the same time some may fail on resource allocation
            retry = 3
            while True:
                try:
                    res = self.connection.request('%s/power/action/powerOn' % vapp_href,
                                                  method='POST')
                    self._wait_for_task_completion(res.object.get('href'))
                    break
                except Exception:
                    if retry <= 0:
                        raise
                    retry -= 1
                    time.sleep(10)

        res = self.connection.request(vapp_href)
        node = self._to_node(res.object)
        return node

    def _instantiate_node(self, name, image, network_elem, vdc, vm_network, vm_fence):
        instantiate_xml = Instantiate_1_5_VAppXML(
            name=name,
            template=image.id,
            network=network_elem,
            vm_network=vm_network,
            vm_fence=vm_fence
        )

        # Instantiate VM and get identifier.
        res = self.connection.request(
            '%s/action/instantiateVAppTemplate' % vdc.id,
            data=instantiate_xml.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml'
            }
        )
        vapp_name = res.object.get('name')
        vapp_href = get_url_path(res.object.get('href'))

        task_href = res.object.find(fixxpath(res.object, "Tasks/Task")).get('href')
        self._wait_for_task_completion(task_href)
        return vapp_name, vapp_href

    def _clone_node(self, name, sourceNode, vdc):

        clone_xml = ET.Element("CloneVAppParams",
                {'name': name, 'deploy': 'false', 'powerOn': 'false',
                 'xmlns': "http://www.vmware.com/vcloud/v1.5",
                 'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"}
        )
        ET.SubElement(clone_xml, 'Description').text = 'Clone of ' + sourceNode.name
        ET.SubElement(clone_xml, 'Source', {'href': sourceNode.id})

        res = self.connection.request(
            '%s/action/cloneVApp' % vdc.id,
            data=ET.tostring(clone_xml),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.cloneVAppParams+xml'
            }
        )
        vapp_name = res.object.get('name')
        vapp_href = get_url_path(res.object.get('href'))

        task_href = res.object.find(fixxpath(res.object, "Tasks/Task")).get('href')
        self._wait_for_task_completion(task_href)

        res = self.connection.request(vapp_href)

        vms = res.object.findall(fixxpath(res.object, "Children/Vm"))

        # Fix the networking for VMs
        for i, vm in enumerate(vms):
            # Remove network
            network_xml = ET.Element("NetworkConnectionSection", {
                'ovf:required': 'false',
                'xmlns': "http://www.vmware.com/vcloud/v1.5",
                'xmlns:ovf': 'http://schemas.dmtf.org/ovf/envelope/1'})
            ET.SubElement(network_xml, "ovf:Info").text = 'Specifies the available VM network connections'
            res = self.connection.request('%s/networkConnectionSection' % get_url_path(vm.get('href')),
                                          data=ET.tostring(network_xml),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.networkConnectionSection+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

            # Re-add network
            network_xml = vm.find(fixxpath(vm, 'NetworkConnectionSection'))
            network_conn_xml = network_xml.find(fixxpath(network_xml, 'NetworkConnection'))
            network_conn_xml.set('needsCustomization', 'true')
            network_conn_xml.remove(network_conn_xml.find(fixxpath(network_xml, 'IpAddress')))
            network_conn_xml.remove(network_conn_xml.find(fixxpath(network_xml, 'MACAddress')))

            res = self.connection.request('%s/networkConnectionSection' % get_url_path(vm.get('href')),
                                          data=ET.tostring(network_xml),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.networkConnectionSection+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

        return vapp_name, vapp_href

    def ex_set_vm_cpu(self, vapp_or_vm_id, vm_cpu):
        """
        Sets the number of virtual CPUs for the specified VM or VMs under the vApp. If the vapp_or_vm_id param
        represents a link to an vApp all VMs that are attached to this vApp will be modified.

        Please ensure that hot-adding a virtual CPU is enabled for the powered on virtual machines.
        Otherwise use this method on undeployed vApp.

        @keyword    vapp_or_vm_id: vApp or VM ID that will be modified. If a vApp ID is used here all attached VMs
                                   will be modified
        @type       vapp_or_vm_id: C{string}

        @keyword    vm_cpu: number of virtual CPUs/cores to allocate for specified VMs
        @type       vm_cpu: C{number}
        """
        self._validate_vm_cpu(vm_cpu)
        self._change_vm_cpu(vapp_or_vm_id, vm_cpu)

    def ex_set_vm_memory(self, vapp_or_vm_id, vm_memory):
        """
        Sets the virtual memory in MB to allocate for the specified VM or VMs under the vApp.
        If the vapp_or_vm_id param represents a link to an vApp all VMs that are attached to
        this vApp will be modified.

        Please ensure that hot-change of virtual memory is enabled for the powered on virtual machines.
        Otherwise use this method on undeployed vApp.

        @keyword    vapp_or_vm_id: vApp or VM ID that will be modified. If a vApp ID is used here all attached VMs
                                   will be modified
        @type       vapp_or_vm_id: C{string}

        @keyword    vm_memory: virtual memory in MB to allocate for the specified VM or VMs
        @type       vm_memory: C{number}
        """
        self._validate_vm_memory(vm_memory)
        self._change_vm_memory(vapp_or_vm_id, vm_memory)

    def ex_add_vm_disk(self, vapp_or_vm_id, vm_disk_size):
        """
        Adds a virtual disk to the specified VM or VMs under the vApp. If the vapp_or_vm_id param
        represents a link to an vApp all VMs that are attached to this vApp will be modified.

        @keyword    vapp_or_vm_id: vApp or VM ID that will be modified. If a vApp ID is used here all attached VMs
                                   will be modified
        @type       vapp_or_vm_id: C{string}

        @keyword    vm_disk_size: the disk capacity in GB that will be added to the specified VM or VMs
        @type       vm_disk_size: C{number}
        """
        self._validate_vm_disk_size(vm_disk_size)
        self._add_vm_disk(vapp_or_vm_id, vm_disk_size)

    @staticmethod
    def _validate_vm_names(names):
        if names is None:
            return
        hname_re = re.compile('^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9]*)[\-])*([A-Za-z]|[A-Za-z][A-Za-z0-9]*[A-Za-z0-9])$')
        for name in names:
            if len(name) > 15:
                raise ValueError('The VM name "' + name + '" is too long for the computer name (max 15 chars allowed).')
            if not hname_re.match(name):
                raise ValueError('The VM name "' + name + '" can not be used. "' + name + '" is not a valid computer name for the VM.')

    @staticmethod
    def _validate_vm_memory(vm_memory):
        if vm_memory is None:
            return
        elif vm_memory not in VIRTUAL_MEMORY_VALS_1_5:
            raise ValueError('%s is not a valid vApp VM memory value' % vm_memory)

    @staticmethod
    def _validate_vm_cpu(vm_cpu):
        if vm_cpu is None:
            return
        elif vm_cpu not in VIRTUAL_CPU_VALS_1_5:
            raise ValueError('%s is not a valid vApp VM CPU value' % vm_cpu)

    @staticmethod
    def _validate_vm_disk_size(vm_disk):
        if vm_disk is None:
            return
        elif int(vm_disk) < 0:
            raise ValueError('%s is not a valid vApp VM disk space value', vm_disk)

    @staticmethod
    def _validate_vm_script(vm_script):
        if vm_script is None:
            return
        # Try to locate the script file
        if not os.path.isabs(vm_script):
            vm_script = os.path.expanduser(vm_script)
            vm_script = os.path.abspath(vm_script)
        if not os.path.isfile(vm_script):
            raise LibcloudError("%s the VM script file does not exist" % vm_script)
        try:
            open(vm_script).read()
        except:
            raise
        return vm_script

    @staticmethod
    def _validate_vm_fence(vm_fence):
        if vm_fence is None:
            return
        elif vm_fence not in FENCE_MODE_VALS_1_5:
            raise ValueError('%s is not a valid fencing mode value' % vm_fence)

    @staticmethod
    def _validate_vm_ipmode(vm_ipmode):
        if vm_ipmode is None:
            return
        elif vm_ipmode == 'MANUAL':
            raise NotImplementedError('MANUAL IP mode: The interface for supplying IPAddress does not exist yet')
        elif vm_ipmode not in IP_MODE_VALS_1_5:
            raise ValueError('%s is not a valid IP address allocation mode value' % vm_ipmode)

    def _change_vm_names(self, vapp_or_vm_id, vm_names):
        if vm_names is None:
            return

        vms = self._get_vm_elements(vapp_or_vm_id)
        for i, vm in enumerate(vms):
            if len(vm_names) <= i:
                return

            # Get GuestCustomizationSection
            res = self.connection.request('%s/guestCustomizationSection' % get_url_path(vm.get('href')))

            # Update GuestCustomizationSection
            res.object.find(fixxpath(res.object, 'ComputerName')).text = vm_names[i]
            # Remove AdminPassword from customization section
            admin_pass = res.object.find(fixxpath(res.object, 'AdminPassword'))
            if admin_pass is not None:
                res.object.remove(admin_pass)
            res = self.connection.request('%s/guestCustomizationSection' % get_url_path(vm.get('href')),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.guestCustomizationSection+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

            # Update Vm name
            req_xml = ET.Element("Vm", {
                'name': vm_names[i],
                'xmlns': "http://www.vmware.com/vcloud/v1.5"})
            res = self.connection.request(get_url_path(vm.get('href')),
                                          data=ET.tostring(req_xml),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.vm+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _change_vm_cpu(self, vapp_or_vm_id, vm_cpu):
        if vm_cpu is None:
            return

        vms = self._get_vm_elements(vapp_or_vm_id)
        for vm in vms:
            # Get virtualHardwareSection/cpu section
            res = self.connection.request('%s/virtualHardwareSection/cpu' % get_url_path(vm.get('href')))

            # Update VirtualQuantity field
            res.object.find(
                '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}VirtualQuantity'
            ).text = str(vm_cpu)
            res = self.connection.request('%s/virtualHardwareSection/cpu' % get_url_path(vm.get('href')),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.rasdItem+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _change_vm_memory(self, vapp_or_vm_id, vm_memory):
        if vm_memory is None:
            return

        vms = self._get_vm_elements(vapp_or_vm_id)
        for vm in vms:
            # Get virtualHardwareSection/memory section
            res = self.connection.request('%s/virtualHardwareSection/memory' % get_url_path(vm.get('href')))

            # Update VirtualQuantity field
            res.object.find(
                '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}VirtualQuantity'
            ).text = str(vm_memory)
            res = self.connection.request('%s/virtualHardwareSection/memory' % get_url_path(vm.get('href')),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.rasdItem+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _add_vm_disk(self, vapp_or_vm_id, vm_disk):
        if vm_disk is None:
            return

        rasd_ns = '{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData}'

        vms = self._get_vm_elements(vapp_or_vm_id)
        for vm in vms:
            # Get virtualHardwareSection/disks section
            res = self.connection.request('%s/virtualHardwareSection/disks' % vm.get('href'))

            existing_ids = []
            new_disk = None
            for item in res.object.findall(fixxpath(res.object, 'Item')):
                # Clean Items from unnecessary stuff
                for elem in item:
                    if elem.tag == '%sInstanceID' % rasd_ns:
                        existing_ids.append(int(elem.text))
                    if elem.tag in ['%sAddressOnParent' % rasd_ns, '%sParent' % rasd_ns]:
                        item.remove(elem)
                if item.find('%sHostResource' % rasd_ns) is not None:
                    new_disk = item

            new_disk = copy.deepcopy(new_disk)
            disk_id = max(existing_ids) + 1
            new_disk.find('%sInstanceID' % rasd_ns).text = str(disk_id)
            new_disk.find('%sElementName' % rasd_ns).text = 'Hard Disk ' + str(disk_id)
            new_disk.find('%sHostResource' % rasd_ns).set(fixxpath(new_disk, 'capacity'), str(int(vm_disk) * 1024))
            res.object.append(new_disk)

            res = self.connection.request('%s/virtualHardwareSection/disks' % vm.get('href'),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type': 'application/vnd.vmware.vcloud.rasditemslist+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _change_vm_script(self, vapp_or_vm_id, vm_script):
        if vm_script is None:
            return

        vms = self._get_vm_elements(vapp_or_vm_id)
        try:
            script = open(vm_script).read()
        except:
            return

        # ElementTree escapes script characters automatically. Escape requirements:
        # http://www.vmware.com/support/vcd/doc/rest-api-doc-1.5-html/types/GuestCustomizationSectionType.html
        for vm in vms:
            # Get GuestCustomizationSection
            res = self.connection.request('%s/guestCustomizationSection' % get_url_path(vm.get('href')))

            # Attempt to update any existing CustomizationScript element
            try:
                res.object.find(fixxpath(res.object, 'CustomizationScript')).text = script
            except:
                # CustomizationScript section does not exist, insert it just before ComputerName
                for i, e in enumerate(res.object):
                    if e.tag == '{http://www.vmware.com/vcloud/v1.5}ComputerName':
                        break
                e = ET.Element('{http://www.vmware.com/vcloud/v1.5}CustomizationScript')
                e.text = script
                res.object.insert(i, e)

            # Remove AdminPassword from customization section due to an API quirk
            admin_pass = res.object.find(fixxpath(res.object, 'AdminPassword'))
            if admin_pass is not None:
                res.object.remove(admin_pass)

            # Update VM's GuestCustomizationSection
            res = self.connection.request('%s/guestCustomizationSection' % get_url_path(vm.get('href')),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type':
                                                   'application/vnd.vmware.vcloud.guestCustomizationSection+xml'
                                          }
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _change_vm_ipmode(self, vapp_or_vm_id, vm_ipmode):
        if vm_ipmode is None:
            return

        vms = self._get_vm_elements(vapp_or_vm_id)

        for vm in vms:
            res = self.connection.request('%s/networkConnectionSection' % get_url_path(vm.get('href')))
            net_conns = res.object.findall(fixxpath(res.object, 'NetworkConnection'))
            for c in net_conns:
                c.find(fixxpath(c, 'IpAddressAllocationMode')).text = vm_ipmode

            res = self.connection.request('%s/networkConnectionSection' % get_url_path(vm.get('href')),
                                          data=ET.tostring(res.object),
                                          method='PUT',
                                          headers={'Content-Type':
                                                   'application/vnd.vmware.vcloud.networkConnectionSection+xml'}
            )
            self._wait_for_task_completion(res.object.get('href'))

    def _configure_vapp_org_network(self, vapp_id, org_network):
        res = self.connection.request('%s/networkConfigSection' % get_url_path(vapp_id))
        org_net_href = self._get_network_href(org_network)

        networkconfig = res.object.findall(fixxpath(res.object, "NetworkConfig"))[0]
        configuration = networkconfig.findall(fixxpath(networkconfig, "Configuration"))[0]

        #Delete fencemode, syslogserversettings, RetainNetInfoAcrossDeployments

        configuration.remove(configuration.findall(fixxpath(configuration, "FenceMode"))[0])
        configuration.remove(configuration.findall(fixxpath(configuration, "RetainNetInfoAcrossDeployments"))[0])
        configuration.remove(configuration.findall(fixxpath(configuration, "SyslogServerSettings"))[0])
        configuration.remove(configuration.findall(fixxpath(configuration, "Features"))[0])
        configuration.remove(configuration.findall(fixxpath(configuration, "IpScope"))[0])


        #Enable NAT from vapp network to org network
        networkconfig = res.object.findall(fixxpath(res.object, "NetworkConfig"))[0]
        configuration = networkconfig.findall(fixxpath(networkconfig, "Configuration"))[0]
        ET.SubElement(configuration, "ns0:ParentNetwork", {
            'type':"application/vnd.vmware.vcloud.network+xml", 
            'name':org_network, 
            'href': org_net_href
        })

        fence_mode = ET.SubElement(configuration, "ns0:FenceMode")
        fence_mode.text = 'natRouted'
        retain = ET.SubElement(configuration, "ns0:RetainNetInfoAcrossDeployments")
        retain.text = "true"
        features = ET.SubElement(configuration, "ns0:Features")
        firewall_service = ET.SubElement(features, "ns0:FirewallService")
        enabled = ET.SubElement(firewall_service, "ns0:IsEnabled")
        #XXX Setup Firewall properly, disabled for now
        enabled.text = 'false'

        #Setup NAT rule
        nat_service = ET.SubElement(features, "ns0:NatService")
        ET.SubElement(nat_service, "ns0:IsEnabled").text = 'true'
        ET.SubElement(nat_service, "ns0:NatType").text = 'ipTranslation'
        ET.SubElement(nat_service, "ns0:Policy").text = 'allowTraffic'


        #Associate the Org network wth the vApp
        networkconfig = ET.SubElement(res.object, "ns0:NetworkConfig", {'networkName':"%s" %org_network})
        ET.SubElement(networkconfig, "ns0:Link", {'rel':'repair', 'href': org_net_href })
        ET.SubElement(networkconfig, "ns0:Description")
        config = ET.SubElement(networkconfig, "ns0:Configuration")
        ET.SubElement(config, "ns0:ParentNetwork", {'type' :
                                                "application/vnd.vmware.vcloud.network+xml",
                                               
                                                'name' : org_network,
                                                'href' : org_net_href
                                               })
        fence_mode = ET.SubElement(config, "ns0:FenceMode")
        fence_mode.text = "bridged"

        retain = ET.SubElement(config, "ns0:RetainNetInfoAcrossDeployments")
        retain.text = "true"
        
        ET.SubElement(config, "ns0:SyslogServerSettings")

        print "NetworkConfigSection : %s" %ET.tostring(res.object)
        res = self.connection.request('%s/networkConfigSection' % get_url_path(vapp_id),
                                      data = ET.tostring(res.object),
                                      method = 'PUT',
                                      headers={'Content-Type':
                                               'application/vnd.vmware.vcloud.networkconfigsection+xml'}
                                     )


        self._wait_for_task_completion(res.object.get('href'))
        

    def _get_network_href(self, network_name):
        network_href = None

        # Find the organisation's network href
        res = self.connection.request(self.org)
        links = res.object.findall(fixxpath(res.object, 'Link'))
        for l in links:
            if  l.attrib['type'] == 'application/vnd.vmware.vcloud.orgNetwork+xml'\
            and l.attrib['name'] == network_name:
                network_href = l.attrib['href']

        if network_href is None:
            raise ValueError('%s is not a valid organisation network name' % network_name)
        else:
            return network_href

    def _get_vm_elements(self, vapp_or_vm_id):
        res = self.connection.request(vapp_or_vm_id)
        if res.object.tag.endswith('VApp'):
            vms = res.object.findall(fixxpath(res.object, 'Children/Vm'))
        elif res.object.tag.endswith('Vm'):
            vms = [res.object]
        else:
            raise ValueError('Specified ID value is not a valid VApp or Vm identifier.')
        return vms

    def _is_node(self, node_or_image):
        return isinstance(node_or_image, Node)

    def _to_node(self, node_elm):

        # Parse VMs as extra field
        vms = []
        for vm_elem in node_elm.findall(fixxpath(node_elm, 'Children/Vm')):
            public_ips = []
            private_ips = []
            password = vm_elem.find(fixxpath(vm_elem, 'GuestCustomizationSection/AdminPassword'))
            if password is not None:
                password = password.text
            for connection in vm_elem.findall(fixxpath(vm_elem, 'NetworkConnectionSection/NetworkConnection')):
                ip = connection.find(fixxpath(connection, "IpAddress"))
                if ip is not None:
                    private_ips.append(ip.text)
                external_ip = connection.find(fixxpath(connection, "ExternalIpAddress"))
                if external_ip is not None:
                    public_ips.append(external_ip.text)
                elif ip is not None:
                    public_ips.append(ip.text)

            vm = {
                'id': vm_elem.get('href'),
                'name': vm_elem.get('name'),
                'state': self.NODE_STATE_MAP[vm_elem.get('status')],
                'public_ips': public_ips,
                'private_ips': private_ips,
                'password' : password
            }
            vms.append(vm)

        # Take the node IP addresses from all VMs
        public_ips = []
        private_ips = []
        for vm in vms:
            public_ips.extend(vm['public_ips'])
            private_ips.extend(vm['private_ips'])

        node = Node(id=node_elm.get('href'),
                    name=node_elm.get('name'),
                    state=self.NODE_STATE_MAP[node_elm.get('status')],
                    public_ips=public_ips,
                    private_ips=private_ips,
                    driver=self.connection.driver,
                    extra={'vms': vms})
        return node
