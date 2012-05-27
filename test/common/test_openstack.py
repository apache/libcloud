import sys
import unittest

from mock import Mock

from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.utils.py3 import PY25


class OpenStackBaseConnectionTest(unittest.TestCase):

    def setUp(self):
        self.timeout = 10
        OpenStackBaseConnection.conn_classes = (None, Mock())
        self.connection = OpenStackBaseConnection('foo', 'bar',
                                                  timeout=self.timeout,
                                                  ex_force_auth_url='https://127.0.0.1')
        self.connection.driver = Mock()
        self.connection.driver.name = 'OpenStackDriver'

    def test_base_connection_timeout(self):
        self.connection.connect()
        self.assertEquals(self.connection.timeout, self.timeout)
        if PY25:
            self.connection.conn_classes[1].assert_called_with(host='127.0.0.1',
                                                               port=443)
        else:
            self.connection.conn_classes[1].assert_called_with(host='127.0.0.1',
                                                               port=443,
                                                               timeout=10)


if __name__ == '__main__':
    sys.exit(unittest.main())
