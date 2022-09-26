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

from libcloud.test import MockHttp
from libcloud.utils.py3 import httplib
from libcloud.common.vultr import VultrException
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.drivers.vultr import VultrNodeDriver, VultrNodeDriverV2


class VultrTestsV2(unittest.TestCase):
    def setUp(self):
        VultrNodeDriver.connectionCls.conn_class = VultrMockHttpV2
        VultrMockHttpV2.type = None
        self.driver = VultrNodeDriver("foo")

    def test_unknown_api_version(self):
        self.assertRaises(NotImplementedError, VultrNodeDriver, "foo", api_version="3")

    def test_correct_class_is_used(self):
        self.assertIsInstance(self.driver, VultrNodeDriverV2)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 25)
        size = sizes[0]
        self.assertEqual(size.id, "vc2-1c-1gb")
        self.assertEqual(size.name, "vc2-1c-1gb")
        for size in sizes:
            self.assertIsInstance(size.price, int)
            self.assertIsInstance(size.ram, int)
            self.assertIsInstance(size.disk, int)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 30)
        image = images[0]
        self.assertEqual(image.id, "124")
        self.assertEqual(image.name, "Windows 2012 R2 x64")
        self.assertEqual(image.extra["arch"], "x64")
        self.assertEqual(image.extra["family"], "windows")

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 17)
        location = locations[0]
        self.assertEqual(location.country, "NL")
        self.assertEqual(location.id, "ams")
        self.assertEqual(location.name, "Amsterdam")
        self.assertIsInstance(location.extra["option"], list)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes(ex_list_bare_metals=False)
        self.assertEqual(len(nodes), 3)
        node = nodes[0]
        self.assertEqual(node.id, "123")
        self.assertEqual(node.name, "test1")
        self.assertEqual(node.image, "477")
        self.assertEqual(node.size, "vc2-1c-2gb")
        self.assertEqual(node.extra["location"], "fra")
        self.assertIn("45.76.83.44", node.public_ips)
        for node in nodes:
            self.assertIsInstance(node.public_ips, list)
            self.assertIsInstance(node.private_ips, list)
            self.assertIsInstance(node.extra["vcpu_count"], int)
            self.assertIsInstance(node.extra["ram"], int)
            self.assertIsInstance(node.extra["disk"], int)
            self.assertIsInstance(node.extra["allowed_bandwidth"], int)

    def test_list_nodes_with_bare_metals(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 5)
        node = nodes[0]
        self.assertEqual(node.id, "123")
        self.assertEqual(node.name, "test1")
        self.assertEqual(node.image, "477")
        self.assertEqual(node.size, "vc2-1c-2gb")
        self.assertEqual(node.extra["vcpu_count"], 1)
        self.assertEqual(node.extra["location"], "fra")
        self.assertFalse(node.extra["is_bare_metal"])
        self.assertIn("45.76.83.44", node.public_ips)
        node = nodes[-1]
        self.assertEqual(node.id, "234")
        self.assertEqual(node.size, "vbm-8c-132gb")
        self.assertEqual(node.state, "pending")
        self.assertEqual(node.extra["cpu_count"], 8)
        self.assertEqual(node.extra["location"], "mia")
        self.assertTrue(node.extra["is_bare_metal"])
        self.assertEqual(node.extra["mac_address"], 189250955239968)

    def test_create_node(self):
        name = "test123"
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]
        node = self.driver.create_node(name=name, image=image, size=size, location=location)
        self.assertEqual(node.id, "123")
        self.assertEqual(node.name, "test123")
        self.assertEqual(node.image, "446")
        self.assertFalse(node.extra["is_bare_metal"])

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        response = self.driver.destroy_node(node)
        self.assertTrue(response)

    def test_start_node(self):
        node = self.driver.list_nodes()[0]
        response = self.driver.start_node(node)
        self.assertTrue(response)

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        response = self.driver.reboot_node(node)
        self.assertTrue(response)

    def test_ex_stop_nodes(self):
        nodes = self.driver.list_nodes()
        response = self.driver.ex_stop_nodes(nodes)
        self.assertTrue(response)

    def test_stop_node(self):
        node = self.driver.list_nodes()[0]
        response = self.driver.stop_node(node)
        self.assertTrue(response)

    def test_ex_get_node(self):
        node = self.driver.ex_get_node("123")
        self.assertEqual(node.name, "test")
        self.assertEqual(node.id, "123")
        self.assertEqual(node.size, "vc2-1c-1gb")
        self.assertEqual(node.image, "477")
        self.assertEqual(node.state, "running")
        self.assertIn("45.76.36.72", node.public_ips)

    def test_ex_resize_node(self):
        node = self.driver.ex_get_node("123")
        size = self.driver.list_sizes()[1]
        node = self.driver.ex_resize_node(node, size)
        self.assertEqual(node.id, "123")
        self.assertEqual(node.size, "vc2-1c-2gb")
        self.assertEqual(node.name, "test4")
        self.assertIn("192.248.168.21", node.public_ips)

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(len(keys), 1)
        key = keys[0]
        self.assertEqual(key.name, "tester")
        self.assertIsNone(key.private_key)
        self.assertEqual(key.extra["id"], "123")

    def test_list_key_pairs_UNAUTHORIZED(self):
        VultrMockHttpV2.type = "UNAUTHORIZED"
        with self.assertRaises(VultrException):
            self.driver.list_key_pairs()

    def test_get_key_pair(self):
        key_id = "123"
        key = self.driver.get_key_pair(key_id)
        self.assertEqual(key.name, "tester")
        self.assertEqual(key.extra["id"], "123")
        self.assertIsNone(key.private_key)

    def test_import_key_pair_from_string(self):
        name = "tester"
        key_material = "material"
        key = self.driver.import_key_pair_from_string(name, key_material)
        self.assertEqual(key.name, "tester")
        self.assertEqual(key.extra["id"], "123")
        self.assertIsNone(key.private_key)

    def test_delete_key_pair(self):
        keys = self.driver.list_key_pairs()
        key = keys[0]
        response = self.driver.delete_key_pair(key)
        self.assertTrue(response)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 2)
        volume = volumes[0]
        self.assertEqual(volume.name, "test1")
        self.assertEqual(volume.id, "123")
        self.assertEqual(volume.size, 10)
        self.assertEqual(volume.state, "available")

    def test_create_volume(self):
        volume = self.driver.create_volume(size=15, name="test4", location="ewr")
        self.assertEqual(volume.name, "test4")
        self.assertEqual(volume.id, "ec6d1ecc-aa70-4f18-8edd-887a258b1b45")
        self.assertEqual(volume.size, 15)
        self.assertEqual(volume.state, "creating")
        self.assertEqual(volume.extra["location"], "ewr")

    def test_attach_volume(self):
        volume = self.driver.list_volumes()[0]
        node = self.driver.list_nodes()[0]
        response = self.driver.attach_volume(node, volume)
        self.assertTrue(response)

    def test_attach_volume_WRONG_LOCATION(self):
        volume = self.driver.list_volumes()[1]
        node = self.driver.list_nodes()[0]
        VultrMockHttpV2.type = "WRONG_LOCATION"
        with self.assertRaises(VultrException):
            self.driver.attach_volume(node, volume)

    def test_detach_volume(self):
        volume = self.driver.list_volumes()[0]
        response = self.driver.detach_volume(volume)
        self.assertTrue(response)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        response = self.driver.destroy_volume(volume)
        self.assertTrue(response)

    def test_ex_get_volume(self):
        volume = self.driver.ex_get_volume("123")
        self.assertEqual(volume.id, "123")
        self.assertEqual(volume.name, "test2")
        self.assertEqual(volume.state, "available")

    def test_ex_resize_volume(self):
        volume = self.driver.list_volumes()[0]
        response = self.driver.ex_resize_volume(volume, 20)
        self.assertTrue(response)

    def test_ex_list_available_sizes_for_location(self):
        location = self.driver.list_locations()[0]
        available_sizes = self.driver.ex_list_available_sizes_for_location(location)
        self.assertTrue(isinstance(available_sizes, list))

    def test_ex_list_networks(self):
        networks = self.driver.ex_list_networks()
        self.assertEqual(len(networks), 2)
        network = networks[0]
        self.assertEqual(network.id, "123")
        self.assertEqual(network.cidr_block, "10.7.96.0/20")
        self.assertEqual(network.location, "ams")

    def test_ex_get_network(self):
        network = self.driver.ex_get_network("123")
        self.assertEqual(network.id, "123")
        self.assertEqual(network.cidr_block, "10.7.96.0/20")
        self.assertEqual(network.location, "ams")

    def test_ex_create_network(self):
        network = self.driver.ex_create_network("10.0.0.0/24", "ams", "TestNetwork")
        self.assertEqual(network.id, "123")
        self.assertEqual(network.cidr_block, "10.0.0.0/24")
        self.assertEqual(network.location, "ams")

    def test_ex_destroy_network(self):
        network = self.driver.ex_get_network("123")
        response = self.driver.ex_destroy_network(network)
        self.assertTrue(response)

    def ex_list_snapshots(self):
        snapshots = self.driver.ex_list_snapshots()
        self.assertEqual(len(snapshots), 2)
        snapshot = snapshots[0]
        self.assertEqual(snapshot.id, "123")
        self.assertEqual(snapshot.size, "25.0")
        self.assertEqual(snapshot.state, "available")
        snapshot = snapshots[1]
        self.assertEqual(snapshot.id, "1234")
        self.assertEqual(snapshot.size, "25.0")
        self.assertEqual(snapshot.state, "creating")

    def test_ex_get_snapshot(self):
        snapshot = self.driver.ex_get_snapshot("123")
        self.assertEqual(snapshot.id, "123")
        self.assertEqual(snapshot.size, 25.0)
        self.assertEqual(snapshot.state, "available")

    def test_ex_create_snapshot(self):
        node = self.driver.list_nodes()[0]
        snapshot = self.driver.ex_create_snapshot(node)
        self.assertEqual(snapshot.id, "123")
        self.assertEqual(snapshot.size, 0)
        self.assertEqual(snapshot.state, "creating")

    def test_ex_delete_snapshot(self):
        snapshot = self.driver.ex_get_snapshot("123")
        response = self.driver.ex_delete_snapshot(snapshot)
        self.assertTrue(response)

    def test_ex_list_bare_metal_sizes(self):
        sizes = self.driver.ex_list_bare_metal_sizes()
        self.assertEqual(len(sizes), 4)
        for size in sizes:
            self.assertIsInstance(size.extra["cpu_count"], int)
            self.assertIsInstance(size.extra["cpu_threads"], int)
            self.assertIsInstance(size.extra["cpu_model"], str)

    def test_create_bare_metal_node(self):
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        size = self.driver.list_sizes()[-1]
        node = self.driver.create_node(name="test1", image=image, location=location, size=size)
        self.assertEqual(node.name, "test1")
        self.assertEqual(node.id, "234")
        self.assertTrue(node.extra["is_bare_metal"])
        self.assertEqual(node.extra["cpu_count"], 4)

    def test_reboot_bare_metal_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[-1]
        self.assertTrue(node.extra["is_bare_metal"])
        response = self.driver.reboot_node(node)
        self.assertTrue(response)

    def test_start_bare_metal_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[-1]
        self.assertTrue(node.extra["is_bare_metal"])
        response = self.driver.start_node(node)
        self.assertTrue(response)

    def test_stop_bare_metal_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[-1]
        self.assertTrue(node.extra["is_bare_metal"])
        response = self.driver.stop_node(node)
        self.assertTrue(response)

    def test_destroy_bare_metal_node(self):
        nodes = self.driver.list_nodes()
        node = nodes[-1]
        self.assertTrue(node.extra["is_bare_metal"])
        response = self.driver.destroy_node(node)
        self.assertTrue(response)

    def test_pagination(self):
        images = self.driver.list_images()
        VultrMockHttpV2.type = "PAGINATED"
        paginated_images = self.driver.list_images()
        self.assertEqual(len(images), len(paginated_images))
        for first, second in zip(images, paginated_images):
            self.assertEqual(first.id, second.id)
            self.assertEqual(first.name, second.name)
            self.assertDictEqual(first.extra, second.extra)


