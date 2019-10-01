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
import warnings

import libcloud.security

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

if __name__ == '__main__':
    sys.exit(unittest.main())
