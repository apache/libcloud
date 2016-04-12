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
Dimension Data Driver
"""

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.compute.base import NodeDriver, Node, NodeAuthPassword
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation
from libcloud.common.dimensiondata import dd_object_to_id
from libcloud.common.dimensiondata import DimensionDataAPIException
from libcloud.common.dimensiondata import (DimensionDataConnection,
                                           DimensionDataStatus)
from libcloud.common.dimensiondata import DimensionDataNetwork
from libcloud.common.dimensiondata import DimensionDataNetworkDomain
from libcloud.common.dimensiondata import DimensionDataVlan
from libcloud.common.dimensiondata import DimensionDataServerCpuSpecification
from libcloud.common.dimensiondata import DimensionDataServerDisk
from libcloud.common.dimensiondata import DimensionDataServerVMWareTools
from libcloud.common.dimensiondata import DimensionDataPublicIpBlock
from libcloud.common.dimensiondata import DimensionDataFirewallRule
from libcloud.common.dimensiondata import DimensionDataFirewallAddress
from libcloud.common.dimensiondata import DimensionDataNatRule
from libcloud.common.dimensiondata import DimensionDataAntiAffinityRule
from libcloud.common.dimensiondata import NetworkDomainServicePlan
from libcloud.common.dimensiondata import API_ENDPOINTS, DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.common.dimensiondata import SERVER_NS, NETWORK_NS, GENERAL_NS
from libcloud.utils.py3 import urlencode
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.utils.py3 import basestring
from libcloud.compute.types import NodeState, Provider

# Node state map is a dictionary with the keys as tuples
# These tuples represent:
# (<state_of_node_from_didata>, <is node started?>, <action happening>)
NODE_STATE_MAP = {
    ('NORMAL', 'true', None):
        NodeState.RUNNING,
    ('NORMAL', 'false', None):
        NodeState.STOPPED,
    ('PENDING_CHANGE', 'true', 'START_SERVER'):
        NodeState.STARTING,
    ('PENDING_ADD', 'true', 'DEPLOY_SERVER'):
        NodeState.STARTING,
    ('PENDING_ADD', 'true', 'DEPLOY_SERVER_WITH_DISK_SPEED'):
        NodeState.STARTING,
    ('PENDING_CHANGE', 'true', 'SHUTDOWN_SERVER'):
        NodeState.STOPPING,
    ('PENDING_CHANGE', 'true', 'POWER_OFF_SERVER'):
        NodeState.STOPPING,
    ('PENDING_CHANGE', 'true', 'REBOOT_SERVER'):
        NodeState.REBOOTING,
    ('PENDING_CHANGE', 'true', 'RESET_SERVER'):
        NodeState.REBOOTING,
    ('PENDING_CHANGE', 'true', 'RECONFIGURE_SERVER'):
        NodeState.RECONFIGURING,
}


class DimensionDataNodeDriver(NodeDriver):
    """
    DimensionData node driver.
    """

    selected_region = None
    connectionCls = DimensionDataConnection
    name = 'DimensionData'
    website = 'http://www.dimensiondata.com/'
    type = Provider.DIMENSIONDATA
    features = {'create_node': ['password']}
    api_version = 1.0

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS:
            raise ValueError('Invalid region: %s' % (region))

        self.selected_region = API_ENDPOINTS[region]

        super(DimensionDataNodeDriver, self).__init__(key=key, secret=secret,
                                                      secure=secure, host=host,
                                                      port=port,
                                                      api_version=api_version,
                                                      region=region,
                                                      **kwargs)

    def _ex_connection_class_kwargs(self):
        """
            Add the region to the kwargs before the connection is instantiated
        """

        kwargs = super(DimensionDataNodeDriver,
                       self)._ex_connection_class_kwargs()
        kwargs['region'] = self.selected_region
        return kwargs

    def create_node(self, name, image, auth, ex_description,
                    ex_network=None, ex_network_domain=None,
                    ex_vlan=None, ex_primary_ipv4=None,
                    ex_memory_gb=None,
                    ex_cpu_specification=None,
                    ex_is_started=True, ex_additional_nics_vlan=None,
                    ex_additional_nics_ipv4=None, **kwargs):
        """
        Create a new DimensionData node

        :keyword    name:   String with a name for this new node (required)
        :type       name:   ``str``

        :keyword    image:  OS Image to boot on node. (required)
        :type       image:  :class:`NodeImage` or ``str``

        :keyword    auth:   Initial authentication information for the
                            node. (If this is a customer LINUX
                            image auth will be ignored)
        :type       auth:   :class:`NodeAuthPassword` or ``str`` or ``None``

        :keyword    ex_description:  description for this node (required)
        :type       ex_description:  ``str``

        :keyword    ex_network:  Network to create the node within
                                 (required unless using ex_network_domain
                                 or ex_primary_ipv4)

        :type       ex_network: :class:`DimensionDataNetwork` or ``str``

        :keyword    ex_network_domain:  Network Domain to create the node
                                        (required unless using network
                                        or ex_primary_ipv4)
        :type       ex_network_domain: :class:`DimensionDataNetworkDomain`
                                        or ``str``

        :keyword    ex_primary_ipv4: Primary nics IPv4 Address
                                     MCP1: (required unless ex_network)
                                     MCP2: (required unless ex_vlan)
        :type       ex_primary_ipv4: ``str``

        :keyword    ex_vlan:  VLAN to create the node within
                              (required unless using network)
        :type       ex_vlan: :class:`DimensionDataVlan` or ``str``

        :keyword    ex_memory_gb:  The amount of memory in GB for the server
        :type       ex_memory_gb: ``int``

        :keyword    ex_cpu_specification: The spec of CPU to deploy (optional)
        :type       ex_cpu_specification:
            :class:`DimensionDataServerCpuSpecification`

        :keyword    ex_is_started:  Start server after creation? default
                                   true (required)
        :type       ex_is_started:  ``bool``

        :keyword    ex_additional_nics_vlan: (MCP2 Only) List of additional
                                              nics to add by vlan
        :type       ex_additional_nics_vlan: ``list`` of
            :class:`DimensionDataVlan` or ``list`` of ``str``

        :keyword    ex_additional_nics_ipv4: (MCP2 Only) List of additional
                                              nics to add by ipv4 address
        :type       ex_additional_nics_ipv4: ``list`` of ``str``

        :return: The newly created :class:`Node`.
        :rtype: :class:`Node`
        """
        password = None
        image_needs_auth = self._image_needs_auth(image)
        if image_needs_auth:
            if isinstance(auth, basestring):
                auth_obj = NodeAuthPassword(password=auth)
                password = auth
            else:
                auth_obj = self._get_and_check_auth(auth)
                password = auth_obj.password

        if (ex_network_domain is None and
                ex_network is None and
                ex_primary_ipv4 is None):
            raise ValueError("One of ex_network_domain, ex_network, "
                             "or ex_ipv6_primary must be specified")

        server_elm = ET.Element('deployServer', {'xmlns': TYPES_URN})
        ET.SubElement(server_elm, "name").text = name
        ET.SubElement(server_elm, "description").text = ex_description
        image_id = self._image_to_image_id(image)
        ET.SubElement(server_elm, "imageId").text = image_id
        ET.SubElement(server_elm, "start").text = str(ex_is_started).lower()
        if password is not None:
            ET.SubElement(server_elm, "administratorPassword").text = password

        if ex_cpu_specification is not None:
            cpu = ET.SubElement(server_elm, "cpu")
            cpu.set('speed', ex_cpu_specification.performance)
            cpu.set('count', str(ex_cpu_specification.cpu_count))
            cpu.set('coresPerSocket',
                    str(ex_cpu_specification.cores_per_socket))

        if ex_memory_gb is not None:
            ET.SubElement(server_elm, "memoryGb").text = str(ex_memory_gb)

        if ex_network is not None:
            network_elm = ET.SubElement(server_elm, "network")
            network_id = self._network_to_network_id(ex_network)
            ET.SubElement(network_elm, "networkId").text = network_id
        elif ex_network_domain is None and ex_primary_ipv4 is not None:
            network_elm = ET.SubElement(server_elm, "network")
            ET.SubElement(network_elm, "privateIpv4").text = ex_primary_ipv4
        elif ex_network_domain is not None:
            net_domain_id = self._network_domain_to_network_domain_id(
                ex_network_domain)
            network_inf_elm = ET.SubElement(
                server_elm, "networkInfo",
                {'networkDomainId': net_domain_id}
            )

            if ex_vlan is not None:
                vlan_id = self._vlan_to_vlan_id(ex_vlan)
                pri_nic = ET.SubElement(network_inf_elm, "primaryNic")
                ET.SubElement(pri_nic, "vlanId").text = vlan_id
            elif ex_primary_ipv4 is not None:
                pri_nic = ET.SubElement(network_inf_elm, "primaryNic")
                ET.SubElement(pri_nic, "privateIpv4").text = ex_primary_ipv4
            else:
                raise ValueError("One of ex_vlan or ex_primary_ipv4 "
                                 "must be specified")

            if isinstance(ex_additional_nics_ipv4, (list, tuple)):
                for ipv4_nic in ex_additional_nics_ipv4:
                    add_nic = ET.SubElement(network_inf_elm, "additionalNic")
                    ET.SubElement(add_nic, "privateIpv4").text = ipv4_nic
            elif ex_additional_nics_ipv4 is not None:
                raise TypeError("ex_additional_nics_ipv4 must "
                                "be None or a tuple/list")

            if isinstance(ex_additional_nics_vlan, (list, tuple)):
                for vlan_nic in ex_additional_nics_vlan:
                    add_nic = ET.SubElement(network_inf_elm, "additionalNic")
                    ET.SubElement(add_nic, "vlanId").text = vlan_nic
            elif ex_additional_nics_vlan is not None:
                raise TypeError("ex_additional_nics_vlan"
                                "must be None or tuple/list")

        response = self.connection.request_with_orgId_api_2(
            'server/deployServer',
            method='POST',
            data=ET.tostring(server_elm)).object

        node_id = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'serverId':
                node_id = info.get('value')

        node = self.ex_get_node_by_id(node_id)

        if image_needs_auth:
            if getattr(auth_obj, "generated", False):
                node.extra['password'] = auth_obj.password

        return node

    def destroy_node(self, node):
        """
        Deletes a node, node must be stopped before deletion


        :keyword node: The node to delete
        :type    node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('deleteServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/deleteServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def reboot_node(self, node):
        """
        Reboots a node by requesting the OS restart via the hypervisor


        :keyword node: The node to reboot
        :type    node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('rebootServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/rebootServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def list_nodes(self, ex_location=None, ex_name=None,
                   ex_ipv6=None, ex_ipv4=None, ex_vlan=None,
                   ex_image=None, ex_deployed=None,
                   ex_started=None, ex_state=None,
                   ex_network=None, ex_network_domain=None):
        """
        List nodes deployed for your organization.

        :keyword ex_location: Filters the node list to nodes that are
                              located in this location
        :type    ex_location: :class:`NodeLocation` or ``str``

        :keyword ex_name: Filters the node list to nodes that have this name
        :type    ex_name ``str``

        :keyword ex_ipv6: Filters the node list to nodes that have this
                          ipv6 address
        :type    ex_ipv6: ``str``

        :keyword ex_ipv4: Filters the node list to nodes that have this
                          ipv4 address
        :type    ex_ipv4: ``str``

        :keyword ex_vlan: Filters the node list to nodes that are in this VLAN
        :type    ex_vlan: :class:`DimensionDataVlan` or ``str``

        :keyword ex_image: Filters the node list to nodes that have this image
        :type    ex_image: :class:`NodeImage` or ``str``

        :keyword ex_deployed: Filters the node list to nodes that are
                              deployed or not
        :type    ex_deployed: ``bool``

        :keyword ex_started: Filters the node list to nodes that are
                             started or not
        :type    ex_started: ``bool``

        :keyword ex_state: Filters the node list by nodes that are in
                           this state
        :type    ex_state: ``str``

        :keyword ex_network: Filters the node list to nodes in this network
        :type    ex_network: :class:`DimensionDataNetwork` or ``str``

        :keyword ex_network_domain: Filters the node list to nodes in this
                                    network domain
        :type    ex_network_domain: :class:`DimensionDataNetworkDomain`
                                    or ``str``

        :return: a list of `Node` objects
        :rtype: ``list`` of :class:`Node`
        """
        node_list = []
        for nodes in self.ex_list_nodes_paginated(
                location=ex_location,
                name=ex_name, ipv6=ex_ipv6,
                ipv4=ex_ipv4, vlan=ex_vlan,
                image=ex_image, deployed=ex_deployed,
                started=ex_started, state=ex_state,
                network=ex_network,
                network_domain=ex_network_domain):
            node_list.extend(nodes)

        return node_list

    def list_images(self, location=None):
        """
        List images available

        Note:  Currently only returns the default 'base OS images'
               provided by DimensionData. Customer images (snapshots)
               are not yet supported.

        :keyword ex_location: Filters the node list to nodes that are
                              located in this location
        :type    ex_location: :class:`NodeLocation` or ``str``

        :return: List of images available
        :rtype: ``list`` of :class:`NodeImage`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = self._location_to_location_id(location)

        return self._to_images(
            self.connection.request_with_orgId_api_2(
                'image/osImage',
                params=params)
            .object)

    def list_sizes(self, location=None):
        """
        return a list of available sizes
            Currently, the size of the node is dictated by the chosen OS base
            image, they cannot be set explicitly.

        @inherits: :class:`NodeDriver.list_sizes`
        """
        return [
            NodeSize(id=1,
                     name="default",
                     ram=0,
                     disk=0,
                     bandwidth=0,
                     price=0,
                     driver=self.connection.driver),
        ]

    def list_locations(self, ex_id=None):
        """
        List locations (datacenters) available for instantiating servers and
        networks.

        :keyword ex_id: Filters the location list to this id
        :type    ex_id: ``str``

        :return:  List of locations
        :rtype:  ``list`` of :class:`NodeLocation`
        """
        params = {}
        if ex_id is not None:
            params['id'] = ex_id

        return self._to_locations(
            self.connection
            .request_with_orgId_api_2(
                'infrastructure/datacenter',
                params=params
            ).object
        )

    def list_networks(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.


        :keyword location: The location
        :type    location: :class:`NodeLocation` or ``str``

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        url_ext = ''
        if location is not None:
            url_ext = '/' + self._location_to_location_id(location)

        return self._to_networks(
            self.connection
            .request_with_orgId_api_1('networkWithLocation%s' % url_ext)
            .object)

    def ex_list_nodes_paginated(self, name=None, location=None,
                                ipv6=None, ipv4=None, vlan=None,
                                image=None, deployed=None, started=None,
                                state=None, network=None, network_domain=None):
        """
        Return a generator which yields node lists in pages

        :keyword location: Filters the node list to nodes that are
                           located in this location
        :type    location: :class:`NodeLocation` or ``str``

        :keyword name: Filters the node list to nodes that have this name
        :type    name ``str``

        :keyword ipv6: Filters the node list to nodes that have this
                       ipv6 address
        :type    ipv6: ``str``

        :keyword ipv4: Filters the node list to nodes that have this
                       ipv4 address
        :type    ipv4: ``str``

        :keyword vlan: Filters the node list to nodes that are in this VLAN
        :type    vlan: :class:`DimensionDataVlan` or ``str``

        :keyword image: Filters the node list to nodes that have this image
        :type    image: :class:`NodeImage` or ``str``

        :keyword deployed: Filters the node list to nodes that are
                           deployed or not
        :type    deployed: ``bool``

        :keyword started: Filters the node list to nodes that are
                          started or not
        :type    started: ``bool``

        :keyword state: Filters the node list to nodes that are in
                        this state
        :type    state: ``str``

        :keyword network: Filters the node list to nodes in this network
        :type    network: :class:`DimensionDataNetwork` or ``str``

        :keyword network_domain: Filters the node list to nodes in this
                                 network domain
        :type    network_domain: :class:`DimensionDataNetworkDomain`
                                 or ``str``

        :return: a list of `Node` objects
        :rtype: ``generator`` of `list` of :class:`Node`
        """

        params = {}
        if location is not None:
            params['datacenterId'] = self._location_to_location_id(location)
        if ipv6 is not None:
            params['ipv6'] = ipv6
        if ipv4 is not None:
            params['privateIpv4'] = ipv4
        if state is not None:
            params['state'] = state
        if started is not None:
            params['started'] = started
        if deployed is not None:
            params['deployed'] = deployed
        if name is not None:
            params['name'] = name
        if network_domain is not None:
            params['networkDomainId'] = \
                self._network_domain_to_network_domain_id(network_domain)
        if network is not None:
            params['networkId'] = self._network_to_network_id(network)
        if vlan is not None:
            params['vlanId'] = self._vlan_to_vlan_id(vlan)
        if image is not None:
            params['sourceImageId'] = self._image_to_image_id(image)

        nodes_obj = self._list_nodes_single_page(params)
        yield self._to_nodes(nodes_obj)

        while nodes_obj.get('pageCount') >= nodes_obj.get('pageSize'):
            params['pageNumber'] = int(nodes_obj.get('pageNumber')) + 1
            nodes_obj = self._list_nodes_single_page(params)
            yield self._to_nodes(nodes_obj)

    def ex_start_node(self, node):
        """
        Powers on an existing deployed server

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('startServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/startServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_shutdown_graceful(self, node):
        """
        This function will attempt to "gracefully" stop a server by
        initiating a shutdown sequence within the guest operating system.
        A successful response on this function means the system has
        successfully passed the request into the operating system.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('shutdownServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/shutdownServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_power_off(self, node):
        """
        This function will abruptly power-off a server.  Unlike
        ex_shutdown_graceful, success ensures the node will stop but some OS
        and application configurations may be adversely affected by the
        equivalent of pulling the power plug out of the machine.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('powerOffServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/powerOffServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_reset(self, node):
        """
        This function will abruptly reset a server.  Unlike
        reboot_node, success ensures the node will restart but some OS
        and application configurations may be adversely affected by the
        equivalent of pulling the power plug out of the machine.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('resetServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/resetServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_update_vm_tools(self, node):
        """
        This function triggers an update of the VMware Tools
        software running on the guest OS of a Server.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        request_elm = ET.Element('updateVmwareTools',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/updateVmwareTools',
            method='POST',
            data=ET.tostring(request_elm)).object
        response_code = findtext(body, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_update_node(self, node, name=None, description=None,
                       cpu_count=None, ram_mb=None):
        """
        Update the node, the name, CPU or RAM

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :param      name: The new name (optional)
        :type       name: ``str``

        :param      description: The new description (optional)
        :type       description: ``str``

        :param      cpu_count: The new CPU count (optional)
        :type       cpu_count: ``int``

        :param      ram_mb: The new Memory in MB (optional)
        :type       ram_mb: ``int``

        :rtype: ``bool``
        """
        data = {}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        if cpu_count is not None:
            data['cpuCount'] = str(cpu_count)
        if ram_mb is not None:
            data['memory'] = str(ram_mb)
        body = self.connection.request_with_orgId_api_1(
            'server/%s' % (node.id),
            method='POST',
            data=urlencode(data, True)).object
        response_code = findtext(body, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_create_anti_affinity_rule(self, node_list):
        """
        Create an anti affinity rule given a list of nodes
        Anti affinity rules ensure that servers will not reside
        on the same VMware ESX host

        :param node_list: The list of nodes to create a rule for
        :type  node_list: ``list`` of :class:`Node` or
                          ``list`` of ``str``

        :rtype: ``bool``
        """
        if not isinstance(node_list, (list, tuple)):
            raise TypeError("Node list must be a list or a tuple.")
        anti_affinity_xml_request = ET.Element('NewAntiAffinityRule',
                                               {'xmlns': SERVER_NS})
        for node in node_list:
            ET.SubElement(anti_affinity_xml_request, 'serverId').text = \
                self._node_to_node_id(node)
        result = self.connection.request_with_orgId_api_1(
            'antiAffinityRule',
            method='POST',
            data=ET.tostring(anti_affinity_xml_request)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_delete_anti_affinity_rule(self, anti_affinity_rule):
        """
        Remove anti affinity rule

        :param anti_affinity_rule: The anti affinity rule to delete
        :type  anti_affinity_rule: :class:`DimensionDataAntiAffinityRule` or
                                   ``str``

        :rtype: ``bool``
        """
        rule_id = self._anti_affinity_rule_to_anti_affinity_rule_id(
            anti_affinity_rule)
        result = self.connection.request_with_orgId_api_1(
            'antiAffinityRule/%s?delete' % (rule_id),
            method='GET').object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_list_anti_affinity_rules(self, network=None, network_domain=None,
                                    node=None, filter_id=None,
                                    filter_state=None):
        """
        List anti affinity rules for a network, network domain, or node

        :param network: The network to list anti affinity rules for
                        One of network, network_domain, or node is required
        :type  network: :class:`DimensionDataNetwork` or ``str``

        :param network_domain: The network domain to list anti affinity rules
                               One of network, network_domain,
                               or node is required
        :type  network_domain: :class:`DimensionDataNetworkDomain` or ``str``

        :param node: The node to list anti affinity rules for
                     One of network, netwok_domain, or node is required
        :type  node: :class:`Node` or ``str``

        :param filter_id: This will allow you to filter the rules
                          by this node id
        :type  filter_id: ``str``

        :type  filter_state: This will allow you to filter rules by
                             node state (i.e. NORMAL)
        :type  filter_state: ``str``

        :rtype: ``list`` of :class:`DimensionDataAntiAffinityRule`
        """
        not_none_arguments = [key
                              for key in (network, network_domain, node)
                              if key is not None]
        if len(not_none_arguments) != 1:
            raise ValueError("One and ONLY one of network, "
                             "network_domain, or node must be set")

        params = {}
        if network_domain is not None:
            params['networkDomainId'] = \
                self._network_domain_to_network_domain_id(network_domain)
        if network is not None:
            params['networkId'] = \
                self._network_to_network_id(network)
        if node is not None:
            params['serverId'] = \
                self._node_to_node_id(node)
        if filter_id is not None:
            params['id'] = filter_id
        if filter_state is not None:
            params['state'] = filter_state

        paged_result = self.connection.paginated_request_with_orgId_api_2(
            'server/antiAffinityRule',
            method='GET',
            params=params
        )

        rules = []
        for result in paged_result:
            rules.extend(self._to_anti_affinity_rules(result))
        return rules

    def ex_attach_node_to_vlan(self, node, vlan=None, private_ipv4=None):
        """
        Attach a node to a VLAN by adding an additional NIC to
        the node on the target VLAN. The IP will be automatically
        assigned based on the VLAN IP network space. Alternatively, provide
        a private IPv4 address instead of VLAN information, and this will
        be assigned to the node on corresponding NIC.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :param      vlan: VLAN to attach the node to
                          (required unless private_ipv4)
        :type       vlan: :class:`DimensionDataVlan`

        :keyword    private_ipv4: Private nic IPv4 Address
                                  (required unless vlan)
        :type       private_ipv4: ``str``

        :rtype: ``bool``
        """
        request = ET.Element('addNic',
                             {'xmlns': TYPES_URN})
        ET.SubElement(request, 'serverId').text = node.id
        nic = ET.SubElement(request, 'nic')

        if vlan is not None:
            ET.SubElement(nic, 'vlanId').text = vlan.id
        elif private_ipv4 is not None:
            ET.SubElement(nic, 'privateIpv4').text = private_ipv4
        else:
            raise ValueError("One of vlan or primary_ipv4 "
                             "must be specified")

        response = self.connection.request_with_orgId_api_2(
            'server/addNic',
            method='POST',
            data=ET.tostring(request)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_destroy_nic(self, nic_id):
        """
        Remove a NIC on a node, removing the node from a VLAN

        :param      nic_id: The identifier of the NIC to remove
        :type       nic_id: ``str``

        :rtype: ``bool``
        """
        request = ET.Element('removeNic',
                             {'xmlns': TYPES_URN,
                              'id': nic_id})

        response = self.connection.request_with_orgId_api_2(
            'server/removeNic',
            method='POST',
            data=ET.tostring(request)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_list_networks(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.

        :param location: The target location
        :type  location: :class:`NodeLocation` or ``str``

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        return self.list_networks(location=location)

    def ex_create_network(self, location, name, description=None):
        """
        Create a new network in an MCP 1.0 location

        :param   location: The target location (MCP1)
        :type    location: :class:`NodeLocation` or ``str``

        :param   name: The name of the network
        :type    name: ``str``

        :param   description: Additional description of the network
        :type    description: ``str``

        :return: A new instance of `DimensionDataNetwork`
        :rtype:  Instance of :class:`DimensionDataNetwork`
        """
        network_location = self._location_to_location_id(location)

        create_node = ET.Element('NewNetworkWithLocation',
                                 {'xmlns': NETWORK_NS})
        ET.SubElement(create_node, "name").text = name
        if description is not None:
            ET.SubElement(create_node, "description").text = description
        ET.SubElement(create_node, "location").text = network_location

        self.connection.request_with_orgId_api_1(
            'networkWithLocation',
            method='POST',
            data=ET.tostring(create_node))

        # MCP1 API does not return the ID, but name is unique for location
        network = list(
            filter(lambda x: x.name == name,
                   self.ex_list_networks(location)))[0]

        return network

    def ex_delete_network(self, network):
        """
        Delete a network from an MCP 1 data center

        :param  network: The network to delete
        :type   network: :class:`DimensionDataNetwork`

        :rtype: ``bool``
        """
        response = self.connection.request_with_orgId_api_1(
            'network/%s?delete' % network.id,
            method='GET').object
        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code == "SUCCESS"

    def ex_rename_network(self, network, new_name):
        """
        Rename a network in MCP 1 data center

        :param  network: The network to rename
        :type   network: :class:`DimensionDataNetwork`

        :param  new_name: The new name of the network
        :type   new_name: ``str``

        :rtype: ``bool``
        """
        response = self.connection.request_with_orgId_api_1(
            'network/%s' % network.id,
            method='POST',
            data='name=%s' % new_name).object
        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code == "SUCCESS"

    def ex_get_network_domain(self, network_domain_id):
        """
        Get an individual Network Domain, by identifier

        :param      network_domain_id: The identifier of the network domain
        :type       network_domain_id: ``str``

        :rtype: :class:`DimensionDataNetworkDomain`
        """
        locations = self.list_locations()
        net = self.connection.request_with_orgId_api_2(
            'network/networkDomain/%s' % network_domain_id).object
        return self._to_network_domain(net, locations)

    def ex_list_network_domains(self, location=None, name=None,
                                service_plan=None, state=None):
        """
        List networks domains deployed across all data center locations
        for your organization.
        The response includes the location of each network domain.

        :param      location: Only network domains in the location (optional)
        :type       location: :class:`NodeLocation` or ``str``

        :param      name: Only network domains of this name (optional)
        :type       name: ``str``

        :param      service_plan: Only network domains of this type (optional)
        :type       service_plan: ``str``

        :param      state: Only network domains in this state (optional)
        :type       state: ``str``

        :return: a list of `DimensionDataNetwork` objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = self._location_to_location_id(location)
        if name is not None:
            params['name'] = name
        if service_plan is not None:
            params['type'] = service_plan
        if state is not None:
            params['state'] = state

        response = self.connection \
            .request_with_orgId_api_2('network/networkDomain',
                                      params=params).object
        return self._to_network_domains(response)

    def ex_create_network_domain(self, location, name, service_plan,
                                 description=None):
        """
        Deploy a new network domain to a data center

        :param      location: The data center to list
        :type       location: :class:`NodeLocation` or ``str``

        :param      name: The name of the network domain to create
        :type       name: ``str``

        :param      service_plan: The service plan, either "ESSENTIALS"
            or "ADVANCED"
        :type       service_plan: ``str``

        :param      description: An additional description of
                                 the network domain
        :type       description: ``str``

        :return: an instance of `DimensionDataNetworkDomain`
        :rtype: :class:`DimensionDataNetworkDomain`
        """
        create_node = ET.Element('deployNetworkDomain', {'xmlns': TYPES_URN})
        ET.SubElement(
            create_node,
            "datacenterId"
        ).text = self._location_to_location_id(location)

        ET.SubElement(create_node, "name").text = name
        if description is not None:
            ET.SubElement(create_node, "description").text = description
        ET.SubElement(create_node, "type").text = service_plan

        response = self.connection.request_with_orgId_api_2(
            'network/deployNetworkDomain',
            method='POST',
            data=ET.tostring(create_node)).object

        network_domain_id = None

        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'networkDomainId':
                network_domain_id = info.get('value')

        return DimensionDataNetworkDomain(
            id=network_domain_id,
            name=name,
            description=description,
            location=location,
            status=NodeState.RUNNING,
            plan=service_plan
        )

    def ex_update_network_domain(self, network_domain):
        """
        Update the properties of a network domain

        :param      network_domain: The network domain with updated properties
        :type       network_domain: :class:`DimensionDataNetworkDomain`

        :return: an instance of `DimensionDataNetworkDomain`
        :rtype: :class:`DimensionDataNetworkDomain`
        """
        edit_node = ET.Element('editNetworkDomain', {'xmlns': TYPES_URN})
        edit_node.set('id', network_domain.id)
        ET.SubElement(edit_node, "name").text = network_domain.name
        if network_domain.description is not None:
            ET.SubElement(edit_node, "description").text \
                = network_domain.description
        ET.SubElement(edit_node, "type").text = network_domain.plan

        self.connection.request_with_orgId_api_2(
            'network/editNetworkDomain',
            method='POST',
            data=ET.tostring(edit_node)).object

        return network_domain

    def ex_delete_network_domain(self, network_domain):
        """
        Delete a network domain

        :param      network_domain: The network domain to delete
        :type       network_domain: :class:`DimensionDataNetworkDomain`

        :rtype: ``bool``
        """
        delete_node = ET.Element('deleteNetworkDomain', {'xmlns': TYPES_URN})
        delete_node.set('id', network_domain.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteNetworkDomain',
            method='POST',
            data=ET.tostring(delete_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_create_vlan(self,
                       network_domain,
                       name,
                       private_ipv4_base_address,
                       description=None,
                       private_ipv4_prefix_size=24):
        """
        Deploy a new VLAN to a network domain

        :param      network_domain: The network domain to add the VLAN to
        :type       network_domain: :class:`DimensionDataNetworkDomain`

        :param      name: The name of the VLAN to create
        :type       name: ``str``

        :param      private_ipv4_base_address: The base IPv4 address
            e.g. 192.168.1.0
        :type       private_ipv4_base_address: ``str``

        :param      description: An additional description of the VLAN
        :type       description: ``str``

        :param      private_ipv4_prefix_size: The size of the IPv4
            address space, e.g 24
        :type       private_ipv4_prefix_size: ``int``

        :return: an instance of `DimensionDataVlan`
        :rtype: :class:`DimensionDataVlan`
        """
        create_node = ET.Element('deployVlan', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, "networkDomainId").text = network_domain.id
        ET.SubElement(create_node, "name").text = name
        if description is not None:
            ET.SubElement(create_node, "description").text = description
        ET.SubElement(create_node, "privateIpv4BaseAddress").text = \
            private_ipv4_base_address
        ET.SubElement(create_node, "privateIpv4PrefixSize").text = \
            str(private_ipv4_prefix_size)

        response = self.connection.request_with_orgId_api_2(
            'network/deployVlan',
            method='POST',
            data=ET.tostring(create_node)).object

        vlan_id = None

        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'vlanId':
                vlan_id = info.get('value')

        return self.ex_get_vlan(vlan_id)

    def ex_get_vlan(self, vlan_id):
        """
        Get a single VLAN, by it's identifier

        :param   vlan_id: The identifier of the VLAN
        :type    vlan_id: ``str``

        :return: an instance of `DimensionDataVlan`
        :rtype: :class:`DimensionDataVlan`
        """
        locations = self.list_locations()
        vlan = self.connection.request_with_orgId_api_2(
            'network/vlan/%s' % vlan_id).object
        return self._to_vlan(vlan, locations)

    def ex_update_vlan(self, vlan):
        """
        Updates the properties of the given VLAN
        Only name and description are updated

        :param      vlan: The VLAN to update
        :type       vlan: :class:`DimensionDataNetworkDomain`

        :return: an instance of `DimensionDataVlan`
        :rtype: :class:`DimensionDataVlan`
        """
        edit_node = ET.Element('editVlan', {'xmlns': TYPES_URN})
        edit_node.set('id', vlan.id)
        ET.SubElement(edit_node, "name").text = vlan.name
        if vlan.description is not None:
            ET.SubElement(edit_node, "description").text \
                = vlan.description

        self.connection.request_with_orgId_api_2(
            'network/editVlan',
            method='POST',
            data=ET.tostring(edit_node)).object

        return vlan

    def ex_expand_vlan(self, vlan):
        """
        Expands the VLAN to the prefix size in private_ipv4_range_size
        The expansion will
        not be permitted if the proposed IP space overlaps with an
        already deployed VLANs IP space.

        :param      vlan: The VLAN to update
        :type       vlan: :class:`DimensionDataNetworkDomain`

        :return: an instance of `DimensionDataVlan`
        :rtype: :class:`DimensionDataVlan`
        """
        edit_node = ET.Element('expandVlan', {'xmlns': TYPES_URN})
        edit_node.set('id', vlan.id)
        ET.SubElement(edit_node, "privateIpv4PrefixSize").text =\
            vlan.private_ipv4_range_size

        self.connection.request_with_orgId_api_2(
            'network/expandVlan',
            method='POST',
            data=ET.tostring(edit_node)).object

        return vlan

    def ex_delete_vlan(self, vlan):
        """
        Deletes an existing VLAN

        :param      vlan: The VLAN to delete
        :type       vlan: :class:`DimensionDataNetworkDomain`

        :rtype: ``bool``
        """
        delete_node = ET.Element('deleteVlan', {'xmlns': TYPES_URN})
        delete_node.set('id', vlan.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteVlan',
            method='POST',
            data=ET.tostring(delete_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_list_vlans(self, location=None, network_domain=None, name=None,
                      ipv4_address=None, ipv6_address=None, state=None):
        """
        List VLANs available, can filter by location and/or network domain

        :param      location: Only VLANs in this location (optional)
        :type       location: :class:`NodeLocation` or ``str``

        :param      network_domain: Only VLANs in this domain (optional)
        :type       network_domain: :class:`DimensionDataNetworkDomain`

        :param      name: Only VLANs with this name (optional)
        :type       name: ``str``

        :param      ipv4_address: Only VLANs with this ipv4 address (optional)
        :type       ipv4_address: ``str``

        :param      ipv6_address: Only VLANs with this ipv6 address  (optional)
        :type       ipv6_address: ``str``

        :param      state: Only VLANs with this state (optional)
        :type       state: ``str``

        :return: a list of DimensionDataVlan objects
        :rtype: ``list`` of :class:`DimensionDataVlan`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = self._location_to_location_id(location)
        if network_domain is not None:
            params['networkDomainId'] = \
                self._network_domain_to_network_domain_id(network_domain)
        if name is not None:
            params['name'] = name
        if ipv4_address is not None:
            params['privateIpv4Address'] = ipv4_address
        if ipv6_address is not None:
            params['ipv6Address'] = ipv6_address
        if state is not None:
            params['state'] = state
        response = self.connection.request_with_orgId_api_2('network/vlan',
                                                            params=params) \
                                  .object
        return self._to_vlans(response)

    def ex_add_public_ip_block_to_network_domain(self, network_domain):
        add_node = ET.Element('addPublicIpBlock', {'xmlns': TYPES_URN})
        ET.SubElement(add_node, "networkDomainId").text =\
            network_domain.id

        response = self.connection.request_with_orgId_api_2(
            'network/addPublicIpBlock',
            method='POST',
            data=ET.tostring(add_node)).object

        block_id = None

        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'ipBlockId':
                block_id = info.get('value')
        return self.ex_get_public_ip_block(block_id)

    def ex_list_public_ip_blocks(self, network_domain):
        params = {}
        params['networkDomainId'] = network_domain.id

        response = self.connection \
            .request_with_orgId_api_2('network/publicIpBlock',
                                      params=params).object
        return self._to_ip_blocks(response)

    def ex_get_public_ip_block(self, block_id):
        locations = self.list_locations()
        block = self.connection.request_with_orgId_api_2(
            'network/publicIpBlock/%s' % block_id).object
        return self._to_ip_block(block, locations)

    def ex_delete_public_ip_block(self, block):
        delete_node = ET.Element('removePublicIpBlock', {'xmlns': TYPES_URN})
        delete_node.set('id', block.id)
        result = self.connection.request_with_orgId_api_2(
            'network/removePublicIpBlock',
            method='POST',
            data=ET.tostring(delete_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_get_node_by_id(self, id):
        node = self.connection.request_with_orgId_api_2(
            'server/server/%s' % id).object
        return self._to_node(node)

    def ex_list_firewall_rules(self, network_domain, page_size=50,
                               page_number=1):
        params = {'pageSize': page_size, 'pageNumber': page_number}
        params['networkDomainId'] = self._network_domain_to_network_domain_id(
            network_domain)

        response = self.connection \
            .request_with_orgId_api_2('network/firewallRule',
                                      params=params).object
        return self._to_firewall_rules(response, network_domain)

    def ex_create_firewall_rule(self, network_domain, rule, position,
                                position_relative_to_rule=None):
        """
        Creates a firewall rule

        :param network_domain: The network domain in which to create
                                the firewall rule
        :type  network_domain: :class:`DimensionDataNetworkDomain` or ``str``

        :param rule: The rule in which to create
        :type  rule: :class:`DimensionDataFirewallRule`

        :param position: The position in which to create the rule
                         There are two types of positions
                         with position_relative_to_rule arg and without it
                         With: 'BEFORE' or 'AFTER'
                         Without: 'FIRST' or 'LAST'
        :type  position: ``str``

        :param position_relative_to_rule: The rule or rule name in
                                          which to decide positioning by
        :type  position_relative_to_rule:
            :class:`DimensionDataFirewallRule` or ``str``

        :rtype: ``bool``
        """
        positions_without_rule = ('FIRST', 'LAST')
        positions_with_rule = ('BEFORE', 'AFTER')

        create_node = ET.Element('createFirewallRule', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, "networkDomainId").text = \
            self._network_domain_to_network_domain_id(network_domain)
        ET.SubElement(create_node, "name").text = rule.name
        ET.SubElement(create_node, "action").text = rule.action
        ET.SubElement(create_node, "ipVersion").text = rule.ip_version
        ET.SubElement(create_node, "protocol").text = rule.protocol
        # Setup source port rule
        source = ET.SubElement(create_node, "source")
        source_ip = ET.SubElement(source, 'ip')
        if rule.source.any_ip:
            source_ip.set('address', 'ANY')
        else:
            source_ip.set('address', rule.source.ip_address)
            if rule.source.ip_prefix_size is not None:
                source_ip.set('prefixSize', str(rule.source.ip_prefix_size))
            if rule.source.port_begin is not None:
                source_port = ET.SubElement(source, 'port')
                source_port.set('begin', rule.source.port_begin)
            if rule.source.port_end is not None:
                source_port.set('end', rule.source.port_end)
        # Setup destination port rule
        dest = ET.SubElement(create_node, "destination")
        dest_ip = ET.SubElement(dest, 'ip')
        if rule.destination.any_ip:
            dest_ip.set('address', 'ANY')
        else:
            dest_ip.set('address', rule.destination.ip_address)
            if rule.destination.ip_prefix_size is not None:
                dest_ip.set('prefixSize', rule.destination.ip_prefix_size)
            if rule.destination.port_begin is not None:
                dest_port = ET.SubElement(dest, 'port')
                dest_port.set('begin', rule.destination.port_begin)
            if rule.destination.port_end is not None:
                dest_port.set('end', rule.destination.port_end)
        # Set up positioning of rule
        ET.SubElement(create_node, "enabled").text = str(rule.enabled).lower()
        placement = ET.SubElement(create_node, "placement")
        if position_relative_to_rule is not None:
            if position not in positions_with_rule:
                raise ValueError("When position_relative_to_rule is specified"
                                 " position must be %s"
                                 % ', '.join(positions_with_rule))
            if isinstance(position_relative_to_rule,
                          DimensionDataFirewallRule):
                rule_name = position_relative_to_rule.name
            else:
                rule_name = position_relative_to_rule
            placement.set('relativeToRule', rule_name)
        else:
            if position not in positions_without_rule:
                raise ValueError("When position_relative_to_rule is not"
                                 " specified position must be %s"
                                 % ', '.join(positions_without_rule))
        placement.set('position', position)

        response = self.connection.request_with_orgId_api_2(
            'network/createFirewallRule',
            method='POST',
            data=ET.tostring(create_node)).object

        rule_id = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'firewallRuleId':
                rule_id = info.get('value')
        rule.id = rule_id
        return rule

    def ex_get_firewall_rule(self, network_domain, rule_id):
        locations = self.list_locations()
        rule = self.connection.request_with_orgId_api_2(
            'network/firewallRule/%s' % rule_id).object
        return self._to_firewall_rule(rule, locations, network_domain)

    def ex_set_firewall_rule_state(self, rule, state):
        """
        Change the state (enabled or disabled) of a rule

        :param rule: The rule to delete
        :type  rule: :class:`DimensionDataFirewallRule`

        :param state: The desired state enabled (True) or disabled (False)
        :type  state: ``bool``

        :rtype: ``bool``
        """
        update_node = ET.Element('editFirewallRule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        ET.SubElement(update_node, 'enabled').text = str(state).lower()
        result = self.connection.request_with_orgId_api_2(
            'network/editFirewallRule',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_delete_firewall_rule(self, rule):
        """
        Delete a firewall rule

        :param rule: The rule to delete
        :type  rule: :class:`DimensionDataFirewallRule`

        :rtype: ``bool``
        """
        update_node = ET.Element('deleteFirewallRule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteFirewallRule',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_create_nat_rule(self, network_domain, internal_ip, external_ip):
        """
        Create a NAT rule

        :param  network_domain: The network domain the rule belongs to
        :type   network_domain: :class:`DimensionDataNetworkDomain`

        :param  internal_ip: The IPv4 address internally
        :type   internal_ip: ``str``

        :param  external_ip: The IPv4 address externally
        :type   external_ip: ``str``

        :rtype: :class:`DimensionDataNatRule`
        """
        create_node = ET.Element('createNatRule', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, 'networkDomainId').text = network_domain.id
        ET.SubElement(create_node, 'internalIp').text = internal_ip
        ET.SubElement(create_node, 'externalIp').text = external_ip
        result = self.connection.request_with_orgId_api_2(
            'network/createNatRule',
            method='POST',
            data=ET.tostring(create_node)).object

        rule_id = None
        for info in findall(result, 'info', TYPES_URN):
            if info.get('name') == 'natRuleId':
                rule_id = info.get('value')

        return DimensionDataNatRule(
            id=rule_id,
            network_domain=network_domain,
            internal_ip=internal_ip,
            external_ip=external_ip,
            status=NodeState.RUNNING
        )

    def ex_list_nat_rules(self, network_domain):
        """
        Get NAT rules for the network domain

        :param  network_domain: The network domain the rules belongs to
        :type   network_domain: :class:`DimensionDataNetworkDomain`

        :rtype: ``list`` of :class:`DimensionDataNatRule`
        """
        params = {}
        params['networkDomainId'] = network_domain.id

        response = self.connection \
            .request_with_orgId_api_2('network/natRule',
                                      params=params).object
        return self._to_nat_rules(response, network_domain)

    def ex_get_nat_rule(self, network_domain, rule_id):
        """
        Get a NAT rule by ID

        :param  network_domain: The network domain the rule belongs to
        :type   network_domain: :class:`DimensionDataNetworkDomain`

        :param  rule_id: The ID of the NAT rule to fetch
        :type   rule_id: ``str``

        :rtype: :class:`DimensionDataNatRule`
        """
        rule = self.connection.request_with_orgId_api_2(
            'network/natRule/%s' % rule_id).object
        return self._to_nat_rule(rule, network_domain)

    def ex_delete_nat_rule(self, rule):
        """
        Delete an existing NAT rule

        :param  rule: The rule to delete
        :type   rule: :class:`DimensionDataNatRule`

        :rtype: ``bool``
        """
        update_node = ET.Element('deleteNatRule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteNatRule',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_get_location_by_id(self, id):
        """
        Get location by ID.

        :param  id: ID of the node location which should be used
        :type   id: ``str``

        :rtype: :class:`NodeLocation`
        """
        location = None
        if id is not None:
            location = self.list_locations(ex_id=id)[0]
        return location

    def ex_wait_for_state(self, state, func, poll_interval=2,
                          timeout=60, *args, **kwargs):
        """
        Wait for the function which returns a instance
        with field status to match

        Keep polling func until one of the desired states is matched

        :param state: Either the desired state (`str`) or a `list` of states
        :type  state: ``str`` or ``list``

        :param  func: The function to call, e.g. ex_get_vlan
        :type   func: ``function``

        :param  poll_interval: The number of seconds to wait between checks
        :type   poll_interval: `int`

        :param  timeout: The total number of seconds to wait to reach a state
        :type   timeout: `int`

        :param  args: The arguments for func
        :type   args: Positional arguments

        :param  kwargs: The arguments for func
        :type   kwargs: Keyword arguments
        """
        return self.connection.wait_for_state(state, func, poll_interval,
                                              timeout, *args, **kwargs)

    def ex_enable_monitoring(self, node, service_plan="ESSENTIALS"):
        """
        Enables cloud monitoring on a node

        :param   node: The node to monitor
        :type    node: :class:`Node`

        :param   service_plan: The service plan, one of ESSENTIALS or
                               ADVANCED
        :type    service_plan: ``str``

        :rtype: ``bool``
        """
        update_node = ET.Element('enableServerMonitoring',
                                 {'xmlns': TYPES_URN})
        update_node.set('id', node.id)
        ET.SubElement(update_node, 'servicePlan').text = service_plan
        result = self.connection.request_with_orgId_api_2(
            'server/enableServerMonitoring',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_update_monitoring_plan(self, node, service_plan="ESSENTIALS"):
        """
        Updates the service plan on a node with monitoring

        :param   node: The node to monitor
        :type    node: :class:`Node`

        :param   service_plan: The service plan, one of ESSENTIALS or
                               ADVANCED
        :type    service_plan: ``str``

        :rtype: ``bool``
        """
        update_node = ET.Element('changeServerMonitoringPlan',
                                 {'xmlns': TYPES_URN})
        update_node.set('id', node.id)
        ET.SubElement(update_node, 'servicePlan').text = service_plan
        result = self.connection.request_with_orgId_api_2(
            'server/changeServerMonitoringPlan',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_disable_monitoring(self, node):
        """
        Disables cloud monitoring for a node

        :param   node: The node to stop monitoring
        :type    node: :class:`Node`

        :rtype: ``bool``
        """
        update_node = ET.Element('disableServerMonitoring',
                                 {'xmlns': TYPES_URN})
        update_node.set('id', node.id)
        result = self.connection.request_with_orgId_api_2(
            'server/disableServerMonitoring',
            method='POST',
            data=ET.tostring(update_node)).object

        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_add_storage_to_node(self, node, amount, speed='STANDARD'):
        """
        Add storage to the node

        :param  node: The server to add storage to
        :type   node: :class:`Node`

        :param  amount: The amount of storage to add, in GB
        :type   amount: ``int``

        :param  speed: The disk speed type
        :type   speed: ``str``

        :rtype: ``bool``
        """
        result = self.connection.request_with_orgId_api_1(
            'server/%s?addLocalStorage&amount=%s&speed=%s' %
            (node.id, amount, speed)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_remove_storage_from_node(self, node, disk_id):
        """
        Remove storage from a node

        :param  node: The server to add storage to
        :type   node: :class:`Node`

        :param  disk_id: The ID of the disk to remove
        :type   disk_id: ``str``

        :rtype: ``bool``
        """
        result = self.connection.request_with_orgId_api_1(
            'server/%s/disk/%s?delete' %
            (node.id, disk_id)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_change_storage_speed(self, node, disk_id, speed):
        """
        Change the speed (disk tier) of a disk

        :param  node: The server to change the disk speed of
        :type   node: :class:`Node`

        :param  disk_id: The ID of the disk to change
        :type   disk_id: ``str``

        :param  speed: The disk speed type e.g. STANDARD
        :type   speed: ``str``

        :rtype: ``bool``
        """
        create_node = ET.Element('ChangeDiskSpeed', {'xmlns': SERVER_NS})
        ET.SubElement(create_node, 'speed').text = speed
        result = self.connection.request_with_orgId_api_1(
            'server/%s/disk/%s/changeSpeed' %
            (node.id, disk_id),
            method='POST',
            data=ET.tostring(create_node)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_change_storage_size(self, node, disk_id, size):
        """
        Change the size of a disk

        :param  node: The server to change the disk of
        :type   node: :class:`Node`

        :param  disk_id: The ID of the disk to resize
        :type   disk_id: ``str``

        :param  size: The disk size in GB
        :type   size: ``int``

        :rtype: ``bool``
        """
        create_node = ET.Element('ChangeDiskSize', {'xmlns': SERVER_NS})
        ET.SubElement(create_node, 'newSizeGb').text = str(size)
        result = self.connection.request_with_orgId_api_1(
            'server/%s/disk/%s/changeSize' %
            (node.id, disk_id),
            method='POST',
            data=ET.tostring(create_node)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_reconfigure_node(self, node, memory_gb, cpu_count, cores_per_socket,
                            cpu_performance):
        """
        Reconfigure the virtual hardware specification of a node

        :param  node: The server to change
        :type   node: :class:`Node`

        :param  memory_gb: The amount of memory in GB (optional)
        :type   memory_gb: ``int``

        :param  cpu_count: The number of CPU (optional)
        :type   cpu_count: ``int``

        :param  cores_per_socket: Number of CPU cores per socket (optional)
        :type   cores_per_socket: ``int``

        :param  cpu_performance: CPU Performance type (optional)
        :type   cpu_performance: ``str``

        :rtype: ``bool``
        """
        update = ET.Element('reconfigureServer', {'xmlns': TYPES_URN})
        update.set('id', node.id)
        if memory_gb is not None:
            ET.SubElement(update, 'memoryGb').text = str(memory_gb)
        if cpu_count is not None:
            ET.SubElement(update, 'cpuCount').text = str(cpu_count)
        if cpu_performance is not None:
            ET.SubElement(update, 'cpuSpeed').text = cpu_performance
        if cores_per_socket is not None:
            ET.SubElement(update, 'coresPerSocket').text = \
                str(cores_per_socket)
        result = self.connection.request_with_orgId_api_2(
            'server/reconfigureServer',
            method='POST',
            data=ET.tostring(update)).object
        response_code = findtext(result, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def ex_clone_node_to_image(self, node, image_name, image_description=None):
        """
        Clone a server into a customer image.

        :param  node: The server to clone
        :type   node: :class:`Node`

        :param  image_name: The name of the clone image
        :type   image_name: ``str``

        :param  description: The description of the image
        :type   description: ``str``

        :rtype: ``bool``
        """
        if image_description is None:
            image_description = ''
        result = self.connection.request_with_orgId_api_1(
            'server/%s?clone=%s&desc=%s' %
            (node.id, image_name, image_description)).object
        response_code = findtext(result, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_list_customer_images(self, location=None):
        """
        Return a list of customer imported images

        :param location: The target location
        :type  location: :class:`NodeLocation` or ``str``

        :rtype: ``list`` of :class:`NodeImage`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = self._location_to_location_id(location)

        return self._to_images(
            self.connection.request_with_orgId_api_2(
                'image/customerImage',
                params=params)
            .object, 'customerImage')

    def ex_get_base_image_by_id(self, id):
        """
        Gets a Base image in the Dimension Data Cloud given the id

        :param id: The id of the image
        :type  id: ``str``

        :rtype: :class:`NodeImage`
        """
        image = self.connection.request_with_orgId_api_2(
            'image/osImage/%s' % id).object
        return self._to_image(image)

    def ex_get_customer_image_by_id(self, id):
        """
        Gets a Customer image in the Dimension Data Cloud given the id

        :param id: The id of the image
        :type  id: ``str``

        :rtype: :class:`NodeImage`
        """
        image = self.connection.request_with_orgId_api_2(
            'image/customerImage/%s' % id).object
        return self._to_image(image)

    def ex_get_image_by_id(self, id):
        """
        Gets a Base/Customer image in the Dimension Data Cloud given the id

        Note: This first checks the base image
              If it is not a base image we check if it is a customer image
              If it is not in either of these a DimensionDataAPIException
              is thrown

        :param id: The id of the image
        :type  id: ``str``

        :rtype: :class:`NodeImage`
        """
        try:
            return self.ex_get_base_image_by_id(id)
        except DimensionDataAPIException as e:
            if e.code != 'RESOURCE_NOT_FOUND':
                raise e
        return self.ex_get_customer_image_by_id(id)

    def _list_nodes_single_page(self, params={}):
        return self.connection.request_with_orgId_api_2(
            'server/server', params=params).object

    def _to_images(self, object, el_name='osImage'):
        images = []
        locations = self.list_locations()

        for element in object.findall(fixxpath(el_name, TYPES_URN)):
            images.append(self._to_image(element, locations))

        return images

    def _to_image(self, element, locations=None):
        location_id = element.get('datacenterId')
        if locations is None:
            locations = self.list_locations(location_id)
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]
        cpu_spec = self._to_cpu_spec(element.find(fixxpath('cpu', TYPES_URN)))
        os_el = element.find(fixxpath('operatingSystem', TYPES_URN))
        if element.tag.endswith('customerImage'):
            is_customer_image = True
        else:
            is_customer_image = False
        extra = {
            'description': findtext(element, 'description', TYPES_URN),
            'OS_type': os_el.get('family'),
            'OS_displayName': os_el.get('displayName'),
            'cpu': cpu_spec,
            'memoryGb': findtext(element, 'memoryGb', TYPES_URN),
            'osImageKey': findtext(element, 'osImageKey', TYPES_URN),
            'created': findtext(element, 'createTime', TYPES_URN),
            'location': location,
            'isCustomerImage': is_customer_image
        }

        return NodeImage(id=element.get('id'),
                         name=str(findtext(element, 'name', TYPES_URN)),
                         extra=extra,
                         driver=self.connection.driver)

    def _to_nat_rules(self, object, network_domain):
        rules = []
        for element in findall(object, 'natRule', TYPES_URN):
            rules.append(
                self._to_nat_rule(element, network_domain))

        return rules

    def _to_nat_rule(self, element, network_domain):
        return DimensionDataNatRule(
            id=element.get('id'),
            network_domain=network_domain,
            internal_ip=findtext(element, 'internalIp', TYPES_URN),
            external_ip=findtext(element, 'externalIp', TYPES_URN),
            status=findtext(element, 'state', TYPES_URN))

    def _to_anti_affinity_rules(self, object):
        rules = []
        for element in findall(object, 'antiAffinityRule', TYPES_URN):
            rules.append(
                self._to_anti_affinity_rule(element))
        return rules

    def _to_anti_affinity_rule(self, element):
        node_list = []
        for node in findall(element, 'serverSummary', TYPES_URN):
            node_list.append(node.get('id'))
        return DimensionDataAntiAffinityRule(
            id=element.get('id'),
            node_list=node_list
        )

    def _to_firewall_rules(self, object, network_domain):
        rules = []
        locations = self.list_locations()
        for element in findall(object, 'firewallRule', TYPES_URN):
            rules.append(
                self._to_firewall_rule(element, locations, network_domain))

        return rules

    def _to_firewall_rule(self, element, locations, network_domain):
        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataFirewallRule(
            id=element.get('id'),
            network_domain=network_domain,
            name=findtext(element, 'name', TYPES_URN),
            action=findtext(element, 'action', TYPES_URN),
            ip_version=findtext(element, 'ipVersion', TYPES_URN),
            protocol=findtext(element, 'protocol', TYPES_URN),
            enabled=findtext(element, 'enabled', TYPES_URN),
            source=self._to_firewall_address(
                element.find(fixxpath('source', TYPES_URN))),
            destination=self._to_firewall_address(
                element.find(fixxpath('destination', TYPES_URN))),
            location=location,
            status=findtext(element, 'state', TYPES_URN))

    def _to_firewall_address(self, element):
        ip = element.find(fixxpath('ip', TYPES_URN))
        port = element.find(fixxpath('port', TYPES_URN))
        return DimensionDataFirewallAddress(
            any_ip=ip.get('address') == 'ANY',
            ip_address=ip.get('address'),
            ip_prefix_size=ip.get('prefixSize'),
            port_begin=port.get('begin') if port is not None else None,
            port_end=port.get('end') if port is not None else None
        )

    def _to_ip_blocks(self, object):
        blocks = []
        locations = self.list_locations()
        for element in findall(object, 'publicIpBlock', TYPES_URN):
            blocks.append(self._to_ip_block(element, locations))

        return blocks

    def _to_ip_block(self, element, locations):
        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataPublicIpBlock(
            id=element.get('id'),
            network_domain=self.ex_get_network_domain(
                findtext(element, 'networkDomainId', TYPES_URN)
            ),
            base_ip=findtext(element, 'baseIp', TYPES_URN),
            size=findtext(element, 'size', TYPES_URN),
            location=location,
            status=findtext(element, 'state', TYPES_URN))

    def _to_networks(self, object):
        networks = []
        locations = self.list_locations()
        for element in findall(object, 'network', NETWORK_NS):
            networks.append(self._to_network(element, locations))

        return networks

    def _to_network(self, element, locations):
        multicast = False
        if findtext(element, 'multicast', NETWORK_NS) == 'true':
            multicast = True

        status = self._to_status(element.find(fixxpath('status', NETWORK_NS)))

        location_id = findtext(element, 'location', NETWORK_NS)
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataNetwork(
            id=findtext(element, 'id', NETWORK_NS),
            name=findtext(element, 'name', NETWORK_NS),
            description=findtext(element, 'description',
                                 NETWORK_NS),
            location=location,
            private_net=findtext(element, 'privateNet',
                                 NETWORK_NS),
            multicast=multicast,
            status=status)

    def _to_network_domains(self, object):
        network_domains = []
        locations = self.list_locations()
        for element in findall(object, 'networkDomain', TYPES_URN):
            network_domains.append(self._to_network_domain(element, locations))

        return network_domains

    def _to_network_domain(self, element, locations):
        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]
        plan = findtext(element, 'type', TYPES_URN)
        if plan is 'ESSENTIALS':
            plan_type = NetworkDomainServicePlan.ESSENTIALS
        else:
            plan_type = NetworkDomainServicePlan.ADVANCED
        return DimensionDataNetworkDomain(
            id=element.get('id'),
            name=findtext(element, 'name', TYPES_URN),
            description=findtext(element, 'description', TYPES_URN),
            plan=plan_type,
            location=location,
            status=findtext(element, 'state', TYPES_URN))

    def _to_vlans(self, object):
        vlans = []
        locations = self.list_locations()
        for element in findall(object, 'vlan', TYPES_URN):
            vlans.append(self._to_vlan(element, locations=locations))

        return vlans

    def _to_vlan(self, element, locations):
        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]
        ip_range = element.find(fixxpath('privateIpv4Range', TYPES_URN))
        ip6_range = element.find(fixxpath('ipv6Range', TYPES_URN))
        network_domain_el = element.find(
            fixxpath('networkDomain', TYPES_URN))
        network_domain = self.ex_get_network_domain(
            network_domain_el.get('id'))
        return DimensionDataVlan(
            id=element.get('id'),
            name=findtext(element, 'name', TYPES_URN),
            description=findtext(element, 'description',
                                 TYPES_URN),
            network_domain=network_domain,
            private_ipv4_range_address=ip_range.get('address'),
            private_ipv4_range_size=int(ip_range.get('prefixSize')),
            ipv6_range_address=ip6_range.get('address'),
            ipv6_range_size=int(ip6_range.get('prefixSize')),
            ipv4_gateway=findtext(
                element,
                'ipv4GatewayAddress',
                TYPES_URN),
            ipv6_gateway=findtext(
                element,
                'ipv6GatewayAddress',
                TYPES_URN),
            location=location,
            status=findtext(element, 'state', TYPES_URN))

    def _to_locations(self, object):
        locations = []
        for element in object.findall(fixxpath('datacenter', TYPES_URN)):
            locations.append(self._to_location(element))

        return locations

    def _to_location(self, element):
        l = NodeLocation(id=element.get('id'),
                         name=findtext(element, 'displayName', TYPES_URN),
                         country=findtext(element, 'country', TYPES_URN),
                         driver=self)
        return l

    def _to_cpu_spec(self, element):
        return DimensionDataServerCpuSpecification(
            cpu_count=int(element.get('count')),
            cores_per_socket=int(element.get('coresPerSocket')),
            performance=element.get('speed'))

    def _to_vmware_tools(self, element):
        return DimensionDataServerVMWareTools(
            status=element.get('runningStatus'),
            version_status=element.get('versionStatus'),
            api_version=element.get('apiVersion'))

    def _to_disks(self, object):
        disk_elements = object.findall(fixxpath('disk', TYPES_URN))
        return [self._to_disk(el) for el in disk_elements]

    def _to_disk(self, element):
        return DimensionDataServerDisk(
            id=element.get('id'),
            scsi_id=int(element.get('scsiId')),
            size_gb=int(element.get('sizeGb')),
            speed=element.get('speed'),
            state=element.get('state')
        )

    def _to_nodes(self, object):
        node_elements = object.findall(fixxpath('server', TYPES_URN))
        return [self._to_node(el) for el in node_elements]

    def _to_node(self, element):
        started = findtext(element, 'started', TYPES_URN)
        status = self._to_status(element.find(fixxpath('progress', TYPES_URN)))
        dd_state = findtext(element, 'state', TYPES_URN)

        node_state = self._get_node_state(dd_state, started, status.action)

        has_network_info \
            = element.find(fixxpath('networkInfo', TYPES_URN)) is not None
        cpu_spec = self._to_cpu_spec(element.find(fixxpath('cpu', TYPES_URN)))
        disks = self._to_disks(element)
        vmware_tools = self._to_vmware_tools(
            element.find(fixxpath('vmwareTools', TYPES_URN)))
        extra = {
            'description': findtext(element, 'description', TYPES_URN),
            'sourceImageId': findtext(element, 'sourceImageId', TYPES_URN),
            'networkId': findtext(element, 'networkId', TYPES_URN),
            'networkDomainId':
                element.find(fixxpath('networkInfo', TYPES_URN))
                .get('networkDomainId')
                if has_network_info else None,
            'datacenterId': element.get('datacenterId'),
            'deployedTime': findtext(element, 'createTime', TYPES_URN),
            'cpu': cpu_spec,
            'memoryMb': int(findtext(
                element,
                'memoryGb',
                TYPES_URN)) * 1024,
            'OS_id': element.find(fixxpath(
                'operatingSystem',
                TYPES_URN)).get('id'),
            'OS_type': element.find(fixxpath(
                'operatingSystem',
                TYPES_URN)).get('family'),
            'OS_displayName': element.find(fixxpath(
                'operatingSystem',
                TYPES_URN)).get('displayName'),
            'status': status,
            'disks': disks,
            'vmWareTools': vmware_tools
        }

        public_ip = findtext(element, 'publicIpAddress', TYPES_URN)

        private_ip = element.find(
            fixxpath('networkInfo/primaryNic', TYPES_URN)) \
            .get('privateIpv4') \
            if has_network_info else \
            element.find(fixxpath('nic', TYPES_URN)).get('privateIpv4')

        extra['ipv6'] = element.find(
            fixxpath('networkInfo/primaryNic', TYPES_URN)) \
            .get('ipv6') \
            if has_network_info else \
            element.find(fixxpath('nic', TYPES_URN)).get('ipv6')

        n = Node(id=element.get('id'),
                 name=findtext(element, 'name', TYPES_URN),
                 state=node_state,
                 public_ips=[public_ip] if public_ip is not None else [],
                 private_ips=[private_ip] if private_ip is not None else [],
                 driver=self.connection.driver,
                 extra=extra)
        return n

    def _to_status(self, element):
        if element is None:
            return DimensionDataStatus()
        s = DimensionDataStatus(action=findtext(element, 'action', TYPES_URN),
                                request_time=findtext(
                                    element,
                                    'requestTime',
                                    TYPES_URN),
                                user_name=findtext(
                                    element,
                                    'userName',
                                    TYPES_URN),
                                number_of_steps=findtext(
                                    element,
                                    'numberOfSteps',
                                    TYPES_URN),
                                step_name=findtext(
                                    element,
                                    'step/name',
                                    TYPES_URN),
                                step_number=findtext(
                                    element,
                                    'step_number',
                                    TYPES_URN),
                                step_percent_complete=findtext(
                                    element,
                                    'step/percentComplete',
                                    TYPES_URN),
                                failure_reason=findtext(
                                    element,
                                    'failureReason',
                                    TYPES_URN))
        return s

    def _image_needs_auth(self, image):
        if not isinstance(image, NodeImage):
            image = self.ex_get_image_by_id(image)
        if image.extra['isCustomerImage'] and image.extra['OS_type'] == 'UNIX':
            return False
        return True

    @staticmethod
    def _get_node_state(state, started, action):
        try:
            return NODE_STATE_MAP[(state, started, action)]
        except KeyError:
            if started == 'true':
                return NodeState.RUNNING
            else:
                return NodeState.TERMINATED

    @staticmethod
    def _node_to_node_id(node):
        return dd_object_to_id(node, Node)

    @staticmethod
    def _location_to_location_id(location):
        return dd_object_to_id(location, NodeLocation)

    @staticmethod
    def _vlan_to_vlan_id(vlan):
        return dd_object_to_id(vlan, DimensionDataVlan)

    @staticmethod
    def _image_to_image_id(image):
        return dd_object_to_id(image, NodeImage)

    @staticmethod
    def _network_to_network_id(network):
        return dd_object_to_id(network, DimensionDataNetwork)

    @staticmethod
    def _anti_affinity_rule_to_anti_affinity_rule_id(rule):
        return dd_object_to_id(rule, DimensionDataAntiAffinityRule)

    @staticmethod
    def _network_domain_to_network_domain_id(network_domain):
        return dd_object_to_id(network_domain, DimensionDataNetworkDomain)
