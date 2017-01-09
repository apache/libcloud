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

import string
import sys
import unittest

from mock import Mock, patch

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
        NFSNConnection.conn_class = NFSNMockHttp
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
