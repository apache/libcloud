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

from libcloud.utils.py3 import httplib

from libcloud.container.base import ContainerImage
from libcloud.container.drivers.kubernetes import KubernetesContainerDriver

from libcloud.test.secrets import CONTAINER_PARAMS_KUBERNETES
from libcloud.test.common.test_kubernetes import KubernetesAuthTestCaseMixin
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp
from libcloud.test import unittest


class KubernetesContainerDriverTestCase(unittest.TestCase,
                                        KubernetesAuthTestCaseMixin):
    driver_cls = KubernetesContainerDriver

    def setUp(self):
        KubernetesContainerDriver.connectionCls.conn_class = KubernetesMockHttp
        KubernetesMockHttp.type = None
        KubernetesMockHttp.use_param = 'a'
        self.driver = KubernetesContainerDriver(*CONTAINER_PARAMS_KUBERNETES)

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0].id,
                         'docker://3c48b5cda79bce4c8866f02a3b96a024edb8f660d10e7d1755e9ced49ef47b36')
        self.assertEqual(containers[0].name, 'hello-world')

    def test_deploy_container(self):
        image = ContainerImage(
            id=None,
            name='hello-world',
            path=None,
            driver=self.driver,
            version=None
        )
        container = self.driver.deploy_container('hello-world', image=image)
        self.assertEqual(container.name, 'hello-world')

    def test_get_container(self):
        container = self.driver.get_container(
            'docker://3c48b5cda79bce4c8866f02a3b96a024edb8f660d10e7d1755e9ced49ef47b36')
        assert container.id == 'docker://3c48b5cda79bce4c8866f02a3b96a024edb8f660d10e7d1755e9ced49ef47b36'

    def test_list_namespaces(self):
        namespaces = self.driver.list_namespaces()
        self.assertEqual(len(namespaces), 2)
        self.assertEqual(namespaces[0].id,
                         'default')
        self.assertEqual(namespaces[0].name, 'default')

    def test_get_namespace(self):
        namespace = self.driver.get_namespace('default')
        self.assertEqual(namespace.id,
                         'default')
        self.assertEqual(namespace.name, 'default')

    def test_create_namespace(self):
        namespace = self.driver.create_namespace('test')
        self.assertEqual(namespace.id,
                         'test')
        self.assertEqual(namespace.name, 'test')

    def test_delete_namespace(self):
        namespace = self.driver.get_namespace('default')
        result = self.driver.delete_namespace(namespace)
        self.assertTrue(result)

    def test_list_pods(self):
        pods = self.driver.ex_list_pods()
        self.assertEqual(len(pods), 1)
        self.assertEqual(pods[0].id, '1fad5411-b9af-11e5-8701-0050568157ec')
        self.assertEqual(pods[0].name, 'hello-world')

    def test_destroy_pod(self):
        result = self.driver.ex_destroy_pod('default', 'default')
        self.assertTrue(result)

    def test_list_nodes(self):
        nodes = self.driver.ex_list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].id, '45949cbb-b99d-11e5-8d53-0050568157ec')
        self.assertEqual(nodes[0].name, '127.0.0.1')

    def test_destroy_node(self):
        result = self.driver.ex_destroy_node('127.0.0.1')
        self.assertTrue(result)

    def test_get_version(self):
        version = self.driver.ex_get_version()
        self.assertEqual(version, 'v1.20.8-gke.900')

    def test_list_nodes_metrics(self):
        nodes_metrics = self.driver.ex_list_nodes_metrics()
        self.assertEqual(len(nodes_metrics), 1)
        self.assertEqual(nodes_metrics[0]['metadata']['name'],
                         'gke-cluster-3-default-pool-76fd57f7-l83v')

    def test_list_pods_metrics(self):
        pods_metrics = self.driver.ex_list_pods_metrics()
        self.assertEqual(len(pods_metrics), 10)
        self.assertEqual(pods_metrics[0]['metadata']['name'],
                         'gke-metrics-agent-sfjzj')
        self.assertEqual(
            pods_metrics[1]['metadata']['name'],
            'stackdriver-metadata-agent-cluster-level-849ff68b6d-fphxl')
        self.assertEqual(pods_metrics[2]['metadata']['name'],
                         'event-exporter-gke-67986489c8-g47rz')

    def test_list_services(self):
        services = self.driver.ex_list_services()
        self.assertEqual(len(services), 4)
        self.assertEqual(services[0]['metadata']['name'], 'kubernetes')
        self.assertEqual(services[1]['metadata']['name'],
                         'default-http-backend')
        self.assertEqual(services[2]['metadata']['name'], 'kube-dns')


class KubernetesMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('kubernetes')

    def _api_v1_pods(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_pods.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_namespaces.json')
        elif method == 'POST':
            body = self.fixtures.load('_api_v1_namespaces_test.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces_default(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_namespaces_default.json')
        elif method == 'DELETE':
            body = self.fixtures.load('_api_v1_namespaces_default_DELETE.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces_default_pods(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_namespaces_default_pods.json')
        elif method == 'POST':
            body = self.fixtures.load(
                '_api_v1_namespaces_default_pods_POST.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces_default_pods_default(
            self, method, url, body, headers):
        if method == 'DELETE':
            body = None
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_nodes(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_nodes.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_nodes_127_0_0_1(self, method, url, body, headers):
        if method == 'DELETE':
            body = None
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_services(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_services.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _version(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_metrics_k8s_io_v1beta1_nodes(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load(
                '_apis_metrics_k8s_io_v1beta1_nodes.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _apis_metrics_k8s_io_v1beta1_pods(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load(
                '_apis_metrics_k8s_io_v1beta1_pods.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
