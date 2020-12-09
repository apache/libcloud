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

from libcloud.utils.py3 import httplib
from libcloud.compute.base import (Node,
                                   NodeState,
                                   NodeImage,
                                   StorageVolume)
from libcloud.compute.drivers.linode import LinodeNodeDriver
from libcloud.compute.drivers.linode import LinodeNodeDriverV4
from libcloud.common.linode import (LinodeExceptionV4,
                                    LinodeDisk,
                                    LinodeIPAddress)
from libcloud.common.types import LibcloudError, InvalidCredsError

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class LinodeTestsV4(unittest.TestCase, TestCaseMixin):
    should_list_volumes = True

    def setUp(self):
        LinodeNodeDriver.connectionCls.conn_class = LinodeMockHttpV4
        LinodeMockHttpV4.type = None
        self.driver = LinodeNodeDriver('foo', api_version='4.0')

    def test_unknown_api_version(self):
        self.assertRaises(NotImplementedError, LinodeNodeDriver,
                          'foo', api_version='2.0')

    def test_correct_class_is_used(self):
        self.assertIsInstance(self.driver, LinodeNodeDriverV4)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 28)
        size = sizes[0]
        self.assertEqual(size.id, 'g6-nanode-1')
        for size in sizes:
            self.assertIsInstance(size.price, float)
            if size.extra['class'] == 'gpu':
                self.assertGreater(size.extra['gpus'], 0)
            else:
                self.assertEqual(size.extra['gpus'], 0)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 34)
        image = images[0]
        self.assertEqual(image.id, 'linode/alpine3.10')
        self.assertEqual(image.extra['type'], 'manual')
        self.assertEqual(image.extra['vendor'], 'Alpine')
        for image in images:
            self.assertIsInstance(image.extra['size'], int)
            self.assertTrue(image.extra['is_public'])

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 10)
        location = locations[0]
        self.assertEqual(location.country, 'IN')
        self.assertEqual(location.id, 'ap-west')
        self.assertEqual(location.extra['status'], 'ok')
        self.assertIsInstance(location.extra['capabilities'], list)

    def test_create_node_response(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        node = self.driver.create_node(location=location,
                                       name='node-name',
                                       image=image,
                                       root_pass='test123456',
                                       size=size)
        self.assertTrue(isinstance(node, Node))

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        node = nodes[0]
        node_2 = nodes[1]
        self.assertEqual(node.id, '22344420')
        self.assertEqual(node.public_ips, ['138.89.34.81'])
        self.assertEqual(node.private_ips, ['192.168.1.230'])
        self.assertEqual(node.extra['hypervisor'], 'kvm')
        self.assertEqual(node_2.public_ips, ['156.12.197.243'])
        self.assertEqual(node_2.private_ips, [])

    def test_list_nodes_UNAUTHORIZED(self):
        LinodeMockHttpV4.type = 'UNAUTHORIZED'
        with self.assertRaises(InvalidCredsError):
            self.driver.list_nodes()

    def test_list_nodes_fills_datetime(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(nodes[0].created_at,
                         datetime(2020, 10, 8, 18, 51, 29))

    def test_create_node(self):
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]

        node = self.driver.create_node(location, size,
                                       image=image, name='TestNode',
                                       root_pass='test123456',
                                       ex_backups_enabled=True,
                                       ex_tags=['testing123'],
                                       ex_private_ip=True)

        self.assertEqual(node.name, 'TestNode')
        self.assertEqual(len(node.private_ips), 1)
        self.assertTrue(node.extra['backups']['enabled'])
        self.assertEqual(node.extra['tags'], ['testing123'])

    def test_create_node_no_root_pass(self):
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]

        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_node(location, size,
                                    image=image, name='TestNode')

    def test_create_node_no_image(self):
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]
        LinodeMockHttpV4.type = 'NO_IMAGE'
        node = self.driver.create_node(location, size,
                                       name='TestNode',
                                       ex_tags=['testing123'])

        self.assertIsNone(node.image)
        self.assertEqual(node.name, 'TestNode')
        self.assertFalse(node.extra['backups']['enabled'])
        self.assertEqual(node.extra['tags'], ['testing123'])
        self.assertEqual(len(node.private_ips), 0)

    def test_create_node_invalid_name(self):
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]

        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_node(location, size, name='Test__Node')
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_node(location, size, name='Test Node')
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_node(location, size, name='Test--Node')
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_node(location, size, name='Test..Node')

    def test_reboot_node(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_start_node(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        result = self.driver.start_node(node)
        self.assertTrue(result)

    def test_start_node_error(self):
        LinodeMockHttpV4.type = 'ALREADY_BOOTED'
        node = Node('22344420', None,
                    NodeState.RUNNING, None, None, driver=self.driver)
        with self.assertRaises(LibcloudError):
            self.driver.start_node(node)

    def test_stop_node(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        result = self.driver.stop_node(node)
        self.assertTrue(result)

    def test_destroy_node(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        result = self.driver.stop_node(node)
        self.assertTrue(result)

    def test_ex_rename_node(self):
        node = Node('22344420', 'name1', None, None, None, driver=self.driver)
        renamed_node = self.driver.ex_rename_node(node, 'new_name')
        self.assertEqual(renamed_node.name, 'new_name')

    def test_ex_resize_node(self):
        node = Node('22344420', None, None, None, None,
                    driver=self.driver, size='g6-nanode-1')
        size = self.driver.list_sizes()[0]
        result = self.driver.ex_resize_node(node, size=size)
        self.assertTrue(result)

    def test_ex_get_node(self):
        node_id = '22344420'
        node = self.driver.ex_get_node(node_id)
        self.assertEqual(node.name, 'test_2')
        self.assertEqual(node.image, 'linode/centos8')
        self.assertEqual(node.extra['tags'], ['testing'])
        self.assertEqual(node.public_ips, ['212.71.239.24'])
        self.assertEqual(node.extra['hypervisor'], 'kvm')

    def test_ex_list_disks(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        disks = self.driver.ex_list_disks(node)
        disk = disks[0]
        self.assertEqual(disk.name, 'CentOS 7 Disk')
        self.assertEqual(disk.size, 25088)
        for disk in disks:
            self.assertIsInstance(disk, LinodeDisk)

    def test_ex_create_disk(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        image = self.driver.list_images()[0]
        disk = self.driver.ex_create_disk(5000, 'TestDisk',
                                          node, 'ext4', image=image,
                                          ex_root_pass='testing123')
        self.assertIsInstance(disk, LinodeDisk)
        self.assertEqual(disk.size, 5000)
        self.assertEqual(disk.filesystem, 'ext4')
        self.assertEqual(disk.name, 'TestingDisk')

    def test_ex_create_disk_no_image(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        disk = self.driver.ex_create_disk(5000, 'TestDisk', node, 'ext4')
        self.assertIsInstance(disk, LinodeDisk)
        self.assertEqual(disk.size, 5000)
        self.assertEqual(disk.filesystem, 'ext4')
        self.assertEqual(disk.name, 'TestingDisk')

    def test_ex_create_disk_exception_no_root_pass(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        image = self.driver.list_images()[0]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.ex_create_disk(5000, 'TestDisk',
                                       node, 'ext4', image=image)

    def test_ex_create_disk_exception_invalid_fs(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        image = self.driver.list_images()[0]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.ex_create_disk(5000, 'TestDisk',
                                       node, 'random_fs', image=image,
                                       ex_root_pass='testing123')

    def test_ex_destroy_disk(self):
        node = Node('22344420', None, NodeState.STOPPED,
                    None, None, driver=self.driver)
        disk = LinodeDisk('23517413', None, None, None,
                          self.driver, None)
        result = self.driver.ex_destroy_disk(node, disk)
        self.assertTrue(result)

    def test_ex_destroy_disk_exception(self):
        node = Node('22344420', None, NodeState.RUNNING,
                    None, None, driver=self.driver)
        disk = LinodeDisk('23517413', None, None, None,
                          self.driver, None)
        with self.assertRaises(LinodeExceptionV4):
            self.driver.ex_destroy_disk(node, disk)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 2)
        volume = volumes[0]
        volume_2 = volumes[1]
        self.assertEqual(volume.id, '12345')
        self.assertEqual(volume.name, 'Testvolume1')
        self.assertEqual(volume.size, 100)
        self.assertEqual(volume.extra['linode_id'], 456353688)
        self.assertIsNone(volume_2.extra['linode_id'])

    def test_create_volume(self):
        node = Node('22344420', None, NodeState.RUNNING,
                    None, None, driver=self.driver)
        volume = self.driver.create_volume('Volume1', 50,
                                           node=node,
                                           tags=['test123', 'testing'])

        self.assertEqual(volume.extra['linode_id'], 22344420)
        self.assertEqual(volume.size, 50)
        self.assertEqual(volume.name, 'Volume1')
        self.assertEqual(volume.extra['tags'], ['test123', 'testing'])

    def test_create_volume_unattached(self):
        location = self.driver.list_locations()[0]
        LinodeMockHttpV4.type = 'UNATTACHED'
        volume = self.driver.create_volume('Volume1', 50,
                                           location=location,
                                           tags=['test123', 'testing'])

        self.assertEqual(volume.size, 50)
        self.assertEqual(volume.name, 'Volume1')
        self.assertEqual(volume.extra['tags'], ['test123', 'testing'])

    def test_create_volume_invalid_name(self):
        location = self.driver.list_locations()[0]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_volume('Volume__1', 50, location=location)
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_volume('Volume 1', 50, location=location)
        with self.assertRaises(LinodeExceptionV4):
            self.driver.create_volume('Volume--1', 50, location=location)

    def test_attach_volume_already_attached(self):
        volume = self.driver.list_volumes()[0]
        node = self.driver.list_nodes()[0]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.attach_volume(node, volume)

    def test_attach_volume(self):
        volume = self.driver.list_volumes()[1]
        node = self.driver.list_nodes()[0]
        attached_volume = self.driver.attach_volume(node, volume)
        self.assertIsInstance(attached_volume, StorageVolume)
        self.assertEqual(str(attached_volume.extra['linode_id']), node.id)

    def test_detach_volume(self):
        volume = self.driver.list_volumes()[0]
        result = self.driver.detach_volume(volume)
        self.assertTrue(result)

    def test_detach_volume_already_detached(self):
        volume = self.driver.list_volumes()[1]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.detach_volume(volume)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[1]
        result = self.driver.destroy_volume(volume)
        self.assertTrue(result)

    def test_destroy_volume_attached(self):
        volume = self.driver.list_volumes()[0]
        with self.assertRaises(LinodeExceptionV4):
            self.driver.destroy_volume(volume)

    def test_ex_resize_volume(self):
        volume = self.driver.list_volumes()[0]
        size = 200
        result = self.driver.ex_resize_volume(volume, size)
        self.assertTrue(result)

    def test_ex_resize_volume_resize_down(self):
        volume = self.driver.list_volumes()[0]
        size = 50
        with self.assertRaises(LinodeExceptionV4):
            self.driver.ex_resize_volume(volume, size)

    def test_ex_clone_volume(self):
        volume = self.driver.list_volumes()[0]
        cloned_volume = self.driver.ex_clone_volume(volume, 'TestingClone')
        self.assertIsInstance(cloned_volume, StorageVolume)
        self.assertEqual(volume.size, cloned_volume.size)
        self.assertEqual(cloned_volume.name, 'TestingClone')

    def test_ex_get_volume(self):
        volume_id = '123456'
        volume = self.driver.ex_get_volume(volume_id)

        self.assertEqual(volume.name, 'Testvolume1')
        self.assertEqual(volume.size, 10)
        self.assertEqual(volume.extra['linode_id'], 456353688)

    def test_create_image(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        disk = self.driver.ex_list_disks(node)[0]
        image = self.driver.create_image(disk, name='Test',
                                         description='Test Image')
        self.assertIsInstance(image, NodeImage)
        self.assertEqual(image.name, 'Test')
        self.assertEqual(image.extra['description'], 'Test Image')

    def test_delete_image(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        disk = self.driver.ex_list_disks(node)[0]
        image = self.driver.create_image(disk, name='Test',
                                         description='Test Image')
        result = self.driver.delete_image(image)
        self.assertTrue(result)

    def test_ex_list_addresses(self):
        ips = self.driver.ex_list_addresses()
        self.assertEqual(len(ips), 3)
        ip = ips[0]
        self.assertEqual(ip.inet, '192.168.15.21')
        self.assertEqual(ip.version, 'ipv4')
        self.assertFalse(ip.public)
        for ip in ips:
            self.assertIsInstance(ip, LinodeIPAddress)

    def test_ex_list_node_addresses(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        ips = self.driver.ex_list_node_addresses(node)
        ip = ips[0]
        self.assertEqual(ip.inet, '176.58.100.100')
        self.assertEqual(ip.version, 'ipv4')
        self.assertTrue(ip.public)
        for ip in ips:
            self.assertIsInstance(ip, LinodeIPAddress)
            self.assertEqual(node.id, str(ip.extra['node_id']))

    def test_ex_allocate_private_address(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        ip = self.driver.ex_allocate_private_address(node)
        self.assertIsInstance(ip, LinodeIPAddress)
        self.assertEqual(ip.version, 'ipv4')
        self.assertEqual(ip.inet, '192.168.100.10')

    def test_ex_share_address(self):
        node = Node('22344420', None, None, None, None, driver=self.driver)
        ips = self.driver.ex_list_addresses()
        result = self.driver.ex_share_address(node, ips)
        self.assertTrue(result)

    def test__paginated_request_two_pages(self):
        LinodeMockHttpV4.type = 'PAGINATED'
        images = self.driver.list_images()
        self.assertEqual(len(images), 34)


class LinodeMockHttpV4(MockHttp):
    fixtures = ComputeFileFixtures('linode_v4')

    def _v4_regions(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_images(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_images.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_image.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_images_PAGINATED(self, method, url, body, headers):
        if 'page=2' not in url:
            body = self.fixtures.load('list_images_paginated_page_1.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load('list_images_paginated_page_2.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_types(self, method, url, body, headers):
        body = self.fixtures.load('list_types.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_nodes.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_NO_IMAGE(self, method, url, body, headers):
        body = self.fixtures.load('create_node_no_image.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_UNAUTHORIZED(self, method, url, body, headers):
        body = '{"errors": [{"reason": "Invalid Token"}]}'
        return (httplib.UNAUTHORIZED, body,
                {}, httplib.responses[httplib.UNAUTHORIZED])

    def _v4_linode_instances_22344420_reboot(self, method, url,
                                             body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_boot(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_boot_ALREADY_BOOTED(self, method,
                                                          url, body, headers):
        body = '{"errors": [{"reason": "Linode 22344420 already booted."}]}'
        return (
            httplib.BAD_REQUEST, body, {},
            httplib.responses[httplib.BAD_REQUEST])

    def _v4_linode_instances_22344420_shutdown(self, method,
                                               url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420(self, method, url, body, headers):
        if method == 'DELETE':
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'PUT':
            body = self.fixtures.load('ex_rename_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'GET':
            body = self.fixtures.load('ex_get_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_resize(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_disks(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_disks.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_disk.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_disks_23517413(
            self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_volumes.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_volume.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_UNATTACHED(self, method, url, body, headers):
        body = self.fixtures.load('create_volume_unattached.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_123456_attach(self, method, url, body, headers):
        body = self.fixtures.load('attach_volume_to_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_12345_detach(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_123456(self, method, url, body, headers):
        if method == 'DELETE':
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'GET':
            body = self.fixtures.load('ex_get_volume.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_12345_resize(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_volumes_12345_clone(self, method, url, body, headers):
        body = self.fixtures.load('clone_volume.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_images_private_12345(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_networking_ips(self, method, url, body, headers):
        body = self.fixtures.load('list_addresses.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_linode_instances_22344420_ips(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_addresses_for_node.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('allocate_private_address.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_networking_ipv4_share(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
