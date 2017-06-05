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
from io import StringIO
import zlib
import requests_mock

import libcloud
from libcloud.test import unittest
from libcloud.common.base import Connection
from libcloud.http import LibcloudConnection
from libcloud.utils.loggingconnection import LoggingConnection


class TestLoggingConnection(unittest.TestCase):
    def tearDown(self):
        Connection.conn_class = LibcloudConnection

    def test_debug_method_uses_log_class(self):
        with StringIO() as fh:
            libcloud.enable_debug(fh)
            conn = Connection(timeout=10)
            conn.connect()
        self.assertTrue(isinstance(conn.connection, LoggingConnection))

    def test_debug_log_class_handles_request(self):
        with StringIO() as fh:
            libcloud.enable_debug(fh)
            conn = Connection(url='http://test.com/')
            conn.connect()
            self.assertEqual(conn.connection.host, 'http://test.com')
            with requests_mock.mock() as m:
                m.get('http://test.com/test', text='data')
                conn.request('/test')
            log = fh.getvalue()
        self.assertTrue(isinstance(conn.connection, LoggingConnection))
        self.assertIn('-i -X GET', log)
        self.assertIn('data', log)

    def test_debug_log_class_handles_request_with_compression(self):
        request = zlib.compress(b'data')
        with StringIO() as fh:
            libcloud.enable_debug(fh)
            conn = Connection(url='http://test.com/')
            conn.connect()
            self.assertEqual(conn.connection.host, 'http://test.com')
            with requests_mock.mock() as m:
                m.get('http://test.com/test', content=request,
                      headers={'content-encoding': 'zlib'})
                conn.request('/test')
            log = fh.getvalue()
        self.assertTrue(isinstance(conn.connection, LoggingConnection))
        self.assertIn('-i -X GET', log)

if __name__ == '__main__':
    sys.exit(unittest.main())
