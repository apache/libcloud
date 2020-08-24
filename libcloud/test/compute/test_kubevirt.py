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

from libcloud.compute.drivers.kubevirt import KubeVirtNodeDriver
from libcloud.compute.types import NodeState

from libcloud.utils.py3 import httplib

from libcloud.test import unittest
from libcloud.test import MockHttp
from libcloud.test.common.test_kubernetes import KubernetesAuthTestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class KubeVirtTestCase(unittest.TestCase, KubernetesAuthTestCaseMixin):

    driver_cls = KubeVirtNodeDriver
    fixtures = ComputeFileFixtures('kubevirt')

    def setUp(self):
        KubeVirtNodeDriver.connectionCls.conn_class = KubeVirtMockHttp
        self.driver = KubeVirtNodeDriver(key='user',
                                         secret='pass',
                                         secure=True,
                                         host='foo',
                                         port=6443)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 5)
        self.assertEqual(locations[0].name, 'default')
        self.assertEqual(locations[1].name, 'kube-node-lease')
        self.assertEqual(locations[2].name, 'kube-public')
        self.assertEqual(locations[3].name, 'kube-system')

        namespace4 = locations[0].driver.list_locations()[4].name
        self.assertEqual(namespace4, 'kubevirt')
        id4 = locations[2].driver.list_locations()[4].id
        self.assertEqual(id4, 'e6d3d7e8-0ee5-428b-8e17-5187779e5627')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        id0 = "74fd7665-fbd6-4565-977c-96bd21fb785a"

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].extra['namespace'], 'default')
        valid_node_states = {NodeState.RUNNING, NodeState.PENDING, NodeState.STOPPED}
        self.assertTrue(nodes[0].state in valid_node_states)
        self.assertEqual(nodes[0].name, 'testvm')
        self.assertEqual(nodes[0].id, id0)

    def test_destroy_node(self):
        nodes = self.driver.list_nodes()
        to_destroy = nodes[-1]
        resp = self.driver.destroy_node(to_destroy)
        self.assertTrue(resp)

    def test_start_node(self):
        nodes = self.driver.list_nodes()
        r1 = self.driver.start_node(nodes[0])
        self.assertTrue(r1)

    def test_stop_node(self):
        nodes = self.driver.list_nodes()
        r1 = self.driver.stop_node(nodes[0])
        self.assertTrue(r1)

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        for node in nodes:
            if node.name == "testvm":
                resp = self.driver.reboot_node(node)

        self.assertTrue(resp)


class KubeVirtMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('kubevirt')

    def _api_v1_namespaces(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_api_v1_namespaces.json')
        else:
            raise AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_default_virtualmachines(self,
                                                                      method,
                                                                      url,
                                                                      body,
                                                                      headers):
        if method == "GET":
            body = self.fixtures.load('get_default_vms.json')
            resp = httplib.OK
        elif method == "POST":
            body = self.fixtures.load('create_vm.json')
            resp = httplib.CREATED
        else:
            AssertionError('Unsupported method')
        return (resp, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_kube_node_lease_virtualmachines(self,
                                                                              method,
                                                                              url,
                                                                              body,
                                                                              headers):
        if method == "GET":
            body = self.fixtures.load('get_kube_node_lease_vms.json')
        elif method == "POST":
            pass
        else:
            AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_kube_public_virtualmachines(self,
                                                                          method,
                                                                          url, body,
                                                                          headers):
        if method == "GET":
            body = self.fixtures.load('get_kube_public_vms.json')
        elif method == "POST":
            pass
        else:
            AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_kube_system_virtualmachines(self,
                                                                          method,
                                                                          url, body,
                                                                          headers):
        if method == "GET":
            body = self.fixtures.load('get_kube_system_vms.json')
        elif method == "POST":
            pass
        else:
            AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_kubevirt_virtualmachines(self,
                                                                       method,
                                                                       url, body,
                                                                       headers):
        if method == "GET":
            body = self.fixtures.load('get_kube_public_vms.json')
        elif method == "POST":
            pass
        else:
            AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_default_virtualmachines_testvm(self,
                                                                             method,
                                                                             url, body,
                                                                             headers):
        header = "application/merge-patch+json"
        data_stop = {"spec": {"running": False}}
        data_start = {"spec": {"running": True}}

        if method == "PATCH" and headers['Content-Type'] == header and body == data_start:
            body = self.fixtures.load('start_testvm.json')

        elif method == "PATCH" and headers['Content-Type'] == header and body == data_stop:
            body = self.fixtures.load('stop_testvm.json')

        else:
            AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_default_virtualmachines_vm_cirros(self,
                                                                                method,
                                                                                url,
                                                                                body,
                                                                                headers):
        header = "application/merge-patch+json"
        data_stop = {"spec": {"running": False}}
        data_start = {"spec": {"running": True}}

        if method == "PATCH" and headers['Content-Type'] == header and body == data_start:
            body = self.fixtures.load('start_vm_cirros.json')

        elif method == "PATCH" and headers['Content-Type'] == header and body == data_stop:
            body = self.fixtures.load('stop_vm_cirros.json')

        else:
            AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_kubevirt_io_v1alpha3_namespaces_default_virtualmachineinstances_testvm(self,
                                                                                     method,
                                                                                     url,
                                                                                     body,
                                                                                     headers):
        if method == "DELETE":
            body = self.fixtures.load('delete_vmi_testvm.json')
        else:
            AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces_default_pods(self, method, url, body, headers):

        if method == "GET":
            body = self.fixtures.load('get_pods.json')
        else:
            AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces_default_services(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('get_services.json')
        else:
            AssertionError('Unsupported method')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
