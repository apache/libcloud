import sys
import unittest

from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver
from libcloud.loadbalancer.drivers.dummy import DummyLBDriver
from libcloud.loadbalancer.drivers.ninefold import NinefoldLBDriver

from .mocks.cloudstack import CloudStackMockHttp
from .test_cloudstack import CloudStackLBTests


class NinefoldLbTestCase(CloudStackLBTests):

    def setUp(self):
        self.jobs = {}
        self.next_job_id = 0

        CloudStackMockHttp.test = self
        NinefoldLBDriver.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)

        self.driver = NinefoldLBDriver('apikey', 'secret')
        self.driver.path = '/test/path'
        self.driver.type = -1
        self.driver.name = 'Ninefold'
        self.driver.connection.poll_interval = 0.0

        self.mock = DummyLBDriver('', '')
        self.setUpMock()

    def test_driver_instantiation(self):
        cls = get_driver(Provider.NINEFOLD)
        cls('username', 'key')


if __name__ == '__main__':
    sys.exit(unittest.main())
