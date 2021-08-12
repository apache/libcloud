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
        if method != 'DELETE':
            raise AssertionError('Unsupported method')
        return (httplib.OK, None, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
