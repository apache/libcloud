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
from types import GeneratorType
from libcloud.utils.py3 import httplib

from libcloud.common.types import InvalidCredsError
from libcloud.common.dimensiondata import DimensionDataAPIException, NetworkDomainServicePlan
from libcloud.common.dimensiondata import DimensionDataServerCpuSpecification, DimensionDataServerDisk, DimensionDataServerVMWareTools
from libcloud.common.dimensiondata import DimensionDataTag, DimensionDataTagKey
from libcloud.common.dimensiondata import DimensionDataIpAddress, \
    DimensionDataIpAddressList, DimensionDataChildIpAddressList, \
    DimensionDataPortList, DimensionDataPort, DimensionDataChildPortList
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.compute.drivers.dimensiondata import DimensionDataNodeDriver as DimensionData
from libcloud.compute.drivers.dimensiondata import DimensionDataNic
from libcloud.compute.base import Node, NodeAuthPassword, NodeLocation
from libcloud.test import MockHttp, unittest, MockRawResponse, StorageMockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import DIMENSIONDATA_PARAMS
from libcloud.utils.xml import fixxpath, findtext, findall


class DimensionDataTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        DimensionData.connectionCls.conn_classes = (None, DimensionDataMockHttp)
        DimensionData.connectionCls.rawResponseCls = \
            DimensionDataMockRawResponse
        DimensionDataMockHttp.type = None
        self.driver = DimensionData(*DIMENSIONDATA_PARAMS)

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            DimensionData(*DIMENSIONDATA_PARAMS, region='blah')

    def test_invalid_creds(self):
        DimensionDataMockHttp.type = 'UNAUTHORIZED'
        with self.assertRaises(InvalidCredsError):
            self.driver.list_nodes()

    def test_get_account_details(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.connection.get_account_details()
        self.assertEqual(ret.full_name, 'Test User')
        self.assertEqual(ret.first_name, 'Test')
        self.assertEqual(ret.email, 'test@example.com')

    def test_list_locations_response(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_locations()
        self.assertEqual(len(ret), 5)
        first_loc = ret[0]
        self.assertEqual(first_loc.id, 'NA3')
        self.assertEqual(first_loc.name, 'US - West')
        self.assertEqual(first_loc.country, 'US')

    def test_list_nodes_response(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 7)

    def test_node_extras(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertTrue(isinstance(ret[0].extra['vmWareTools'], DimensionDataServerVMWareTools))
        self.assertTrue(isinstance(ret[0].extra['cpu'], DimensionDataServerCpuSpecification))
        self.assertTrue(isinstance(ret[0].extra['disks'], list))
        self.assertTrue(isinstance(ret[0].extra['disks'][0], DimensionDataServerDisk))
        self.assertEqual(ret[0].extra['disks'][0].size_gb, 10)
        self.assertTrue(isinstance(ret[1].extra['disks'], list))
        self.assertTrue(isinstance(ret[1].extra['disks'][0], DimensionDataServerDisk))
        self.assertEqual(ret[1].extra['disks'][0].size_gb, 10)

    def test_server_states(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertTrue(ret[0].state == 'running')
        self.assertTrue(ret[1].state == 'starting')
        self.assertTrue(ret[2].state == 'stopping')
        self.assertTrue(ret[3].state == 'reconfiguring')
        self.assertTrue(ret[4].state == 'running')
        self.assertTrue(ret[5].state == 'terminated')
        self.assertTrue(ret[6].state == 'stopped')
        self.assertEqual(len(ret), 7)

    def test_list_nodes_response_PAGINATED(self):
        DimensionDataMockHttp.type = 'PAGINATED'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 9)

    def test_paginated_mcp2_call_EMPTY(self):
        # cache org
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'EMPTY'
        node_list_generator = self.driver.connection.paginated_request_with_orgId_api_2('server/server')
        empty_node_list = []
        for node_list in node_list_generator:
            empty_node_list.extend(node_list)
        self.assertTrue(len(empty_node_list) == 0)

    def test_paginated_mcp2_call_PAGED_THEN_EMPTY(self):
        # cache org
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'PAGED_THEN_EMPTY'
        node_list_generator = self.driver.connection.paginated_request_with_orgId_api_2('server/server')
        final_node_list = []
        for node_list in node_list_generator:
            final_node_list.extend(node_list)
        self.assertTrue(len(final_node_list) == 2)

    def test_paginated_mcp2_call_with_page_size(self):
        # cache org
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'PAGESIZE50'
        node_list_generator = self.driver.connection.paginated_request_with_orgId_api_2('server/server', page_size=50)
        self.assertTrue(isinstance(node_list_generator, GeneratorType))

    # We're making sure here the filters make it to the URL
    # See  _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_ALLFILTERS for asserts
    def test_list_nodes_response_strings_ALLFILTERS(self):
        DimensionDataMockHttp.type = 'ALLFILTERS'
        ret = self.driver.list_nodes(ex_location='fake_loc', ex_name='fake_name',
                                     ex_ipv6='fake_ipv6', ex_ipv4='fake_ipv4', ex_vlan='fake_vlan',
                                     ex_image='fake_image', ex_deployed=True,
                                     ex_started=True, ex_state='fake_state',
                                     ex_network='fake_network', ex_network_domain='fake_network_domain')
        self.assertTrue(isinstance(ret, list))
        self.assertEqual(len(ret), 7)

        node = ret[3]
        self.assertTrue(isinstance(node.extra['disks'], list))
        self.assertTrue(isinstance(node.extra['disks'][0], DimensionDataServerDisk))
        self.assertEqual(node.size.id, '1')
        self.assertEqual(node.image.id, '3ebf3c0f-90fe-4a8b-8585-6e65b316592c')
        self.assertEqual(node.image.name, 'WIN2008S/32')
        disk = node.extra['disks'][0]
        self.assertEqual(disk.id, "c2e1f199-116e-4dbc-9960-68720b832b0a")
        self.assertEqual(disk.scsi_id, 0)
        self.assertEqual(disk.size_gb, 50)
        self.assertEqual(disk.speed, "STANDARD")
        self.assertEqual(disk.state, "NORMAL")

    def test_list_nodes_response_LOCATION(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_locations()
        first_loc = ret[0]
        ret = self.driver.list_nodes(ex_location=first_loc)
        for node in ret:
            self.assertEqual(node.extra['datacenterId'], 'NA3')

    def test_list_nodes_response_LOCATION_STR(self):
        DimensionDataMockHttp.type = None
        ret = self.driver.list_nodes(ex_location='NA3')
        for node in ret:
            self.assertEqual(node.extra['datacenterId'], 'NA3')

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
        with self.assertRaises(DimensionDataAPIException):
            node.reboot()

    def test_destroy_node_response(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_destroy_node_response_RESOURCE_BUSY(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        with self.assertRaises(DimensionDataAPIException):
            node.destroy()

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].name, 'RedHat 6 64-bit 2 CPU')
        self.assertEqual(images[0].id, 'c14b1a46-2428-44c1-9c1a-b20e6418d08c')
        self.assertEqual(images[0].extra['location'].id, 'NA9')
        self.assertEqual(images[0].extra['cpu'].cpu_count, 2)
        self.assertEqual(images[0].extra['OS_displayName'], 'REDHAT6/64')

    def test_clean_failed_deployment_response_with_node(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_clean_failed_deployment(node)
        self.assertTrue(ret is True)

    def test_clean_failed_deployment_response_with_node_id(self):
        node = 'e75ead52-692f-4314-8725-c8a4f4d13a87'
        ret = self.driver.ex_clean_failed_deployment(node)
        self.assertTrue(ret is True)

    def test_ex_list_customer_images(self):
        images = self.driver.ex_list_customer_images()
        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].name, 'ImportedCustomerImage')
        self.assertEqual(images[0].id, '5234e5c7-01de-4411-8b6e-baeb8d91cf5d')
        self.assertEqual(images[0].extra['location'].id, 'NA9')
        self.assertEqual(images[0].extra['cpu'].cpu_count, 4)
        self.assertEqual(images[0].extra['OS_displayName'], 'REDHAT6/64')

    def test_create_mcp1_node_optional_param(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        network = self.driver.ex_list_networks()[0]
        cpu_spec = DimensionDataServerCpuSpecification(cpu_count='4',
                                                       cores_per_socket='2',
                                                       performance='STANDARD')
        disks = [DimensionDataServerDisk(scsi_id='0', speed='HIGHPERFORMANCE')]
        node = self.driver.create_node(name='test2', image=image, auth=root_pw,
                                       ex_description='test2 node',
                                       ex_network=network,
                                       ex_is_started=False,
                                       ex_memory_gb=8,
                                       ex_disks=disks,
                                       ex_cpu_specification=cpu_spec,
                                       ex_primary_dns='10.0.0.5',
                                       ex_secondary_dns='10.0.0.6'
                                       )
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_mcp1_node_response_no_pass_random_gen(self):
        image = self.driver.list_images()[0]
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=None,
                                       ex_description='test2 node',
                                       ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')
        self.assertTrue('password' in node.extra)

    def test_create_mcp1_node_response_no_pass_customer_windows(self):
        image = self.driver.ex_list_customer_images()[1]
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=None,
                                       ex_description='test2 node', ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')
        self.assertTrue('password' in node.extra)

    def test_create_mcp1_node_response_no_pass_customer_windows_STR(self):
        image = self.driver.ex_list_customer_images()[1].id
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=None,
                                       ex_description='test2 node', ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')
        self.assertTrue('password' in node.extra)

    def test_create_mcp1_node_response_no_pass_customer_linux(self):
        image = self.driver.ex_list_customer_images()[0]
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=None,
                                       ex_description='test2 node', ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')
        self.assertTrue('password' not in node.extra)

    def test_create_mcp1_node_response_no_pass_customer_linux_STR(self):
        image = self.driver.ex_list_customer_images()[0].id
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node(name='test2', image=image, auth=None,
                                       ex_description='test2 node', ex_network=network,
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')
        self.assertTrue('password' not in node.extra)

    def test_create_mcp1_node_response_STR(self):
        rootPw = 'pass123'
        image = self.driver.list_images()[0].id
        network = self.driver.ex_list_networks()[0].id
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

    def test_create_node_response_network_domain_STR(self):
        rootPw = NodeAuthPassword('pass123')
        location = self.driver.ex_get_location_by_id('NA9')
        image = self.driver.list_images(location=location)[0]
        network_domain = self.driver.ex_list_network_domains(location=location)[0].id
        vlan = self.driver.ex_list_vlans(location=location)[0].id
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

    def test_create_mcp1_node_no_network(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(InvalidRequestError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=rootPw,
                                    ex_description='test2 node',
                                    ex_network=None,
                                    ex_is_started=False)

    def test_create_node_mcp1_ipv4(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network='fakenetwork',
                                       ex_primary_ipv4='10.0.0.1',
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_mcp1_network(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network='fakenetwork',
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_mcp2_vlan(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_vlan='fakevlan',
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_mcp2_ipv4(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_ipv4='10.0.0.1',
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_network_domain_no_vlan_or_ipv4(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=rootPw,
                                    ex_description='test2 node',
                                    ex_network_domain='fake_network_domain',
                                    ex_is_started=False)

    def test_create_node_response(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(
            name='test3',
            image=image,
            auth=rootPw,
            ex_network_domain='fakenetworkdomain',
            ex_primary_nic_vlan='fakevlan'
        )
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_ms_time_zone(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(
            name='test3',
            image=image,
            auth=rootPw,
            ex_network_domain='fakenetworkdomain',
            ex_primary_nic_vlan='fakevlan',
            ex_microsoft_time_zone='040'
        )
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_ambigious_mcps_fail(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(
                name='test3',
                image=image,
                auth=rootPw,
                ex_network_domain='fakenetworkdomain',
                ex_network='fakenetwork',
                ex_primary_nic_vlan='fakevlan'
            )

    def test_create_node_no_network_domain_fail(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(
                name='test3',
                image=image,
                auth=rootPw,
                ex_primary_nic_vlan='fakevlan'
            )

    def test_create_node_no_primary_nic_fail(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(
                name='test3',
                image=image,
                auth=rootPw,
                ex_network_domain='fakenetworkdomain'
            )

    def test_create_node_primary_vlan_nic(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(
            name='test3',
            image=image,
            auth=rootPw,
            ex_network_domain='fakenetworkdomain',
            ex_primary_nic_vlan='fakevlan',
            ex_primary_nic_network_adapter='v1000'
        )
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_primary_ipv4(self):
        rootPw = 'pass123'
        image = self.driver.list_images()[0]
        node = self.driver.create_node(
            name='test3',
            image=image,
            auth=rootPw,
            ex_network_domain='fakenetworkdomain',
            ex_primary_nic_private_ipv4='10.0.0.1'
        )
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_both_primary_nic_and_vlan_fail(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(
                name='test3',
                image=image,
                auth=rootPw,
                ex_network_domain='fakenetworkdomain',
                ex_primary_nic_private_ipv4='10.0.0.1',
                ex_primary_nic_vlan='fakevlan'
            )

    def test_create_node_cpu_specification(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        cpu_spec = DimensionDataServerCpuSpecification(cpu_count='4',
                                                       cores_per_socket='2',
                                                       performance='STANDARD')
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_nic_private_ipv4='10.0.0.1',
                                       ex_is_started=False,
                                       ex_cpu_specification=cpu_spec)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_memory(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]

        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_nic_private_ipv4='10.0.0.1',
                                       ex_is_started=False,
                                       ex_memory_gb=8)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_disks(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        disks = [DimensionDataServerDisk(scsi_id='0', speed='HIGHPERFORMANCE')]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_nic_private_ipv4='10.0.0.1',
                                       ex_is_started=False,
                                       ex_disks=disks)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_disks_fail(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        disks = 'blah'
        with self.assertRaises(TypeError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=root_pw,
                                    ex_description='test2 node',
                                    ex_network_domain='fakenetworkdomain',
                                    ex_primary_nic_private_ipv4='10.0.0.1',
                                    ex_is_started=False,
                                    ex_disks=disks)

    def test_create_node_ipv4_gateway(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_nic_private_ipv4='10.0.0.1',
                                       ex_is_started=False,
                                       ex_ipv4_gateway='10.2.2.2')
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_network_domain_no_vlan_no_ipv4_fail(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(ValueError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=rootPw,
                                    ex_description='test2 node',
                                    ex_network_domain='fake_network_domain',
                                    ex_is_started=False)

    def test_create_node_mcp2_additional_nics_legacy(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        additional_vlans = ['fakevlan1', 'fakevlan2']
        additional_ipv4 = ['10.0.0.2', '10.0.0.3']
        node = self.driver.create_node(
            name='test2',
            image=image,
            auth=rootPw,
            ex_description='test2 node',
            ex_network_domain='fakenetworkdomain',
            ex_primary_ipv4='10.0.0.1',
            ex_additional_nics_vlan=additional_vlans,
            ex_additional_nics_ipv4=additional_ipv4,
            ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_bad_additional_nics_ipv4(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(TypeError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=rootPw,
                                    ex_description='test2 node',
                                    ex_network_domain='fake_network_domain',
                                    ex_vlan='fake_vlan',
                                    ex_additional_nics_ipv4='badstring',
                                    ex_is_started=False)

    def test_create_node_additional_nics(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        nic1 = DimensionDataNic(vlan='fake_vlan',
                                network_adapter_name='v1000')
        nic2 = DimensionDataNic(private_ip_v4='10.1.1.2',
                                network_adapter_name='v1000')
        additional_nics = [nic1, nic2]

        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=root_pw,
                                       ex_description='test2 node',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_nic_private_ipv4='10.0.0.1',
                                       ex_additional_nics=additional_nics,
                                       ex_is_started=False)

        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_create_node_additional_nics_vlan_ipv4_coexist_fail(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        nic1 = DimensionDataNic(private_ip_v4='10.1.1.1', vlan='fake_vlan',
                                network_adapter_name='v1000')
        nic2 = DimensionDataNic(private_ip_v4='10.1.1.2', vlan='fake_vlan2',
                                network_adapter_name='v1000')
        additional_nics = [nic1, nic2]
        with self.assertRaises(ValueError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=root_pw,
                                    ex_description='test2 node',
                                    ex_network_domain='fakenetworkdomain',
                                    ex_primary_nic_private_ipv4='10.0.0.1',
                                    ex_additional_nics=additional_nics,
                                    ex_is_started=False
                                    )

    def test_create_node_additional_nics_invalid_input_fail(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        additional_nics = 'blah'
        with self.assertRaises(TypeError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=root_pw,
                                    ex_description='test2 node',
                                    ex_network_domain='fakenetworkdomain',
                                    ex_primary_nic_private_ipv4='10.0.0.1',
                                    ex_additional_nics=additional_nics,
                                    ex_is_started=False
                                    )

    def test_create_node_additional_nics_vlan_ipv4_not_exist_fail(self):
        root_pw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        nic1 = DimensionDataNic(network_adapter_name='v1000')
        nic2 = DimensionDataNic(network_adapter_name='v1000')
        additional_nics = [nic1, nic2]
        with self.assertRaises(ValueError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=root_pw,
                                    ex_description='test2 node',
                                    ex_network_domain='fakenetworkdomain',
                                    ex_primary_nic_private_ipv4='10.0.0.1',
                                    ex_additional_nics=additional_nics,
                                    ex_is_started=False)

    def test_create_node_bad_additional_nics_vlan(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        with self.assertRaises(TypeError):
            self.driver.create_node(name='test2',
                                    image=image,
                                    auth=rootPw,
                                    ex_description='test2 node',
                                    ex_network_domain='fake_network_domain',
                                    ex_vlan='fake_vlan',
                                    ex_additional_nics_vlan='badstring',
                                    ex_is_started=False)

    def test_create_node_mcp2_indicate_dns(self):
        rootPw = NodeAuthPassword('pass123')
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='test2',
                                       image=image,
                                       auth=rootPw,
                                       ex_description='test node dns',
                                       ex_network_domain='fakenetworkdomain',
                                       ex_primary_ipv4='10.0.0.1',
                                       ex_primary_dns='8.8.8.8',
                                       ex_secondary_dns='8.8.4.4',
                                       ex_is_started=False)
        self.assertEqual(node.id, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(node.extra['status'].action, 'DEPLOY_SERVER')

    def test_ex_shutdown_graceful(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_shutdown_graceful(node)
        self.assertTrue(ret is True)

    def test_ex_shutdown_graceful_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_shutdown_graceful(node)

    def test_ex_start_node(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_start_node(node)
        self.assertTrue(ret is True)

    def test_ex_start_node_INPROGRESS(self):
        DimensionDataMockHttp.type = 'INPROGRESS'
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_start_node(node)

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
        node = Node(id='11', name=None, state='STOPPING',
                    public_ips=None, private_ips=None, driver=self.driver)

        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_power_off(node)

    def test_ex_reset(self):
        node = Node(id='11', name=None, state=None,
                    public_ips=None, private_ips=None, driver=self.driver)
        ret = self.driver.ex_reset(node)
        self.assertTrue(ret is True)

    def test_ex_attach_node_to_vlan(self):
        node = self.driver.ex_get_node_by_id('e75ead52-692f-4314-8725-c8a4f4d13a87')
        vlan = self.driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
        ret = self.driver.ex_attach_node_to_vlan(node, vlan)
        self.assertTrue(ret is True)

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

    def test_ex_create_network_NO_DESCRIPTION(self):
        location = self.driver.ex_get_location_by_id('NA9')
        net = self.driver.ex_create_network(location, "Test Network")
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

    def test_ex_create_network_domain_NO_DESCRIPTION(self):
        location = self.driver.ex_get_location_by_id('NA9')
        plan = NetworkDomainServicePlan.ADVANCED
        net = self.driver.ex_create_network_domain(location=location,
                                                   name='test',
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

    def test_ex_list_network_domains_ALLFILTERS(self):
        DimensionDataMockHttp.type = 'ALLFILTERS'
        nets = self.driver.ex_list_network_domains(location='fake_location', name='fake_name',
                                                   service_plan='fake_plan', state='fake_state')
        self.assertEqual(nets[0].name, 'Aurora')
        self.assertTrue(isinstance(nets[0].location, NodeLocation))

    def test_ex_list_vlans(self):
        vlans = self.driver.ex_list_vlans()
        self.assertEqual(vlans[0].name, "Primary")

    def test_ex_list_vlans_ALLFILTERS(self):
        DimensionDataMockHttp.type = 'ALLFILTERS'
        vlans = self.driver.ex_list_vlans(location='fake_location', network_domain='fake_network_domain',
                                          name='fake_name', ipv4_address='fake_ipv4', ipv6_address='fake_ipv6', state='fake_state')
        self.assertEqual(vlans[0].name, "Primary")

    def test_ex_create_vlan(self,):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        vlan = self.driver.ex_create_vlan(network_domain=net,
                                          name='test',
                                          private_ipv4_base_address='10.3.4.0',
                                          private_ipv4_prefix_size='24',
                                          description='test vlan')
        self.assertEqual(vlan.id, '0e56433f-d808-4669-821d-812769517ff8')

    def test_ex_create_vlan_NO_DESCRIPTION(self,):
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

    def test_ex_wait_for_state_NODE(self):
        self.driver.ex_wait_for_state('running',
                                      self.driver.ex_get_node_by_id,
                                      id='e75ead52-692f-4314-8725-c8a4f4d13a87')

    def test_ex_wait_for_state_FAIL(self):
        with self.assertRaises(DimensionDataAPIException) as context:
            self.driver.ex_wait_for_state('starting',
                                          self.driver.ex_get_node_by_id,
                                          id='e75ead52-692f-4314-8725-c8a4f4d13a87',
                                          timeout=2
                                          )
        self.assertEqual(context.exception.code, 'running')
        self.assertTrue('timed out' in context.exception.msg)

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

    def test_ex_create_firewall_rule_with_specific_source_ip(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        specific_source_ip_rule = list(filter(lambda x: x.name == 'SpecificSourceIP',
                                              rules))[0]
        rule = self.driver.ex_create_firewall_rule(net, specific_source_ip_rule, 'FIRST')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_create_firewall_rule_with_source_ip(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        specific_source_ip_rule = \
            list(filter(lambda x: x.name == 'SpecificSourceIP',
                        rules))[0]
        specific_source_ip_rule.source.any_ip = False
        specific_source_ip_rule.source.ip_address = '10.0.0.1'
        specific_source_ip_rule.source.ip_prefix_size = '15'
        rule = self.driver.ex_create_firewall_rule(net,
                                                   specific_source_ip_rule,
                                                   'FIRST')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_create_firewall_rule_with_any_ip(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        specific_source_ip_rule = \
            list(filter(lambda x: x.name == 'SpecificSourceIP',
                        rules))[0]
        specific_source_ip_rule.source.any_ip = True
        rule = self.driver.ex_create_firewall_rule(net,
                                                   specific_source_ip_rule,
                                                   'FIRST')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_create_firewall_rule_ip_prefix_size(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_list_firewall_rules(net)[0]
        rule.source.address_list_id = None
        rule.source.any_ip = False
        rule.source.ip_address = '10.2.1.1'
        rule.source.ip_prefix_size = '10'
        rule.destination.address_list_id = None
        rule.destination.any_ip = False
        rule.destination.ip_address = '10.0.0.1'
        rule.destination.ip_prefix_size = '20'
        self.driver.ex_create_firewall_rule(net, rule, 'LAST')

    def test_ex_create_firewall_rule_address_list(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_list_firewall_rules(net)[0]
        rule.source.address_list_id = '12345'
        rule.destination.address_list_id = '12345'
        self.driver.ex_create_firewall_rule(net, rule, 'LAST')

    def test_ex_create_firewall_rule_port_list(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_list_firewall_rules(net)[0]
        rule.source.port_list_id = '12345'
        rule.destination.port_list_id = '12345'
        self.driver.ex_create_firewall_rule(net, rule, 'LAST')

    def test_ex_create_firewall_rule_port(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_list_firewall_rules(net)[0]
        rule.source.port_list_id = None
        rule.source.port_begin = '8000'
        rule.source.port_end = '8005'
        rule.destination.port_list_id = None
        rule.destination.port_begin = '7000'
        rule.destination.port_end = '7005'
        self.driver.ex_create_firewall_rule(net, rule, 'LAST')

    def test_ex_create_firewall_rule_ALL_VALUES(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        for rule in rules:
            self.driver.ex_create_firewall_rule(net, rule, 'LAST')

    def test_ex_create_firewall_rule_WITH_POSITION_RULE(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        rule = self.driver.ex_create_firewall_rule(net, rules[-2], 'BEFORE', rules[-1])
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_create_firewall_rule_WITH_POSITION_RULE_STR(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        rule = self.driver.ex_create_firewall_rule(net, rules[-2], 'BEFORE', 'RULE_WITH_SOURCE_AND_DEST')
        self.assertEqual(rule.id, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')

    def test_ex_create_firewall_rule_FAIL_POSITION(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        with self.assertRaises(ValueError):
            self.driver.ex_create_firewall_rule(net, rules[0], 'BEFORE')

    def test_ex_create_firewall_rule_FAIL_POSITION_WITH_RULE(self):
        net = self.driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
        rules = self.driver.ex_list_firewall_rules(net)
        with self.assertRaises(ValueError):
            self.driver.ex_create_firewall_rule(net, rules[0], 'LAST', 'RULE_WITH_SOURCE_AND_DEST')

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

    def test_ex_edit_firewall_rule(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.source.any_ip = True
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_source_ipaddresslist(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.source.address_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
        rule.source.any_ip = False
        rule.source.ip_address = '10.0.0.1'
        rule.source.ip_prefix_size = 10
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_destination_ipaddresslist(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.destination.address_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
        rule.destination.any_ip = False
        rule.destination.ip_address = '10.0.0.1'
        rule.destination.ip_prefix_size = 10
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_destination_ipaddress(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.source.address_list_id = None
        rule.source.any_ip = False
        rule.source.ip_address = '10.0.0.1'
        rule.source.ip_prefix_size = '10'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_source_ipaddress(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.destination.address_list_id = None
        rule.destination.any_ip = False
        rule.destination.ip_address = '10.0.0.1'
        rule.destination.ip_prefix_size = '10'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_with_relative_rule(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        placement_rule = self.driver.ex_list_firewall_rules(
            network_domain=net)[-1]
        result = self.driver.ex_edit_firewall_rule(
            rule=rule, position='BEFORE',
            relative_rule_for_position=placement_rule)
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_with_relative_rule_by_name(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        placement_rule = self.driver.ex_list_firewall_rules(
            network_domain=net)[-1]
        result = self.driver.ex_edit_firewall_rule(
            rule=rule, position='BEFORE',
            relative_rule_for_position=placement_rule.name)
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_source_portlist(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.source.port_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_source_port(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.source.port_list_id = None
        rule.source.port_begin = '3'
        rule.source.port_end = '10'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_destination_portlist(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.destination.port_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_destination_port(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        rule.destination.port_list_id = None
        rule.destination.port_begin = '3'
        rule.destination.port_end = '10'
        result = self.driver.ex_edit_firewall_rule(rule=rule, position='LAST')
        self.assertTrue(result)

    def test_ex_edit_firewall_rule_invalid_position_fail(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        with self.assertRaises(ValueError):
            self.driver.ex_edit_firewall_rule(rule=rule, position='BEFORE')

    def test_ex_edit_firewall_rule_invalid_position_relative_rule_fail(self):
        net = self.driver.ex_get_network_domain(
            '8cdfd607-f429-4df6-9352-162cfc0891be')
        rule = self.driver.ex_get_firewall_rule(
            net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
        relative_rule = self.driver.ex_list_firewall_rules(
            network_domain=net)[-1]
        with self.assertRaises(ValueError):
            self.driver.ex_edit_firewall_rule(rule=rule, position='FIRST',
                                              relative_rule_for_position=relative_rule)

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
        result = self.driver.ex_remove_storage_from_node(node, 0)
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

    def test_ex_get_location_by_id(self):
        location = self.driver.ex_get_location_by_id('NA9')
        self.assertTrue(location.id, 'NA9')

    def test_ex_get_location_by_id_NO_LOCATION(self):
        location = self.driver.ex_get_location_by_id(None)
        self.assertIsNone(location)

    def test_ex_get_base_image_by_id(self):
        image_id = self.driver.list_images()[0].id
        image = self.driver.ex_get_base_image_by_id(image_id)
        self.assertEqual(image.extra['OS_type'], 'UNIX')

    def test_ex_get_customer_image_by_id(self):
        image_id = self.driver.ex_list_customer_images()[1].id
        image = self.driver.ex_get_customer_image_by_id(image_id)
        self.assertEqual(image.extra['OS_type'], 'WINDOWS')

    def test_ex_get_image_by_id_base_img(self):
        image_id = self.driver.list_images()[1].id
        image = self.driver.ex_get_base_image_by_id(image_id)
        self.assertEqual(image.extra['OS_type'], 'WINDOWS')

    def test_ex_get_image_by_id_customer_img(self):
        image_id = self.driver.ex_list_customer_images()[0].id
        image = self.driver.ex_get_customer_image_by_id(image_id)
        self.assertEqual(image.extra['OS_type'], 'UNIX')

    def test_ex_get_image_by_id_customer_FAIL(self):
        image_id = 'FAKE_IMAGE_ID'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_get_base_image_by_id(image_id)

    def test_ex_create_anti_affinity_rule(self):
        node_list = self.driver.list_nodes()
        success = self.driver.ex_create_anti_affinity_rule([node_list[0], node_list[1]])
        self.assertTrue(success)

    def test_ex_create_anti_affinity_rule_TUPLE(self):
        node_list = self.driver.list_nodes()
        success = self.driver.ex_create_anti_affinity_rule((node_list[0], node_list[1]))
        self.assertTrue(success)

    def test_ex_create_anti_affinity_rule_TUPLE_STR(self):
        node_list = self.driver.list_nodes()
        success = self.driver.ex_create_anti_affinity_rule((node_list[0].id, node_list[1].id))
        self.assertTrue(success)

    def test_ex_create_anti_affinity_rule_FAIL_STR(self):
        node_list = 'string'
        with self.assertRaises(TypeError):
            self.driver.ex_create_anti_affinity_rule(node_list)

    def test_ex_create_anti_affinity_rule_FAIL_EXISTING(self):
        node_list = self.driver.list_nodes()
        DimensionDataMockHttp.type = 'FAIL_EXISTING'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_create_anti_affinity_rule((node_list[0], node_list[1]))

    def test_ex_delete_anti_affinity_rule(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        rule = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0]
        success = self.driver.ex_delete_anti_affinity_rule(rule)
        self.assertTrue(success)

    def test_ex_delete_anti_affinity_rule_STR(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        rule = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0]
        success = self.driver.ex_delete_anti_affinity_rule(rule.id)
        self.assertTrue(success)

    def test_ex_delete_anti_affinity_rule_FAIL(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        rule = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0]
        DimensionDataMockHttp.type = 'FAIL'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_delete_anti_affinity_rule(rule)

    def test_ex_list_anti_affinity_rules_NETWORK_DOMAIN(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        rules = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain)
        self.assertTrue(isinstance(rules, list))
        self.assertEqual(len(rules), 2)
        self.assertTrue(isinstance(rules[0].id, str))
        self.assertTrue(isinstance(rules[0].node_list, list))

    def test_ex_list_anti_affinity_rules_NETWORK(self):
        network = self.driver.list_networks()[0]
        rules = self.driver.ex_list_anti_affinity_rules(network=network)
        self.assertTrue(isinstance(rules, list))
        self.assertEqual(len(rules), 2)
        self.assertTrue(isinstance(rules[0].id, str))
        self.assertTrue(isinstance(rules[0].node_list, list))

    def test_ex_list_anti_affinity_rules_NODE(self):
        node = self.driver.list_nodes()[0]
        rules = self.driver.ex_list_anti_affinity_rules(node=node)
        self.assertTrue(isinstance(rules, list))
        self.assertEqual(len(rules), 2)
        self.assertTrue(isinstance(rules[0].id, str))
        self.assertTrue(isinstance(rules[0].node_list, list))

    def test_ex_list_anti_affinity_rules_PAGINATED(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        DimensionDataMockHttp.type = 'PAGINATED'
        rules = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain)
        self.assertTrue(isinstance(rules, list))
        self.assertEqual(len(rules), 4)
        self.assertTrue(isinstance(rules[0].id, str))
        self.assertTrue(isinstance(rules[0].node_list, list))

    def test_ex_list_anti_affinity_rules_ALLFILTERS(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        DimensionDataMockHttp.type = 'ALLFILTERS'
        rules = self.driver.ex_list_anti_affinity_rules(network_domain=net_domain, filter_id='FAKE_ID', filter_state='FAKE_STATE')
        self.assertTrue(isinstance(rules, list))
        self.assertEqual(len(rules), 2)
        self.assertTrue(isinstance(rules[0].id, str))
        self.assertTrue(isinstance(rules[0].node_list, list))

    def test_ex_list_anti_affinity_rules_BAD_ARGS(self):
        with self.assertRaises(ValueError):
            self.driver.ex_list_anti_affinity_rules(network='fake_network', network_domain='fake_network_domain')

    def test_ex_create_tag_key(self):
        success = self.driver.ex_create_tag_key('MyTestKey')
        self.assertTrue(success)

    def test_ex_create_tag_key_ALLPARAMS(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'ALLPARAMS'
        success = self.driver.ex_create_tag_key('MyTestKey', description="Test Key Desc.", value_required=False, display_on_report=False)
        self.assertTrue(success)

    def test_ex_create_tag_key_BADREQUEST(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'BADREQUEST'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_create_tag_key('MyTestKey')

    def test_ex_list_tag_keys(self):
        tag_keys = self.driver.ex_list_tag_keys()
        self.assertTrue(isinstance(tag_keys, list))
        self.assertTrue(isinstance(tag_keys[0], DimensionDataTagKey))
        self.assertTrue(isinstance(tag_keys[0].id, str))

    def test_ex_list_tag_keys_ALLFILTERS(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'ALLFILTERS'
        self.driver.ex_list_tag_keys(id='fake_id', name='fake_name', value_required=False, display_on_report=False)

    def test_ex_get_tag_by_id(self):
        tag = self.driver.ex_get_tag_key_by_id('d047c609-93d7-4bc5-8fc9-732c85840075')
        self.assertTrue(isinstance(tag, DimensionDataTagKey))

    def test_ex_get_tag_by_id_NOEXIST(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'NOEXIST'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_get_tag_key_by_id('d047c609-93d7-4bc5-8fc9-732c85840075')

    def test_ex_get_tag_by_name(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'SINGLE'
        tag = self.driver.ex_get_tag_key_by_name('LibcloudTest')
        self.assertTrue(isinstance(tag, DimensionDataTagKey))

    def test_ex_get_tag_by_name_NOEXIST(self):
        with self.assertRaises(ValueError):
            self.driver.ex_get_tag_key_by_name('LibcloudTest')

    def test_ex_modify_tag_key_NAME(self):
        tag_key = self.driver.ex_list_tag_keys()[0]
        DimensionDataMockHttp.type = 'NAME'
        success = self.driver.ex_modify_tag_key(tag_key, name='NewName')
        self.assertTrue(success)

    def test_ex_modify_tag_key_NOTNAME(self):
        tag_key = self.driver.ex_list_tag_keys()[0]
        DimensionDataMockHttp.type = 'NOTNAME'
        success = self.driver.ex_modify_tag_key(tag_key, description='NewDesc', value_required=False, display_on_report=True)
        self.assertTrue(success)

    def test_ex_modify_tag_key_NOCHANGE(self):
        tag_key = self.driver.ex_list_tag_keys()[0]
        DimensionDataMockHttp.type = 'NOCHANGE'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_modify_tag_key(tag_key)

    def test_ex_remove_tag_key(self):
        tag_key = self.driver.ex_list_tag_keys()[0]
        success = self.driver.ex_remove_tag_key(tag_key)
        self.assertTrue(success)

    def test_ex_remove_tag_key_NOEXIST(self):
        tag_key = self.driver.ex_list_tag_keys()[0]
        DimensionDataMockHttp.type = 'NOEXIST'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_remove_tag_key(tag_key)

    def test_ex_apply_tag_to_asset(self):
        node = self.driver.list_nodes()[0]
        success = self.driver.ex_apply_tag_to_asset(node, 'TagKeyName', 'FakeValue')
        self.assertTrue(success)

    def test_ex_apply_tag_to_asset_NOVALUE(self):
        node = self.driver.list_nodes()[0]
        DimensionDataMockHttp.type = 'NOVALUE'
        success = self.driver.ex_apply_tag_to_asset(node, 'TagKeyName')
        self.assertTrue(success)

    def test_ex_apply_tag_to_asset_NOTAGKEY(self):
        node = self.driver.list_nodes()[0]
        DimensionDataMockHttp.type = 'NOTAGKEY'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_apply_tag_to_asset(node, 'TagKeyNam')

    def test_ex_apply_tag_to_asset_BADASSETTYPE(self):
        network = self.driver.list_networks()[0]
        DimensionDataMockHttp.type = 'NOTAGKEY'
        with self.assertRaises(TypeError):
            self.driver.ex_apply_tag_to_asset(network, 'TagKeyNam')

    def test_ex_remove_tag_from_asset(self):
        node = self.driver.list_nodes()[0]
        success = self.driver.ex_remove_tag_from_asset(node, 'TagKeyName')
        self.assertTrue(success)

    def test_ex_remove_tag_from_asset_NOTAG(self):
        node = self.driver.list_nodes()[0]
        DimensionDataMockHttp.type = 'NOTAG'
        with self.assertRaises(DimensionDataAPIException):
            self.driver.ex_remove_tag_from_asset(node, 'TagKeyNam')

    def test_ex_list_tags(self):
        tags = self.driver.ex_list_tags()
        self.assertTrue(isinstance(tags, list))
        self.assertTrue(isinstance(tags[0], DimensionDataTag))
        self.assertTrue(len(tags) == 3)

    def test_ex_list_tags_ALLPARAMS(self):
        self.driver.connection._get_orgId()
        DimensionDataMockHttp.type = 'ALLPARAMS'
        tags = self.driver.ex_list_tags(asset_id='fake_asset_id', asset_type='fake_asset_type',
                                        location='fake_location', tag_key_name='fake_tag_key_name',
                                        tag_key_id='fake_tag_key_id', value='fake_value',
                                        value_required=False, display_on_report=False)
        self.assertTrue(isinstance(tags, list))
        self.assertTrue(isinstance(tags[0], DimensionDataTag))
        self.assertTrue(len(tags) == 3)

    def test_priv_location_to_location_id(self):
        location = self.driver.ex_get_location_by_id('NA9')
        self.assertEqual(
            self.driver._location_to_location_id(location),
            'NA9'
        )

    def test_priv_location_to_location_id_STR(self):
        self.assertEqual(
            self.driver._location_to_location_id('NA9'),
            'NA9'
        )

    def test_priv_location_to_location_id_TYPEERROR(self):
        with self.assertRaises(TypeError):
            self.driver._location_to_location_id([1, 2, 3])

    def test_priv_image_needs_auth_os_img(self):
        image = self.driver.list_images()[0]
        self.assertTrue(self.driver._image_needs_auth(image))

    def test_priv_image_needs_auth_os_img_STR(self):
        image = self.driver.list_images()[0].id
        self.assertTrue(self.driver._image_needs_auth(image))

    def test_priv_image_needs_auth_cust_img_windows(self):
        image = self.driver.ex_list_customer_images()[1]
        self.assertTrue(self.driver._image_needs_auth(image))

    def test_priv_image_needs_auth_cust_img_windows_STR(self):
        image = self.driver.ex_list_customer_images()[1].id
        self.assertTrue(self.driver._image_needs_auth(image))

    def test_priv_image_needs_auth_cust_img_linux(self):
        image = self.driver.ex_list_customer_images()[0]
        self.assertTrue(not self.driver._image_needs_auth(image))

    def test_priv_image_needs_auth_cust_img_linux_STR(self):
        image = self.driver.ex_list_customer_images()[0].id
        self.assertTrue(not self.driver._image_needs_auth(image))

    def test_summary_usage_report(self):
        report = self.driver.ex_summary_usage_report('2016-06-01', '2016-06-30')
        report_content = report
        self.assertEqual(len(report_content), 13)
        self.assertEqual(len(report_content[0]), 6)

    def test_detailed_usage_report(self):
        report = self.driver.ex_detailed_usage_report('2016-06-01', '2016-06-30')
        report_content = report
        self.assertEqual(len(report_content), 42)
        self.assertEqual(len(report_content[0]), 4)

    def test_audit_log_report(self):
        report = self.driver.ex_audit_log_report('2016-06-01', '2016-06-30')
        report_content = report
        self.assertEqual(len(report_content), 25)
        self.assertEqual(report_content[2][2], 'OEC_SYSTEM')

    def test_ex_list_ip_address_list(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        ip_list = self.driver.ex_list_ip_address_list(
            ex_network_domain=net_domain)
        self.assertTrue(isinstance(ip_list, list))
        self.assertEqual(len(ip_list), 4)
        self.assertTrue(isinstance(ip_list[0].name, str))
        self.assertTrue(isinstance(ip_list[0].description, str))
        self.assertTrue(isinstance(ip_list[0].ip_version, str))
        self.assertTrue(isinstance(ip_list[0].state, str))
        self.assertTrue(isinstance(ip_list[0].create_time, str))
        self.assertTrue(isinstance(ip_list[0].child_ip_address_lists, list))
        self.assertEqual(len(ip_list[1].child_ip_address_lists), 1)
        self.assertTrue(isinstance(ip_list[1].child_ip_address_lists[0].name,
                                   str))

    def test_ex_get_ip_address_list(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        DimensionDataMockHttp.type = 'FILTERBYNAME'
        ip_list = self.driver.ex_get_ip_address_list(
            ex_network_domain=net_domain.id,
            ex_ip_address_list_name='Test_IP_Address_List_3')
        self.assertTrue(isinstance(ip_list, list))
        self.assertEqual(len(ip_list), 1)
        self.assertTrue(isinstance(ip_list[0].name, str))
        self.assertTrue(isinstance(ip_list[0].description, str))
        self.assertTrue(isinstance(ip_list[0].ip_version, str))
        self.assertTrue(isinstance(ip_list[0].state, str))
        self.assertTrue(isinstance(ip_list[0].create_time, str))
        ips = ip_list[0].ip_address_collection
        self.assertEqual(len(ips), 3)
        self.assertTrue(isinstance(ips[0].begin, str))
        self.assertTrue(isinstance(ips[0].prefix_size, str))
        self.assertTrue(isinstance(ips[2].end, str))

    def test_ex_create_ip_address_list_FAIL(self):
        net_domain = self.driver.ex_list_network_domains()[0]

        with self.assertRaises(TypeError):
            self.driver.ex_create_ip_address_list(
                ex_network_domain=net_domain.id)

    def test_ex_create_ip_address_list(self):
        name = "Test_IP_Address_List_3"
        description = "Test Description"
        ip_version = "IPV4"
        child_ip_address_list_id = '0291ef78-4059-4bc1-b433-3f6ad698dc41'
        child_ip_address_list = DimensionDataChildIpAddressList(
            id=child_ip_address_list_id,
            name="test_child_ip_addr_list")
        net_domain = self.driver.ex_list_network_domains()[0]
        ip_address_1 = DimensionDataIpAddress(begin='190.2.2.100')
        ip_address_2 = DimensionDataIpAddress(begin='190.2.2.106',
                                              end='190.2.2.108')
        ip_address_3 = DimensionDataIpAddress(begin='190.2.2.0',
                                              prefix_size='24')
        ip_address_collection = [ip_address_1, ip_address_2,
                                 ip_address_3]

        # Create IP Address List
        success = self.driver.ex_create_ip_address_list(
            ex_network_domain=net_domain, name=name,
            ip_version=ip_version, description=description,
            ip_address_collection=ip_address_collection,
            child_ip_address_list=child_ip_address_list)

        self.assertTrue(success)

    def test_ex_create_ip_address_list_STR(self):
        name = "Test_IP_Address_List_3"
        description = "Test Description"
        ip_version = "IPV4"
        child_ip_address_list_id = '0291ef78-4059-4bc1-b433-3f6ad698dc41'
        net_domain = self.driver.ex_list_network_domains()[0]
        ip_address_1 = DimensionDataIpAddress(begin='190.2.2.100')
        ip_address_2 = DimensionDataIpAddress(begin='190.2.2.106',
                                              end='190.2.2.108')
        ip_address_3 = DimensionDataIpAddress(begin='190.2.2.0',
                                              prefix_size='24')
        ip_address_collection = [ip_address_1, ip_address_2,
                                 ip_address_3]

        # Create IP Address List
        success = self.driver.ex_create_ip_address_list(
            ex_network_domain=net_domain.id, name=name,
            ip_version=ip_version, description=description,
            ip_address_collection=ip_address_collection,
            child_ip_address_list=child_ip_address_list_id)

        self.assertTrue(success)

    def test_ex_edit_ip_address_list(self):
        ip_address_1 = DimensionDataIpAddress(begin='190.2.2.111')
        ip_address_collection = [ip_address_1]

        child_ip_address_list = DimensionDataChildIpAddressList(
            id='2221ef78-4059-4bc1-b433-3f6ad698dc41',
            name="test_child_ip_address_list edited")

        ip_address_list = DimensionDataIpAddressList(
            id='1111ef78-4059-4bc1-b433-3f6ad698d111',
            name="test ip address list edited",
            ip_version="IPv4", description="test",
            ip_address_collection=ip_address_collection,
            child_ip_address_lists=child_ip_address_list,
            state="NORMAL",
            create_time='2015-09-29T02:49:45'
        )

        success = self.driver.ex_edit_ip_address_list(
            ex_ip_address_list=ip_address_list,
            description="test ip address list",
            ip_address_collection=ip_address_collection,
            child_ip_address_lists=child_ip_address_list
        )

        self.assertTrue(success)

    def test_ex_edit_ip_address_list_STR(self):
        ip_address_1 = DimensionDataIpAddress(begin='190.2.2.111')
        ip_address_collection = [ip_address_1]

        child_ip_address_list = DimensionDataChildIpAddressList(
            id='2221ef78-4059-4bc1-b433-3f6ad698dc41',
            name="test_child_ip_address_list edited")

        success = self.driver.ex_edit_ip_address_list(
            ex_ip_address_list='84e34850-595d- 436e-a885-7cd37edb24a4',
            description="test ip address list",
            ip_address_collection=ip_address_collection,
            child_ip_address_lists=child_ip_address_list
        )

        self.assertTrue(success)

    def test_ex_delete_ip_address_list(self):
        child_ip_address_list = DimensionDataChildIpAddressList(
            id='2221ef78-4059-4bc1-b433-3f6ad698dc41',
            name="test_child_ip_address_list edited")

        ip_address_list = DimensionDataIpAddressList(
            id='1111ef78-4059-4bc1-b433-3f6ad698d111',
            name="test ip address list edited",
            ip_version="IPv4", description="test",
            ip_address_collection=None,
            child_ip_address_lists=child_ip_address_list,
            state="NORMAL",
            create_time='2015-09-29T02:49:45'
        )

        success = self.driver.ex_delete_ip_address_list(
            ex_ip_address_list=ip_address_list)
        self.assertTrue(success)

    def test_ex_delete_ip_address_list_STR(self):
        success = self.driver.ex_delete_ip_address_list(
            ex_ip_address_list='111ef78-4059-4bc1-b433-3f6ad698d111')
        self.assertTrue(success)

    def test_ex_list_portlist(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        portlist = self.driver.ex_list_portlist(
            ex_network_domain=net_domain)
        self.assertTrue(isinstance(portlist, list))
        self.assertEqual(len(portlist), 3)
        self.assertTrue(isinstance(portlist[0].name, str))
        self.assertTrue(isinstance(portlist[0].description, str))
        self.assertTrue(isinstance(portlist[0].state, str))
        self.assertTrue(isinstance(portlist[0].port_collection, list))
        self.assertTrue(isinstance(portlist[0].port_collection[0].begin, str))
        self.assertTrue(isinstance(portlist[0].port_collection[0].end, str))
        self.assertTrue(isinstance(portlist[0].child_portlist_list, list))
        self.assertTrue(isinstance(portlist[0].child_portlist_list[0].id,
                                   str))
        self.assertTrue(isinstance(portlist[0].child_portlist_list[0].name,
                                   str))
        self.assertTrue(isinstance(portlist[0].create_time, str))

    def test_ex_get_port_list(self):
        net_domain = self.driver.ex_list_network_domains()[0]

        portlist_id = self.driver.ex_list_portlist(
            ex_network_domain=net_domain)[0].id

        portlist = self.driver.ex_get_portlist(
            ex_portlist_id=portlist_id)
        self.assertTrue(isinstance(portlist, DimensionDataPortList))

        self.assertTrue(isinstance(portlist.name, str))
        self.assertTrue(isinstance(portlist.description, str))
        self.assertTrue(isinstance(portlist.state, str))
        self.assertTrue(isinstance(portlist.port_collection, list))
        self.assertTrue(isinstance(portlist.port_collection[0].begin, str))
        self.assertTrue(isinstance(portlist.port_collection[0].end, str))
        self.assertTrue(isinstance(portlist.child_portlist_list, list))
        self.assertTrue(isinstance(portlist.child_portlist_list[0].id,
                                   str))
        self.assertTrue(isinstance(portlist.child_portlist_list[0].name,
                                   str))
        self.assertTrue(isinstance(portlist.create_time, str))

    def test_ex_get_portlist_STR(self):
        net_domain = self.driver.ex_list_network_domains()[0]

        portlist = self.driver.ex_list_portlist(
            ex_network_domain=net_domain)[0]

        port_list = self.driver.ex_get_portlist(
            ex_portlist_id=portlist.id)
        self.assertTrue(isinstance(port_list, DimensionDataPortList))

        self.assertTrue(isinstance(port_list.name, str))
        self.assertTrue(isinstance(port_list.description, str))
        self.assertTrue(isinstance(port_list.state, str))
        self.assertTrue(isinstance(port_list.port_collection, list))
        self.assertTrue(isinstance(port_list.port_collection[0].begin, str))
        self.assertTrue(isinstance(port_list.port_collection[0].end, str))
        self.assertTrue(isinstance(port_list.child_portlist_list, list))
        self.assertTrue(isinstance(port_list.child_portlist_list[0].id,
                                   str))
        self.assertTrue(isinstance(port_list.child_portlist_list[0].name,
                                   str))
        self.assertTrue(isinstance(port_list.create_time, str))

    def test_ex_create_portlist_NOCHILDPORTLIST(self):
        name = "Test_Port_List"
        description = "Test Description"

        net_domain = self.driver.ex_list_network_domains()[0]

        port_1 = DimensionDataPort(begin='8080')
        port_2 = DimensionDataIpAddress(begin='8899',
                                              end='9023')
        port_collection = [port_1, port_2]

        # Create IP Address List
        success = self.driver.ex_create_portlist(
            ex_network_domain=net_domain, name=name,
            description=description,
            port_collection=port_collection
        )

        self.assertTrue(success)

    def test_ex_create_portlist(self):
        name = "Test_Port_List"
        description = "Test Description"

        net_domain = self.driver.ex_list_network_domains()[0]

        port_1 = DimensionDataPort(begin='8080')
        port_2 = DimensionDataIpAddress(begin='8899',
                                              end='9023')
        port_collection = [port_1, port_2]

        child_port_1 = DimensionDataChildPortList(
            id="333174a2-ae74-4658-9e56-50fc90e086cf", name='test port 1')
        child_port_2 = DimensionDataChildPortList(
            id="311174a2-ae74-4658-9e56-50fc90e04444", name='test port 2')
        child_ports = [child_port_1, child_port_2]

        # Create IP Address List
        success = self.driver.ex_create_portlist(
            ex_network_domain=net_domain, name=name,
            description=description,
            port_collection=port_collection,
            child_portlist_list=child_ports
        )

        self.assertTrue(success)

    def test_ex_create_portlist_STR(self):
        name = "Test_Port_List"
        description = "Test Description"

        net_domain = self.driver.ex_list_network_domains()[0]

        port_1 = DimensionDataPort(begin='8080')
        port_2 = DimensionDataIpAddress(begin='8899',
                                              end='9023')
        port_collection = [port_1, port_2]

        child_port_1 = DimensionDataChildPortList(
            id="333174a2-ae74-4658-9e56-50fc90e086cf", name='test port 1')
        child_port_2 = DimensionDataChildPortList(
            id="311174a2-ae74-4658-9e56-50fc90e04444", name='test port 2')
        child_ports_ids = [child_port_1.id, child_port_2.id]

        # Create IP Address List
        success = self.driver.ex_create_portlist(
            ex_network_domain=net_domain.id, name=name,
            description=description,
            port_collection=port_collection,
            child_portlist_list=child_ports_ids
        )

        self.assertTrue(success)

    def test_ex_edit_portlist(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        portlist = self.driver.ex_list_portlist(net_domain)[0]

        description = "Test Description"

        port_1 = DimensionDataPort(begin='8080')
        port_2 = DimensionDataIpAddress(begin='8899',
                                        end='9023')
        port_collection = [port_1, port_2]

        child_port_1 = DimensionDataChildPortList(
            id="333174a2-ae74-4658-9e56-50fc90e086cf", name='test port 1')
        child_port_2 = DimensionDataChildPortList(
            id="311174a2-ae74-4658-9e56-50fc90e04444", name='test port 2')
        child_ports = [child_port_1.id, child_port_2.id]

        # Create IP Address List
        success = self.driver.ex_edit_portlist(
            ex_portlist=portlist,
            description=description,
            port_collection=port_collection,
            child_portlist_list=child_ports
        )
        self.assertTrue(success)

    def test_ex_edit_portlist_STR(self):
        portlist_id = "484174a2-ae74-4658-9e56-50fc90e086cf"
        description = "Test Description"

        port_1 = DimensionDataPort(begin='8080')
        port_2 = DimensionDataIpAddress(begin='8899',
                                        end='9023')
        port_collection = [port_1, port_2]

        child_port_1 = DimensionDataChildPortList(
            id="333174a2-ae74-4658-9e56-50fc90e086cf", name='test port 1')
        child_port_2 = DimensionDataChildPortList(
            id="311174a2-ae74-4658-9e56-50fc90e04444", name='test port 2')
        child_ports_ids = [child_port_1.id, child_port_2.id]

        # Create IP Address List
        success = self.driver.ex_edit_portlist(
            ex_portlist=portlist_id,
            description=description,
            port_collection=port_collection,
            child_portlist_list=child_ports_ids
        )
        self.assertTrue(success)

    def test_ex_delete_portlist(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        portlist = self.driver.ex_list_portlist(net_domain)[0]

        success = self.driver.ex_delete_portlist(
            ex_portlist=portlist)
        self.assertTrue(success)

    def test_ex_delete_portlist_STR(self):
        net_domain = self.driver.ex_list_network_domains()[0]
        portlist = self.driver.ex_list_portlist(net_domain)[0]

        success = self.driver.ex_delete_portlist(
            ex_portlist=portlist.id)
        self.assertTrue(success)


class InvalidRequestError(Exception):
    def __init__(self, tag):
        super(InvalidRequestError, self).__init__("Invalid Request - %s" % tag)


class DimensionDataMockRawResponse(MockRawResponse):
    fixtures = ComputeFileFixtures('dimensiondata')

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_report_usage(self, method, url, body, headers):
        body = self.fixtures.load(
            'summary_usage_report.csv'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_report_usageDetailed(self, method, url, body, headers):
        body = self.fixtures.load(
            'detailed_usage_report.csv'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_auditlog(self, method, url, body, headers):
        body = self.fixtures.load(
            'audit_log.csv'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])


class DimensionDataMockHttp(StorageMockHttp, MockHttp):

    fixtures = ComputeFileFixtures('dimensiondata')

    def _oec_0_9_myaccount_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_PAGINATED(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_ALLFILTERS(self, method, url, body, headers):
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

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkWithLocation_NA9(self, method, url, body, headers):
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

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_create.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_FAIL_EXISTING(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_create_FAIL.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_07e3621a_a920_4a9a_943c_d8021f27f418(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_delete.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_07e3621a_a920_4a9a_943c_d8021f27f418_FAIL(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_antiAffinityRule_delete_FAIL.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_deleteServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_deleteServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_rebootServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_rebootServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server(self, method, url, body, headers):
        if url.endswith('datacenterId=NA3'):
            body = self.fixtures.load(
                'server_server_NA3.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGESIZE50(self, method, url, body, headers):
        if not url.endswith('pageSize=50'):
            raise ValueError("pageSize is not set as expected")
        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_paginated_empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGED_THEN_EMPTY(self, method, url, body, headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_server_paginated_empty.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_server_paginated.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGINATED(self, method, url, body, headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_server.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_server_paginated.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGINATEDEMPTY(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_paginated_empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_loc'
            elif key == 'networkId':
                assert value == 'fake_network'
            elif key == 'networkDomainId':
                assert value == 'fake_network_domain'
            elif key == 'vlanId':
                assert value == 'fake_vlan'
            elif key == 'ipv6':
                assert value == 'fake_ipv6'
            elif key == 'privateIpv4':
                assert value == 'fake_ipv4'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            elif key == 'started':
                assert value == 'True'
            elif key == 'deployed':
                assert value == 'True'
            elif key == 'sourceImageId':
                assert value == 'fake_image'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_antiAffinityRule_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'id':
                assert value == 'FAKE_ID'
            elif key == 'state':
                assert value == 'FAKE_STATE'
            elif key == 'pageSize':
                assert value == '250'
            elif key == 'networkDomainId':
                pass
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'server_antiAffinityRule_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule_PAGINATED(self, method, url, body, headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_antiAffinityRule_list.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_antiAffinityRule_list_PAGINATED.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter(self, method, url, body, headers):
        if url.endswith('id=NA9'):
            body = self.fixtures.load(
                'infrastructure_datacenter_NA9.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'infrastructure_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter_ALLFILTERS(self, method, url, body, headers):
        if url.endswith('id=NA9'):
            body = self.fixtures.load(
                'infrastructure_datacenter_NA9.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'infrastructure_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_updateVmwareTools(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}updateVmwareTools":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_updateVmwareTools.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_startServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_startServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_shutdownServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_shutdownServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_resetServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}resetServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_resetServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_powerOffServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_powerOffServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_11_INPROGRESS(
            self, method, url, body, headers):
        body = self.fixtures.load('server_GetServer.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_networkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'type':
                assert value == 'fake_plan'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'network_networkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_vlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'networkDomainId':
                assert value == 'fake_network_domain'
            elif key == 'ipv6Address':
                assert value == 'fake_ipv6'
            elif key == 'privateIpv4Address':
                assert value == 'fake_ipv4'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'network_vlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployServer":
            raise InvalidRequestError(request.tag)

        # Make sure the we either have a network tag with an IP or networkId
        # Or Network info with a primary nic that has privateip or vlanid
        network = request.find(fixxpath('network', TYPES_URN))
        network_info = request.find(fixxpath('networkInfo', TYPES_URN))
        if network is not None:
            if network_info is not None:
                raise InvalidRequestError("Request has both MCP1 and MCP2 values")
            ipv4 = findtext(network, 'privateIpv4', TYPES_URN)
            networkId = findtext(network, 'networkId', TYPES_URN)
            if ipv4 is None and networkId is None:
                raise InvalidRequestError('Invalid request MCP1 requests need privateIpv4 or networkId')
        elif network_info is not None:
            if network is not None:
                raise InvalidRequestError("Request has both MCP1 and MCP2 values")
            primary_nic = network_info.find(fixxpath('primaryNic', TYPES_URN))
            ipv4 = findtext(primary_nic, 'privateIpv4', TYPES_URN)
            vlanId = findtext(primary_nic, 'vlanId', TYPES_URN)
            if ipv4 is None and vlanId is None:
                raise InvalidRequestError('Invalid request MCP2 requests need privateIpv4 or vlanId')
        else:
            raise InvalidRequestError('Invalid request, does not have network or network_info in XML')

        body = self.fixtures.load(
            'server_deployServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deployNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be_ALLFILTERS(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deployVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_0e56433f_d808_4669_821d_812769517ff8(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_vlan_0e56433f_d808_4669_821d_812769517ff8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_expandVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}expandVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_expandVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_addPublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addPublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_addPublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_publicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_removePublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removePublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_removePublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_firewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_createFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_createNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_natRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_addNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removeNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_removeNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_disableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}disableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_disableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_enableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}enableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_enableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeServerMonitoringPlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}changeServerMonitoringPlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_changeServerMonitoringPlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_c14b1a46_2428_44c1_9c1a_b20e6418d08c(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_c14b1a46_2428_44c1_9c1a_b20e6418d08c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_6b4fb0c7_a57b_4f58_b59c_9958f94f971a(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_6b4fb0c7_a57b_4f58_b59c_9958f94f971a.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_FAKE_IMAGE_ID(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_customerImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_customerImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_customerImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_FAKE_IMAGE_ID(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_customerImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_reconfigureServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}reconfigureServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_reconfigureServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_cleanServer(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_cleanServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addDisk(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_addDisk.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeDisk(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_removeDisk.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is not None:
            raise ValueError("Default description for a tag should be blank")
        if value_required is None or value_required != 'true':
            raise ValueError("Default valueRequired should be true")
        if display_on_report is None or display_on_report != 'true':
            raise ValueError("Default displayOnReport should be true")

        body = self.fixtures.load(
            'tag_createTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey_ALLPARAMS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is None:
            raise ValueError("Description should have a value")
        if value_required is None or value_required != 'false':
            raise ValueError("valueRequired should be false")
        if display_on_report is None or display_on_report != 'false':
            raise ValueError("displayOnReport should be false")

        body = self.fixtures.load(
            'tag_createTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey_BADREQUEST(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_createTagKey_BADREQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_SINGLE(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_list_SINGLE.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'id':
                assert value == 'fake_id'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'valueRequired':
                assert value == 'false'
            elif key == 'displayOnReport':
                assert value == 'false'
            elif key == 'pageSize':
                assert value == '250'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'tag_tagKey_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_d047c609_93d7_4bc5_8fc9_732c85840075(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_5ab77f5f_5aa9_426f_8459_4eab34e03d54.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_d047c609_93d7_4bc5_8fc9_732c85840075_NOEXIST(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_5ab77f5f_5aa9_426f_8459_4eab34e03d54_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NAME(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is not None:
            raise ValueError("Description should be empty")
        if value_required is not None:
            raise ValueError("valueRequired should be empty")
        if display_on_report is not None:
            raise ValueError("displayOnReport should be empty")
        body = self.fixtures.load(
            'tag_editTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NOTNAME(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is not None:
            raise ValueError("Name should be empty")
        if description is None:
            raise ValueError("Description should not be empty")
        if value_required is None:
            raise ValueError("valueRequired should not be empty")
        if display_on_report is None:
            raise ValueError("displayOnReport should not be empty")
        body = self.fixtures.load(
            'tag_editTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NOCHANGE(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_editTagKey_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_deleteTagKey(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteTagKey":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'tag_deleteTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_deleteTagKey_NOEXIST(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_deleteTagKey_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}applyTags":
            raise InvalidRequestError(request.tag)
        asset_type = findtext(request, 'assetType', TYPES_URN)
        asset_id = findtext(request, 'assetId', TYPES_URN)
        tag = request.find(fixxpath('tag', TYPES_URN))
        tag_key_name = findtext(tag, 'tagKeyName', TYPES_URN)
        value = findtext(tag, 'value', TYPES_URN)
        if asset_type is None:
            raise ValueError("assetType should not be empty")
        if asset_id is None:
            raise ValueError("assetId should not be empty")
        if tag_key_name is None:
            raise ValueError("tagKeyName should not be empty")
        if value is None:
            raise ValueError("value should not be empty")

        body = self.fixtures.load(
            'tag_applyTags.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags_NOVALUE(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}applyTags":
            raise InvalidRequestError(request.tag)
        asset_type = findtext(request, 'assetType', TYPES_URN)
        asset_id = findtext(request, 'assetId', TYPES_URN)
        tag = request.find(fixxpath('tag', TYPES_URN))
        tag_key_name = findtext(tag, 'tagKeyName', TYPES_URN)
        value = findtext(tag, 'value', TYPES_URN)
        if asset_type is None:
            raise ValueError("assetType should not be empty")
        if asset_id is None:
            raise ValueError("assetId should not be empty")
        if tag_key_name is None:
            raise ValueError("tagKeyName should not be empty")
        if value is not None:
            raise ValueError("value should be empty")

        body = self.fixtures.load(
            'tag_applyTags.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags_NOTAGKEY(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_applyTags_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_removeTags(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removeTags":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'tag_removeTag.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_removeTags_NOTAG(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_removeTag_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tag(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tag_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tag_ALLPARAMS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'assetId':
                assert value == 'fake_asset_id'
            elif key == 'assetType':
                assert value == 'fake_asset_type'
            elif key == 'valueRequired':
                assert value == 'false'
            elif key == 'displayOnReport':
                assert value == 'false'
            elif key == 'pageSize':
                assert value == '250'
            elif key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'value':
                assert value == 'fake_value'
            elif key == 'tagKeyName':
                assert value == 'fake_tag_key_name'
            elif key == 'tagKeyId':
                assert value == 'fake_tag_key_id'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'tag_tag_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_ipAddressList(
            self, method, url, body, headers):
        body = self.fixtures.load('ip_address_lists.xml')
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_ipAddressList_FILTERBYNAME(
            self, method, url, body, headers):
        body = self.fixtures.load('ip_address_lists_FILTERBYNAME.xml')
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createIpAddressList(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "createIpAddressList":
            raise InvalidRequestError(request.tag)

        net_domain = findtext(request, 'networkDomainId', TYPES_URN)
        if net_domain is None:
            raise ValueError("Network Domain should not be empty")

        name = findtext(request, 'name', TYPES_URN)
        if name is None:
            raise ValueError("Name should not be empty")

        ip_version = findtext(request, 'ipVersion', TYPES_URN)
        if ip_version is None:
            raise ValueError("IP Version should not be empty")

        ip_address_col_required = findall(request, 'ipAddress', TYPES_URN)
        child_ip_address_required = findall(request, 'childIpAddressListId',
                                            TYPES_URN)

        if 0 == len(ip_address_col_required) and \
                0 == len(child_ip_address_required):
            raise ValueError("At least one ipAddress element or "
                             "one childIpAddressListId element must be "
                             "provided.")

        if ip_address_col_required[0].get('begin') is None:
            raise ValueError("IP Address should not be empty")

        body = self.fixtures.load(
            'ip_address_list_create.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editIpAddressList(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "editIpAddressList":
            raise InvalidRequestError(request.tag)

        ip_address_list = request.get('id')
        if ip_address_list is None:
            raise ValueError("IpAddressList ID should not be empty")

        name = findtext(request, 'name', TYPES_URN)
        if name is not None:
            raise ValueError("Name should not exists in request")

        ip_version = findtext(request, 'ipVersion', TYPES_URN)
        if ip_version is not None:
            raise ValueError("IP Version should not exists in request")

        ip_address_col_required = findall(request, 'ipAddress', TYPES_URN)
        child_ip_address_required = findall(request, 'childIpAddressListId',
                                            TYPES_URN)

        if 0 == len(ip_address_col_required) and \
                0 == len(child_ip_address_required):
            raise ValueError("At least one ipAddress element or "
                             "one childIpAddressListId element must be "
                             "provided.")

        if ip_address_col_required[0].get('begin') is None:
            raise ValueError("IP Address should not be empty")

        body = self.fixtures.load(
            'ip_address_list_edit.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteIpAddressList(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "deleteIpAddressList":
            raise InvalidRequestError(request.tag)

        ip_address_list = request.get('id')
        if ip_address_list is None:
            raise ValueError("IpAddressList ID should not be empty")

        body = self.fixtures.load(
            'ip_address_list_delete.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_portList(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'port_list_lists.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_portList_c8c92ea3_2da8_4d51_8153_f39bec794d69(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'port_list_get.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createPortList(
            self, method, url, body, headers):

        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "createPortList":
            raise InvalidRequestError(request.tag)

        net_domain = findtext(request, 'networkDomainId', TYPES_URN)
        if net_domain is None:
            raise ValueError("Network Domain should not be empty")

        ports_required = findall(request, 'port', TYPES_URN)
        child_port_list_required = findall(request, 'childPortListId',
                                           TYPES_URN)

        if 0 == len(ports_required) and \
                0 == len(child_port_list_required):
            raise ValueError("At least one port element or one "
                             "childPortListId element must be provided")

        if ports_required[0].get('begin') is None:
            raise ValueError("PORT begin value should not be empty")

        body = self.fixtures.load(
            'port_list_create.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editPortList(
            self, method, url, body, headers):

        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "editPortList":
            raise InvalidRequestError(request.tag)

        ports_required = findall(request, 'port', TYPES_URN)
        child_port_list_required = findall(request, 'childPortListId',
                                           TYPES_URN)

        if 0 == len(ports_required) and \
                0 == len(child_port_list_required):
            raise ValueError("At least one port element or one "
                             "childPortListId element must be provided")

        if ports_required[0].get('begin') is None:
            raise ValueError("PORT begin value should not be empty")

        body = self.fixtures.load(
            'port_list_edit.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deletePortList(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "deletePortList":
            raise InvalidRequestError(request.tag)

        port_list = request.get('id')
        if port_list is None:
            raise ValueError("Port List ID should not be empty")

        body = self.fixtures.load(
            'ip_address_list_delete.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

if __name__ == '__main__':
    sys.exit(unittest.main())
