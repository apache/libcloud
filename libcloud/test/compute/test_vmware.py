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


import os
import sys
import unittest
import uuid

import mock

from libcloud.compute.drivers import vmware
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState


class ExecuteMock(object):

    def __init__(self):
        self.stack = []

    def add(self, command, returncode=0, stdout="", stderr=""):
        self.stack.append((command, returncode, stdout, stderr))

    def __call__(self, command, *args, **kwargs):
        if not self.stack:
            raise AssertionError("Stack depleted but test expected more results (%s)" % (command, ))
        expected_command, returncode, stdout, stderr = self.stack.pop(0)
        if expected_command != command:
            raise AssertionError("Expected command %s but got %s" % (expected_command, command))
        return returncode, stdout, stderr

    def list_nodes(self, *nodes):
        self.add(
            ['vmrun', 'list'],
            stdout="Total running VMs: 1\n" + "\n".join(n[0] for n in nodes)
            )
        for n in nodes:
            self.add(
                ['vmrun', 'readVariable', n[0], 'runtimeConfig', 'displayName'],
                stdout=n[1],
                )
            self.add(
                ['vmrun', 'readVariable', n[0], 'guestVar', 'ip'],
                stdout=n[2],
                )

class VmwareTests(unittest.TestCase):

    def setUp(self):
        self.expect = vmware.execute = ExecuteMock()
        self.driver = vmware.VMWareDriver(vmrun='vmrun')

    @mock.patch("glob.glob")
    def test_list_images(self, glob):
        glob.return_value = ["/template.vmware/template.vmx"]
        images = self.driver.list_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].id, "/template.vmware/template.vmx")
        self.assertEqual(images[0].name, "VMWare Image")

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 3)
        self.assertEqual(sizes[0].name, "small")
        self.assertEqual(sizes[1].name, "medium")
        self.assertEqual(sizes[2].name, "large")

    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    @mock.patch("glob.glob")
    @mock.patch("uuid.uuid4")
    def test_create_node(self, uuid4, glob, exists, makedirs):
        exists.return_value = True
        glob.return_value = ['/template.vmwarevm/template.vmx']
        uuid4.return_value = "dummy_uuid"

        target = os.path.join(self.driver.vm_instances, uuid4.return_value, "vm.vmx")
        self.expect.add(['vmrun', 'clone', '/template.vmwarevm/template.vmx', target])
        self.expect.add(['vmrun', 'writeVariable', target, 'runtimeConfig', 'displayName', 'testNode'])
        self.expect.add(['vmrun', 'start', target, 'nogui'])

        image = self.driver.list_images()[0]
        node = self.driver.create_node(
            name='testNode', image=image, size=None)
        self.assertTrue(isinstance(node, Node))
        self.assertEqual('testNode', node.name)

    def test_list_nodes(self):
        self.expect.list_nodes(["/ubuntu.vmwarevm/ubuntu.vmx", "testNode", "192.168.1.5"])
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, '/ubuntu.vmwarevm/ubuntu.vmx')
        self.assertEqual(node.name, 'testNode')
        self.assertEqual(node.public_ips, ['192.168.1.5'])

    def test_reboot_node(self):
        self.expect.list_nodes(["/ubuntu.vmwarevm/ubuntu.vmx", "testNode", "192.168.1.5"])
        self.expect.add(
            ['vmrun', 'reset', '/ubuntu.vmwarevm/ubuntu.vmx', 'hard'],
            )

        node = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node)

    @mock.patch('shutil.rmtree')
    def test_destroy_node(self, rmtree):
        self.expect.list_nodes(["/ubuntu.vmwarevm/ubuntu.vmx", "testNode", "192.168.1.5"])
        self.expect.add(
            ['vmrun', 'stop', '/ubuntu.vmwarevm/ubuntu.vmx', 'hard'],
            )
        self.expect.add(
            ['vmrun', 'deleteVM', '/ubuntu.vmwarevm/ubuntu.vmx'],
            )

        node = self.driver.list_nodes()[0]
        ret = self.driver.destroy_node(node)

        rmtree.assert_called_with("/ubuntu.vmwarevm")

if __name__ == '__main__':
    sys.exit(unittest.main())

