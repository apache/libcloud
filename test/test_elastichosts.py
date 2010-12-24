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
# Copyright 2009 RedRata Ltd

import sys
import unittest
import httplib

from libcloud.drivers.elastichosts import ElasticHostsBaseNodeDriver
from test import MockHttp, TestCaseMixin
from test.file_fixtures import FileFixtures

class ElasticHostsTestCase(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        ElasticHostsBaseNodeDriver.connectionCls.conn_classes = (None,
                                                            ElasticHostsHttp)
        self.driver = ElasticHostsBaseNodeDriver('foo', 'bar')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(isinstance(nodes, list))
        self.assertEqual(len(nodes), 1)
        
        node = nodes[0]
        self.assertEqual(node.public_ip[0], "1.2.3.4")
        self.assertEqual(node.public_ip[1], "1.2.3.5")
        self.assertEqual(node.extra['smp'], 1)

    def test_list_sizes(self):
        images = self.driver.list_sizes()
        self.assertEqual(len(images), 5)
        image = images[0]
        self.assertEqual(image.id, 'small')
        self.assertEqual(image.name, 'Small instance')
        self.assertEqual(image.cpu, 2000)
        self.assertEqual(image.ram, 1700)
        self.assertEqual(image.disk, 160)

    def test_list_images(self):
        sizes = self.driver.list_images()
        self.assertEqual(len(sizes), 8)
        size = sizes[0]
        self.assertEqual(size.id, '38df0986-4d85-4b76-b502-3878ffc80161')
        self.assertEqual(size.name, 'CentOS Linux 5.5')
        
    def test_list_locations_response(self):
        pass

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        self.assertTrue(self.driver.create_node(name="api.ivan.net.nz", image=image, size=size))

class ElasticHostsHttp(MockHttp):

    fixtures = FileFixtures('elastichosts')
    
    def _servers_b605ca90_c3e6_4cee_85f8_a8ebdf8f9903_reset(self, method, url, body, headers):
         return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
    
    def _servers_b605ca90_c3e6_4cee_85f8_a8ebdf8f9903_destroy(self, method, url, body, headers):
         return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
    
    def _drives_create(self, method, url, body, headers):
        body = self.fixtures.load('drives_create.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    
    def _drives_0012e24a_6eae_4279_9912_3432f698cec8_image_38df0986_4d85_4b76_b502_3878ffc80161_gunzip(self, method, url, body, headers):
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _drives_0012e24a_6eae_4279_9912_3432f698cec8_info(self, method, url, body, headers):
        body = self.fixtures.load('drives_info.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    
    def _servers_create(self, method, url, body, headers):
        body = self.fixtures.load('servers_create.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _servers_info(self, method, url, body, headers):
        body = self.fixtures.load('servers_info.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
