# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
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

from libcloud.drivers.opennebula import OpenNebulaNodeDriver
from libcloud.base import Node, NodeImage, NodeSize

from test import MockHttp, TestCaseMixin
from test.file_fixtures import FileFixtures

import httplib

from secrets import OPENNEBULA_USER, OPENNEBULA_KEY

class OpenNebulaTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        OpenNebulaNodeDriver.connectionCls.conn_classes = (None, OpenNebulaMockHttp)
        self.driver = OpenNebulaNodeDriver(OPENNEBULA_USER, OPENNEBULA_KEY)

    def test_create_node(self):
        image = NodeImage(id=1, name='UbuntuServer9.04-Contextualized', driver=self.driver)
        size = NodeSize(1, 'small', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='MyCompute', image=image, size=size)
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'MyCompute')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        node = nodes[0]
        self.assertEqual(node.id, '5')
        self.assertEqual(node.name, 'MyCompute')

    def test_reboot_node(self):
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node(5, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 3)
        self.assertTrue('small' in [ s.name for s in sizes])
        self.assertTrue('medium' in [ s.name for s in sizes])
        self.assertTrue('large' in [ s.name for s in sizes])

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 2)
        image = images[0]
        self.assertEqual(image.id, '1')
        self.assertEqual(image.name, 'UbuntuServer9.04-Contextualized')

class OpenNebulaMockHttp(MockHttp):

    fixtures = FileFixtures('opennebula')

    def _compute(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('computes.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'POST':
            body = self.fixtures.load('compute.xml')
            return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _storage(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('storage.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _compute_5(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('compute.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        if method == 'PUT':
            body = ""
            return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

        if method == 'DELETE':
            body = ""
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _compute_15(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('compute.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _storage_1(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('disk.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _storage_8(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('disk.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
