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
import os.path
import random
import platform
import warnings
import threading

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

import requests

import libcloud.security

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import reload
from libcloud.utils.py3 import assertRaisesRegex
from libcloud.http import LibcloudConnection

from libcloud.test import unittest

ORIGINAL_CA_CERTS_PATH = libcloud.security.CA_CERTS_PATH


class TestHttpLibSSLTests(unittest.TestCase):

    def setUp(self):
        libcloud.security.VERIFY_SSL_CERT = False
        libcloud.security.CA_CERTS_PATH = ORIGINAL_CA_CERTS_PATH
        self.httplib_object = LibcloudConnection('foo.bar', port=80)

    def test_custom_ca_path_using_env_var_doesnt_exist(self):
        os.environ['SSL_CERT_FILE'] = '/foo/doesnt/exist'

        try:
            reload(libcloud.security)
        except ValueError as e:
            msg = 'Certificate file /foo/doesnt/exist doesn\'t exist'
            self.assertEqual(str(e), msg)
        else:
            self.fail('Exception was not thrown')

    def test_custom_ca_path_using_env_var_is_directory(self):
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.environ['SSL_CERT_FILE'] = file_path

        expected_msg = 'Certificate file can\'t be a directory'
        assertRaisesRegex(self, ValueError, expected_msg,
                          reload, libcloud.security)

    def test_custom_ca_path_using_env_var_exist(self):
        # When setting a path we don't actually check that a valid CA file is
        # provided.
        # This happens later in the code in http.connect method
        file_path = os.path.abspath(__file__)
        os.environ['SSL_CERT_FILE'] = file_path

        reload(libcloud.security)

        self.assertEqual(libcloud.security.CA_CERTS_PATH, file_path)

    def test_ca_cert_list_warning(self):
        with warnings.catch_warnings(record=True) as w:
            self.httplib_object.verify = True
            self.httplib_object._setup_ca_cert(
                ca_cert=[ORIGINAL_CA_CERTS_PATH])
            self.assertEqual(self.httplib_object.ca_cert,
                             ORIGINAL_CA_CERTS_PATH)
            self.assertEqual(w[0].category, DeprecationWarning)

    def test_setup_ca_cert(self):
        # verify = False, _setup_ca_cert should be a no-op
        self.httplib_object.verify = False
        self.httplib_object._setup_ca_cert()

        self.assertIsNone(self.httplib_object.ca_cert)

        # verify = True, a valid path is provided, self.ca_cert should be set to
        # a valid path
        self.httplib_object.verify = True

        libcloud.security.CA_CERTS_PATH = os.path.abspath(__file__)
        self.httplib_object._setup_ca_cert()

        self.assertTrue(self.httplib_object.ca_cert is not None)


@unittest.skipIf(platform.python_implementation() == "PyPy",
                 "Skipping test under PyPy since it causes segfault")
class HttpLayerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listen_host = '127.0.0.1'
        cls.listen_port = random.randint(10024, 65555)
        cls.mock_server = HTTPServer((cls.listen_host, cls.listen_port), MockHTTPServerRequestHandler)

        cls.mock_server_thread = threading.Thread(target=cls.mock_server.serve_forever)
        cls.mock_server_thread.setDaemon(True)
        cls.mock_server_thread.start()

    @classmethod
    def tearDownCls(cls):
        cls.mock_server_thread.kill()

    def test_prepared_request_empty_body_chunked_encoding_not_used(self):
        connection = LibcloudConnection(host=self.listen_host, port=self.listen_port)
        connection.prepared_request(method='GET', url='/test/prepared-request-1', body='', stream=True)

        self.assertEqual(connection.response.status_code, httplib.OK)
        self.assertEqual(connection.response.content, b'/test/prepared-request-1')

        connection = LibcloudConnection(host=self.listen_host, port=self.listen_port)
        connection.prepared_request(method='GET', url='/test/prepared-request-2', body=None, stream=True)

        self.assertEqual(connection.response.status_code, httplib.OK)
        self.assertEqual(connection.response.content, b'/test/prepared-request-2')

    def test_prepared_request_with_body(self):
        connection = LibcloudConnection(host=self.listen_host, port=self.listen_port)
        connection.prepared_request(method='GET', url='/test/prepared-request-3', body='test body', stream=True)

        self.assertEqual(connection.response.status_code, httplib.OK)
        self.assertEqual(connection.response.content, b'/test/prepared-request-3')


class MockHTTPServerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/test/prepared-request-1', '/test/prepared-request-2']:
            # Verify that chunked encoding is not used for prepared requests
            # with empty body
            # See https://github.com/apache/libcloud/issues/1487
            headers = dict(self.headers)
            assert 'Content-Length' not in headers

            self.connection.setblocking(0)
            # Body should not contain '0' which indicates chunked request
            body = self.rfile.read(1)
            assert body is None

            self.send_response(requests.codes.ok)
            self.end_headers()

            self.wfile.write(self.path.encode('utf-8'))
        elif self.path == '/test/prepared-request-3':
            headers = dict(self.headers)
            assert int(headers['Content-Length']) == 9

            body = self.rfile.read(int(headers['Content-Length']))
            assert body == b'test body'

            self.send_response(requests.codes.ok)
            self.end_headers()

            self.wfile.write(self.path.encode('utf-8'))
        else:
            self.send_response(requests.codes.internal_server_error)
            self.end_headers()


if __name__ == '__main__':
    sys.exit(unittest.main())
