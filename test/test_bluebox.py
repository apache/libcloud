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
import exceptions

from libcloud.drivers.bluebox import BlueboxNodeDriver as Bluebox
from libcloud.base import Node
from libcloud.types import NodeState

import httplib

from test import MockHttp
from test.file_fixtures import FileFixtures

from secrets import BLUEBOX_CUSTOMER_ID, BLUEBOX_API_KEY

class BlueboxTest(unittest.TestCase):

    def setUp(self):
        Bluebox.connectionCls.conn_classes = (None, BlueboxMockHttp)
        self.driver = Bluebox(BLUEBOX_CUSTOMER_ID, BLUEBOX_API_KEY)

    def test_create_node(self):
        node = self.driver.create_node(
          product='94fd37a7-2606-47f7-84d5-9000deda52ae',
          template='c66b8145-f768-45ef-9878-395bf8b1b7ff',
          password='testpass',
          username='deploy',
          hostname='foo'
        )
        self.assertEqual(node.name, 'foo')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.name, 'foo')
        self.assertEqual(node.state, NodeState.RUNNING)

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

class BlueboxMockHttp(MockHttp):

    fixtures = FileFixtures('bluebox')


if __name__ == '__main__':
    sys.exit(unittest.main())
