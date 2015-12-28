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

from libcloud.container.drivers.docker import DockerContainerDriver

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_DOCKER
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class DockerContainerDriverTestCase(unittest.TestCase):

    def setUp(self):
        DockerContainerDriver.connectionCls.conn_classes = (
            DockerMockHttp, DockerMockHttp)
        DockerMockHttp.type = None
        DockerMockHttp.use_param = 'a'
        self.driver = DockerContainerDriver(*CONTAINER_PARAMS_DOCKER)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 4)
        self.assertIsInstance(images[0], ContainerImage)
        self.assertEqual(images[0].id,
                         'cf55d61f5307b7a18a45980971d6cfd40b737dd661879c4a6b3f2aecc3bc37b0')
        self.assertEqual(images[0].name, 'mongo:latest')

    def test_install_image(self):
        image = self.driver.install_image('ubuntu:12.04')
        self.assertTrue(image is not None)
        self.assertEqual(image.id, 'cf55d61f5307b7a18a45980971d6cfd40b737dd661879c4a6b3f2aecc3bc37b0')

    def test_list_containers(self):
        containers = self.driver.list_containers(all=True)
        self.assertEqual(len(containers), 6)
        self.assertEqual(containers[0].id,
                         '160936dc54fe8c332095676d9379003534b8cddd7565fa63018996e06dae1b6b')
        self.assertEqual(containers[0].name, 'hubot')
        self.assertEqual(containers[0].image.name, 'stackstorm/hubot')

    def test_deploy_container(self):
        image = self.driver.list_images()[0]
        container = self.driver.deploy_container(image=image, name='test')
        self.assertEqual(container.id, 'a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        self.assertEqual(container.name, 'gigantic_goldberg')

    def test_get_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        self.assertEqual(container.id, 'a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        self.assertEqual(container.name, 'gigantic_goldberg')

    def test_start_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        container.start()

    def test_stop_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        container.stop()

    def test_restart_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        container.restart()

    def test_delete_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        container.destroy()

    def test_ex_rename_container(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        self.driver.ex_rename_container(container, 'bob')

    def test_ex_get_logs(self):
        container = self.driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
        logs = self.driver.ex_get_logs(container)
        self.assertTrue(logs is not None)

    def test_ex_search_images(self):
        images = self.driver.ex_search_images('mysql')
        self.assertEqual(len(images), 25)
        self.assertEqual(images[0].name, 'mysql')


class DockerMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('docker')

    def _version(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_search(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('search.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_json(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('images.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_create(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('create_image.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {'Content-Type': 'application/json'},
                httplib.responses[httplib.OK])

    def _containers_json(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('containers.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _containers_create(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('create_container.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
            self, method, url, body, headers):
        if method == 'DELETE':
            body = ''
        else:
            raise AssertionError('Unsupported method')
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
            self, method, url, body, headers):
        if method == 'POST':
            body = ''
        else:
            raise AssertionError('Unsupported method')
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
            self, method, url, body, headers):
        if method == 'POST':
            body = ''
        else:
            raise AssertionError('Unsupported method')
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
            self, method, url, body, headers):
        if method == 'POST':
            body = ''
        else:
            raise AssertionError('Unsupported method')
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
            self, method, url, body, headers):
        if method == 'POST':
            body = ''
        else:
            raise AssertionError('Unsupported method')
        return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('container_a68.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('logs.txt')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {'content-type': 'text/plain'}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
