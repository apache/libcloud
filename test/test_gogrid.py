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
    import json
except ImportError:
    import simplejson as json

from libcloud.drivers.gogrid import GoGridNodeDriver
from libcloud.base import Node, NodeImage, NodeSize

from test import MockHttp, TestCaseMixin
from test.file_fixtures import FileFixtures

import httplib

class GoGridTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        GoGridNodeDriver.connectionCls.conn_classes = (None, GoGridMockHttp)
        self.driver = GoGridNodeDriver("foo", "bar")

    def test_create_node(self):
        image = NodeImage(1531, None, self.driver)
        size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)

        node = self.driver.create_node(name='test1', image=image, size=size)
        self.assertEqual(node.name, 'test1')
        self.assertTrue(node.id is not None)

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, 90967)

    def test_reboot_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 4)
        self.assertEqual(image.name, 'CentOS 5.3 (32-bit) w/ None')
        self.assertEqual(image.id, 1531)

class GoGridMockHttp(MockHttp):

    fixtures = FileFixtures('gogrid')

    def _api_grid_image_list(self, method, url, body, headers):
        body = self.fixtures.load('image_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_list(self, method, url, body, headers):
        body = self.fixtures.load('server_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_power(self, method, url, body, headers):
        body = self.fixtures.load('server_power.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_add(self, method, url, body, headers):
        body = self.fixtures.load('server_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_delete(self, method, url, body, headers):
        body = self.fixtures.load('server_delete.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
