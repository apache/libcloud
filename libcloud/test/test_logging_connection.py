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

import os
import sys
from io import StringIO
import zlib
import requests_mock

import mock

import libcloud
from libcloud.test import unittest
from libcloud.common.base import Connection
from libcloud.http import LibcloudConnection
from libcloud.utils.loggingconnection import LoggingConnection

EXPECTED_DATA_JSON = """
HTTP/1.1 200 OK
Content-Type: application/json

{"foo": "bar!"}
""".strip()

EXPECTED_DATA_JSON_PRETTY = """
HTTP/1.1 200 OK
Content-Type: application/json

{
    "foo": "bar!"
}
""".strip()

EXPECTED_DATA_XML = """
HTTP/1.1 200 OK
Content-Type: text/xml

<foo><bar /></foo>
""".strip()

EXPECTED_DATA_XML_PRETTY = """
HTTP/1.1 200 OK
Content-Type: application/xml

<foo><bar /></foo>
""".strip()


class TestLoggingConnection(unittest.TestCase):
    def setUp(self):
        super(TestLoggingConnection, self).setUp()
        self._reset_environ()

    def tearDown(self):
        super(TestLoggingConnection, self).tearDown()
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

    def test_log_response_json_content_type(self):
        conn = LoggingConnection(host='example.com', port=80)

        r = self._get_mock_response('application/json', '{"foo": "bar!"}')
        result = conn._log_response(r).replace('\r', '')
        self.assertTrue(EXPECTED_DATA_JSON in result)

    def test_log_response_xml_content_type(self):
        conn = LoggingConnection(host='example.com', port=80)

        r = self._get_mock_response('text/xml', '<foo><bar /></foo>')
        result = conn._log_response(r).replace('\r', '')
        self.assertTrue(EXPECTED_DATA_XML in result)

    def test_log_response_with_pretty_print_json_content_type(self):
        os.environ['LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE'] = '1'

        conn = LoggingConnection(host='example.com', port=80)

        # body type is unicode
        r = self._get_mock_response('application/json', '{"foo": "bar!"}')
        result = conn._log_response(r).replace('\r', '')
        self.assertTrue(EXPECTED_DATA_JSON_PRETTY in result)

        # body type is bytes
        r = self._get_mock_response('application/json', bytes('{"foo": "bar!"}', 'utf-8'))
        result = conn._log_response(r).replace('\r', '')
        self.assertTrue(EXPECTED_DATA_JSON_PRETTY in result)

    def test_log_response_with_pretty_print_xml_content_type(self):
        os.environ['LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE'] = '1'

        conn = LoggingConnection(host='example.com', port=80)

        r = self._get_mock_response('application/xml', '<foo><bar /></foo>')
        result = conn._log_response(r).replace('\r', '')
        self.assertTrue(EXPECTED_DATA_XML_PRETTY in result)

    def _reset_environ(self):
        if 'LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE' in os.environ:
            del os.environ['LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE']

    def _get_mock_response(self, content_type, body):
        header = mock.Mock()
        header.title.return_value = 'Content-Type'
        header.lower.return_value = 'content-type'

        r = mock.Mock()
        r.version = 11
        r.status = '200'
        r.reason = 'OK'
        r.getheaders.return_value = [(header, content_type)]
        r.read.return_value = body

        return r


if __name__ == '__main__':
    sys.exit(unittest.main())
