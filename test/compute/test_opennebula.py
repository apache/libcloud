# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
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
OpenNebula.org test suite.
"""

__docformat__ = 'epytext'

import unittest
import sys

from libcloud.utils.py3 import httplib

from libcloud.compute.base import Node, NodeImage, NodeSize, NodeState
from libcloud.compute.drivers.opennebula import *

from test.file_fixtures import ComputeFileFixtures
from test.compute import TestCaseMixin
from test import MockHttp

from test.secrets import OPENNEBULA_PARAMS


class OpenNebula_1_4_Tests(unittest.TestCase, TestCaseMixin):
    """
    OpenNebula.org test suite for OpenNebula v1.4.
    """

    def setUp(self):
        """
        Setup test environment.
        """
        OpenNebulaNodeDriver.connectionCls.conn_classes = (
            OpenNebula_1_4_MockHttp, OpenNebula_1_4_MockHttp)
        self.driver = OpenNebulaNodeDriver(*OPENNEBULA_PARAMS + ('1.4',))

    def test_create_node(self):
        """
        Test create_node functionality.
        """
        image = NodeImage(id=5, name='Ubuntu 9.04 LAMP', driver=self.driver)
        size = NodeSize(id=1, name='small', ram=None, disk=None,
                        bandwidth=None, price=None, driver=self.driver)
        networks = list()
        networks.append(OpenNebulaNetwork(id=5, name='Network 5',
                        address='192.168.0.0', size=256, driver=self.driver))
        networks.append(OpenNebulaNetwork(id=15, name='Network 15',
                        address='192.168.1.0', size=256, driver=self.driver))

        node = self.driver.create_node(name='Compute 5', image=image,
                                       size=size, networks=networks)

        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'Compute 5')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].name, None)
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].address, '192.168.0.1')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[1].name, None)
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].address, '192.168.1.1')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.private_ips, [])
        self.assertEqual(node.image.id, '5')
        self.assertEqual(node.image.extra['dev'], 'sda1')

    def test_destroy_node(self):
        """
        Test destroy_node functionality.
        """
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_reboot_node(self):
        """
        Test reboot_node functionality.
        """
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_list_nodes(self):
        """
        Test list_nodes functionality.
        """
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 2)
        node = nodes[0]
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'Compute 5')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].name, None)
        self.assertEqual(node.public_ips[0].address, '192.168.0.1')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].name, None)
        self.assertEqual(node.public_ips[1].address, '192.168.1.1')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.private_ips, [])
        self.assertEqual(node.image.id, '5')
        self.assertEqual(node.image.extra['dev'], 'sda1')
        node = nodes[1]
        self.assertEqual(node.id, '15')
        self.assertEqual(node.name, 'Compute 15')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].name, None)
        self.assertEqual(node.public_ips[0].address, '192.168.0.2')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].name, None)
        self.assertEqual(node.public_ips[1].address, '192.168.1.2')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.private_ips, [])
        self.assertEqual(node.image.id, '15')
        self.assertEqual(node.image.extra['dev'], 'sda1')

    def test_list_images(self):
        """
        Test list_images functionality.
        """
        images = self.driver.list_images()

        self.assertEqual(len(images), 2)
        image = images[0]
        self.assertEqual(image.id, '5')
        self.assertEqual(image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(image.extra['size'], '2048')
        self.assertEqual(image.extra['url'],
                         'file:///images/ubuntu/jaunty.img')
        image = images[1]
        self.assertEqual(image.id, '15')
        self.assertEqual(image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(image.extra['size'], '2048')
        self.assertEqual(image.extra['url'],
                         'file:///images/ubuntu/jaunty.img')

    def test_list_sizes(self):
        """
        Test list_sizes functionality.
        """
        sizes = self.driver.list_sizes()

        self.assertEqual(len(sizes), 3)
        size = sizes[0]
        self.assertEqual(size.id, '1')
        self.assertEqual(size.name, 'small')
        self.assertEqual(size.ram, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)
        size = sizes[1]
        self.assertEqual(size.id, '2')
        self.assertEqual(size.name, 'medium')
        self.assertEqual(size.ram, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)
        size = sizes[2]
        self.assertEqual(size.id, '3')
        self.assertEqual(size.name, 'large')
        self.assertEqual(size.ram, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)

    def test_list_locations(self):
        """
        Test list_locations functionality.
        """
        locations = self.driver.list_locations()

        self.assertEqual(len(locations), 1)
        location = locations[0]
        self.assertEqual(location.id, '0')
        self.assertEqual(location.name, '')
        self.assertEqual(location.country, '')

    def test_ex_list_networks(self):
        """
        Test ex_list_networks functionality.
        """
        networks = self.driver.ex_list_networks()

        self.assertEqual(len(networks), 2)
        network = networks[0]
        self.assertEqual(network.id, '5')
        self.assertEqual(network.name, 'Network 5')
        self.assertEqual(network.address, '192.168.0.0')
        self.assertEqual(network.size, '256')
        network = networks[1]
        self.assertEqual(network.id, '15')
        self.assertEqual(network.name, 'Network 15')
        self.assertEqual(network.address, '192.168.1.0')
        self.assertEqual(network.size, '256')

    def test_node_action(self):
        """
        Test ex_node_action functionality.
        """
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.ex_node_action(node, ACTION.STOP)
        self.assertTrue(ret)


class OpenNebula_2_0_Tests(unittest.TestCase, TestCaseMixin):
    """
    OpenNebula.org test suite for OpenNebula v2.0 through v3.2.
    """

    def setUp(self):
        """
        Setup test environment.
        """
        OpenNebulaNodeDriver.connectionCls.conn_classes = (
            OpenNebula_2_0_MockHttp, OpenNebula_2_0_MockHttp)
        self.driver = OpenNebulaNodeDriver(*OPENNEBULA_PARAMS + ('2.0',))

    def test_create_node(self):
        """
        Test create_node functionality.
        """
        image = NodeImage(id=5, name='Ubuntu 9.04 LAMP', driver=self.driver)
        size = OpenNebulaNodeSize(id=1, name='small', ram=1024, cpu=1,
                                  disk=None, bandwidth=None, price=None,
                                  driver=self.driver)
        networks = list()
        networks.append(OpenNebulaNetwork(id=5, name='Network 5',
                        address='192.168.0.0', size=256, driver=self.driver))
        networks.append(OpenNebulaNetwork(id=15, name='Network 15',
                        address='192.168.1.0', size=256, driver=self.driver))
        context = {'hostname': 'compute-5'}

        node = self.driver.create_node(name='Compute 5', image=image,
                                       size=size, networks=networks,
                                       context=context)

        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'Compute 5')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].name, 'Network 5')
        self.assertEqual(node.public_ips[0].address, '192.168.0.1')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[0].extra['mac'], '02:00:c0:a8:00:01')
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].name, 'Network 15')
        self.assertEqual(node.public_ips[1].address, '192.168.1.1')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.public_ips[1].extra['mac'], '02:00:c0:a8:01:01')
        self.assertEqual(node.private_ips, [])
        self.assertTrue(len([size for size in self.driver.list_sizes() \
                        if size.id == node.size.id]) == 1)
        self.assertEqual(node.image.id, '5')
        self.assertEqual(node.image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(node.image.extra['type'], 'DISK')
        self.assertEqual(node.image.extra['target'], 'hda')
        context = node.extra['context']
        self.assertEqual(context['hostname'], 'compute-5')

    def test_destroy_node(self):
        """
        Test destroy_node functionality.
        """
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_reboot_node(self):
        """
        Test reboot_node functionality.
        """
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_list_nodes(self):
        """
        Test list_nodes functionality.
        """
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 2)
        node = nodes[0]
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'Compute 5')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].name, 'Network 5')
        self.assertEqual(node.public_ips[0].address, '192.168.0.1')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[0].extra['mac'], '02:00:c0:a8:00:01')
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].name, 'Network 15')
        self.assertEqual(node.public_ips[1].address, '192.168.1.1')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.public_ips[1].extra['mac'], '02:00:c0:a8:01:01')
        self.assertEqual(node.private_ips, [])
        self.assertTrue(len([size for size in self.driver.list_sizes() \
                        if size.id == node.size.id]) == 1)
        self.assertEqual(node.image.id, '5')
        self.assertEqual(node.image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(node.image.extra['type'], 'DISK')
        self.assertEqual(node.image.extra['target'], 'hda')
        context = node.extra['context']
        self.assertEqual(context['hostname'], 'compute-5')
        node = nodes[1]
        self.assertEqual(node.id, '15')
        self.assertEqual(node.name, 'Compute 15')
        self.assertEqual(node.state,
                         OpenNebulaNodeDriver.NODE_STATE_MAP['RUNNING'])
        self.assertEqual(node.public_ips[0].id, '5')
        self.assertEqual(node.public_ips[0].name, 'Network 5')
        self.assertEqual(node.public_ips[0].address, '192.168.0.2')
        self.assertEqual(node.public_ips[0].size, 1)
        self.assertEqual(node.public_ips[0].extra['mac'], '02:00:c0:a8:00:02')
        self.assertEqual(node.public_ips[1].id, '15')
        self.assertEqual(node.public_ips[1].name, 'Network 15')
        self.assertEqual(node.public_ips[1].address, '192.168.1.2')
        self.assertEqual(node.public_ips[1].size, 1)
        self.assertEqual(node.public_ips[1].extra['mac'], '02:00:c0:a8:01:02')
        self.assertEqual(node.private_ips, [])
        self.assertTrue(len([size for size in self.driver.list_sizes() \
                        if size.id == node.size.id]) == 1)
        self.assertEqual(node.image.id, '15')
        self.assertEqual(node.image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(node.image.extra['type'], 'DISK')
        self.assertEqual(node.image.extra['target'], 'hda')
        context = node.extra['context']
        self.assertEqual(context['hostname'], 'compute-15')

    def test_list_images(self):
        """
        Test list_images functionality.
        """
        images = self.driver.list_images()

        self.assertEqual(len(images), 2)
        image = images[0]
        self.assertEqual(image.id, '5')
        self.assertEqual(image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(image.extra['description'],
                         'Ubuntu 9.04 LAMP Description')
        self.assertEqual(image.extra['type'], 'OS')
        self.assertEqual(image.extra['size'], '2048')
        image = images[1]
        self.assertEqual(image.id, '15')
        self.assertEqual(image.name, 'Ubuntu 9.04 LAMP')
        self.assertEqual(image.extra['description'],
                         'Ubuntu 9.04 LAMP Description')
        self.assertEqual(image.extra['type'], 'OS')
        self.assertEqual(image.extra['size'], '2048')

    def test_list_sizes(self):
        """
        Test list_sizes functionality.
        """
        sizes = self.driver.list_sizes()

        self.assertEqual(len(sizes), 4)
        size = sizes[0]
        self.assertEqual(size.id, '1')
        self.assertEqual(size.name, 'small')
        self.assertEqual(size.ram, 1024)
        self.assertTrue(size.cpu is None or isinstance(size.cpu, int))
        self.assertTrue(size.vcpu is None or isinstance(size.vcpu, int))
        self.assertEqual(size.cpu, 1)
        self.assertEqual(size.vcpu, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)
        size = sizes[1]
        self.assertEqual(size.id, '2')
        self.assertEqual(size.name, 'medium')
        self.assertEqual(size.ram, 4096)
        self.assertTrue(size.cpu is None or isinstance(size.cpu, int))
        self.assertTrue(size.vcpu is None or isinstance(size.vcpu, int))
        self.assertEqual(size.cpu, 4)
        self.assertEqual(size.vcpu, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)
        size = sizes[2]
        self.assertEqual(size.id, '3')
        self.assertEqual(size.name, 'large')
        self.assertEqual(size.ram, 8192)
        self.assertTrue(size.cpu is None or isinstance(size.cpu, int))
        self.assertTrue(size.vcpu is None or isinstance(size.vcpu, int))
        self.assertEqual(size.cpu, 8)
        self.assertEqual(size.vcpu, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)
        size = sizes[3]
        self.assertEqual(size.id, '4')
        self.assertEqual(size.name, 'custom')
        self.assertEqual(size.ram, 0)
        self.assertEqual(size.cpu, 0)
        self.assertEqual(size.vcpu, None)
        self.assertEqual(size.disk, None)
        self.assertEqual(size.bandwidth, None)
        self.assertEqual(size.price, None)

    def test_list_locations(self):
        """
        Test list_locations functionality.
        """
        locations = self.driver.list_locations()

        self.assertEqual(len(locations), 1)
        location = locations[0]
        self.assertEqual(location.id, '0')
        self.assertEqual(location.name, '')
        self.assertEqual(location.country, '')

    def test_ex_list_networks(self):
        """
        Test ex_list_networks functionality.
        """
        networks = self.driver.ex_list_networks()

        self.assertEqual(len(networks), 2)
        network = networks[0]
        self.assertEqual(network.id, '5')
        self.assertEqual(network.name, 'Network 5')
        self.assertEqual(network.address, '192.168.0.0')
        self.assertEqual(network.size, '256')
        network = networks[1]
        self.assertEqual(network.id, '15')
        self.assertEqual(network.name, 'Network 15')
        self.assertEqual(network.address, '192.168.1.0')
        self.assertEqual(network.size, '256')


class OpenNebula_1_4_MockHttp(MockHttp):
    """
    Mock HTTP server for testing v1.4 of the OpenNebula.org compute driver.
    """

    fixtures = ComputeFileFixtures('opennebula_1_4')

    def _compute(self, method, url, body, headers):
        """
        Compute pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('computes.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('compute_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _storage(self, method, url, body, headers):
        """
        Storage pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('storage.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('disk_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _network(self, method, url, body, headers):
        """
        Network pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('networks.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('network_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _compute_5(self, method, url, body, headers):
        """
        Compute entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('compute_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])

    def _compute_15(self, method, url, body, headers):
        """
        Compute entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('compute_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])

    def _storage_5(self, method, url, body, headers):
        """
        Storage entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('disk_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])

    def _storage_15(self, method, url, body, headers):
        """
        Storage entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('disk_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])

    def _network_5(self, method, url, body, headers):
        """
        Network entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('network_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])

    def _network_15(self, method, url, body, headers):
        """
        Network entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('network_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.OK, body, {},
                    httplib.responses[httplib.OK])


class OpenNebula_2_0_MockHttp(MockHttp):
    """
    Mock HTTP server for testing v2.0 through v3.2 of the OpenNebula.org
    compute driver.
    """

    fixtures = ComputeFileFixtures('opennebula_2_0')

    def _compute(self, method, url, body, headers):
        """
        Compute pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('compute_collection.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('compute_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _storage(self, method, url, body, headers):
        """
        Storage pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('storage_collection.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('storage_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _network(self, method, url, body, headers):
        """
        Network pool resources.
        """
        if method == 'GET':
            body = self.fixtures.load('network_collection.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('network_5.xml')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])

    def _compute_5(self, method, url, body, headers):
        """
        Compute entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('compute_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

    def _compute_15(self, method, url, body, headers):
        """
        Compute entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('compute_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

    def _storage_5(self, method, url, body, headers):
        """
        Storage entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('storage_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

    def _storage_15(self, method, url, body, headers):
        """
        Storage entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('storage_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

    def _network_5(self, method, url, body, headers):
        """
        Network entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('network_5.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

    def _network_15(self, method, url, body, headers):
        """
        Network entry resource.
        """
        if method == 'GET':
            body = self.fixtures.load('network_15.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])

if __name__ == '__main__':
    sys.exit(unittest.main())
