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
import json
import mock
import re
import sys
import unittest

from io import BytesIO

import email.utils
import pytest
from mock import Mock
from mock import PropertyMock

from libcloud.common.google import GoogleAuthType
from libcloud.common.types import InvalidCredsError
from libcloud.storage.base import Container
from libcloud.storage.base import Object
from libcloud.storage.drivers import google_storage
from libcloud.test import StorageMockHttp
from libcloud.test.common.test_google import GoogleTestCase
from libcloud.test.file_fixtures import StorageFileFixtures
from libcloud.test.secrets import STORAGE_GOOGLE_STORAGE_PARAMS
from libcloud.test.storage.test_s3 import S3Tests, S3MockHttp
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import StringIO

CONN_CLS = google_storage.GoogleStorageConnection
JSON_CONN_CLS = google_storage.GoogleStorageJSONConnection

TODAY = email.utils.formatdate(usegmt=True)


def _error_helper(code, headers):
    message = httplib.responses[code]
    body = {
        'error': {
            'errors': [
                {
                    'code': code,
                    'message': message,
                    'reason': message,
                },
            ],
        },
    }
    return code, json.dumps(body), headers, httplib.responses[code]


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
            'content-length': '12345',
            'last-modified': 'Thu, 13 Sep 2012 07:13:22 GMT'
        }

        return httplib.OK, body, headers, httplib.responses[httplib.OK]

    def _container_path_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED,
                '',
                self.base_headers,
                httplib.responses[httplib.OK])


class GoogleStorageJSONMockHttp(StorageMockHttp):
    """
    Extracts bucket and object out of requests and routes to methods of the
    forms (bucket, object, entity, and type are sanitized values
    {'-', '.', '/' are replaced with '_'}):

    _<bucket>[_<type>]
    _<bucket>_acl[_entity][_<type>]
    _<bucket>_defaultObjectAcl[_<entity>][_<type>]
    _<bucket>_<object>[_<type>]
    _<bucket>_<object>_acl[_<entity>][_<type>]

    Ugly example:
        /storage/v1/b/test-bucket/o/test-object/acl/test-entity
        with type='FOO' yields
        _test_bucket_test_object_acl_test_entity_FOO
    """
    fixtures = StorageFileFixtures('google_storage')
    base_headers = {}

    # Path regex captures bucket, object, defaultObjectAcl, and acl values.
    path_rgx = re.compile(
        r'/storage/[^/]+/b/([^/]+)'
        r'(?:/(defaultObjectAcl(?:/[^/]+)?$)|'
        r'(?:/o/(.+?))?(?:/(acl(?:/[^/]+)?))?$)')

    # Permissions to use when handling requests.
    bucket_perms = google_storage.ContainerPermissions.NONE
    object_perms = google_storage.ObjectPermissions.NONE

    _FORBIDDEN = _error_helper(httplib.FORBIDDEN, base_headers)
    _NOT_FOUND = _error_helper(httplib.NOT_FOUND, base_headers)
    _PRECONDITION_FAILED = _error_helper(
        httplib.PRECONDITION_FAILED, base_headers)

    def _get_method_name(self, type, use_param, qs, path):
        match = self.path_rgx.match(path)
        if not match:
            raise ValueError('%s is not a valid path.' % path)

        joined_groups = '_'.join([g for g in match.groups() if g])
        if type:
            meth_name = '_%s_%s' % (joined_groups, type)
        else:
            meth_name = '_%s' % joined_groups
        # Return sanitized method name.
        return meth_name.replace('/', '_').replace('.', '_').replace('-', '_')

    def _response_helper(self, fixture):
        body = self.fixtures.load(fixture)
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    ####################
    # Request handlers #
    ####################
    def _test_bucket(self, method, url, body, headers):
        """Bucket request."""
        if method != 'GET':
            raise NotImplementedError('%s is not implemented.' % method)

        if self.bucket_perms < google_storage.ContainerPermissions.READER:
            return self._FORBIDDEN
        else:
            return self._response_helper('get_container.json')

    def _test_bucket_acl(self, method, url, body, headers):
        """Bucket list ACL request."""
        if method != 'GET':
            raise NotImplementedError('%s is not implemented.' % method)

        if self.bucket_perms < google_storage.ContainerPermissions.OWNER:
            return self._FORBIDDEN
        else:
            return self._response_helper('list_container_acl.json')

    def _test_bucket_test_object(self, method, url, body, headers):
        """Object request."""
        if method != 'GET':
            raise NotImplementedError('%s is not implemented.' % method)

        if self.object_perms < google_storage.ObjectPermissions.READER:
            return self._FORBIDDEN
        else:
            return self._response_helper('get_object.json')

    def _test_bucket_test_object_acl(self, method, url, body, headers):
        """Object list ACL request."""
        if method != 'GET':
            raise NotImplementedError('%s is not implemented.' % method)

        if self.object_perms < google_storage.ObjectPermissions.OWNER:
            return self._FORBIDDEN
        else:
            return self._response_helper('list_object_acl.json')

    def _test_bucket_writecheck(self, method, url, body, headers):
        gen_match = headers.get('x-goog-if-generation-match')
        if method != 'DELETE' or gen_match != '0':
            msg = ('Improper write check delete strategy. method: %s, '
                   'headers: %s' % (method, headers))
            raise ValueError(msg)

        if self.bucket_perms < google_storage.ContainerPermissions.WRITER:
            return self._FORBIDDEN
        else:
            return self._PRECONDITION_FAILED


