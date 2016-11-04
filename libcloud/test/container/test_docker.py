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
        # Create a test driver for each version
        versions = ('linux_124', 'mac_124')
        self.drivers = []
        for version in versions:
            DockerContainerDriver.connectionCls.conn_classes = (
                DockerMockHttp, DockerMockHttp)
            DockerMockHttp.type = None
            DockerMockHttp.use_param = 'a'
            driver = DockerContainerDriver(*CONTAINER_PARAMS_DOCKER)
            driver.version = version
            self.drivers.append(driver)

    def test_list_images(self):
        for driver in self.drivers:
            images = driver.list_images()
            self.assertEqual(len(images), 4)
            self.assertIsInstance(images[0], ContainerImage)
            self.assertEqual(images[0].id,
                             'cf55d61f5307b7a18a45980971d6cfd40b737dd661879c4a6b3f2aecc3bc37b0')
            self.assertEqual(images[0].name, 'mongo:latest')

    def test_install_image(self):
        for driver in self.drivers:
            image = driver.install_image('ubuntu:12.04')
            self.assertTrue(image is not None)
            self.assertEqual(image.id, '992069aee4016783df6345315302fa59681aae51a8eeb2f889dea59290f21787')

    def test_list_containers(self):
        for driver in self.drivers:
            containers = driver.list_containers(all=True)
            self.assertEqual(len(containers), 6)
            self.assertEqual(containers[0].id,
                             '160936dc54fe8c332095676d9379003534b8cddd7565fa63018996e06dae1b6b')
            self.assertEqual(containers[0].name, 'hubot')
            self.assertEqual(containers[0].image.name, 'stackstorm/hubot')

    def test_deploy_container(self):
        for driver in self.drivers:
            image = driver.list_images()[0]
            container = driver.deploy_container(image=image, name='test')
            self.assertEqual(container.id, 'a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            self.assertEqual(container.name, 'gigantic_goldberg')

    def test_get_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            self.assertEqual(container.id, 'a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            self.assertEqual(container.name, 'gigantic_goldberg')

    def test_start_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            container.start()

    def test_stop_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            container.stop()

    def test_restart_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            container.restart()

    def test_delete_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            container.destroy()

    def test_ex_rename_container(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            driver.ex_rename_container(container, 'bob')

    def test_ex_get_logs(self):
        for driver in self.drivers:
            container = driver.get_container('a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303')
            logs = driver.ex_get_logs(container)
            self.assertTrue(logs is not None)

    def test_ex_search_images(self):
        for driver in self.drivers:
            images = driver.ex_search_images('mysql')
            self.assertEqual(len(images), 25)
            self.assertEqual(images[0].name, 'mysql')


class DockerMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('docker')
    version = None

    def _version(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('linux_124/version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _vlinux_124_images_search(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/search.json'), {}, httplib.responses[httplib.OK])

    def _vmac_124_images_search(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/search.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_images_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])

    def _vmac_124_images_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_images_create(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_image.txt'), {'Content-Type': 'application/json', 'transfer-encoding': 'chunked'},
                httplib.responses[httplib.OK])

    def _vmac_124_images_create(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/create_image.txt'), {'Content-Type': 'application/json', 'transfer-encoding': 'chunked'},
                httplib.responses[httplib.OK])

    def _vlinux_124_containers_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/containers.json'), {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/containers.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_create(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_container.json'), {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_create(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/create_container.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/container_a68.json'), {}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/container_a68.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/logs.txt'), {'content-type': 'text/plain'}, httplib.responses[httplib.OK])

    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
            self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/logs.txt'), {'content-type': 'text/plain'}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
