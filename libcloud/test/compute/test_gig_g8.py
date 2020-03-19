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
import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.test import MockHttp
from libcloud.compute.base import NodeImage, NodeSize, Node, StorageVolume
from libcloud.compute.drivers.gig_g8 import G8NodeDriver, G8Network, G8PortForward
from libcloud.test.file_fixtures import ComputeFileFixtures


class G8MockHttp(MockHttp):
    """Fixtures needed for tests related to rating model"""
    fixtures = ComputeFileFixtures('gig_g8')

    def __getattr__(self, key):
        def method(method, path, params, headers):
            response = self.fixtures.load('{}_{}.json'.format(method, key.lstrip("_")))
            return (httplib.OK, response, {}, httplib.responses[httplib.OK])

        return method


class G8Tests(unittest.TestCase):
    def setUp(self):
        G8NodeDriver.connectionCls.conn_class = G8MockHttp
        self.driver = G8NodeDriver(1, "token", "https://myg8.example.com")

    def test_list_networks(self):
        networks = self.driver.ex_list_networks()
        self.assertGreater(len(networks), 0)
        for network in networks:
            self.assertIsInstance(network, G8Network)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertGreater(len(nodes), 0)
        for node in nodes:
            self.assertIsInstance(node, Node)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertGreater(len(sizes), 0)
        for size in sizes:
            self.assertIsInstance(size, NodeSize)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertGreater(len(images), 0)
        for image in images:
            self.assertIsInstance(image, NodeImage)

    def test_create_node(self):
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        network = self.driver.ex_list_networks()[0]
        node = self.driver.create_node("my test", image, network, "my description", size)
        self.assertIsInstance(node, Node)

    def test_stop_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.stop_node(node)
        self.assertTrue(result)

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.destroy_node(node)
        self.assertTrue(result)

    def test_start_node(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.start_node(node)
        self.assertTrue(result)

    def test_create_network(self):
        network = self.driver.ex_create_network("my network")
        self.assertIsInstance(network, G8Network)

    def test_destroy_network(self):
        network = self.driver.ex_list_networks()[0]
        result = self.driver.ex_destroy_network(network)
        self.assertTrue(result)

    def test_list_portforward(self):
        network = self.driver.ex_list_networks()[0]
        forwards = self.driver.ex_list_portforwards(network)
        self.assertGreater(len(forwards), 0)
        for forward in forwards:
            self.assertIsInstance(forward, G8PortForward)

    def test_create_forward(self):
        network = self.driver.ex_list_networks()[0]
        node = self.driver.list_nodes()[0]
        result = self.driver.ex_create_portforward(network, node, 34022, 22)
        self.assertIsInstance(result, G8PortForward)

    def test_delete_portforward(self):
        network = self.driver.ex_list_networks()[0]
        forward = self.driver.ex_list_portforwards(network)[0]
        res = self.driver.ex_delete_portforward(forward)
        self.assertTrue(res)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertGreater(len(volumes), 1)
        for volume in volumes:
            self.assertIsInstance(volume, StorageVolume)

    def test_create_volume(self):
        volume = self.driver.create_volume(10, "my volume", "my description")
        self.assertIsInstance(volume, StorageVolume)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        res = self.driver.destroy_volume(volume)
        self.assertTrue(res)

    def test_attach_volume(self):
        volume = self.driver.list_volumes()[0]
        node = self.driver.list_nodes()[0]
        res = self.driver.attach_volume(node, volume)
        self.assertTrue(res)

    def test_detach_volume(self):
        volume = self.driver.list_volumes()[0]
        node = self.driver.list_nodes()[0]
        res = self.driver.detach_volume(node, volume)
        self.assertTrue(res)



if __name__ == '__main__':
    sys.exit(unittest.main())
