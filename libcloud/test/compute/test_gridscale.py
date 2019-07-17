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

from datetime import datetime
from libcloud.utils.iso8601 import UTC

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.gridscale import GridscaleNodeDriver
from libcloud.compute.base import NodeSize

from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import GRIDSCALE_PARAMS


class Gridscale_Tests(LibcloudTestCase):
    def setUp(self):
        GridscaleNodeDriver.connectionCls.conn_class = GridscaleMockHttp
        GridscaleMockHttp.type = None
        self.driver = GridscaleNodeDriver(*GRIDSCALE_PARAMS)

    def test_create_node_success(self):
        image = self.driver.list_images()[0]
        size = NodeSize(id=0, name='test', bandwidth=0, price=0, ram=10240,
                        driver=self.driver, disk=50, extra={'cores': 2})
        location = self.driver.list_locations()[0]
        sshkey = ["b1682d3a-1869-4bdc-8ffe-e74a261d300c"]
        GridscaleMockHttp.type = 'POST'
        node = self.driver.create_node(name='test', size=size, image=image,
                                       location=location, ex_ssh_key_ids=sshkey)

        self.assertEqual(node.name, 'test.test')
        self.assertEqual(node.public_ips, ['185.102.95.236', '2a06:2380:0:1::211'])

    def test_create_image_success(self):
        node = self.driver.list_nodes()[0]
        GridscaleMockHttp.type = 'POST'
        image = self.driver.create_image(node, 'test.test')
        self.assertTrue(image)

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, 'test.test')
        self.assertEqual(nodes[0].public_ips, ['185.102.95.236', '2a06:2380:0:1::211'])
        self.assertEqual(nodes[0].extra['cores'], 2)
        self.assertEqual(nodes[0].extra['memory'], 10240)

    def test_list_locations_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 1)
        volume = volumes[0]
        self.assertEqual(volume.id, "e66bb753-4a03-4ee2-a069-a601f393c9ee")
        self.assertEqual(volume.name, "linux")
        self.assertEqual(volume.size, 50)
        self.assertEqual(volume.driver, self.driver)

    def test_list_images_success(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)

        image = images[0]
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0].name, 'karl')
        self.assertEqual(keys[0].public_key, "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC")

    def test_list_volume_snapshots(self):
        volume = self.driver.list_volumes()[0]
        snapshots = self.driver.list_volume_snapshots(volume)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].id, "d755de62-4d75-4d61-addd-a5c9743a5deb")

    def test_list_volumes_empty(self):
        GridscaleMockHttp.type = 'EMPTY'
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 0)

    def test_ex_list_networks(self):
        networks = self.driver.ex_list_networks()[0]
        self.assertEqual(networks.id, "1196529b-a8de-417f")

    def test_ex_list_ips(self):
        ip = self.driver.ex_list_ips()[0]
        self.assertEqual(ip.id, "56b8d161-325b-4fd4")

    def test_ex_destroy_ip(self):
        ip = self.driver.ex_list_ips()[0]

        GridscaleMockHttp.type = 'DELETE'
        self.assertTrue(self.driver.ex_destroy_ip(ip))

    def test_ex_destroy_network(self):
        network = self.driver.ex_list_networks()[0]

        GridscaleMockHttp.type = 'DELETE'
        self.assertTrue(self.driver.ex_destroy_network(network))

    def test_destroy_node_success(self):
        # Regular destroy
        node = self.driver.list_nodes()[0]
        GridscaleMockHttp.type = 'DELETE'

        res = self.driver.destroy_node(node)
        self.assertTrue(res)

        # Destroy associated resources
        res = self.driver.destroy_node(node, ex_destroy_associated_resources=True)
        self.assertTrue(res)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        GridscaleMockHttp.type = 'DELETE'
        res = self.driver.destroy_volume(volume)
        self.assertTrue(res)

    def test_destroy_volume_snapshot(self):
        volume = self.driver.list_volumes()[0]
        snapshot = self.driver.list_volume_snapshots(volume)[0]
        GridscaleMockHttp.type = 'DELETE'
        res = self.driver.destroy_volume_snapshot(snapshot)
        self.assertTrue(res)

    def test_get_image_success(self):
        image = self.driver.get_image("12345")
        self.assertEqual(image.id, "12345")

    def test_list_nodes_fills_created_datetime(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(nodes[0].created_at, datetime(2019, 6, 7, 12, 56, 44, tzinfo=UTC))

    def test_ex_list_volumes_for_node(self):
        node = self.driver.list_nodes()[0]
        volumes = self.driver.ex_list_volumes_for_node(node=node)
        self.assertEqual(len(volumes), 1)
        self.assertEqual(volumes[0].size, 50)

    def test_ex_list_ips_for_node(self):
        node = self.driver.list_nodes()[0]
        ips = self.driver.ex_list_ips_for_node(node=node)
        self.assertEqual(len(ips), 1)
        self.assertEqual(ips[0].ip_address, '185.102.95.236')

    def test_ex_rename_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.ex_rename_node(node, name='new-name'))

    def test_ex_rename_volume(self):
        volume = self.driver.list_volumes()[0]
        self.assertTrue(self.driver.ex_rename_volume(volume, name='new-name'))

    def test_ex_network(self):
        network = self.driver.ex_list_networks()[0]
        self.assertTrue(self.driver.ex_rename_network(network, name='new-name'))


class GridscaleMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('gridscale')

    def _objects_servers(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_locations(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_storages(self, method, url, body, headers):
        body = self.fixtures.load('list_volumes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_storages_DELETE(self, method, url, body, headers):
        # test_destroy_node_success
        body = self.fixtures.load('list_volumes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_ips_DELETE(self, method, url, body, headers):
        # test_destroy_node_success
        body = self.fixtures.load('ex_list_ips.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_ips_56b8d161_325b_4fd4_DELETE(self, method, url, body, headers):
        # test_destroy_node_success
        return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])

    def _objects_storages_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_volumes_empty.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_templates(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_sshkeys(self, method, url, body, headers):
        body = self.fixtures.load('list_key_pairs.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee_snapshots(
        self, method, url, body, headers):
        body = self.fixtures.load('list_volume_snapshots.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f(
        self, method, url, body, headers):
        # test_ex_rename_node
        if method == 'PATCH':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee(
        self, method, url, body, headers):
        # test_ex_rename_node
        if method == 'PATCH':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_networks_1196529b_a8de_417f(
        self, method, url, body, headers):
        # test_ex_rename_network
        if method == 'PATCH':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_servers_POST(self, method, url, body, headers):
        # create_node
        if method == 'POST':
            body = self.fixtures.load('create_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _requests_x123xx1x_123x_1x12_123x_123xxx123x1x_POST(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('create_node_response_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_690de890_13c0_4e76_8a01_e10ba8786e53_POST(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('create_node_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    # create_volume
    def _objects_storages_POST(self, method, url, body, headers):
        body = self.fixtures.load('create_volume.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_storages_690de890_13c0_4e76_8a01_e10ba8786e53_POST(self, method,
                                                                    url, body, headers):
        body = self.fixtures.load('create_volume_response_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_ips_POST(self, method, url, body, headers):
        # ex_create_ip
        if method == 'POST':
            body = self.fixtures.load('create_ip.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_ips_690de890_13c0_4e76_8a01_e10ba8786e53_POST(self, method, url,
                                                                body, headers):
        body = self.fixtures.load('create_ip_response_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_storages_POST(self, method, url, body, headers):
        body = self.fixtures.load('volume_to_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_ips_POST(self, method, url, body, headers):
        body = self.fixtures.load('ips_to_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_networks_POST(self, method, url, body, headers):
        body = self.fixtures.load('create_network.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_networks_1196529b_a8de_417f_DELETE(self, method, url, body, headers):
        # test_ex_destroy_network
        if method == 'DELETE':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_networks_POST(self, method, url, body, headers):
        body = self.fixtures.load('network_to_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_power_POST(self, method, url, body, headers):
        if method == 'PATCH':
            body = self.fixtures.load('ex_start_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_POST(self, method, url, body, headers):
        body = self.fixtures.load('create_node_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_networks(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('ex_list_networks.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_ips(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('ex_list_ips.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_servers_1479405e_d46c_47a2_91e8_eb43951c899f_DELETE(self, method, url, body, headers):
        if method == 'DELETE':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee_DELETE(self, method, url, body, headers):
        if method == 'DELETE':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee_snapshots_d755de62_4d75_4d61_addd_a5c9743a5deb_DELETE(self, method, url, body, headers):
        if method == 'DELETE':
            return (httplib.NO_CONTENT, None, {}, httplib.responses[httplib.NO_CONTENT])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_templates_POST(self, method, url, body, headers):
        # create_image
        if method == 'POST':
            body = self.fixtures.load('create_image.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee_snapshots_POST(self, method, url, body, headers):
        # create_image
        if method == 'POST':
            body = self.fixtures.load('create_image.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_storages_e66bb753_4a03_4ee2_a069_a601f393c9ee_snapshots_690de890_13c0_4e76_8a01_e10ba8786e53_POST(self, method, url, body, headers):
        # create_image
        body = self.fixtures.load('create_image_dict.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _objects_templates_690de890_13c0_4e76_8a01_e10ba8786e53_POST(self, method, url, body, headers):
        # create_image
        if method == 'GET':
            body = self.fixtures.load('create_image_dict.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')

    def _objects_templates_12345(self, method, url, body, headers):
        # get_image
        if method == 'GET':
            body = self.fixtures.load('get_image.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:  # pragma: no cover
            raise ValueError('Invalid method')


if __name__ == '__main__':
    sys.exit(unittest.main())
