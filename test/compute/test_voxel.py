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
import httplib

from libcloud.compute.drivers.voxel import VoxelNodeDriver as Voxel
from libcloud.compute.types import InvalidCredsError

from test import MockHttp
from test.file_fixtures import ComputeFileFixtures

from test.secrets import VOXEL_KEY, VOXEL_SECRET

class VoxelTest(unittest.TestCase):

    def setUp(self):

        Voxel.connectionCls.conn_classes = (None, VoxelMockHttp)
        VoxelMockHttp.type = None
        self.driver = Voxel(VOXEL_KEY, VOXEL_SECRET)

    def test_auth_failed(self):
        VoxelMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_nodes()
        except Exception, e:
            self.assertTrue(isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        VoxelMockHttp.type = 'LIST_NODES'
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, 'www.voxel.net')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()

        self.assertEqual(len(sizes), 13)

    def test_list_images(self):
        VoxelMockHttp.type = 'LIST_IMAGES'
        images = self.driver.list_images()

        self.assertEqual(len(images), 1)

    def test_list_locations(self):
        VoxelMockHttp.type = 'LIST_LOCATIONS'
        locations = self.driver.list_locations()

        self.assertEqual(len(locations), 2)
        self.assertEqual(locations[0].name, 'Amsterdam')

    def test_create_node(self):
        pass

    def test_reboot_node(self):
        pass

    def test_destroy_node(self):
        pass

class VoxelMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('voxel')

    def _UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load('unauthorized.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _LIST_NODES(self, method, url, body, headers):
        body = self.fixtures.load('nodes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _LIST_IMAGES(self, method, url, body, headers):
        body = self.fixtures.load('images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _LIST_LOCATIONS(self, method, url, body, headers):
        body = self.fixtures.load('locations.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
