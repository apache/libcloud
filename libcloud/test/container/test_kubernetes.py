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

from libcloud.test import unittest

from libcloud.container.base import ContainerImage

from libcloud.container.drivers.kubernetes import KubernetesContainerDriver

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_KUBERNETES
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class KubernetesContainerDriverTestCase(unittest.TestCase):

    def setUp(self):
        KubernetesContainerDriver.connectionCls.conn_classes = (
            KubernetesMockHttp, KubernetesMockHttp)
        KubernetesMockHttp.type = None
        KubernetesMockHttp.use_param = 'a'
        self.driver = KubernetesContainerDriver(*CONTAINER_PARAMS_KUBERNETES)

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0].id,
                         'docker://3c48b5cda79bce4c8866f02a3b96a024edb8f660d10e7d1755e9ced49ef47b36')
        self.assertEqual(containers[0].name, 'hello-world')

    def test_list_clusters(self):
        clusters = self.driver.list_clusters()
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].id,
                         'default')
        self.assertEqual(clusters[0].name, 'default')

    def test_get_cluster(self):
        cluster = self.driver.get_cluster('default')
        self.assertEqual(cluster.id,
                         'default')
        self.assertEqual(cluster.name, 'default')

    def test_create_cluster(self):
        cluster = self.driver.create_cluster('test')
        self.assertEqual(cluster.id,
                         'test')
        self.assertEqual(cluster.name, 'test')

    def test_destroy_cluster(self):
        cluster = self.driver.get_cluster('default')
        result = self.driver.destroy_cluster(cluster)
        self.assertTrue(result)

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


class KubernetesMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('kubernetes')

    def _version(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_pods(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_pods.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_nodes(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_nodes.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_nodes_127_0_0_1(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_nodes_127_0_0_1.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_v1_namespaces(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('_api_v1_namespaces.json')
        elif method == 'POST':
            body = self.fixtures.load('_api_v1_namespaces_test.json')
        elif method == 'DELETE':
            body = self.fixtures.load('_api_v1_namespaces_DELETE.json')
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
            body = self.fixtures.load('_api_v1_namespaces_default_pods_POST.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
