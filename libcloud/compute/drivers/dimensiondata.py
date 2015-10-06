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

from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation
from libcloud.common.dimensiondata import (DimensionDataConnection,
                                           DimensionDataStatus)
from libcloud.common.dimensiondata import DimensionDataNetwork
from libcloud.common.dimensiondata import DimensionDataNetworkDomain
from libcloud.common.dimensiondata import DimensionDataVlan
from libcloud.common.dimensiondata import DimensionDataPublicIpBlock
from libcloud.common.dimensiondata import DimensionDataFirewallRule
from libcloud.common.dimensiondata import DimensionDataFirewallAddress
from libcloud.common.dimensiondata import DimensionDataNatRule
from libcloud.common.dimensiondata import NetworkDomainServicePlan
from libcloud.common.dimensiondata import API_ENDPOINTS
from libcloud.common.dimensiondata import DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.common.dimensiondata import SERVER_NS
from libcloud.common.dimensiondata import NETWORK_NS
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.compute.types import NodeState, Provider


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
                    ex_vlan=None,
                    ex_is_started=True, **kwargs):
        """
        Create a new DimensionData node

        :keyword    name:   String with a name for this new node (required)
        :type       name:   ``str``

        :keyword    image:  OS Image to boot on node. (required)
        :type       image:  :class:`NodeImage`

        :keyword    auth:   Initial authentication information for the
                            node (required)
        :type       auth:   :class:`NodeAuthPassword`

        :keyword    ex_description:  description for this node (required)
        :type       ex_description:  ``str``

        :keyword    ex_network:  Network to create the node within (required,
                                unless using Network Domain)
        :type       ex_network: :class:`DimensionDataNetwork`

        :keyword    ex_network_domain:  Network Domain to create the node
                                        (required unless using network)
        :type       ex_network_domain: :class:`DimensionDataNetworkDomain`

        :keyword    ex_vlan:  VLAN to create the node within
                                        (required unless using network)
        :type       ex_vlan: :class:`DimensionDataVlan`

        :keyword    ex_is_started:  Start server after creation? default
                                   true (required)
        :type       ex_is_started:  ``bool``

        :return: The newly created :class:`Node`.
        :rtype: :class:`Node`
        """

        password = None
        auth_obj = self._get_and_check_auth(auth)
        password = auth_obj.password

        if not isinstance(ex_network, DimensionDataNetwork):
            if not isinstance(ex_network_domain, DimensionDataNetworkDomain):
                raise ValueError('ex_network must be of DimensionDataNetwork '
                                 'type or ex_network_domain must be of '
                                 'DimensionDataNetworkDomain type')

        server_elm = ET.Element('deployServer', {'xmlns': TYPES_URN})
        ET.SubElement(server_elm, "name").text = name
        ET.SubElement(server_elm, "description").text = ex_description
        ET.SubElement(server_elm, "imageId").text = image.id
        ET.SubElement(server_elm, "start").text = str(ex_is_started).lower()
        ET.SubElement(server_elm, "administratorPassword").text = password

        if ex_network is not None:
            network_elm = ET.SubElement(server_elm, "network")
            ET.SubElement(network_elm, "networkId").text = ex_network.id
        if ex_network_domain is not None:
            network_inf_elm = ET.SubElement(server_elm, "networkInfo",
                                            {'networkDomainId':
                                             ex_network_domain.id})
            pri_nic = ET.SubElement(network_inf_elm, "primaryNic")
            ET.SubElement(pri_nic, "vlanId").text = ex_vlan.id

        response = self.connection.request_with_orgId_api_2(
            'server/deployServer',
            method='POST',
            data=ET.tostring(server_elm)).object

        node_id = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'serverId':
                node_id = info.get('value')

        node = self.ex_get_node_by_id(node_id)

        if getattr(auth_obj, "generated", False):
            node.extra['password'] = auth_obj.password

        return node

    def destroy_node(self, node):
        request_elm = ET.Element('deleteServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/deleteServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def reboot_node(self, node):
        request_elm = ET.Element('rebootServer',
                                 {'xmlns': TYPES_URN, 'id': node.id})
        body = self.connection.request_with_orgId_api_2(
            'server/rebootServer',
            method='POST',
            data=ET.tostring(request_elm)).object
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def list_nodes(self):
        nodes = self._to_nodes(
            self.connection.request_with_orgId_api_2('server/server').object)

        return nodes

    def list_images(self, location=None):
        """
        return a list of available images
            Currently only returns the default 'base OS images' provided by
            DimensionData. Customer images (snapshots) are not yet supported.

        @inherits: :class:`NodeDriver.list_images`
        """
        params = {}
        if location is not None:
            params['location'] = location.id

        return self._to_base_images(
            self.connection.request_api_1('base/imageWithDiskSpeed',
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

    def list_locations(self):
        """
        list locations (datacenters) available for instantiating servers and
        networks.

        @inherits: :class:`NodeDriver.list_locations`
        """
        return self._to_locations(
            self.connection
            .request_with_orgId_api_2('infrastructure/datacenter').object)

    def list_networks(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.


        :keyword location: The location
        :type    location: :class:`NodeLocation`

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        url_ext = ''
        if location is not None:
            url_ext = '/' + location.id

        return self._to_networks(
            self.connection
            .request_with_orgId_api_1('networkWithLocation%s' % url_ext)
            .object)

    def _to_base_images(self, object):
        images = []
        locations = self.list_locations()

        for element in object.findall(fixxpath("image", SERVER_NS)):
            images.append(self._to_base_image(element, locations))

        return images

    def _to_base_image(self, element, locations):
        # Eventually we will probably need multiple _to_image() functions
        # that parse <ServerImage> differently than <DeployedImage>.
        # DeployedImages are customer snapshot images, and ServerImages are
        # 'base' images provided by DimensionData
        location_id = element.get('location')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        extra = {
            'description': findtext(element, 'description', SERVER_NS),
            'OS_type': findtext(element, 'operatingSystem/type', SERVER_NS),
            'OS_displayName': findtext(element, 'operatingSystem/displayName',
                                       SERVER_NS),
            'cpuCount': findtext(element, 'cpuCount', SERVER_NS),
            'resourcePath': findtext(element, 'resourcePath', SERVER_NS),
            'memory': findtext(element, 'memory', SERVER_NS),
            'osStorage': findtext(element, 'osStorage', SERVER_NS),
            'additionalStorage': findtext(element, 'additionalStorage',
                                          SERVER_NS),
            'created': findtext(element, 'created', SERVER_NS),
            'location': location,
        }

        return NodeImage(id=element.get('id'),
                         name=str(findtext(element, 'name', SERVER_NS)),
                         extra=extra,
                         driver=self.connection.driver)

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
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

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
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

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
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

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
        responseCode = findtext(body, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_list_networks(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        params = {}
        if location is not None:
            params['location'] = location.id

        response = self.connection \
            .request_with_orgId_api_1('networkWithLocation',
                                      params=params).object
        return self._to_networks(response)

    def ex_get_network_domain(self, network_domain_id):
        locations = self.list_locations()
        net = self.connection.request_with_orgId_api_2(
            'network/networkDomain/%s' % network_domain_id).object
        return self._to_network_domain(net, locations)

    def ex_list_network_domains(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = location.id

        response = self.connection \
            .request_with_orgId_api_2('network/networkDomain',
                                      params=params).object
        return self._to_network_domains(response)

    def ex_create_network_domain(self, location, name, description=None,
                                 service_plan=
                                 NetworkDomainServicePlan.ADVANCED):
        """
        Deploy a new network domain to a data center
        """
        create_node = ET.Element('deployNetworkDomain', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, "datacenterId").text = location.id
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
            if info.get('name') == 'networkDomainId"':
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
        """
        edit_node = ET.Element('editNetworkDomain', {'xmlns': TYPES_URN})
        edit_node.set('id', network_domain.id)
        ET.SubElement(edit_node, "name").text = network_domain.name
        if network_domain.description is not None:
            ET.SubElement(edit_node, "description").text \
                = network_domain.description
        ET.SubElement(edit_node, "type").text = network_domain.plan

        response = self.connection.request_with_orgId_api_2(
            'network/editNetworkDomain',
            method='POST',
            data=ET.tostring(edit_node)).object

        return network_domain

    def ex_delete_network_domain(self, network_domain):
        delete_node = ET.Element('deleteNetworkDomain', {'xmlns': TYPES_URN})
        delete_node.set('id', network_domain.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteNetworkDomain',
            method='POST',
            data=ET.tostring(delete_node)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_create_vlan(self,
                       network_domain,
                       name,
                       private_ipv4_base_address,
                       description=None,
                       private_ipv4_prefix_size='24'):
        """
        Deploy a new VLAN to a network domain
        """
        create_node = ET.Element('deployVlan', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, "networkDomainId").text = network_domain.id
        ET.SubElement(create_node, "name").text = name
        if description is not None:
            ET.SubElement(create_node, "description").text = description
        ET.SubElement(create_node, "privateIpv4BaseAddress").text = \
            private_ipv4_base_address
        ET.SubElement(create_node, "privateIpv4PrefixSize").text = \
            private_ipv4_prefix_size

        response = self.connection.request_with_orgId_api_2(
            'network/deployVlan',
            method='POST',
            data=ET.tostring(create_node)).object

        vlan_id = None

        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'vlanId':
                vlan_id = info.get('value')

        return DimensionDataVlan(
            id=vlan_id,
            name=name,
            description=description,
            location=network_domain.location,
            status=NodeState.RUNNING,
            private_ipv4_range_address=private_ipv4_base_address,
            private_ipv4_range_size=private_ipv4_prefix_size
        )

    def ex_get_vlan(self, vlan_id):
        locations = self.list_locations()
        vlan = self.connection.request_with_orgId_api_2(
            'network/vlan/%s' % vlan_id).object
        return self._to_vlan(vlan, locations)

    def ex_update_vlan(self, vlan):
        """
        Updates the properties of the given VLAN
        Only name and description are updated
        """
        edit_node = ET.Element('editVlan', {'xmlns': TYPES_URN})
        edit_node.set('id', vlan.id)
        ET.SubElement(edit_node, "name").text = vlan.name
        if vlan.description is not None:
            ET.SubElement(edit_node, "description").text \
                = vlan.description

        response = self.connection.request_with_orgId_api_2(
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
        """
        edit_node = ET.Element('expandVlan', {'xmlns': TYPES_URN})
        edit_node.set('id', vlan.id)
        ET.SubElement(edit_node, "privateIpv4PrefixSize").text =\
            vlan.private_ipv4_range_size

        response = self.connection.request_with_orgId_api_2(
            'network/expandVlan',
            method='POST',
            data=ET.tostring(edit_node)).object

        return vlan

    def ex_delete_vlan(self, vlan):
        delete_node = ET.Element('deleteVlan', {'xmlns': TYPES_URN})
        delete_node.set('id', vlan.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteVlan',
            method='POST',
            data=ET.tostring(delete_node)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_list_vlans(self, location=None, network_domain=None):
        """
        List VLANs available in a given networkDomain

        :return: a list of DimensionDataVlan objects
        :rtype: ``list`` of :class:`DimensionDataVlan`
        """
        params = {}
        if location is not None:
            params['datacenterId'] = location.id
        if network_domain is not None:
            params['networkDomainId'] = network_domain.id
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
            if info.get('name') == 'publicIpBlockId':
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

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_get_node_by_id(self, id):
        node = self.connection.request_with_orgId_api_2(
            'server/server/%s' % id).object
        return self._to_node(node)

    def ex_list_firewall_rules(self, network_domain):
        params = {}
        params['networkDomainId'] = network_domain.id

        response = self.connection \
            .request_with_orgId_api_2('network/firewallRule',
                                      params=params).object
        return self._to_firewall_rules(response, network_domain)

    def ex_create_firewall_rule(self, network_domain, rule, position):
        create_node = ET.Element('createFirewallRule', {'xmlns': TYPES_URN})
        ET.SubElement(create_node, "networkDomainId").text = network_domain.id
        ET.SubElement(create_node, "name").text = rule.name
        ET.SubElement(create_node, "action").text = rule.action
        ET.SubElement(create_node, "ipVersion").text = rule.ipVersion
        ET.SubElement(create_node, "protocol").text = rule.protocol
        # Setup source port rule
        source = ET.SubElement(create_node, "source")
        source_ip = ET.SubElement(source, 'ip')
        if rule.source.any_ip:
            source_ip.set('address', 'ANY')
        else:
            source_ip.set('address', rule.source.ip_address)
            source_ip.set('prefixSize', rule.source.ip_prefix_size)
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
            dest_ip.set('prefixSize', rule.destination.ip_prefix_size)
            dest_port = ET.SubElement(dest, 'port')
            dest_port.set('begin', rule.destination.port_begin)
            if rule.destination.port_end is not None:
                dest_port.set('end', rule.destination.port_end)
        ET.SubElement(create_node, "enabled").text = 'true'
        placement = ET.SubElement(create_node, "placement")
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
        """
        update_node = ET.Element('editFirewallrule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        ET.SubElement(update_node, 'enabled').text = str(state).lower()
        result = self.connection.request_with_orgId_api_2(
            'network/editFirewallRule',
            method='POST',
            data=ET.tostring(update_node)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_delete_firewall_rule(self, rule):
        update_node = ET.Element('deleteFirewallrule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteFirewallRule',
            method='POST',
            data=ET.tostring(update_node)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_create_nat_rule(self, network_domain, internal_ip, external_ip):
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
        params = {}
        params['networkDomainId'] = network_domain.id

        response = self.connection \
            .request_with_orgId_api_2('network/natRule',
                                      params=params).object
        return self._to_nat_rules(response, network_domain)

    def ex_get_nat_rule(self, network_domain, rule_id):
        rule = self.connection.request_with_orgId_api_2(
            'network/natRule/%s' % rule_id).object
        return self._to_nat_rule(rule, network_domain)

    def ex_delete_nat_rule(self, rule):
        update_node = ET.Element('deleteNatrule', {'xmlns': TYPES_URN})
        update_node.set('id', rule.id)
        result = self.connection.request_with_orgId_api_2(
            'network/deleteNatRule',
            method='POST',
            data=ET.tostring(update_node)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'IN_PROGRESS' or responseCode == 'OK'

    def ex_get_location_by_id(self, id):
        """
        Get location by ID.

        :param  id: ID of the node location which should be used
        :type   id: ``str``

        :rtype: :class:`NodeLocation`
        """
        location = None
        if id is not None:
            location = list(
                filter(lambda x: x.id == id, self.list_locations()))[0]
        return location

    def _to_nat_rules(self, object, network_domain):
        rules = []
        for element in findall(object, 'natRule', TYPES_URN):
            rules.append(
                self._to_nat_rule(element, network_domain))

        return rules

    def _to_nat_rule(self, element, network_domain):
        status = self._to_status(element.find(fixxpath('state', TYPES_URN)))

        return DimensionDataNatRule(
            id=element.get('id'),
            network_domain=network_domain,
            internal_ip=findtext(element, 'internalIp', TYPES_URN),
            external_ip=findtext(element, 'externalIp', TYPES_URN),
            status=status)

    def _to_firewall_rules(self, object, network_domain):
        rules = []
        locations = self.list_locations()
        for element in findall(object, 'firewallRule', TYPES_URN):
            rules.append(
                self._to_firewall_rule(element, locations, network_domain))

        return rules

    def _to_firewall_rule(self, element, locations, network_domain):
        status = self._to_status(element.find(fixxpath('state', TYPES_URN)))

        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataFirewallRule(
            id=element.get('id'),
            network_domain=network_domain,
            name=findtext(element, 'name', TYPES_URN),
            action=findtext(element, 'action', TYPES_URN),
            ipVersion=findtext(element, 'ipVersion', TYPES_URN),
            protocol=findtext(element, 'protocol', TYPES_URN),
            enabled=findtext(element, 'enabled', TYPES_URN),
            source=self._to_firewall_address(
                element.find(fixxpath('source', TYPES_URN))),
            destination=self._to_firewall_address(
                element.find(fixxpath('destination', TYPES_URN))),
            location=location,
            status=status)

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
        status = self._to_status(element.find(fixxpath('state', TYPES_URN)))

        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataPublicIpBlock(
            id=element.get('id'),
            network_domain=self.ex_get_network_domain(
                findtext(element, 'networkDomainId', TYPES_URN)
            ),
            baseIp=findtext(element, 'baseIp', TYPES_URN),
            size=findtext(element, 'size', TYPES_URN),
            location=location,
            status=status)

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
        status = self._to_status(element.find(fixxpath('state', TYPES_URN)))

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
            status=status)

    def _to_vlans(self, object):
        vlans = []
        locations = self.list_locations()
        for element in findall(object, 'vlan', TYPES_URN):
            vlans.append(self._to_vlan(element, locations=locations))

        return vlans

    def _to_vlan(self, element, locations):
        status = self._to_status(element.find(fixxpath('state', TYPES_URN)))

        location_id = element.get('datacenterId')
        location = list(filter(lambda x: x.id == location_id,
                               locations))[0]

        return DimensionDataVlan(
            id=element.get('id'),
            name=findtext(element, 'name', TYPES_URN),
            description=findtext(element, 'description',
                                 TYPES_URN),
            private_ipv4_range_address= \
                element.find(fixxpath('privateIpv4Range', TYPES_URN)) \
                    .get('address'),
            private_ipv4_range_size= \
                element.find(fixxpath('privateIpv4Range', TYPES_URN)) \
                    .get('prefixSize'),
            location=location,
            status=status)

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

    def _to_nodes(self, object):
        node_elements = object.findall(fixxpath('Server', TYPES_URN))

        return [self._to_node(el) for el in node_elements]

    def _to_node(self, element):
        if findtext(element, 'started', TYPES_URN) == 'true':
            state = NodeState.RUNNING
        else:
            state = NodeState.TERMINATED

        status = self._to_status(element.find(fixxpath('progress', TYPES_URN)))

        has_network_info \
            = element.find(fixxpath('networkInfo', TYPES_URN)) is not None

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
            'cpuCount': int(findtext(
                element,
                'cpuCount',
                TYPES_URN)),
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
            'status': status
        }

        public_ip = findtext(element, 'publicIpAddress', TYPES_URN)

        private_ip = element.find(
            fixxpath('networkInfo/primaryNic', TYPES_URN)) \
            .get('privateIpv4') \
            if has_network_info else \
            element.find(fixxpath('nic', TYPES_URN)).get('privateIpv4')

        n = Node(id=element.get('id'),
                 name=findtext(element, 'name', TYPES_URN),
                 state=state,
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
