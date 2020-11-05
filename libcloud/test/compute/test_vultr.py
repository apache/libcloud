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

try:
    import simplejson as json  # pylint: disable=unused-import
except ImportError:
    # pylint: disable=unused-import
    import json  # NOQA

from libcloud.utils.py3 import httplib

from libcloud.common.types import ServiceUnavailableError

from libcloud.compute.drivers.vultr import VultrNodeDriver
from libcloud.compute.base import NodeImage, NodeSize

from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import VULTR_PARAMS


# class VultrTests(unittest.TestCase, TestCaseMixin):
class VultrTests(LibcloudTestCase):

    def setUp(self):
        VultrNodeDriver.connectionCls.conn_class = VultrMockHttp
        VultrMockHttp.type = None
        self.driver = VultrNodeDriver(*VULTR_PARAMS)

    def test_list_images_dont_require_api_key(self):
        self.driver.list_images()
        self.assertFalse(self.driver.connection.require_api_key())

    def test_list_images_success(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)

        image = images[0]
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_sizes_dont_require_api_key(self):
        self.driver.list_sizes()
        self.assertFalse(self.driver.connection.require_api_key())

    def test_list_sizes_success(self):
        """count of current plans"""
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) == 19)

        size = sizes[0]
        self.assertTrue(size.id.isdigit())
        self.assertEqual(size.name, '8192 MB RAM,110 GB SSD,10.00 TB BW')
        self.assertEqual(size.ram, 8192)

        size = sizes[16]
        self.assertTrue(size.id.isdigit())
        self.assertEqual(size.name, '16384 MB RAM,384 GB SSD,5.00 TB BW')
        self.assertEqual(size.ram, 16384)

    def test_list_locations_dont_require_api_key(self):
        self.driver.list_locations()
        self.assertFalse(self.driver.connection.require_api_key())

    def test_list_locations_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)

        location = locations[0]
        self.assertEqual(location.id, '1')
        self.assertEqual(location.name, 'New Jersey')
        self.assertEqual(location.extra['continent'], 'North America')

    def test_list_locations_extra_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)
        extra_keys = [
            'continent',
            'state',
            'ddos_protection',
            'block_storage',
            'regioncode']
        for location in locations:
            self.assertTrue(len(location.extra.keys()) >= 5)
            self.assertTrue(all(item in location.extra.keys()
                                for item in extra_keys))

    def test_list_nodes_require_api_key(self):
        self.driver.list_nodes()
        self.assertTrue(self.driver.connection.require_api_key())

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 3)
        self.assertTrue(nodes[0].id.isdigit())
        self.assertEqual(nodes[0].id, '41306569')
        self.assertEqual(nodes[0].public_ips, ['45.76.43.87'])
        self.assertEqual(nodes[0].private_ips, ['10.7.96.85'])
        self.assertEqual(nodes[2].private_ips, [])

    def test_list_nodes_image_success(self):
        nodes = self.driver.list_nodes()
        node = nodes[0]
        self.assertTrue(isinstance(node.image, NodeImage))

    def test_list_nodes_size_success(self):
        nodes = self.driver.list_nodes()
        node = nodes[0]
        self.assertTrue(isinstance(node.size, NodeSize))

    def test_list_nodes_success_extra(self):
        extra_keys = [
            "default_password", "pending_charges", "cost_per_month",
        ]
        nodes = self.driver.list_nodes()
        for node in nodes:
            self.assertTrue(len(node.extra.keys()) > 5)
            self.assertTrue(all(item in node.extra.keys()
                                for item in extra_keys))

    def test_reboot_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_create_node_success(self):
        test_size = self.driver.list_sizes()[0]
        test_image = self.driver.list_images()[0]
        test_location = self.driver.list_locations()[0]
        created_node = self.driver.create_node('test-node', test_size,
                                               test_image, test_location)
        self.assertEqual(created_node.id, "41326859")

    def test_destroy_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.destroy_node(node)
        self.assertTrue(result)

    def test_list_key_pairs_success(self):
        key_pairs = self.driver.list_key_pairs()
        self.assertEqual(len(key_pairs), 1)
        key_pair = key_pairs[0]
        self.assertEqual(key_pair.id, '5806a8ef2a0c6')
        self.assertEqual(key_pair.name, 'test-key-pair')

    def test_create_key_pair_success(self):
        res = self.driver.create_key_pair('test-key-pair')
        self.assertTrue(res)

    def test_delete_key_pair_success(self):
        key_pairs = self.driver.list_key_pairs()
        key_pair = key_pairs[0]
        res = self.driver.delete_key_pair(key_pair)
        self.assertTrue(res)

    def test_rate_limit(self):
        VultrMockHttp.type = 'SERVICE_UNAVAILABLE'
        self.assertRaises(ServiceUnavailableError, self.driver.list_nodes)


class VultrMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('vultr')

    # pylint: disable=unused-argument
    def _v1_regions_list(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_os_list(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_plans_list(self, method, url, body, headers):
        body = self.fixtures.load('list_sizes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_server_list(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_server_list_SERVICE_UNAVAILABLE(self, method, url, body, headers):
        body = self.fixtures.load('error_rate_limit.txt')
        return (httplib.SERVICE_UNAVAILABLE, body, {},
                httplib.responses[httplib.SERVICE_UNAVAILABLE])

    # pylint: disable=unused-argument
    def _v1_server_create(self, method, url, body, headers):
        body = self.fixtures.load('create_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_server_destroy(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_server_reboot(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_sshkey_list(self, method, url, body, headers):
        body = self.fixtures.load('list_key_pairs.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_sshkey_create(self, method, url, body, headers):
        body = self.fixtures.load('create_key_pair.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # pylint: disable=unused-argument
    def _v1_sshkey_destroy(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
