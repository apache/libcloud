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

from __future__ import with_statement
import sys
import json

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.kamatera import KamateraNodeDriver
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeImage, NodeLocation, NodeAuthSSHKey
from libcloud.common.exceptions import BaseHTTPError
from libcloud.compute import providers
from libcloud.test import LibcloudTestCase, unittest, MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import KAMATERA_PARAMS


class KamateraAuthenticationTests(LibcloudTestCase):

    def setUp(self):
        KamateraNodeDriver.connectionCls.conn_class = KamateraMockHttp
        self.driver = KamateraNodeDriver("nosuchuser", "nopwd")

    def test_authentication_fails(self):
        with self.assertRaises(BaseHTTPError):
            self.driver.list_locations()


class KamateraNodeDriverTests(LibcloudTestCase):

    def setUp(self):
        KamateraTestDriver.connectionCls.conn_class = KamateraMockHttp
        self.driver = KamateraTestDriver(*KAMATERA_PARAMS)
        self.eu_node_location = NodeLocation(
            id='EU',
            name='Amsterdam',
            country='The Netherlands',
            driver=self.driver)
        self.il_node_location = NodeLocation(
            id='IL',
            name='Rosh Haayin',
            country='Israel',
            driver=self.driver)
        self.centos_8_EU_node_image = NodeImage(
            id='EU:6000C2987c9641fd2619a149ba2ca01a',
            name='CentOS 8.0 64-bit - Minimal Configuration',
            driver=self.driver,
            extra={'datacenter': 'EU',
                   'os': 'CentOS',
                   'code': '8.0 64bit_minimal',
                   'osDiskSizeGB': 5,
                   "ramMBMin": {"A": 256, "B": 256, "T": 256, "D": 256}})
        self.small_node_size = self.driver.ex_get_size(
            ramMB=4096,
            diskSizeGB=30,
            cpuType='B',
            cpuCores=2,
            monthlyTrafficPackage='t5000',
            id='small',
            name='small')

    def test_creating_driver(self):
        cls = providers.get_driver(Provider.KAMATERA)
        self.assertIs(cls, KamateraNodeDriver)

    def test_features(self):
        features = self.driver.features['create_node']
        self.assertIn('password', features)
        self.assertIn('generates_password', features)
        self.assertIn('ssh_key', features)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) == 13)
        self.assert_object(self.il_node_location, objects=locations)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes(self.eu_node_location)
        self.assertTrue(len(sizes) >= 1)
        self.assert_object(self.small_node_size, objects=sizes)

    def test_list_images(self):
        images = self.driver.list_images(self.eu_node_location)
        self.assertTrue(len(images) > 10)
        self.assert_object(self.centos_8_EU_node_image, objects=images)

    def test_ex_list_capabilities(self):
        capabilities = self.driver.ex_list_capabilities(self.eu_node_location)
        self.assertEqual(
            set(['cpuTypes', 'defaultMonthlyTrafficPackage', 'diskSizeGB',
                 'monthlyTrafficPackage']), set(capabilities.keys()))
        self.assertTrue(len(capabilities['cpuTypes']), 4)
        self.assertEqual(
            set(['id', 'description', 'name', 'ramMB', 'cpuCores']),
            set(capabilities['cpuTypes'][0]))

    def test_create_node(self):
        node = self.driver.create_node(
            name='test_server', size=self.small_node_size,
            image=self.centos_8_EU_node_image, location=self.eu_node_location)

        self.assertTrue(len(node.id) > 8)
        self.assertEqual(node.name, 'my-server')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)
        self.assertTrue(len(node.extra['generated_password']) > 0)

    def test_create_node_with_ssh_keys(self):
        node = self.driver.create_node(
            name='test_server_pubkey', size=self.small_node_size,
            image=self.centos_8_EU_node_image, location=self.eu_node_location,
            auth=NodeAuthSSHKey('publickey'))

        self.assertTrue(len(node.id) > 8)
        self.assertEqual(node.name, 'my-server')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)
        self.assertFalse('generated_password' in node.extra)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(len(nodes) >= 1)
        node = nodes[0]
        self.assertEqual(node.name, 'test_server')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.driver, self.driver)

    def test_list_nodes_full(self):
        nodes = self.driver.list_nodes(ex_full_details=True)
        self.assertTrue(len(nodes) >= 1)
        node = nodes[0]
        self.assertEqual(node.name, 'my-server')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        success = self.driver.reboot_node(nodes[0])
        self.assertTrue(success)

    def assert_object(self, expected_object, objects):
        same_data = any([self.objects_equals(
            expected_object, obj) for obj in objects])
        self.assertTrue(
            same_data, "Objects does not match (%s, %s)" % (
                expected_object, objects[:2]))

    def objects_equals(self, expected_obj, obj):
        for name in vars(expected_obj):
            expected_data = getattr(expected_obj, name)
            actual_data = getattr(obj, name)
            same_data = self.data_equals(expected_data, actual_data)
            if not same_data:
                break
        return same_data

    def data_equals(self, expected_data, actual_data):
        if isinstance(expected_data, dict):
            return self.dicts_equals(expected_data, actual_data)
        else:
            return expected_data == actual_data

    def dicts_equals(self, d1, d2):
        dict_keys_same = set(d1.keys()) == set(d2.keys())
        if not dict_keys_same:
            return False

        for key in d1.keys():
            if d1[key] != d2[key]:
                return False

        return True