class VultrMockHttpV2(MockHttp):
    fixtures = ComputeFileFixtures("vultr_v2")

    def _v2_regions(self, method, url, body, headers):
        body = self.fixtures.load("list_locations.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_os(self, method, url, body, headers):
        body = self.fixtures.load("list_images.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_plans(self, method, url, body, headers):
        body = self.fixtures.load("list_sizes.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_instances(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("list_nodes.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("create_node.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_bare_metals(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_list_bare_metal_nodes.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("create_node_bare_metal.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_instances_123(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
        elif method == "GET":
            body = self.fixtures.load("ex_get_node.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "PATCH":
            body = self.fixtures.load("ex_resize_node.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_instances_123_start(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_instances_123_reboot(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_instances_halt(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_ssh_keys(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("list_key_pairs.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("import_key_pair_from_string.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_ssh_keys_UNAUTHORIZED(self, method, url, body, headers):
        body = '{"error":"Invalid API token.","status":401}'
        return (httplib.UNAUTHORIZED, body, {}, httplib.responses[httplib.UNAUTHORIZED])

    def _v2_ssh_keys_123(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "GET":
            body = self.fixtures.load("get_key_pair.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_blocks(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("list_volumes.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("create_volume.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_blocks_123(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_get_volume.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
        elif method == "PATCH":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_blocks_123_attach(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_blocks_1234_attach_WRONG_LOCATION(self, method, url, body, headers):
        body = (
            '{"error": "unable to attach: Block storage volume must be in '
            'the same region as the server it is attached to.",'
            ' "status": 400}'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _v2_blocks_123_detach(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_regions_ams_availability(self, method, url, body, headers):
        body = self.fixtures.load("ex_list_available_sizes_for_location.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_private_networks(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_list_networks.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("ex_create_network.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_private_networks_123(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_get_network.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_os_PAGINATED(self, method, url, body, headers):
        if "cursor" not in url:
            body = self.fixtures.load("list_images_paginated_1.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif "cursor=bmV4dF9fMjMw" in url:
            body = self.fixtures.load("list_images_paginated_2.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load("list_images_paginated_3.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_snapshots(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_list_snapshots.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load("ex_create_snapshot.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_snapshots_123(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("ex_get_snapshot.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_bare_metals_234_reboot(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_bare_metals_234_start(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_bare_metals_234_halt(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_bare_metals_234(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_plans_metal(self, method, url, body, headers):
        body = self.fixtures.load("ex_list_bare_metal_sizes.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
