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
import re
import json
import base64

from libcloud.utils.py3 import httplib, ensure_string
from libcloud.compute.drivers.kamatera import KamateraNodeDriver, KamateraResponse
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, NodeAuthSSHKey, Node
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
        # KamateraNodeDriver.connectionCls.conn_class = KamateraMockHttp
        self.driver = KamateraNodeDriver(*KAMATERA_PARAMS)
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
        self.small_node_size = NodeSize(
            id='small',
            name='small',
            ram=4096,
            disk=30,
            bandwidth=0,
            price=0,
            driver=self.driver,
            extra={'cpuType': 'B', 'cpuCores': 2, 'monthlyTrafficPackage': 't5000',
                   'extraDiskSizesGB': []})

    def test_creating_driver(self):
        cls = providers.get_driver(Provider.KAMATERA)
        self.assertIs(cls, KamateraNodeDriver)

    def test_features(self):
        features = self.driver.features['create_node']
        self.assertIn('password', features)

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
        self.assertEqual(set(['cpuTypes', 'defaultMonthlyTrafficPackage', 'diskSizeGB',
                             'monthlyTrafficPackage']), set(capabilities.keys()))
        self.assertTrue(len(capabilities['cpuTypes']), 4)
        self.assertEqual(set(['id', 'description', 'name', 'ramMB', 'cpuCores']),
                         set(capabilities['cpuTypes'][0]))

    def test_create_node(self):
        node = self.driver.create_node(name='test_server', size=self.small_node_size,
                                       image=self.centos_8_EU_node_image, location=self.eu_node_location,
                                       )

        self.assertTrue(re.match('^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$', node.id))
        self.assertEqual(node.name, 'test_server')
        self.assertEqual(node.state, NodeState.STARTING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)
        self.assertTrue(len(node.extra['password']) > 0)
        self.assertTrue(len(node.extra['vnc_password']) > 0)

    def test_create_node_with_ssh_keys(self):
        image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                          name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                          extra={'type': 'template'},
                          driver=self.driver)
        location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver=self.driver)
        size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                        extra={'storage_tier': 'maxiops'}, price=None, driver=self.driver)

        auth = NodeAuthSSHKey('publikey')
        node = self.driver.create_node(name='test_server', size=size, image=image, location=location, auth=auth)
        self.assertTrue(re.match('^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$', node.id))
        self.assertEqual(node.name, 'test_server')
        self.assertEqual(node.state, NodeState.STARTING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()

        self.assertTrue(len(nodes) >= 1)
        node = nodes[0]
        self.assertEqual(node.name, 'test_server')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        success = self.driver.reboot_node(nodes[0])
        self.assertTrue(success)

    def test_destroy_node(self):
        if KamateraNodeDriver.connectionCls.conn_class == KamateraMockHttp:
            nodes = [Node(id='00893c98_5d5a_4363_b177_88df518a2b60', name='', state='',
                          public_ips=[], private_ips=[], driver=self.driver)]
        else:
            nodes = self.driver.list_nodes()
        success = self.driver.destroy_node(nodes[0])
        self.assertTrue(success)

    def assert_object(self, expected_object, objects):
        same_data = any([self.objects_equals(expected_object, obj) for obj in objects])
        self.assertTrue(same_data, "Objects does not match (%s, %s)" % (expected_object, objects[:2]))

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
            if isinstance(d1[key], KamateraMonthlyTrafficPackage):
                if d1[key].id != d2[key].id or d1[key].description != d2[key].description:
                    return False
            elif d1[key] != d2[key]:
                return False

        return True


class KamateraMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('kamatera')

    def _service_server(self, method, url, body, headers):
        client_id, secret = headers['AuthClientId'], headers['AuthSecret']
        if client_id == 'nosuchuser' and secret == 'nopwd':
            body = self.fixtures.load('failed_auth.json')
            status = httplib.UNAUTHORIZED
        else:
            body = self.fixtures.load({
                '/service/server?datacenter=1': 'datacenters.json',
                '/service/server?sizes=1&datecenter=EU': 'sizes_datacenter_EU.json',
                '/service/server?images=1&datacenter=EU': 'images_datacenter_EU.json',
                '/service/server?images=1&datacenter=': 'images_datacenter_EU.json',
                '/service/server?capabilities=1&datacenter=EU': 'capabilities_datacenter_EU.json',
                '/service/server': 'create_Server.json'
            }[url])
            status = httplib.OK
        return status, body, {}, httplib.responses[status]


if __name__ == '__main__':
    sys.exit(unittest.main())
