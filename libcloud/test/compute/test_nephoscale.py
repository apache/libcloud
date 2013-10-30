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
from libcloud.compute.drivers.nephoscale import NephoscaleNodeDriver
from libcloud.compute.types import NodeState

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import NEPHOSCALE_PARAMS


class NephoscaleTests(unittest.TestCase):
    def setUp(self):
        NephoscaleNodeDriver.connectionCls.conn_classes = \
            (None, NephoscaleMockHttp)
        NephoscaleMockHttp.type = None
        self.driver = NephoscaleNodeDriver(*NEPHOSCALE_PARAMS)


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

    def test_list_all_keys(self):
        keys = self.driver.list_all_keys()
        self.assertEqual(len(keys), 1)

        self.assertEqual(keys[0].id, 7717)
        self.assertEqual(keys[0].name, 'test1')
        self.assertEqual(keys[0].pub_key, None)



class NephoscaleMockHttp(MockHttp):

    def _sizes(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

   

if __name__ == '__main__':
    sys.exit(unittest.main())
