import sys

from libcloud.test import unittest

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

from libcloud.container.base import ContainerImage
from libcloud.container.base import Container

from libcloud.container.drivers.lxd import LXDContainerDriver

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_LXD
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class LXDContainerDriverTestCase(unittest.TestCase):

    """
    Unit tests for LXDContainerDriver
    """

    @staticmethod
    def dummy_certificate_validator(key_file, cert_file):
        pass

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

    def test_list_images(self):
        for driver in self.drivers:
            images = driver.list_images()
            self.assertEqual(len(images), 1)
            self.assertIsInstance(images[0], ContainerImage)
            self.assertEqual(images[0].id, 'trusty')
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
            container = driver.deploy_container(name='first_lxd_container',
                                                image='54c8caac1f61901ed86c68f24af5f5d3672bdc62c71d04f06df3a59e95684473',
                                                parameters={})
            self.assertIsInstance(container, Container)
            self.assertEqual(container.name, 'first_lxd_container')


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

    def _vlinux_124_images_search(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/search.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_images(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_images_54c8caac1f61901ed86c68f24af5f5d3672bdc62c71d04f06df3a59e95684473(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/image.json'), {}, httplib.responses[httplib.OK])

    def _vlinux_124_images_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_image.txt'),
                {'Content-Type': 'application/json', 'transfer-encoding': 'chunked'},
                httplib.responses[httplib.OK])

    def _linux_124_containers(
        self, method, url, body, headers):

        if method == 'GET':
            return (httplib.OK, self.fixtures.load('linux_124/containers.json'), {}, httplib.responses[httplib.OK])
        elif method == 'POST' or method == 'PUT':
            # we do a POST when we create a container
            # we will return a dummy background operation
            return (httplib.OK, self.fixtures.load('linux_124/background_op.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_first_lxd_container(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/first_lxd_container.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_second_lxd_container(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/second_lxd_container.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_containers_first_lxd_container_state(self, method, url, body, headers):

        if method == 'PUT':
            json = self.fixtures.load('linux_124/background_op.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            json = self.fixtures.load('linux_124/first_lxd_container.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])

    def _linux_124_containers_second_lxd_container_state(self, method, url, body, headers):

        if method == 'PUT':
            json = self.fixtures.load('linux_124/background_op.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            json = self.fixtures.load('linux_124/second_lxd_container.json')
            return (httplib.OK, json, {}, httplib.responses[httplib.OK])

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

if __name__ == '__main__':
    sys.exit(unittest.main())