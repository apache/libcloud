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
#
# Maintainer: Aaron Welch <welch@packet.net>
# Based on code written by Jed Smith <jed@packet.com> who based it on
# code written by Alex Polvi <polvi@cloudkick.com>
#

import sys
import unittest
from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.packet import PacketNodeDriver
from libcloud.compute.base import Node, KeyPair
from libcloud.compute.types import NodeState

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class PacketTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        PacketNodeDriver.connectionCls.conn_classes = (None, PacketMockHttp)
        self.driver = PacketNodeDriver('foo')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes('project-id')
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.id, '1e52437e-bbbb-cccc-dddd-74a9dfd3d3bb')
        self.assertEqual(node.name, 'test-node')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue('147.75.255.255' in node.public_ips)
        self.assertTrue('2604:EEEE::EE' in node.public_ips)
        self.assertTrue('10.0.0.255' in node.private_ips)
        self.assertEqual(node.extra['created_at'], '2015-05-03T15:50:49Z')
        self.assertEqual(node.extra['updated_at'], '2015-05-03T16:00:08Z')
        self.assertEqual(node.extra['billing_cycle'], 'hourly')
        self.assertEqual(node.extra['locked'], False)
        self.assertEqual(node.size.id, 'baremetal_1')
        self.assertEqual(node.size.name, 'Type 1')
        self.assertEqual(node.size.ram, 16384)
        self.assertEqual(node.size.disk, 240)
        self.assertEqual(node.size.price, 0.4)
        self.assertEqual(node.size.extra['line'], 'baremetal')
        self.assertEqual(node.image.id, 'ubuntu_14_04')
        self.assertEqual(node.image.name, 'Ubuntu 14.04 LTS')
        self.assertEqual(node.image.extra['distro'], 'ubuntu')
        self.assertEqual(node.image.extra['version'], '14.04')

    def test_list_nodes_response(self):
        nodes = self.driver.list_nodes('project-id')
        self.assertTrue(isinstance(nodes, list))
        for node in nodes:
            self.assertTrue(isinstance(node, Node))

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 1)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 4)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 1)

    def test_create_node(self):
        node = self.driver.create_node(ex_project_id="project-id",
                                       name="node-name",
                                       size=self.driver.list_sizes()[0],
                                       image=self.driver.list_images()[0],
                                       location=self.driver.list_locations()[
                                           0])
        self.assertTrue(isinstance(node, Node))

    def test_create_node_response(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        node = self.driver.create_node(ex_project_id="project-id",
                                       name='node-name',
                                       image=image,
                                       size=size,
                                       location=location)
        self.assertTrue(isinstance(node, Node))

    def test_reboot_node(self):
        node = self.driver.list_nodes('project-id')[0]
        self.driver.reboot_node(node)

    def test_reboot_node_response(self):
        node = self.driver.list_nodes('project-id')[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        node = self.driver.list_nodes('project-id')[0]
        self.driver.destroy_node(node)

    def test_destroy_node_response(self):
        node = self.driver.list_nodes('project-id')[0]
        self.driver.destroy_node(node)

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(len(keys), 3)

    def test_create_key_pair(self):
        key = self.driver.create_key_pair(name="sshkey-name",
                                          public_key="ssh-rsa AAAAB3NzaC1yc2EA\
AAADAQABAAABAQDI4pIqzpb5g3992h+yr527VRcaB68KE4vPjWPPoiQws49KIs2NMcOzS9QE4641uW\
1u5ML2HgQdfYKMF/YFGnI1Y6xV637DjhDyZYV9LasUH49npSSJjsBcsk9JGfUpNAOdcgpFzK8V90ei\
OrOC5YncxdwwG8pwjFI9nNVPCl4hYEu1iXdyysHvkFfS2fklsNjLWrzfafPlaen+qcBxygCA0sFdW/\
7er50aJeghdBHnE2WhIKLUkJxnKadznfAge7oEe+3LLAPfP+3yHyvp2+H0IzmVfYvAjnzliYetqQ8p\
g5ZW2BiJzvqz5PebGS70y/ySCNW1qQmJURK/Wc1bt9en root@libcloud")
        self.assertTrue(isinstance(key, KeyPair))

    def test_delete_key_pair(self):
        key = self.driver.list_key_pairs()[0]
        self.driver.delete_key_pair(key)


class PacketMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('packet')

    def _facilities(self, method, url, body, headers):
        body = self.fixtures.load('facilities.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _plans(self, method, url, body, headers):
        body = self.fixtures.load('plans.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _operating_systems(self, method, url, body, headers):
        body = self.fixtures.load('operatingsystems.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ssh_keys(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('sshkeys.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('sshkey_create.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ssh_keys_2c1a7f23_1dc6_4a37_948e_d9857d9f607c(self, method, url,
                                                       body, headers):
        if method == 'DELETE':
            return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _projects_project_id_devices(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('device_create.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            body = self.fixtures.load('devices.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _devices_1e52437e_bbbb_cccc_dddd_74a9dfd3d3bb(self, method, url,
                                                      body, headers):
        if method == 'DELETE':
            return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _devices_1e52437e_bbbb_cccc_dddd_74a9dfd3d3bb_actions(
            self, method, url, body, headers):
            return (httplib.OK, '', {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
