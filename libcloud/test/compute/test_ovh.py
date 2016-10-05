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
from mock import patch

from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.ovh import OvhNodeDriver

from libcloud.test.common.test_ovh import BaseOvhMockHttp
from libcloud.test.secrets import OVH_PARAMS
from libcloud.test.file_fixtures import ComputeFileFixtures


class OvhMockHttp(BaseOvhMockHttp):
    """Fixtures needed for tests related to rating model"""
    fixtures = ComputeFileFixtures('ovh')

    def _json_1_0_auth_time_get(self, method, url, body, headers):
        body = self.fixtures.load('auth_time_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_region_get(self, method, url, body, headers):
        body = self.fixtures.load('region_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_get(self, method, url, body, headers):
        body = self.fixtures.load('flavor_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_region_SBG1_get(self, method, url, body, headers):
        body = self.fixtures.load('flavor_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_foo_id_get(self, method, url, body, headers):
        body = self.fixtures.load('flavor_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_image_get(self, method, url, body, headers):
        body = self.fixtures.load('image_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_image_foo_id_get(self, method, url, body, headers):
        body = self.fixtures.load('image_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_sshkey_region_SBG1_get(self, method, url, body, headers):
        body = self.fixtures.load('ssh_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_sshkey_post(self, method, url, body, headers):
        body = self.fixtures.load('ssh_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_ssh_mykey_get(self, method, url, body, headers):
        body = self.fixtures.load('ssh_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_get(self, method, url, body, headers):
        body = self.fixtures.load('instance_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_foo_get(self, method, url, body, headers):
        body = self.fixtures.load('instance_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_foo_delete(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_post(self, method, url, body, headers):
        body = self.fixtures.load('instance_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_get(self, method, url, body, headers):
        body = self.fixtures.load('volume_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_post(self, method, url, body, headers):
        body = self.fixtures.load('volume_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_get(self, method, url, body, headers):
        body = self.fixtures.load('volume_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_delete(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_attach_post(self, method, url, body, headers):
        body = self.fixtures.load('volume_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_detach_post(self, method, url, body, headers):
        body = self.fixtures.load('volume_get_detail.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


@patch('libcloud.common.ovh.OvhConnection._timedelta', 42)
class OvhTests(unittest.TestCase):
    def setUp(self):
        OvhNodeDriver.connectionCls.conn_classes = (
            OvhMockHttp, OvhMockHttp)
        OvhMockHttp.type = None
        self.driver = OvhNodeDriver(*OVH_PARAMS)

    def test_list_locations(self):
        images = self.driver.list_locations()
        self.assertTrue(len(images) > 0)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) > 0)

    def test_get_image(self):
        image = self.driver.get_image('foo-id')
        self.assertEqual(image.id, 'foo-id')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) > 0)

    def test_get_size(self):
        size = self.driver.ex_get_size('foo-id')
        self.assertEqual(size.id, 'foo-id')

    def test_list_key_pairs(self):
        keys = self.driver.list_sizes()
        self.assertTrue(len(keys) > 0)

    def test_get_key_pair(self):
        location = self.driver.list_locations()[0]
        key = self.driver.get_key_pair('mykey', location)
        self.assertEqual(key.name, 'mykey')

    def test_import_key_pair_from_string(self):
        location = self.driver.list_locations()[0]
        key = self.driver.import_key_pair_from_string('mykey', 'material',
                                                      location)
        self.assertEqual(key.name, 'mykey')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(len(nodes) > 0)

    def test_get_node(self):
        node = self.driver.ex_get_node('foo')
        self.assertEqual(node.name, 'test_vm')

    def test_create_node(self):
        location = self.driver.list_locations()[0]
        image = self.driver.list_sizes(location)[0]
        size = self.driver.list_sizes(location)[0]
        node = self.driver.create_node(name='test_vm', image=image, size=size,
                                       location=location)
        self.assertEqual(node.name, 'test_vm')

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertTrue(len(volumes) > 0)

    def test_get_volume(self):
        volume = self.driver.ex_get_volume('foo')
        self.assertEqual(volume.name, 'testvol')

    def test_create_volume(self):
        location = self.driver.list_locations()[0]
        volume = self.driver.create_volume(size=10, name='testvol',
                                           location=location)
        self.assertEqual(volume.name, 'testvol')

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        self.driver.destroy_volume(volume)

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.ex_get_volume('foo')
        response = self.driver.attach_volume(node=node, volume=volume)
        self.assertTrue(response)

    def test_detach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.ex_get_volume('foo')
        response = self.driver.detach_volume(ex_node=node, volume=volume)
        self.assertTrue(response)

if __name__ == '__main__':
    sys.exit(unittest.main())
