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

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

import sys
import unittest
from libcloud.utils.py3 import httplib

from libcloud.common.types import InvalidCredsError
from libcloud.common.dimensiondata import DimensionDataAPIException, NetworkDomainServicePlan
from libcloud.common.dimensiondata import DimensionDataServerCpuSpecification
from libcloud.compute.drivers.dimensiondata import DimensionDataNodeDriver as DimensionData
from libcloud.compute.base import Node, NodeAuthPassword, NodeLocation

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.secrets import DIMENSIONDATA_PARAMS


class DimensionDataTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        DimensionData.connectionCls.conn_classes = (None, DimensionDataMockHttp)
        DimensionDataMockHttp.type = None
        self.driver = DimensionData(*DIMENSIONDATA_PARAMS)

    def test_invalid_region(self):
        try:
            self.driver = DimensionData(*DIMENSIONDATA_PARAMS, region='blah')
        except ValueError:
            pass

    def test_invalid_creds(self):
        DimensionDataMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_nodes()
            self.assertTrue(
                False)  # Above command should have thrown an InvalidCredsException
        except InvalidCredsError:
            pass

    def test_list_locations_response(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_locations()
        self.assertEqual(len(ret), 5)
        first_node = ret[0]
        self.assertEqual(first_node.id, 'NA3')
        self.assertEqual(first_node.name, 'US - West')
        self.assertEqual(first_node.country, 'US')

    def test_list_nodes_response(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 2)

    def test_list_sizes_response(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 1)
        size = ret[0]
        self.assertEqual(size.name, 'default')

    def test_reboot_node_response(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_reboot_node_response_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        try:
            node.reboot()
            self.assertTrue(
                False)  # above command should have thrown DimensionDataAPIException
        except DimensionDataAPIException:
            pass

    def test_destroy_node_response(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_destroy_node_response_RESOURCE_BUSY(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        try:
            node.destroy()
            self.assertTrue(
                False)  # above command should have thrown DimensionDataAPIException
        except DimensionDataAPIException:
            pass

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].name, 'RedHat 6 64-bit 2 CPU')
        self.assertEqual(images[0].id, 'c14b1a46-2428-44c1-9c1a-b20e6418d08c')
        self.assertEqual(images[0].extra['location'].id, 'NA9')
        self.assertEqual(images[0].extra['cpu'].cpu_count, 2)
        self.assertEqual(images[0].extra['OS_displayName'], 'REDHAT6/64')

    def test_ex_list_customer_images(self):
        images = self.driver.ex_list_customer_images()
        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].name, 'ImportedCustomerImage')
        self.assertEqual(images[0].id, '5234e5c7-01de-4411-8b6e-baeb8d91cf5d')
        self.assertEqual(images[0].extra['location'].id, 'NA9')
        self.assertEqual(images[0].extra['cpu'].cpu_count, 4)
        self.assertEqual(images[0].extra['OS_displayName'], 'REDHAT6/64')

    def test_create_node_response(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=rootPw,
                                       ex_description='test2 node', ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_response_network_domain(self):
        rootPw = NodeAuthPassword('pass123')
        location = self.driver.ex_get_location_by_id('NA9')
        image = self.driver.list_images(location=location)[0]
        network_domain = self.driver.ex_list_network_domains(location=location)[0]
        vlan = self.driver.ex_list_vlans(location=location)[0]
        cpu = DimensionDataServerCpuSpecification(
            cpu_count=4,
            cores_per_socket=1,
            performance='HIGHPERFORMANCE'
        )
        node = self.driver.create_node(name='test2', image=image, auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain=network_domain,
                                       ex_vlan=vlan,
                                       ex_is_started=False, ex_cpu_specification=cpu,
                                       ex_memory_gb=4)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_no_network(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        try:
            self.driver.create_node(name='test2', image=image, auth=rootPw,
                                    ex_description='test2 node', ex_network=None,
                                    ex_isStarted=False)
        except ValueError:
            pass

    def test_ex_shutdown_graceful(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_shutdown_graceful(node)
        self.assertTrue(ret is True)

    def test_ex_shutdown_graceful_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        try:
            self.driver.ex_shutdown_graceful(node)
            self.assertTrue(
                False)  # above command should have thrown DimensionDataAPIException
        except DimensionDataAPIException:
            pass

    def test_ex_start_node(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_start_node(node)
        self.assertTrue(ret is True)

    def test_ex_start_node_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        try:
            self.driver.ex_start_node(node)
            self.assertTrue(
                False)  # above command should have thrown DimensionDataAPIException
        except DimensionDataAPIException:
            pass

    def test_ex_power_off(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_power_off(node)
        self.assertTrue(ret is True)

    def test_ex_update_vm_tools(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_update_vm_tools(node)
        self.assertTrue(ret is True)

    def test_ex_power_off_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        try:
            self.driver.ex_power_off(node)
            self.assertTrue(
                False)  # above command should have thrown DimensionDataAPIException
        except DimensionDataAPIException:
            pass

    def test_ex_reset(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_reset(node)
        self.assertTrue(ret is True)

    def test_ex_attach_node_to_vlan(self):
        node = self.driver.ex_get_node_by_id('e75ead52-692f-4314-8725-c8a4f4d13a87')
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        ret = self.driver.ex_attach_node_to_vlan(node, vlan)
        self.assertTrue(ret)

    def test_ex_destroy_nic(self):
        node = self.driver.ex_destroy_nic('a202e51b-41c0-4cfc-add0-b1c62fc0ecf6')
        self.assertTrue(node)

    def test_list_networks(self):
        nets = self.driver.list_networks()
        self.assertEqual(nets[0].name, 'test-net1')
        self.assertTrue(isinstance(nets[0].location, NodeLocation))

    def test_ex_create_network(self):
        location = self.driver.ex_get_location_by_id('NA9')
        net = self.driver.ex_create_network(location, "Test Network", "test")
        self.assertEqual(net.id, "208e3a8e-9d2f-11e2-b29c-001517c4643e")
        self.assertEqual(net.name, "Test Network")

    def test_ex_delete_network(self):
        net = self.driver.ex_list_networks()[0]
        result = self.driver.ex_delete_network(net)
        self.assertTrue(result)

    def test_ex_rename_network(self):
        net = self.driver.ex_list_networks()[0]
        result = self.driver.ex_rename_network(net, "barry")
        self.assertTrue(result)

    def test_ex_create_network_domain(self):
        location = self.driver.ex_get_location_by_id('NA9')
        plan = NetworkDomainServicePlan.ADVANCED
        net = self.driver.ex_create_network_domain(location=location,
                                                   name='test',
                                                   description='test',
                                                   service_plan=plan)
        self.assertEqual(net.name, 'test')
        self.assertTrue(net.id, 'f14a871f-9a25-470c-aef8-51e13202e1aa')

    def test_ex_get_network_domain(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        self.assertEqual(net.id, '8cdfd607-f429-4df6-9352-162cfc0891be')
        self.assertEqual(net.description, 'test2')
        self.assertEqual(net.name, 'test')

    def test_ex_update_network_domain(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        net.name = 'new name'
        net2 = self.driver.ex_update_network_domain(net)
        self.assertEqual(net2.name, 'new name')

    def test_ex_delete_network_domain(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        result = self.driver.ex_delete_network_domain(net)
        self.assertTrue(result)

    def test_ex_list_networks(self):
        nets = self.driver.ex_list_networks()
        self.assertEqual(nets[0].name, 'test-net1')
        self.assertTrue(isinstance(nets[0].location, NodeLocation))

    def test_ex_list_network_domains(self):
        nets = self.driver.ex_list_network_domains()
        self.assertEqual(nets[0].name, 'Aurora')
        self.assertTrue(isinstance(nets[0].location, NodeLocation))

    def test_ex_list_vlans(self):
        vlans = self.driver.ex_list_vlans()
        self.assertEqual(vlans[0].name, "Primary")

    def test_ex_create_vlan(self,):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        vlan = self.driver.ex_create_vlan(network_domain=net,
                                          name='test',
                                          private_ipv4_base_address='10.3.4.0',
                                          private_ipv4_prefix_size='24')
        self.assertEqual(vlan.id, '0e56433f-d808-4669-821d-812769517ff8')

    def test_ex_get_vlan(self):
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        self.assertEqual(vlan.id, '0e56433f-d808-4669-821d-812769517ff8')
        self.assertEqual(vlan.description, 'test2')
        self.assertEqual(vlan.status, 'NORMAL')
        self.assertEqual(vlan.name, 'Production VLAN')
        self.assertEqual(vlan.private_ipv4_range_address, '10.0.3.0')
        self.assertEqual(vlan.private_ipv4_range_size, 24)
        self.assertEqual(vlan.ipv6_range_size, 64)
        self.assertEqual(vlan.ipv6_range_address, '2607:f480:1111:1153:0:0:0:0')
        self.assertEqual(vlan.ipv4_gateway, '10.0.3.1')
        self.assertEqual(vlan.ipv6_gateway, '2607:f480:1111:1153:0:0:0:1')

    def test_ex_wait_for_state(self):
        self.driver.ex_wait_for_state('NORMAL',
                                      self.driver.ex_get_vlan,
                                      vlan_id='0e56433f-d808-4669-821d-812769517ff8')

    def test_ex_update_vlan(self):
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        vlan.name = 'new name'
        vlan2 = self.driver.ex_update_vlan(vlan)
        self.assertEqual(vlan2.name, 'new name')

    def test_ex_delete_vlan(self):
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        result = self.driver.ex_delete_vlan(vlan)
        self.assertTrue(result)

    def test_ex_expand_vlan(self):
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        vlan.private_ipv4_range_size = '23'
        vlan = self.driver.ex_expand_vlan(vlan)
        self.assertEqual(vlan.private_ipv4_range_size, '23')

    def test_ex_add_public_ip_block_to_network_domain(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        block = self.driver.ex_add_public_ip_block_to_network_domain(net)
        self.assertEqual(block.id, '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')

    def test_ex_list_public_ip_blocks(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        blocks = self.driver.ex_list_public_ip_blocks(net)
        self.assertEqual(blocks[0].base_ip, '168.128.4.18')
        self.assertEqual(blocks[0].size, '2')
        self.assertEqual(blocks[0].id, '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
        self.assertEqual(blocks[0].location.id, 'NA9')
        self.assertEqual(blocks[0].network_domain.id, net.id)

    def test_ex_get_public_ip_block(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        block = self.driver.ex_get_public_ip_block('9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
        self.assertEqual(block.base_ip, '168.128.4.18')
        self.assertEqual(block.size, '2')
        self.assertEqual(block.id, '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
        self.assertEqual(block.location.id, 'NA9')
        self.assertEqual(block.network_domain.id, net.id)

    def test_ex_delete_public_ip_block(self):
        block = self.driver.ex_get_public_ip_block('9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
        result = self.driver.ex_delete_public_ip_block(block)
        self.assertTrue(result)

    def test_ex_list_firewall_rules(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        self.assertEqual(rules[0].id, '756cba02-b0bc-48f4-aea5-9445870b6148')
        self.assertEqual(rules[0].network_domain.id, '8cdfd607-f429-4df6-9352-162cfc0891be')
        self.assertEqual(rules[0].name, 'CCDEFAULT.BlockOutboundMailIPv4')
        self.assertEqual(rules[0].action, 'DROP')
        self.assertEqual(rules[0].ip_version, 'IPV4')
        self.assertEqual(rules[0].protocol, 'TCP')
        self.assertEqual(rules[0].source.ip_address, 'ANY')
        self.assertTrue(rules[0].source.any_ip)
        self.assertTrue(rules[0].destination.any_ip)

    def test_ex_create_firewall_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        rule = self.driver.ex_create_firewall_rule(net, rules[0], 'FIRST')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_get_firewall_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_set_firewall_rule_state(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        result = self.driver.ex_set_firewall_rule_state(rule, False)
        self.assertTrue(result)

    def test_ex_delete_firewall_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        result = self.driver.ex_delete_firewall_rule(rule)
        self.assertTrue(result)

    def test_ex_create_nat_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_create_nat_rule(net, '1.2.3.4', '4.3.2.1')
        self.assertEqual(rule.id, 'd31c2db0-be6b-4d50-8744-9a7a534b5fba')

    def test_ex_list_nat_rules(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_nat_rules(net)
        self.assertEqual(rules[0].id, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
        self.assertEqual(rules[0].internal_ip, '10.0.0.15')
        self.assertEqual(rules[0].external_ip, '165.180.12.18')

    def test_ex_get_nat_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_nat_rule(net, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
        self.assertEqual(rule.id, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
        self.assertEqual(rule.internal_ip, '10.0.0.16')
        self.assertEqual(rule.external_ip, '165.180.12.19')

    def test_ex_delete_nat_rule(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_nat_rule(net, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
        result = self.driver.ex_delete_nat_rule(rule)
        self.assertTrue(result)

    def test_ex_enable_monitoring(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_enable_monitoring(node, "ADVANCED")
        self.assertTrue(result)

    def test_ex_disable_monitoring(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_disable_monitoring(node)
        self.assertTrue(result)

    def test_ex_change_monitoring_plan(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_update_monitoring_plan(node, "ESSENTIALS")
        self.assertTrue(result)

    def test_ex_add_storage_to_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_add_storage_to_node(node, 30, 'PERFORMANCE')
        self.assertTrue(result)

    def test_ex_remove_storage_from_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_remove_storage_from_node(node, 1)
        self.assertTrue(result)

    def test_ex_change_storage_speed(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_change_storage_speed(node, 1, 'PERFORMANCE')
        self.assertTrue(result)

    def test_ex_change_storage_size(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_change_storage_size(node, 1, 100)
        self.assertTrue(result)

    def test_ex_clone_node_to_image(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_clone_node_to_image(node, 'my image', 'a description')
        self.assertTrue(result)

    def test_ex_update_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_update_node(node, 'my new name', 'a description', 2, 4048)
        self.assertTrue(result)

    def test_ex_reconfigure_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_reconfigure_node(node, 4, 4, 1, 'HIGHPERFORMANCE')
        self.assertTrue(result)


class InvalidRequestError(Exception):
    def __init__(self, tag):
        super(InvalidRequestError, self).__init__("Invalid Request - %s" % tag)


class DimensionDataMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('dimensiondata')

    def _oec_0_9_myaccount_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_base_image(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_base_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_base_imageWithDiskSpeed(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_base_imageWithDiskSpeed.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployed(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployed.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_pendingDeploy(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_pendingDeploy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_datacenter(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11(self, method, url, body, headers):
        body = None
        action = url.split('?')[-1]

        if action == 'restart':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_restart.xml')
        elif action == 'shutdown':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_shutdown.xml')
        elif action == 'delete':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_delete.xml')
        elif action == 'start':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_start.xml')
        elif action == 'poweroff':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_poweroff.xml')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_INPROGRESS(self, method, url, body, headers):
        body = None
        action = url.split('?')[-1]

        if action == 'restart':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_restart_INPROGRESS.xml')
        elif action == 'shutdown':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_shutdown_INPROGRESS.xml')
        elif action == 'delete':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_delete_INPROGRESS.xml')
        elif action == 'start':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_start_INPROGRESS.xml')
        elif action == 'poweroff':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_11_poweroff_INPROGRESS.xml')

        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server(self, method, url, body, headers):
        body = self.fixtures.load(
            '_oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkWithLocation(self, method, url, body, headers):
        if method is "POST":
            request = ET.fromstring(body)
            if request.tag != "{http://oec.api.opsource.net/schemas/network}NewNetworkWithLocation":
                raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkWithLocation.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_4bba37be_506f_11e3_b29c_001517c4643e(self, method,
                                                                                                   url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_4bba37be_506f_11e3_b29c_001517c4643e.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1_changeSize(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1_changeSize.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1_changeSpeed(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1_changeSpeed.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1(self, method, url, body, headers):
        action = url.split('?')[-1]
        if action == 'delete':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_disk_1.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_POST.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_updateVmwareTools(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}updateVmwareTools":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_updateVmwareTools.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_resetServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}resetServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_resetServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_0e56433f_d808_4669_821d_812769517ff8(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_0e56433f_d808_4669_821d_812769517ff8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_expandVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}expandVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_expandVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_addPublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addPublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_addPublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_removePublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removePublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_removePublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removeNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_disableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}disableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_disableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_enableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}enableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_enableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeServerMonitoringPlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}changeServerMonitoringPlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeServerMonitoringPlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_reconfigureServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}reconfigureServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_reconfigureServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
