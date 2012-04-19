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
import sys
import re
import base64
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import b

urlparse = urlparse.urlparse

import time

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import _ElementInterface
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

DEFAULT_API_VERSION = '0.8'


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
            'Item',
            {'xmlns': "http://schemas.dmtf.org/ovf/envelope/1"}
        )
        self._add_instance_id(mem_item, '2')
        self._add_resource_type(mem_item, '4')
        self._add_virtual_quantity(mem_item, self.memory)

        return mem_item

    def _add_instance_id(self, parent, id):
        elm = ET.SubElement(
            parent,
            'InstanceID',
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = id
        return elm

    def _add_resource_type(self, parent, type):
        elm = ET.SubElement(
            parent,
            'ResourceType',
            {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
        )
        elm.text = type
        return elm

    def _add_virtual_quantity(self, parent, amount):
        elm = ET.SubElement(
             parent,
             'VirtualQuantity',
             {'xmlns': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData'}
         )
        elm.text = amount
        return elm

    def _add_network_association(self, parent):
        return ET.SubElement(
            parent,
            'NetworkAssociation',
            {'href': self.net_href}
        )


class VCloudResponse(XmlResponse):

    def success(self):
        return self.status in (httplib.OK, httplib.CREATED,
                               httplib.NO_CONTENT, httplib.ACCEPTED)


class VCloudConnection(ConnectionUserAndKey):
    """
    Connection class for the vCloud driver
    """

    responseCls = VCloudResponse
    token = None
    host = None

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
            conn.request(method='POST', url='/api/v0.8/login',
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
    name = 'vCloud'
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
                     fixxpath(res, 'AvailableNetwors/Network')
                 )]
            )

        return networks

    def _to_image(self, image):
        image = NodeImage(id=image.get('href'),
                          name=image.get('name'),
                          driver=self.connection.driver)
        return image

    def _to_node(self, elm):
        state = self.NODE_STATE_MAP[elm.get('status')]
        name = elm.get('name')
        public_ips = []
        private_ips = []

        # Following code to find private IPs works for Terremark
        connections = elm.findall('%s/%s' % (
                '{http://schemas.dmtf.org/ovf/envelope/1}NetworkConnectionSection',
                fixxpath(elm, 'NetworkConnection')
            )
        )
        if not connections:
            connections = elm.findall(fixxpath(elm, 'Children/Vm/NetworkConnectionSection/NetworkConnection'))

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

    def _wait_for_task_completion(self, task_href,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        start_time = time.time()
        res = self.connection.request(task_href)
        status = res.object.get('status')
        while status != 'success':
            if status == 'error':
                # Get error reason from the response body
                error_elem = res.object.find(fixxpath(res.object, 'Error'))
                error_msg = "Unknown error"
                if error_elem != None:
                    error_msg = error_elem.get('message')
                raise Exception("Error status returned by task %s.: %s"
                                % (task_href, error_msg))
            if status == 'canceled':
                raise Exception("Canceled status returned by task %s."
                                % task_href)
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout while waiting for task %s."
                                % task_href)
            time.sleep(5)
            res = self.connection.request(task_href)
            status = res.object.get('status')

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
        return res.status == httplib.ACCEPTED

    def reboot_node(self, node):
        res = self.connection.request('%s/power/action/reset'
                                      % get_url_path(node.id),
                                      method='POST')
        return res.status in [httplib.ACCEPTED, httplib.NO_CONTENT]

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
                % kwargs.get('vdc', self.vdcs[0].id),
            data=instantiate_xml.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml'
            }
        )
        vapp_href = get_url_path(res.object.get('href'))

        # Deploy the VM from the identifier.
        res = self.connection.request('%s/action/deploy' % vapp_href,
                                      method='POST')

        self._wait_for_task_completion(res.object.get('href'))

        # Power on the VM.
        res = self.connection.request('%s/power/action/powerOn' % vapp_href,
                                      method='POST')

        res = self.connection.request(vapp_href)
        node = self._to_node(res.object)

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
            org_name = body.get('org')
            org_list_url = get_url_path(
                next((link for link in body.findall(fixxpath(body, 'Link'))
                    if link.get('type') == 'application/vnd.vmware.vcloud.orgList+xml')).get('href')
            )

            conn.request(method='GET', url=org_list_url,
                         headers=self.add_default_headers({}))
            body = ET.XML(conn.getresponse().read())
            self.driver.org = get_url_path(
                next((org for org in body.findall(fixxpath(body, 'Org'))
                    if org.get('name') == org_name)).get('href')
            )

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/*+xml;version=1.5'
        headers['x-vcloud-authorization'] = self.token
        return headers


class Instantiate_1_5_VAppXML(object):
    def __init__(self, name, template, network):
        self.name = name
        self.template = template
        self.network = network
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
        parent.set('networkName', self.network.get('name'))
        configuration = ET.SubElement(parent, 'Configuration')
        ET.SubElement(configuration, 'ParentNetwork', {'href': self.network.get('href')})
        configuration.append(self.network.find(fixxpath(self.network, 'Configuration/FenceMode')))


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
        @keyword    ex_network: link to a "Network" e.g., "https://services.vcloudexpress.terremark.com/api/network/7"
        @type       ex_network: C{string}

        @keyword    ex_vdc: link to a "VDC" e.g., "https://services.vcloudexpress.terremark.com/api/vdc/1"
        @type       ex_vdc: C{string}

        @keyword    ex_vm_names: list of names to be used as a VM and computer name. The name must be max. 15 characters
                                 long and follow the host name requirements
        @type       ex_vm_names: C{list} of L{string}

        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs.get('size', None)
        ex_vm_names = kwargs.get('ex_vm_names')

        self._validate_vm_names(ex_vm_names)

        # Some providers don't require a network link
        network_href = kwargs.get('ex_network', None)
        if network_href:
            network_elem = self.connection.request(network_href).object
        else:
            network_elem = None

        vdc = kwargs.get('ex_vdc', self.vdcs[0])
        if not vdc:
            vdc = self.vdcs[0]

        if self._is_node(image):
            vapp_name, vapp_href = self._clone_node(name, image, vdc)
        else:
            vapp_name, vapp_href = self._instantiate_node(name, image, network_elem, vdc)

        self._change_vm_names(vapp_href, ex_vm_names)

        # Power on the VM.
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

    def _instantiate_node(self, name, image, network_elem, vdc):
        instantiate_xml = Instantiate_1_5_VAppXML(
            name=name,
            template=image.id,
            network=network_elem
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

    def _change_vm_names(self, vapp_href, vm_names):
        if vm_names is None:
            return

        res = self.connection.request(vapp_href)
        vms = res.object.findall(fixxpath(res.object, "Children/Vm"))

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

    def _is_node(self, node_or_image):
        return isinstance(node_or_image, Node)
