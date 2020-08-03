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

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

from libcloud.container.base import ContainerImage
from libcloud.container.base import Container

from libcloud.container.drivers.lxd import LXDStoragePool
from libcloud.container.drivers.lxd import LXDAPIException
from libcloud.container.drivers.lxd import LXDContainerDriver
from libcloud.container.drivers.lxd import LXDServerInfo

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_LXD
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class LXDContainerDriverTestCase(unittest.TestCase):

    """
    Unit tests for LXDContainerDriver
    """

    def setUp(self):
        # Create a test driver for each version
        versions = ('linux_124',)
        self.drivers = []
        for version in versions:
            LXDContainerDriver.connectionCls.conn_class = \
                LXDMockHttp
            LXDMockHttp.type = None
            LXDMockHttp.use_param = 'a'
            driver = LXDContainerDriver(*CONTAINER_PARAMS_LXD)
            driver.connectionCls.conn_class = \
                LXDMockHttp
            driver.version = version
            self.drivers.append(driver)

    def test_ex_get_api_endpoints_trusted(self):
        for driver in self.drivers:
            api = driver.ex_get_api_endpoints()
            self.assertEqual(api[0], driver.version)

    def test_ex_get_server_configuration(self):
        for driver in self.drivers:
            server_config = driver.ex_get_server_configuration()
            self.assertIsInstance(server_config, LXDServerInfo)
            self.assertEqual(server_config.api_extensions, [])
            self.assertEqual(server_config.api_status, "stable")
            self.assertEqual(server_config.api_version, "linux_124")
            self.assertEqual(server_config.auth, "guest")
            self.assertEqual(server_config.public, False)

    def test_list_images(self):
        img_id = "54c8caac1f61901ed86c68f24af5f5d3672bdc62c71d04f06df3a59e95684473"
        for driver in self.drivers:
            images = driver.list_images()
            self.assertEqual(len(images), 1)
            self.assertIsInstance(images[0], ContainerImage)
            self.assertEqual(images[0].id, img_id)
            self.assertEqual(images[0].name, 'trusty')

    def test_list_containers(self):
        for driver in self.drivers:
            containers = driver.list_containers()
            self.assertEqual(len(containers), 2)
            self.assertIsInstance(containers[0], Container)
            self.assertIsInstance(containers[1], Container)
            self.assertEqual(containers[0].name, 'first_lxd_container')
            self.assertEqual(containers[1].name, 'second_lxd_container')

    def test_get_container(self):
        for driver in self.drivers:
            container = driver.get_container(id='second_lxd_container')
            self.assertIsInstance(container, Container)
            self.assertEqual(container.name, 'second_lxd_container')
            self.assertEqual(container.id, 'second_lxd_container')
            self.assertEqual(container.state, 'stopped')

    def test_start_container(self):
        for driver in self.drivers:
            container = driver.get_container(id='first_lxd_container')
            container.start()
            self.assertEqual(container.state, 'running')

    def test_stop_container(self):
        for driver in self.drivers:
            container = driver.get_container(id='second_lxd_container')
            container.stop()
            self.assertEqual(container.state, 'stopped')

    def test_restart_container(self):
        for driver in self.drivers:
            container = driver.get_container(id='second_lxd_container')
            container.restart()

    def test_delete_container(self):
        for driver in self.drivers:
            container = driver.get_container(id='second_lxd_container')
            container.destroy()

    def test_deploy_container(self):
        for driver in self.drivers:
            image = ContainerImage(id=None,
                                   name=None,
                                   path=None, version=None, driver=driver)
            container = driver.deploy_container(name='first_lxd_container',
                                                image=image,
                                                parameters='{"source":{"type":"image", '
                                                           '"fingerprint":"7ed08b435c92cd8a8a884c88e8722f2e7546a51e891982a90ea9c15619d7df9b"}}')
            self.assertIsInstance(container, Container)
            self.assertEqual(container.name, 'first_lxd_container')

    # test images
    def test_install_image_no_dict(self):
        with self.assertRaises(LXDAPIException) as exc:
            for driver in self.drivers:
                container = driver.install_image(path=None)
                self.assertEqual(str(exc), "Install an image for LXD requires specification of image_data")

    # test storage pools

    def test_list_storage_pools(self):
        for driver in self.drivers:
            pools = driver.ex_list_storage_pools()
            self.assertEqual(len(pools), 2)
            self.assertIsInstance(pools[0], LXDStoragePool)
            self.assertIsInstance(pools[1], LXDStoragePool)
            self.assertEqual(pools[0].name, 'pool1')
            self.assertEqual(pools[1].name, 'pool2')

    def test_get_storage_pool_no_metadata(self):
        with self.assertRaises(LXDAPIException) as exc:
            for driver in self.drivers:
                driver.ex_get_storage_pool(id='pool3')
                self.assertEqual(str(exc), 'Storage pool with name pool3 has no data')

    def test_delete_storage_pool(self):
        for driver in self.drivers:
            driver.ex_delete_storage_pool(id='pool1')

    def test_delete_storage_pool_fail(self):
        with self.assertRaises(LXDAPIException) as exc:
            for driver in self.drivers:
                driver.ex_delete_storage_pool(id='pool2')


class LXDMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('lxd')
    version = None

    def _version(
        self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('linux_124/version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def root(self, method, url, body, headers):
        json = self.fixtures.load('linux_124/endpoints_sucess.json')
        return (httplib.OK, json, {}, httplib.responses[httplib.OK])

    def _linux_124(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/version.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_images(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_images_54c8caac1f61901ed86c68f24af5f5d3672bdc62c71d04f06df3a59e95684473(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/image.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers(
        self, method, url, body, headers):

        if method == 'GET':
            return (httplib.OK, self.fixtures.load('linux_124/containers.json'), {}, httplib.responses[httplib.OK])
        elif method == 'POST' or method == 'PUT':
            # we do a POST when we create a container
            # we will return a dummy background operation
            return (httplib.OK, self.fixtures.load('linux_124/background_op.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_first_lxd_container(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/first_lxd_container.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_second_lxd_container(
        self, method, url, body, headers):

        if method == 'PUT' or method == 'DELETE':
            json = self.fixtures.load('linux_124/background_op.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            return (httplib.OK, self.fixtures.load('linux_124/second_lxd_container.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_first_lxd_container_state(self, method, url, body, headers):

        if method == 'PUT' or method == 'DELETE':
            json = self.fixtures.load('linux_124/background_op.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            json = self.fixtures.load('linux_124/first_lxd_container.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])

    def _linux_124_containers_second_lxd_container_state(self, method, url, body, headers):

        if method == 'PUT' or method == 'DELETE':
            json = self.fixtures.load('linux_124/background_op.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            json = self.fixtures.load('linux_124/second_lxd_container.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])

    def _linux_124_operations_1_wait(self, method, url, body, header):
        return (httplib.OK, self.fixtures.load("linux_124/operation_1_wait.json"), {}, httplib.responses[httplib.OK])

    def _linux_124_storage_pools(self, method, url, body, header):

        if method == 'GET':
            json = self.fixtures.load('linux_124/storage_pools.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])

    def _linux_124_storage_pools_pool1(self, method, url, body, header):

        if method == 'GET':
            json = self.fixtures.load('linux_124/storage_pool_1.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'DELETE':
            return (httplib.OK,
                    self.fixtures.load('linux_124/storage_pool_delete_sucess.json'),
                    {},
                    httplib.responses[httplib.OK])

    def _linux_124_storage_pools_pool2(self, method, url, body, header):

        if method == 'GET':
            json = self.fixtures.load('linux_124/storage_pool_2.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'DELETE':
            return (httplib.OK,
                    self.fixtures.load('linux_124/storage_pool_delete_fail.json'),
                    {},
                    httplib.responses[httplib.OK])

    def _linux_124_storage_pools_pool3(self, method, url, body, header):

        if method == 'GET':
            json = self.fixtures.load('linux_124/no_meta_pool.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])


    """
    def _vlinux_124_containers_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_container.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    
    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/container_a68.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/logs.txt'), {'content-type': 'text/plain'},
                httplib.responses[httplib.OK])
    """

if __name__ == '__main__':
    sys.exit(unittest.main())
