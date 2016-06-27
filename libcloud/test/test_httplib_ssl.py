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
import ssl
import socket

import mock
from mock import patch

import libcloud.security

from libcloud.utils.py3 import reload
from libcloud.httplib_ssl import LibcloudHTTPSConnection

from libcloud.test import unittest

ORIGINAL_CA_CERS_PATH = libcloud.security.CA_CERTS_PATH


class TestHttpLibSSLTests(unittest.TestCase):

    def setUp(self):
        libcloud.security.VERIFY_SSL_CERT = False
        libcloud.security.CA_CERTS_PATH = ORIGINAL_CA_CERS_PATH
        self.httplib_object = LibcloudHTTPSConnection('foo.bar')

    def test_custom_ca_path_using_env_var_doesnt_exist(self):
        os.environ['SSL_CERT_FILE'] = '/foo/doesnt/exist'

        try:
            reload(libcloud.security)
        except ValueError:
            e = sys.exc_info()[1]
            msg = 'Certificate file /foo/doesnt/exist doesn\'t exist'
            self.assertEqual(str(e), msg)
        else:
            self.fail('Exception was not thrown')

    def test_custom_ca_path_using_env_var_is_directory(self):
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.environ['SSL_CERT_FILE'] = file_path

        expected_msg = 'Certificate file can\'t be a directory'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                reload, libcloud.security)

    def test_custom_ca_path_using_env_var_exist(self):
        # When setting a path we don't actually check that a valid CA file is
        # provided.
        # This happens later in the code in httplib_ssl.connect method
        file_path = os.path.abspath(__file__)
        os.environ['SSL_CERT_FILE'] = file_path

        reload(libcloud.security)

        self.assertEqual(libcloud.security.CA_CERTS_PATH, [file_path])

    @patch('warnings.warn')
    def test_setup_verify(self, _):
        libcloud.security.CA_CERTS_PATH = []

        # Should throw a runtime error
        libcloud.security.VERIFY_SSL_CERT = True

        expected_msg = libcloud.security.CA_CERTS_UNAVAILABLE_ERROR_MSG
        self.assertRaisesRegexp(RuntimeError, expected_msg,
                                self.httplib_object._setup_verify)

        libcloud.security.VERIFY_SSL_CERT = False
        self.httplib_object._setup_verify()

    @patch('warnings.warn')
    def test_setup_ca_cert(self, _):
        # verify = False, _setup_ca_cert should be a no-op
        self.httplib_object.verify = False
        self.httplib_object._setup_ca_cert()

        self.assertEqual(self.httplib_object.ca_cert, None)

        # verify = True, a valid path is provided, self.ca_cert should be set to
        # a valid path
        self.httplib_object.verify = True

        libcloud.security.CA_CERTS_PATH = [os.path.abspath(__file__)]
        self.httplib_object._setup_ca_cert()

        self.assertTrue(self.httplib_object.ca_cert is not None)

        # verify = True, no CA certs are available, exception should be thrown
        libcloud.security.CA_CERTS_PATH = []

        expected_msg = libcloud.security.CA_CERTS_UNAVAILABLE_ERROR_MSG
        self.assertRaisesRegexp(RuntimeError, expected_msg,
                                self.httplib_object._setup_ca_cert)

    @mock.patch('socket.create_connection', mock.MagicMock())
    @mock.patch('socket.socket', mock.MagicMock())
    def test_connect_throws_friendly_error_message_on_ssl_wrap_connection_reset_by_peer(self):

        mock_wrap_socket = None

        if getattr(ssl, 'HAS_SNI', False):
            ssl.SSLContext.wrap_socket = mock.MagicMock()
            mock_wrap_socket = ssl.SSLContext.wrap_socket
        else:
            ssl.wrap_socket = mock.MagicMock()
            mock_wrap_socket = ssl.wrap_socket

        # Test that we re-throw a more friendly error message in case
        # "connection reset by peer" error occurs when trying to establish a
        # SSL connection
        libcloud.security.VERIFY_SSL_CERT = True
        self.httplib_object.verify = True
        self.httplib_object.http_proxy_used = False

        # No connection reset by peer, original exception should be thrown
        mock_wrap_socket.side_effect = Exception('foo bar fail')

        expected_msg = 'foo bar fail'
        self.assertRaisesRegexp(Exception, expected_msg,
                                self.httplib_object.connect)

        # Connection reset by peer, wrapped exception with friendly error
        # message should be thrown
        mock_wrap_socket.side_effect = socket.error('Connection reset by peer')

        expected_msg = 'Failed to establish SSL / TLS connection'
        self.assertRaisesRegexp(socket.error, expected_msg,
                                self.httplib_object.connect)

        # Same error but including errno
        with self.assertRaises(socket.error) as cm:
            mock_wrap_socket.side_effect = socket.error(104, 'Connection reset by peer')
            self.httplib_object.connect()

        e = cm.exception
        self.assertEqual(e.errno, 104)
        self.assertTrue(expected_msg in str(e))

        # Test original exception is propagated correctly on non reset by peer
        # error
        with self.assertRaises(socket.error) as cm:
            mock_wrap_socket.side_effect = socket.error(105, 'Some random error')
            self.httplib_object.connect()

        e = cm.exception
        self.assertEqual(e.errno, 105)
        self.assertTrue('Some random error' in str(e))

    def test_certifi_ca_bundle_in_search_path(self):
        mock_certifi_ca_bundle_path = '/certifi/bundle/path'

        # Certifi not available
        import libcloud.security
        reload(libcloud.security)

        original_length = len(libcloud.security.CA_CERTS_PATH)

        self.assertTrue(mock_certifi_ca_bundle_path not in
                        libcloud.security.CA_CERTS_PATH)

        # Certifi is available
        mock_certifi = mock.Mock()
        mock_certifi.where.return_value = mock_certifi_ca_bundle_path
        sys.modules['certifi'] = mock_certifi

        # Certifi CA bundle path should be injected at the begining of search list
        import libcloud.security
        reload(libcloud.security)

        self.assertEqual(libcloud.security.CA_CERTS_PATH[0],
                         mock_certifi_ca_bundle_path)
        self.assertEqual(len(libcloud.security.CA_CERTS_PATH),
                         (original_length + 1))

        # Certifi is available, but USE_CERTIFI is set to False
        os.environ['LIBCLOUD_SSL_USE_CERTIFI'] = 'false'

        import libcloud.security
        reload(libcloud.security)

        self.assertTrue(mock_certifi_ca_bundle_path not in
                        libcloud.security.CA_CERTS_PATH)
        self.assertEqual(len(libcloud.security.CA_CERTS_PATH), original_length)

        # And enabled
        os.environ['LIBCLOUD_SSL_USE_CERTIFI'] = 'true'

        import libcloud.security
        reload(libcloud.security)

        self.assertEqual(libcloud.security.CA_CERTS_PATH[0],
                         mock_certifi_ca_bundle_path)
        self.assertEqual(len(libcloud.security.CA_CERTS_PATH),
                         (original_length + 1))


if __name__ == '__main__':
    sys.exit(unittest.main())
