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

import unittest
import sys

from libcloud.compute.base import Node
from libcloud.compute.drivers.onapp import OnAppNodeDriver
from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.test.secrets import ONAPP_PARAMS
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.utils.py3 import httplib


class OnAppNodeTestCase(LibcloudTestCase):
    driver_klass = OnAppNodeDriver

    def setUp(self):
        self.driver_klass.connectionCls.conn_class = OnAppMockHttp

        self.driver = OnAppNodeDriver(*ONAPP_PARAMS)

    def test_create_node(self):
        node = self.driver.create_node(
            name='onapp-new-fred',
            ex_memory=512,
            ex_cpus=4,
            ex_cpu_shares=4,
            ex_hostname='onapp-new-fred',
            ex_template_id='template_id',
            ex_primary_disk_size=100,
            ex_swap_disk_size=1,
            ex_required_virtual_machine_build=0,
            ex_required_ip_address_assignment=0
        )

        extra = node.extra

        self.assertEqual('onapp-new-fred', node.name)
        self.assertEqual('456789', node.id)
        self.assertEqual('456789', node.id)

        self.assertEqual('delivered', node.state)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('8.8.8.8', extra['local_remote_access_ip_address'])

        self.assertEqual(['192.168.15.73'], node.private_ips)
        self.assertEqual([], node.public_ips)

    def test_destroy_node(self):
        node = Node('identABC', 'testnode',
                    ['123.123.123.123'], [],
                    {'state': 'test', 'template_id': 88}, None)
        res = self.driver.destroy_node(node=node)
        self.assertTrue(res)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        extra = nodes[0].extra
        private_ips = nodes[0].private_ips

        self.assertEqual(1, len(nodes))
        self.assertEqual('onapp-fred', nodes[0].name)
        self.assertEqual('123456', nodes[0].id)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('9.9.9.9', extra['local_remote_access_ip_address'])

        self.assertEqual(1, len(private_ips))
        self.assertEqual('192.168.15.72', private_ips[0])

    def test_list_images(self):
        images = self.driver.list_images()
        extra = images[0].extra

        self.assertEqual(1, len(images))
        self.assertEqual('CentOS 5.11 x64', images[0].name)
        self.assertEqual('123456', images[0].id)

        self.assertEqual(True, extra['allowed_swap'])
        self.assertEqual(256, extra['min_memory_size'])
        self.assertEqual('rhel', extra['distribution'])

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(2, len(keys))
        self.assertEqual(1, keys[0].name)
        self.assertIsNotNone(keys[0].public_key)
        self.assertIsNotNone(keys[1].public_key)

    def test_get_key_pair(self):
        key = self.driver.get_key_pair(1)
        self.assertEqual(1, key.name)
        self.assertIsNotNone(key.public_key)

    def test_import_key_pair_from_string(self):
        key = self.driver.import_key_pair_from_string(
            'name',
            'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8uuUq')
        self.assertEqual(3, key.name)
        self.assertEqual(
            'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8uuUq',
            key.public_key)

    def test_delete_key_pair(self):
        key = self.driver.get_key_pair(1)
        response = self.driver.delete_key_pair(key)
        self.assertTrue(response)


class OnAppMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('onapp')

    def _virtual_machines_json(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_nodes.json')
        else:
            body = self.fixtures.load('create_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_identABC_json(self, method, url, body, headers):
        return (
            httplib.NO_CONTENT,
            '',
            {},
            httplib.responses[httplib.NO_CONTENT]
        )

    def _templates_json(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _profile_json(self, method, url, body, headers):
        body = self.fixtures.load('profile.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _users_123_ssh_keys_json(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_key_pairs.json')
        else:
            body = self.fixtures.load('import_key_pair.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _users_123_ssh_keys_1_json(self, method, url, body, headers):
        body = self.fixtures.load('get_key_pair.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _settings_ssh_keys_1_json(self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {},
                httplib.responses[httplib.NO_CONTENT])


if __name__ == '__main__':
    sys.exit(unittest.main())
