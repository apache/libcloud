import sys

from libcloud.test import unittest

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

from libcloud.container.base import ContainerImage

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
            driver = LXDContainerDriver(key=CONTAINER_PARAMS_LXD[0],
                                        secret=CONTAINER_PARAMS_LXD[1],
                                        secure=CONTAINER_PARAMS_LXD[2],
                                        host=CONTAINER_PARAMS_LXD[3],
                                        port=CONTAINER_PARAMS_LXD[4],
                                        key_file=None, #CONTAINER_PARAMS_LXD[5],
                                        cert_file=None, #CONTAINER_PARAMS_LXD[6],
                                        ca_cert=CONTAINER_PARAMS_LXD[7],
                                        certificate_validator=LXDContainerDriverTestCase.dummy_certificate_validator)
            driver.connectionCls.conn_class = \
                LXDMockHttp
            driver.version = version
            self.drivers.append(driver)

    """
    Test Scenario: Application attempts to generate an action that is not in LXD_API_STATE_ACTIONS
    Expected Output: InvalidArgument exception should be thrown
    """
    """
    def test_invalid_action_given(self):

        conn = LXDContainerDriverTestCase.get_lxd_connection()

        with ValueError as e:
            conn._do_container_action(container=None, action="INVALID",
                                  timeout=None, stateful=None, force=None)
            self.assertEqual(str(e), "Invalid action specified")
    """

    def test_list_images(self):
        for driver in self.drivers:
            images = driver.list_images()
            self.assertEqual(len(images), 1)
            self.assertIsInstance(images[0], ContainerImage)
            self.assertEqual(images[0].id, 'trusty')
            self.assertEqual(images[0].name, 'trusty')


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

    """
    def _vmac_124_images_search(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/search.json'), {}, httplib.responses[httplib.OK])
    """
    def _linux_124_images(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])

    def _linux_124_images_54c8caac1f61901ed86c68f24af5f5d3672bdc62c71d04f06df3a59e95684473(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/image.json'), {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_images_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/images.json'), {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_images_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_image.txt'),
                {'Content-Type': 'application/json', 'transfer-encoding': 'chunked'},
                httplib.responses[httplib.OK])

    """
    def _vmac_124_images_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/create_image.txt'),
                {'Content-Type': 'application/json', 'transfer-encoding': 'chunked'},
                httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/containers.json'), {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/containers.json'), {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/create_container.json'), {}, httplib.responses[httplib.OK])
    """
    def _vmac_124_containers_create(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('mac_124/create_container.json'), {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """
    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_start(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_restart(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_rename(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_stop(
        self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/container_a68.json'), {}, httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_json(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/container_a68.json'), {}, httplib.responses[httplib.OK])
    """

    def _vlinux_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/logs.txt'), {'content-type': 'text/plain'},
                httplib.responses[httplib.OK])

    """
    def _vmac_124_containers_a68c1872c74630522c7aa74b85558b06824c5e672cee334296c50fb209825303_logs(
        self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('linux_124/logs.txt'), {'content-type': 'text/plain'},
                httplib.responses[httplib.OK])
    """

if __name__ == '__main__':
    sys.exit(unittest.main())