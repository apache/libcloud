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
from libcloud.utils.py3 import httplib

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.brightbox import BrightboxNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import BRIGHTBOX_PARAMS


class BrightboxTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        BrightboxNodeDriver.connectionCls.conn_classes = (None, BrightboxMockHttp)
        BrightboxMockHttp.type = None
        self.driver = BrightboxNodeDriver(*BRIGHTBOX_PARAMS)

    def test_authentication(self):
        BrightboxMockHttp.type = 'INVALID_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

        BrightboxMockHttp.type = 'UNAUTHORIZED_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertTrue('109.107.42.129' in nodes[0].public_ips)
        self.assertTrue('10.110.24.54' in nodes[0].private_ips)
        self.assertEqual(nodes[0].state, NodeState.RUNNING)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 1)
        self.assertEqual(sizes[0].id, 'typ-4nssg')
        self.assertEqual(sizes[0].name, 'Brightbox Nano Instance')
        self.assertEqual(sizes[0].ram, 512)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].id, 'img-9vxqi')
        self.assertEqual(images[0].name, 'Brightbox Lucid 32')
        self.assertEqual(images[0].extra['arch'], '32-bit')

    def test_reboot_node_response(self):
        node = self.driver.list_nodes()[0]
        self.assertRaises(NotImplementedError, self.driver.reboot_node, [node])

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='Test Node', image=image, size=size)
        self.assertEqual('srv-3a97e', node.id)
        self.assertEqual('Test Node', node.name)


class BrightboxMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('brightbox')

    def _token(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.OK, self.fixtures.load('token.json'))

    def _token_INVALID_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.BAD_REQUEST, '{"error":"invalid_client"}')

    def _token_UNAUTHORIZED_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.UNAUTHORIZED, '{"error":"unauthorized_client"}')

    def _1_0_images(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_images.json'))

    def _1_0_servers(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_servers.json'))
        elif method == 'POST':
            body = json.loads(body)

            node = json.loads(self.fixtures.load('create_server.json'))

            node['name'] = body['name']

            return self.response(httplib.ACCEPTED, json.dumps(node))

    def _1_0_servers_srv_3a97e(self, method, url, body, headers):
        if method == 'DELETE':
            return self.response(httplib.ACCEPTED, '')

    def _1_0_server_types(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_server_types.json'))

    def _1_0_zones(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_zones.json'))

    def response(self, status, body):
        return (status, body, {'content-type': 'application/json'}, httplib.responses[status])


if __name__ == '__main__':
    sys.exit(unittest.main())
