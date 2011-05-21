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

from libcloud.compute.base import Node
from libcloud.compute.drivers.elastichosts import \
                              (ElasticHostsBaseNodeDriver as ElasticHosts,
                               ElasticHostsException)
from libcloud.common.types import InvalidCredsError, MalformedResponseError

from test import MockHttp
from test.file_fixtures import ComputeFileFixtures

class ElasticHostsTestCase(unittest.TestCase):

    def setUp(self):
        ElasticHosts.connectionCls.conn_classes = (None,
                                                            ElasticHostsHttp)
        ElasticHostsHttp.type = None
        self.driver = ElasticHosts('foo', 'bar')
        self.node = Node(id=72258, name=None, state=None, public_ip=None,
                         private_ip=None, driver=self.driver)

    def test_invalid_creds(self):
        ElasticHostsHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_nodes()
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_malformed_response(self):
        ElasticHostsHttp.type = 'MALFORMED'
        try:
            self.driver.list_nodes()
        except MalformedResponseError:
            pass
        else:
            self.fail('test should have thrown')

    def test_parse_error(self):
        ElasticHostsHttp.type = 'PARSE_ERROR'
        try:
            self.driver.list_nodes()
        except Exception, e:
            self.assertTrue(str(e).find('X-Elastic-Error') != -1)
        else:
            self.fail('test should have thrown')

    def test_ex_set_node_configuration(self):
        success = self.driver.ex_set_node_configuration(node=self.node,
                                                        name='name',
                                                        cpu='2')

    def test_ex_set_node_configuration_invalid_keys(self):
        try:
            self.driver.ex_set_node_configuration(node=self.node, foo='bar')
        except ElasticHostsException:
            pass
        else:
            self.fail('Invalid option specified, but an exception was not thrown')

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
        self.assertEqual(len(images), 6)
        image = [i for i in images if i.id == 'small'][0]
        self.assertEqual(image.id, 'small')
        self.assertEqual(image.name, 'Small instance')
        self.assertEqual(image.cpu, 2000)
        self.assertEqual(image.ram, 1700)
        self.assertEqual(image.disk, 160)
        self.assertTrue(isinstance(image.price, float))

    def test_list_images(self):
        sizes = self.driver.list_images()
        self.assertEqual(len(sizes), 8)
        size = [s for s in sizes if \
                s.id == '38df0986-4d85-4b76-b502-3878ffc80161'][0]
        self.assertEqual(size.id, '38df0986-4d85-4b76-b502-3878ffc80161')
        self.assertEqual(size.name, 'CentOS Linux 5.5')

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        sizes = self.driver.list_sizes()
        size = [s for s in sizes if \
                s.id == 'large'][0]
        images = self.driver.list_images()
        image = [i for i in images if \
                i.id == '38df0986-4d85-4b76-b502-3878ffc80161'][0]

        self.assertTrue(self.driver.create_node(name="api.ivan.net.nz",
                                                image=image, size=size))

class ElasticHostsHttp(MockHttp):

    fixtures = ComputeFileFixtures('elastichosts')

    def _servers_info_UNAUTHORIZED(self, method, url, body, headers):
         return (httplib.UNAUTHORIZED, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _servers_info_MALFORMED(self, method, url, body, headers):
         body = "{malformed: '"
         return (httplib.OK, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _servers_info_PARSE_ERROR(self, method, url, body, headers):
         return (505, body, {}, httplib.responses[httplib.NO_CONTENT])

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

    def _servers_72258_set(self, method, url, body, headers):
        body = '{}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
