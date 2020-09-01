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

from libcloud.compute.drivers.vsphere import VSphere_REST_NodeDriver

from libcloud.utils.py3 import httplib

from libcloud.test import unittest
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures


class KubeVirtTestCase(unittest.TestCase):

    driver_cls = VSphere_REST_NodeDriver
    fixtures = ComputeFileFixtures('vsphere')

    def setUp(self):
        VSphere_REST_NodeDriver.connectionCls.conn_class = VSphereMockHttp
        self.driver = VSphere_REST_NodeDriver(key='user',
                                              secret='pass',
                                              secure=True,
                                              host='foo',
                                              port=443)

    def test_list_nodes(self):
        vm_id = "vm-80"
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, 'vCenter')
        self.assertEqual(nodes[0].id, vm_id)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].id, "host-74")
        self.assertEqual(locations[0].name, "100.100.100.100")

    def test_destroy_node(self):
        nodes = self.driver.list_nodes()
        to_destroy = nodes[-1]
        resp = self.driver.destroy_node(to_destroy)
        self.assertTrue(resp)

    def test_start_node(self):
        nodes = self.driver.list_nodes()
        resp = self.driver.start_node(nodes[0])
        self.assertTrue(resp)

    def test_stop_node(self):
        nodes = self.driver.list_nodes()
        resp = self.driver.stop_node(nodes[0])
        self.assertTrue(resp)

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        resp = self.driver.reboot_node(nodes[0])
        self.assertTrue(resp)


class VSphereMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('vsphere')

    def _rest_com_vmware_cis_session(self, method, url, body, headers):
        if method == "POST":
            body = self.fixtures.load('session_token.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_vm(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('list_nodes.json')
        elif method == "POST":
            return
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_vm_vm_80(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('node_80.json')
        elif method == "POST":
            return
        elif method == "DELETE":
            body = ""
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_cluster(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('list_clusters.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_host(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('list_hosts.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_appliance_networking_interfaces(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('list_interfaces.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_vm_vm_80_power_stop(self, method, url, body, headers):
        if method != "POST":
            raise AssertionError('Unsupported method')
        body = ""

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_vm_vm_80_power_start(self, method, url, body, headers):
        if method != "POST":
            raise AssertionError('Unsupported method')
        body = ""

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_vcenter_vm_vm_80_power_reset(self, method, url, body, headers):
        if method != "POST":
            raise AssertionError('Unsupported method')
        body = ""

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
