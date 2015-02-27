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
    import simplejson as json
except ImportError:
    import json  # NOQA

from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.vultr import VultrNodeDriver

from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import VULTR_PARAMS


# class VultrTests(unittest.TestCase, TestCaseMixin):
class VultrTests(LibcloudTestCase):

    def setUp(self):
        VultrNodeDriver.connectionCls.conn_classes = \
            (VultrMockHttp, VultrMockHttp)
        VultrMockHttp.type = None
        self.driver = VultrNodeDriver(*VULTR_PARAMS)

    def test_list_images_success(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)

        image = images[0]
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_sizes_success(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) == 22)

        size = sizes[0]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '512 MB RAM,160 GB SATA,1.00 TB BW')
        self.assertEqual(size.ram, 512)

        size = sizes[21]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '65536 MB RAM,800 GB SSD,9.00 TB BW')
        self.assertEqual(size.ram, 65536)

    def test_list_locations_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)

        location = locations[0]
        self.assertEqual(location.id, '1')
        self.assertEqual(location.name, 'New Jersey')

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].id, '1')
        self.assertEqual(nodes[0].public_ips, ['108.61.206.153'])

    def test_reboot_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_destroy_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.destroy_node(node)
        self.assertTrue(result)


class VultrMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('vultr')

    def _v1_regions_list(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_os_list(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_plans_list(self, method, url, body, headers):
        body = self.fixtures.load('list_sizes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_server_list(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_server_destroy(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

    def _v1_server_reboot(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
