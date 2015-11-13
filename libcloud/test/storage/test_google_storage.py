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

import mock
import sys
import unittest

import email.utils

from libcloud.common.google import GoogleAuthType
from libcloud.storage.drivers.google_storage import GoogleStorageConnection
from libcloud.storage.drivers.google_storage import GoogleStorageDriver
from libcloud.storage.drivers.google_storage import SIGNATURE_IDENTIFIER
from libcloud.test import LibcloudTestCase
from libcloud.test.file_fixtures import StorageFileFixtures
from libcloud.test.secrets import STORAGE_GOOGLE_STORAGE_PARAMS
from libcloud.test.storage.test_s3 import S3Tests, S3MockHttp
from libcloud.utils.py3 import httplib


class GoogleStorageMockHttp(S3MockHttp):
    fixtures = StorageFileFixtures('google_storage')

    def _test2_test_get_object(self, method, url, body, headers):
        # test_get_object
        # Google uses a different HTTP header prefix for meta data
        body = self.fixtures.load('list_containers.xml')
        headers = {'content-type': 'application/zip',
                   'etag': '"e31208wqsdoj329jd"',
                   'x-goog-meta-rabbits': 'monkeys',
                   'content-length': 12345,
                   'last-modified': 'Thu, 13 Sep 2012 07:13:22 GMT'
                   }

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])


class GoogleStorageConnectionTest(LibcloudTestCase):
    conn_cls = GoogleStorageConnection
    today = email.utils.formatdate(usegmt=True)

    @mock.patch('email.utils.formatdate')
    @mock.patch('libcloud.common.google.'
                'GoogleBaseConnection.add_default_headers')
    @mock.patch('libcloud.storage.drivers.google_storage.'
                'GoogleStorageConnection._setup_oauth2')
    def test_add_default_headers(self, _, mock_base_method, mock_formatdate):
        mock_formatdate.return_value = self.today
        starting_headers = {'starting': 'headers'}
        changed_headers = {'changed': 'headers'}
        project = 'foo-project'

        # Should use base add_default_headers
        mock_base_method.return_value = dict(changed_headers)
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCE)
        conn.get_project = lambda: None
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         dict(changed_headers))
        mock_base_method.assert_called_once_with(dict(starting_headers))
        mock_base_method.reset_mock()

        # Base add_default_headers with project
        mock_base_method.return_value = dict(changed_headers)
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCE)
        conn.get_project = lambda: project
        headers = dict(changed_headers)
        headers[GoogleStorageConnection.PROJECT_ID_HEADER] = project
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         headers)
        mock_base_method.assert_called_once_with(dict(starting_headers))
        mock_base_method.reset_mock()

        # Should use S3 add_default_headers
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = lambda: None
        headers = dict(starting_headers)
        headers['Date'] = self.today
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         headers)
        mock_base_method.assert_not_called()

        # S3 add_default_headers with project
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = lambda: project
        headers = dict(starting_headers)
        headers['Date'] = self.today
        headers[GoogleStorageConnection.PROJECT_ID_HEADER] = project
        self.assertEqual(conn.add_default_headers(dict(starting_headers)),
                         headers)
        mock_base_method.assert_not_called()

    @mock.patch('libcloud.common.google.GoogleBaseConnection.encode_data')
    @mock.patch('libcloud.storage.drivers.google_storage.'
                'GoogleStorageConnection._setup_oauth2')
    def test_encode_data(self, _, mock_base_method):
        old_data = 'old data!'
        new_data = 'new data!'

        # Should use Base encode_data
        mock_base_method.return_value = new_data
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCE)
        self.assertEqual(conn.encode_data(old_data), new_data)
        mock_base_method.assert_called_once_with(old_data)
        mock_base_method.reset_mock()

        # Should use S3 encode_data (which does nothing)
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCS_S3)
        self.assertEqual(conn.encode_data(old_data), old_data)
        mock_base_method.assert_not_called()

    @mock.patch('libcloud.common.google.GoogleBaseConnection.pre_connect_hook')
    @mock.patch('libcloud.storage.drivers.google_storage._get_aws_auth_param')
    @mock.patch('libcloud.storage.drivers.google_storage.'
                'GoogleStorageConnection._setup_oauth2')
    def test_pre_connect_hook(self, _, mock_auth_param_method,
                              mock_base_method):
        starting_params = {'starting': 'params'}
        changed_params = {'changed': 'params'}
        starting_headers = {'starting': 'headers'}
        changed_headers = {'changed': 'headers'}

        # Should use Base pre_connect_hook
        mock_base_method.return_value = (dict(changed_params),
                                         dict(changed_headers))
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCE)
        self.assertEqual(
            conn.pre_connect_hook(
                dict(starting_params), dict(starting_headers)),
            (dict(changed_params), dict(changed_headers)))
        mock_base_method.assert_called_once_with(
            dict(starting_params), dict(starting_headers))
        mock_base_method.reset_mock()

        # Should use S3 pre_connect_hook
        mock_auth_param_method.return_value = 'signature!'
        conn = self.conn_cls('foo_user', 'bar_key', secure=True,
                             auth_type=GoogleAuthType.GCS_S3)
        conn.action = 'GET'
        conn.method = '/foo'
        headers = dict(starting_headers)
        headers['Authorization'] = '%s %s:%s' % (SIGNATURE_IDENTIFIER,
                                                 'foo_user', 'signature!')
        self.assertEqual(
            conn.pre_connect_hook(
                dict(starting_params), dict(starting_headers)),
            (dict(starting_params), headers))
        mock_base_method.assert_not_called()
        mock_auth_param_method.assert_called_once()
        mock_auth_param_method.reset_mock()


class GoogleStorageTests(S3Tests):
    driver_type = GoogleStorageDriver
    driver_args = STORAGE_GOOGLE_STORAGE_PARAMS
    mock_response_klass = GoogleStorageMockHttp

    def test_billing_not_enabled(self):
        # TODO
        pass

    def test_token(self):
        # Not supported on Google Storage
        pass


if __name__ == '__main__':
    sys.exit(unittest.main())
