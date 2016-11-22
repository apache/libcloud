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

from libcloud.compute.drivers.cloudscale import CloudscaleNodeDriver

from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import CLOUDSCALE_PARAMS


class CloudscaleTests(LibcloudTestCase):

    def setUp(self):
        CloudscaleNodeDriver.connectionCls.conn_classes = \
            (None, CloudscaleMockHttp)
        self.driver = CloudscaleNodeDriver(*CLOUDSCALE_PARAMS)

    def test_list_images_success(self):
        images = self.driver.list_images()
        image, = images
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_sizes_success(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 2)

        size = sizes[0]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, 'Flex-2')
        self.assertEqual(size.ram, 2048)

        size = sizes[1]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, 'Flex-4')
        self.assertEqual(size.ram, 4096)

    def test_list_locations_not_existing(self):
        # assertRaises doesn't exist in Python 2.5?!
        try:
            self.driver.list_locations()
        except NotImplementedError:
            pass
        else:
            assert False, 'Did not raise the wished error.'

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].id, '47cec963-fcd2-482f-bdb6-24461b2d47b1')
        self.assertEqual(
            nodes[0].public_ips,
            ['185.98.122.176', '2a06:c01:1:1902::7ab0:176']
        )

    def test_reboot_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_create_node_success(self):
        test_size = self.driver.list_sizes()[0]
        test_image = self.driver.list_images()[0]
        created_node = self.driver.create_node('node-name', test_size, test_image)
        self.assertEqual(created_node.id, "47cec963-fcd2-482f-bdb6-24461b2d47b1")

    def test_destroy_node_success(self):
        node = self.driver.list_nodes()[0]
        result = self.driver.destroy_node(node)
        self.assertTrue(result)


class CloudscaleMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('cloudscale')

    def _v1_images(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_flavors(self, method, url, body, headers):
        body = self.fixtures.load('list_sizes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_servers(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_nodes.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load('create_node.json')
            response = httplib.responses[httplib.CREATED]
            return (httplib.CREATED, body, {}, response)

    def _v1_servers_47cec963_fcd2_482f_bdb6_24461b2d47b1(self, method, url, body, headers):
        assert method == 'DELETE'
        return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])

    def _v1_servers_47cec963_fcd2_482f_bdb6_24461b2d47b1_reboot(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
