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

import copy
import mock
import sys
import unittest

import email.utils

from libcloud.common.google import GoogleAuthType
from libcloud.storage.drivers import google_storage
from libcloud.test.common.test_google import GoogleTestCase
from libcloud.test.file_fixtures import StorageFileFixtures
from libcloud.test.secrets import STORAGE_GOOGLE_STORAGE_PARAMS
from libcloud.test.storage.test_s3 import S3Tests, S3MockHttp
from libcloud.utils.py3 import httplib

CONN_CLS = google_storage.GoogleStorageConnection
STORAGE_CLS = google_storage.GoogleStorageDriver

TODAY = email.utils.formatdate(usegmt=True)


class GoogleStorageMockHttp(S3MockHttp):
    fixtures = StorageFileFixtures('google_storage')

    def _test2_test_get_object(self, method, url, body, headers):
        # test_get_object
        # Google uses a different HTTP header prefix for meta data
        body = self.fixtures.load('list_containers.xml')
        headers = {
            'content-type': 'application/zip',
            'etag': '"e31208wqsdoj329jd"',
            'x-goog-meta-rabbits': 'monkeys',
            'content-length': 12345,
            'last-modified': 'Thu, 13 Sep 2012 07:13:22 GMT'
        }

        return (
            httplib.OK,
            body,
            headers,
            httplib.responses[httplib.OK]
        )


class GoogleStorageConnectionTest(GoogleTestCase):

    @mock.patch('email.utils.formatdate')
    def test_add_default_headers(self, mock_formatdate):
        mock_formatdate.return_value = TODAY
        starting_headers = {'starting': 'headers'}
        project = 'foo-project'

        # Modify headers when there is no project.
        conn = CONN_CLS('foo_user', 'bar_key', secure=True,
                        auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = lambda: None
        headers = dict(starting_headers)
        headers['Date'] = TODAY
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         headers)

        # Modify headers when there is a project.
        conn = CONN_CLS('foo_user', 'bar_key', secure=True,
                        auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = lambda: project
        headers = dict(starting_headers)
        headers['Date'] = TODAY
        headers[CONN_CLS.PROJECT_ID_HEADER] = project
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         headers)

    @mock.patch('libcloud.storage.drivers.s3.'
                'BaseS3Connection.get_auth_signature')
    def test_get_s3_auth_signature(self, mock_s3_auth_sig_method):
        # Check that the S3 HMAC signature method is used.
        # Check that headers are copied and modified properly before calling
        # the signature method.
        mock_s3_auth_sig_method.return_value = 'mock signature!'
        starting_params = {}
        starting_headers = {
            'Date': TODAY,
            'x-goog-foo': 'X-GOOG: MAINTAIN UPPERCASE!',
            'x-Goog-bar': 'Header key should be lowered',
            'Other': 'LOWER THIS!'
        }
        modified_headers = {
            'date': TODAY,
            'x-goog-foo': 'X-GOOG: MAINTAIN UPPERCASE!',
            'x-goog-bar': 'Header key should be lowered',
            'other': 'lower this!'
        }

        conn = CONN_CLS('foo_user', 'bar_key', secure=True,
                        auth_type=GoogleAuthType.GCS_S3)
        conn.method = 'GET'
        conn.action = '/path'
        result = conn._get_s3_auth_signature(starting_params, starting_headers)
        self.assertNotEqual(starting_headers, modified_headers)
        self.assertEqual(result, 'mock signature!')
        mock_s3_auth_sig_method.assert_called_once_with(
            method='GET',
            headers=modified_headers,
            params=starting_params,
            expires=None,
            secret_key='bar_key',
            path='/path',
            vendor_prefix='x-goog'
        )

    @mock.patch('libcloud.common.google.GoogleOAuth2Credential')
    def test_pre_connect_hook_oauth2(self, mock_oauth2_credential_init):
        # Check that we get the Authorization header from the OAuth2 token,
        # not from the HMAC signature method.
        # Check that the headers and pa
        mock_oauth2_credential_init.return_value = mock.Mock()
        starting_params = {'starting': 'params'}
        starting_headers = {'starting': 'headers'}

        conn = CONN_CLS('foo_user', 'bar_key', secure=True,
                        auth_type=GoogleAuthType.GCE)
        conn._get_s3_auth_signature = mock.Mock()
        conn.oauth2_credential = mock.Mock()
        conn.oauth2_credential.access_token = 'Access_Token!'
        expected_headers = dict(starting_headers)
        expected_headers['Authorization'] = 'Bearer Access_Token!'
        result = conn.pre_connect_hook(dict(starting_params),
                                       dict(starting_headers))
        self.assertEqual(result, (starting_params, expected_headers))

    def test_pre_connect_hook_hmac(self):
        # Check that we call for a HMAC signature, passing params and headers
        # Check that we properly apply the HMAC signature.
        # Check that we don't use OAuth2 credentials.
        starting_params = {'starting': 'params'}
        starting_headers = {'starting': 'headers'}

        def fake_hmac_method(params, headers):
            # snapshot the params and headers passed (they are modified later)
            fake_hmac_method.params_passed = copy.deepcopy(params)
            fake_hmac_method.headers_passed = copy.deepcopy(headers)
            return 'fake signature!'

        conn = CONN_CLS('foo_user', 'bar_key', secure=True,
                        auth_type=GoogleAuthType.GCS_S3)
        conn._get_s3_auth_signature = fake_hmac_method
        conn.action = 'GET'
        conn.method = '/foo'
        expected_headers = dict(starting_headers)
        expected_headers['Authorization'] = (
            '%s %s:%s' % (google_storage.SIGNATURE_IDENTIFIER, 'foo_user',
                          'fake signature!')
        )
        result = conn.pre_connect_hook(dict(starting_params),
                                       dict(starting_headers))
        self.assertEqual(result, (dict(starting_params), expected_headers))
        self.assertEqual(fake_hmac_method.params_passed, starting_params)
        self.assertEqual(fake_hmac_method.headers_passed, starting_headers)
        self.assertIsNone(conn.oauth2_credential)


class GoogleStorageTests(S3Tests, GoogleTestCase):
    driver_type = STORAGE_CLS
    driver_args = STORAGE_GOOGLE_STORAGE_PARAMS
    mock_response_klass = GoogleStorageMockHttp
    driver = google_storage.GoogleStorageDriver

    def test_billing_not_enabled(self):
        # TODO
        pass

    def test_token(self):
        # Not supported on Google Storage
        pass


if __name__ == '__main__':
    sys.exit(unittest.main())
