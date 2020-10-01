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
#
# Maintainer: Jed Smith <jed@linode.com>
# Based upon code written by Alex Polvi <polvi@cloudkick.com>
#

import sys
import unittest
from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.linode import LinodeNodeDriver
from libcloud.compute.base import Node, NodeAuthPassword
from libcloud.compute.base import NodeAuthSSHKey, StorageVolume

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class LinodeTest(unittest.TestCase, TestCaseMixin):
    # The Linode test suite

    def setUp(self):
        LinodeNodeDriver.connectionCls.conn_class = LinodeMockHttp
        LinodeMockHttp.use_param = 'api_action'
        self.driver = LinodeNodeDriver('foo', api_version='3.0')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.id, "8098")
        self.assertEqual(node.name, 'api-node3')
        self.assertEqual(node.extra['PLANID'], '2')
        self.assertTrue('75.127.96.245' in node.public_ips)
        self.assertEqual(node.private_ips, [])

    def test_reboot_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        # An exception would indicate failure
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_create_node_password_auth(self):
        # Will exception on failure
        self.driver.create_node(name="Test",
                                location=self.driver.list_locations()[0],
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[6],
                                auth=NodeAuthPassword("test123"))

    def test_create_node_ssh_key_auth(self):
        # Will exception on failure
        node = self.driver.create_node(name="Test",
                                       location=self.driver.list_locations()[
                                           0],
                                       size=self.driver.list_sizes()[0],
                                       image=self.driver.list_images()[6],
                                       auth=NodeAuthSSHKey('foo'))
        self.assertTrue(isinstance(node, Node))

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 9)
        for size in sizes:
            self.assertEqual(size.ram, int(size.name.split(" ")[1]))

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 30)

    def test_create_node_response(self):
        # should return a node object
        node = self.driver.create_node(name="node-name",
                                       location=self.driver.list_locations()[
                                           0],
                                       size=self.driver.list_sizes()[0],
                                       image=self.driver.list_images()[0],
                                       auth=NodeAuthPassword("foobar"))
        self.assertTrue(isinstance(node, Node))

    def test_destroy_volume(self):
        # Will exception on failure
        node = self.driver.list_nodes()[0]
        volume = StorageVolume(id=55648, name="test", size=1024,
                               driver=self.driver, extra={"LINODEID": node.id})
        self.driver.destroy_volume(volume)

    def test_ex_create_volume(self):
        # should return a StorageVolume object
        node = self.driver.list_nodes()[0]
        volume = self.driver.ex_create_volume(size=4096,
                                              name="Another test image",
                                              node=node,
                                              fs_type="ext4")
        self.assertTrue(isinstance(volume, StorageVolume))

    def test_ex_list_volumes(self):
        # should return list of StorageVolume objects
        node = self.driver.list_nodes()[0]
        volumes = self.driver.ex_list_volumes(node=node)

        self.assertTrue(isinstance(volumes, list))
        self.assertTrue(isinstance(volumes[0], StorageVolume))
        self.assertEqual(len(volumes), 2)


class LinodeMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('linode')

    def _avail_datacenters(self, method, url, body, headers):
        body = self.fixtures.load('_avail_datacenters.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_linodeplans(self, method, url, body, headers):
        body = self.fixtures.load('_avail_linodeplans.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_distributions(self, method, url, body, headers):
        body = self.fixtures.load('_avail_distributions.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.create","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.create","DATA":{"JobID":1298,"DiskID":55647}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_delete(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.delete","DATA":{"JobID":1298,"DiskID":55648}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_createfromdistribution(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.disk.createFromDistribution","DATA":{"JobID":1298,"DiskID":55647}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_disk_list(self, method, url, body, headers):
        body = self.fixtures.load('_linode_disk_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_delete(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.delete","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_update(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.update","DATA":{"LinodeID":8098}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_reboot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.reboot","DATA":{"JobID":1305}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _avail_kernels(self, method, url, body, headers):
        body = self.fixtures.load('_avail_kernels.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_boot(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.boot","DATA":{"JobID":1300}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_config_create(self, method, url, body, headers):
        body = '{"ERRORARRAY":[],"ACTION":"linode.config.create","DATA":{"ConfigID":31239}}'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_list(self, method, url, body, headers):
        body = self.fixtures.load('_linode_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('_linode_ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _batch(self, method, url, body, headers):
        body = self.fixtures.load('_batch.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
