import sys

from libcloud.common.types import LibcloudError
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.dummy import DummyLBDriver
from libcloud.loadbalancer.drivers.cloudstack import CloudStackLBDriver

from .mocks.cloudstack import CloudStackMockHttp

from .test_loadbalancer import BaseLBTests


class CloudStackLBTests(BaseLBTests):

    def setUp(self):
        self.jobs = {}
        self.next_job_id = 0

        CloudStackMockHttp.test = self
        CloudStackLBDriver.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)

        self.driver = CloudStackLBDriver('apikey', 'secret', host='host', path='/test/path')
        self.driver.type = -1
        self.driver.name = 'CloudStack'
        self.driver.connection.poll_interval = 0.0

        self.mock = DummyLBDriver('', '')
        self.setUpMock()

    def test_user_must_provide_host_and_path(self):
        expected_msg = 'When instantiating CloudStack driver directly ' + \
                       'you also need to provide host and path argument'
        cls = get_driver(Provider.CLOUDSTACK)

        self.assertRaisesRegexp(Exception, expected_msg, cls,
                                'key', 'secret')

        try:
            cls('key', 'secret', True, 'localhost', '/path')
        except Exception:
             self.fail('host and path provided but driver raised an exception')


if __name__ == "__main__":
    sys.exit(unittest.main())
