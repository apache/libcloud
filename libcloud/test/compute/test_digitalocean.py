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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b
from libcloud.utils.py3 import u

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.digitalocean import DigitalOceanNodeDriver
from libcloud.compute.types import NodeState

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import DIGITAL_OCEAN_PARAMS


#class DigitalOceanTests(unittest.TestCase, TestCaseMixin):
class DigitalOceanTests(unittest.TestCase):
    def setUp(self):
        DigitalOceanNodeDriver.connectionCls.conn_classes = \
            (None, DigitalOceanMockHttp)
        DigitalOceanMockHttp.type = None
        self.driver = DigitalOceanNodeDriver(*DIGITAL_OCEAN_PARAMS)

    def test_authentication(self):
        DigitalOceanMockHttp.type = 'UNAUTHORIZED_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

    def test_list_images_success(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)

        image = images[0]
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_sizes_success(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) >= 1)

        size = sizes[0]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '512MB')
        self.assertEqual(size.ram, 512)

        size = sizes[4]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '8GB')
        self.assertEqual(size.ram, 8 * 1024)

    def test_list_locations_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)

        location = locations[0]
        self.assertEqual(location.id, '1')
        self.assertEqual(location.name, 'New York 1')

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, 'test-2')
        self.assertEqual(nodes[0].public_ips, [])

    def test_reboot_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_destroy_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.destroy_node(node)
        self.assertTrue(result)

    def test_ex_list_ssh_keys(self):
        keys = self.driver.ex_list_ssh_keys()
        self.assertEqual(len(keys), 1)

        self.assertEqual(keys[0].id, 7717)
        self.assertEqual(keys[0].name, 'test1')
        self.assertEqual(keys[0].pub_key, None)

    def test_ex_destroy_ssh_key(self):
        key = self.driver.ex_list_ssh_keys()[0]
        result = self.driver.ex_destroy_ssh_key(key.id)
        self.assertTrue(result)


class DigitalOceanMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('digitalocean')

    def _regions(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _sizes(self, method, url, body, headers):
        body = self.fixtures.load('list_sizes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _droplets(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _droplets_119461_reboot(self, method, url, body, headers):
        # reboot_node
        body = self.fixtures.load('reboot_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _droplets_119461_destroy(self, method, url, body, headers):
        # destroy_node
        body = self.fixtures.load('destroy_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ssh_keys(self, method, url, body, headers):
        body = self.fixtures.load('ex_list_ssh_keys.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ssh_keys_7717_destroy(self, method, url, body, headers):
        # destroy_ssh_key
        body = self.fixtures.load('ex_destroy_ssh_key.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _droplets_UNAUTHORIZED_CLIENT(self, method, url, body, headers):
        body = self.fixtures.load('error.txt')
        return (httplib.FOUND, body, {}, httplib.responses[httplib.FOUND])

if __name__ == '__main__':
    sys.exit(unittest.main())
