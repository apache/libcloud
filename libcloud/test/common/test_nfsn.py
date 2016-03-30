from mock import Mock, patch
import string
import sys
import unittest

from libcloud.common.nfsn import NFSNConnection
from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.utils.py3 import httplib


mock_time = Mock()
mock_time.return_value = 1000000

mock_salt = Mock()
mock_salt.return_value = 'yumsalty1234'

mock_header = 'testid;1000000;yumsalty1234;66dfb282a9532e5b8e6a9517764d5fbc001a4a2e'


class NFSNConnectionTestCase(LibcloudTestCase):

    def setUp(self):
        NFSNConnection.conn_classes = (None, NFSNMockHttp)
        NFSNMockHttp.type = None
        self.driver = NFSNConnection('testid', 'testsecret')

    def test_salt_length(self):
        self.assertEqual(16, len(self.driver._salt()))

    def test_salt_is_unique(self):
        s1 = self.driver._salt()
        s2 = self.driver._salt()
        self.assertNotEqual(s1, s2)

    def test_salt_characters(self):
        """ salt must be alphanumeric """
        salt_characters = string.ascii_letters + string.digits
        for c in self.driver._salt():
            self.assertIn(c, salt_characters)

    @patch('time.time', mock_time)
    def test_timestamp(self):
        """ Check that timestamp uses time.time """
        self.assertEqual('1000000', self.driver._timestamp())

    @patch('time.time', mock_time)
    @patch('libcloud.common.nfsn.NFSNConnection._salt', mock_salt)
    def test_auth_header(self):
        """ Check that X-NFSN-Authentication is set """
        response = self.driver.request(action='/testing')
        self.assertEqual(httplib.OK, response.status)


class NFSNMockHttp(MockHttp):

    def _testing(self, method, url, body, headers):
        if headers['X-NFSN-Authentication'] == mock_header:
            return (httplib.OK, '', {}, httplib.responses[httplib.OK])
        else:
            return (httplib.UNAUTHORIZED, '', {},
                    httplib.responses[httplib.UNAUTHORIZED])


if __name__ == '__main__':
    sys.exit(unittest.main())
