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
import base64
import json
import time

import mock

from libcloud.utils.py3 import httplib
from libcloud.test import MockHttp
from libcloud.compute.base import NodeImage, NodeSize, Node, StorageVolume
from libcloud.compute.drivers.gig_g8 import G8NodeDriver, G8Network, G8PortForward
import libcloud.common.gig_g8

from libcloud.test.file_fixtures import ComputeFileFixtures

# For tests we don't want to actually verify a token since we use an expired on
original_is_jwt_expired = libcloud.common.gig_g8.is_jwt_expired


def mock_is_jwt_expired(jwt):
    return False


class G8MockHttp(MockHttp):
    """Fixtures needed for tests related to rating model"""
    fixtures = ComputeFileFixtures('gig_g8')

    def __getattr__(self, key):
        def method(method, path, params, headers):
            response = self.fixtures.load('{}_{}.json'.format(method, key.lstrip("_")))
            return (httplib.OK, response, {}, httplib.responses[httplib.OK])

        return method


@mock.patch('libcloud.common.gig_g8.is_jwt_expired', mock_is_jwt_expired)
class G8Tests(unittest.TestCase):
    def setUp(self):
        G8NodeDriver.connectionCls.conn_class = G8MockHttp
        self.driver = G8NodeDriver(1, "header.eyJhenAiOiJkZndlcmdyZWdyZSIsImV4cCI6MTU5MDUyMzEwNSwiaXNzIjoiaXRzeW91b25saW5lIiwicmVmcmVzaF90b2tlbiI6Inh4eHh4eHgiLCJzY29wZSI6WyJ1c2VyOmFkbWluIl0sInVzZXJuYW1lIjoiZXhhbXBsZSJ9.signature", "https://myg8.example.com")

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

    def test_is_jwt_expired(self):
        data = {"azp": "example",
                "exp": int(time.time()),
                "iss": "itsyouonline",
                "refresh_token": "xxxxxxx",
                "scope": ["user:admin"],
                "username": "example"}

        def contruct_jwt(data):
            jsondata = json.dumps(data).encode()
            return "header.{}.signature".format(base64.encodebytes(jsondata).decode())

        libcloud.common.gig_g8.is_jwt_expired = original_is_jwt_expired

        self.assertTrue(libcloud.common.gig_g8.is_jwt_expired(contruct_jwt(data)))
        data["exp"] = int(time.time()) + 300  # expire in 5min
        self.assertFalse(libcloud.common.gig_g8.is_jwt_expired(contruct_jwt(data)))


if __name__ == '__main__':
    sys.exit(unittest.main())