class GoogleStorageConnectionTest(GoogleTestCase):

    @mock.patch('email.utils.formatdate')
    def test_add_default_headers(self, mock_formatdate):
        mock_formatdate.return_value = TODAY
        starting_headers = {'starting': 'headers'}
        project = 'foo-project'

        # Modify headers when there is no project.
        conn = CONN_CLS(
            'foo_user', 'bar_key', secure=True,
            auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = mock.Mock(return_value=None)
        headers = dict(starting_headers)
        headers['Date'] = TODAY
        self.assertEqual(
            conn.add_default_headers(dict(starting_headers)), headers)

        # Modify headers when there is a project.
        conn = CONN_CLS(
            'foo_user', 'bar_key', secure=True,
            auth_type=GoogleAuthType.GCS_S3)
        conn.get_project = mock.Mock(return_value=project)
        headers = dict(starting_headers)
        headers['Date'] = TODAY
        headers[CONN_CLS.PROJECT_ID_HEADER] = project
        self.assertEqual(
            conn.add_default_headers(dict(starting_headers)), headers)

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

        conn = CONN_CLS(
            'foo_user', 'bar_key', secure=True,
            auth_type=GoogleAuthType.GCS_S3)
        conn.method = 'GET'
        conn.action = '/path'
        result = conn._get_s3_auth_signature(starting_params, starting_headers)
        self.assertNotEqual(starting_headers, modified_headers)
        self.assertEqual(result, 'mock signature!')
        mock_s3_auth_sig_method.assert_called_once_with(
            method='GET', headers=modified_headers, params=starting_params,
            expires=None, secret_key='bar_key', path='/path',
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

        conn = CONN_CLS(
            'foo_user', 'bar_key', secure=True, auth_type=GoogleAuthType.GCE)
        conn._get_s3_auth_signature = mock.Mock()
        conn.oauth2_credential = mock.Mock()
        conn.oauth2_credential.access_token = 'Access_Token!'
        expected_headers = dict(starting_headers)
        expected_headers['Authorization'] = 'Bearer Access_Token!'
        result = conn.pre_connect_hook(
            dict(starting_params), dict(starting_headers))
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

        conn = CONN_CLS(
            'foo_user', 'bar_key', secure=True,
            auth_type=GoogleAuthType.GCS_S3)
        conn._get_s3_auth_signature = fake_hmac_method
        conn.action = 'GET'
        conn.method = '/foo'
        expected_headers = dict(starting_headers)
        expected_headers['Authorization'] = (
            '%s %s:%s' % (google_storage.SIGNATURE_IDENTIFIER, 'foo_user',
                          'fake signature!')
        )
        result = conn.pre_connect_hook(
            dict(starting_params), dict(starting_headers))
        self.assertEqual(result, (dict(starting_params), expected_headers))
        self.assertEqual(fake_hmac_method.params_passed, starting_params)
        self.assertEqual(fake_hmac_method.headers_passed, starting_headers)
        self.assertIsNone(conn.oauth2_credential)


class GoogleStorageTests(S3Tests, GoogleTestCase):
    driver_type = google_storage.GoogleStorageDriver
    driver_args = STORAGE_GOOGLE_STORAGE_PARAMS
    mock_response_klass = GoogleStorageMockHttp

    def setUp(self):
        super(GoogleStorageTests, self).setUp()
        self.driver_type.jsonConnectionCls.conn_class = GoogleStorageJSONMockHttp

    def tearDown(self):
        self._remove_test_file()

    def test_billing_not_enabled(self):
        # TODO
        pass

    def test_token(self):
        # Not supported on Google Storage
        pass

    def test_delete_permissions(self):
        mock_request = mock.Mock()
        self.driver.json_connection.request = mock_request

        # Test deleting object permissions.
        self.driver.ex_delete_permissions(
            'bucket', 'object', entity='user-foo')
        url = '/storage/v1/b/bucket/o/object/acl/user-foo'
        mock_request.assert_called_once_with(url, method='DELETE')

        # Test deleting bucket permissions.
        mock_request.reset_mock()
        self.driver.ex_delete_permissions('bucket', entity='user-foo')
        url = '/storage/v1/b/bucket/acl/user-foo'
        mock_request.assert_called_once_with(url, method='DELETE')

    def test_delete_permissions_no_entity(self):
        mock_request = mock.Mock()
        mock_get_user = mock.Mock(return_value=None)
        self.driver._get_user = mock_get_user
        self.driver.json_connection.request = mock_request

        # Test deleting permissions on an object with no entity.
        self.assertRaises(
            ValueError, self.driver.ex_delete_permissions, 'bucket', 'object')

        # Test deleting permissions on an bucket with no entity.
        self.assertRaises(
            ValueError, self.driver.ex_delete_permissions, 'bucket')

        mock_request.assert_not_called()

        # Test deleting permissions on an object with a default entity.
        mock_get_user.return_value = 'foo@foo.com'
        self.driver.ex_delete_permissions('bucket', 'object')
        url = '/storage/v1/b/bucket/o/object/acl/user-foo@foo.com'
        mock_request.assert_called_once_with(url, method='DELETE')

        # Test deleting permissions on an bucket with a default entity.
        mock_request.reset_mock()
        mock_get_user.return_value = 'foo@foo.com'
        self.driver.ex_delete_permissions('bucket')
        url = '/storage/v1/b/bucket/acl/user-foo@foo.com'
        mock_request.assert_called_once_with(url, method='DELETE')

    def test_get_permissions(self):
        def test_permission_config(bucket_perms, object_perms):
            GoogleStorageJSONMockHttp.bucket_perms = bucket_perms
            GoogleStorageJSONMockHttp.object_perms = object_perms

            perms = self.driver.ex_get_permissions(
                'test-bucket', 'test-object')
            self.assertEqual(perms, (bucket_perms, object_perms))

        bucket_levels = range(len(google_storage.ContainerPermissions.values))
        object_levels = range(len(google_storage.ObjectPermissions.values))
        for bucket_perms in bucket_levels:
            for object_perms in object_levels:
                test_permission_config(bucket_perms, object_perms)

    def test_set_permissions(self):
        mock_request = mock.Mock()
        self.driver.json_connection.request = mock_request

        # Test setting object permissions.
        self.driver.ex_set_permissions(
            'bucket', 'object', entity='user-foo', role='OWNER')
        url = '/storage/v1/b/bucket/o/object/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo'}))

        # Test setting object permissions with an ObjectPermissions value.
        mock_request.reset_mock()
        self.driver.ex_set_permissions(
            'bucket', 'object', entity='user-foo',
            role=google_storage.ObjectPermissions.OWNER)
        url = '/storage/v1/b/bucket/o/object/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo'}))

        # Test setting bucket permissions.
        mock_request.reset_mock()
        self.driver.ex_set_permissions(
            'bucket', entity='user-foo', role='OWNER')
        url = '/storage/v1/b/bucket/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo'}))

        # Test setting bucket permissions with a ContainerPermissions value.
        mock_request.reset_mock()
        self.driver.ex_set_permissions(
            'bucket', entity='user-foo',
            role=google_storage.ContainerPermissions.OWNER)
        url = '/storage/v1/b/bucket/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo'}))

    def test_set_permissions_bad_roles(self):
        mock_request = mock.Mock()
        self.driver.json_connection.request = mock_request

        # Test forgetting a role.
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket', 'object')
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket')
        mock_request.assert_not_called()

        # Test container permissions on an object.
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket', 'object',
            role=google_storage.ContainerPermissions.OWNER)
        mock_request.assert_not_called()

        # Test object permissions on a container.
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket',
            role=google_storage.ObjectPermissions.OWNER)
        mock_request.assert_not_called()

    def test_set_permissions_no_entity(self):
        mock_request = mock.Mock()
        mock_get_user = mock.Mock(return_value=None)
        self.driver._get_user = mock_get_user
        self.driver.json_connection.request = mock_request

        # Test for setting object permissions with no entity.
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket', 'object',
            role='OWNER')

        # Test for setting bucket permissions with no entity.
        self.assertRaises(
            ValueError, self.driver.ex_set_permissions, 'bucket', role='OWNER')

        mock_request.assert_not_called()

        # Test for setting object permissions with a default entity.
        mock_get_user.return_value = 'foo@foo.com'
        self.driver.ex_set_permissions('bucket', 'object', role='OWNER')
        url = '/storage/v1/b/bucket/o/object/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo@foo.com'}))

        # Test for setting bucket permissions with a default entity.
        mock_request.reset_mock()
        mock_get_user.return_value = 'foo@foo.com'
        self.driver.ex_set_permissions('bucket', role='OWNER')
        url = '/storage/v1/b/bucket/acl'
        mock_request.assert_called_once_with(
            url, method='POST',
            data=json.dumps({'role': 'OWNER', 'entity': 'user-foo@foo.com'}))

    def test_invalid_credentials_on_upload(self):
        self.mock_response_klass.type = 'UNAUTHORIZED'
        container = Container(name='container', driver=self.driver, extra={})
        with pytest.raises(InvalidCredsError):
            self.driver.upload_object_via_stream(
                BytesIO(b' '), container, 'path')

    def test_download_object_data_is_not_buffered_in_memory(self):
        # Test case which verifies that response.body attribute is not accessed
        # and as such, whole body response is not buffered into RAM

        # If content is consumed and response.content attribute accessed execption
        # will be thrown and test will fail

        mock_response = Mock(name='mock response')
        mock_response.headers = {}
        mock_response.status_code = 200
        msg = '"content" attribute was accessed but it shouldn\'t have been'
        type(mock_response).content = PropertyMock(name='mock content attribute',
                                                   side_effect=Exception(msg))
        mock_response.iter_content.return_value = StringIO('a' * 1000)

        self.driver.connection.connection.getresponse = Mock()
        self.driver.connection.connection.getresponse.return_value = mock_response

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object_NO_BUFFER', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = self._file_path
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=True,
                                             delete_on_failure=True)
        self.assertTrue(result)


if __name__ == '__main__':
    sys.exit(unittest.main())