class KamateraTestDriver(KamateraNodeDriver):

    def ex_wait_command(self, *args, **kwargs):
        kwargs['poll_interval_seconds'] = 0
        return KamateraNodeDriver.ex_wait_command(self, *args, **kwargs)


class KamateraMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('kamatera')

    def _service_server(self, method, url, body, headers):
        client_id, secret = headers['AuthClientId'], headers['AuthSecret']
        if client_id == 'nosuchuser' and secret == 'nopwd':
            body = self.fixtures.load('failed_auth.json')
            status = httplib.UNAUTHORIZED
        else:
            if url == '/service/server' and json.loads(body).get('ssh-key'):
                body = self.fixtures.load('create_server_sshkey.json')
            else:
                body = self.fixtures.load({
                    '/service/server?datacenter=1': 'datacenters.json',
                    '/service/server?sizes=1&datacenter=EU':
                        'sizes_datacenter_EU.json',
                    '/service/server?images=1&datacenter=EU':
                        'images_datacenter_EU.json',
                    '/service/server?capabilities=1&datacenter=EU':
                        'capabilities_datacenter_EU.json',
                    '/service/server': 'create_server.json'
                }[url])
            status = httplib.OK
        return status, body, {}, httplib.responses[status]

    def _service_queue(self, method, url, body, headers):
        if not hasattr(self, '_service_queue_call_count'):
            self._service_queue_call_count = 0
        self._service_queue_call_count += 1
        body = self.fixtures.load({
            '/service/queue?id=12345':
                'queue_12345-%s.json' % self._service_queue_call_count
        }[url])
        status = httplib.OK
        return status, body, {}, httplib.responses[status]

    def _service_server_info(self, method, url, body, headers):
        body = self.fixtures.load({
            "/service/server/info": "server_info.json"
        }[url])
        status = httplib.OK
        return status, body, {}, httplib.responses[status]

    def _service_servers(self, method, url, body, headers):
        body = self.fixtures.load({
            '/service/servers': 'servers.json'
        }[url])
        status = httplib.OK
        return status, body, {}, httplib.responses[status]

    def _service_server_reboot(self, method, url, body, headers):
        body = self.fixtures.load({
            '/service/server/reboot': 'server_operation.json'
        }[url])
        status = httplib.OK
        return status, body, {}, httplib.responses[status]


if __name__ == '__main__':
    sys.exit(unittest.main())
