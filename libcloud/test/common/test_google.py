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
"""
Tests for Google Connection classes.
"""
import datetime
import mock
import os
import sys
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.google import (GoogleAuthError,
                                    GoogleAuthType,
                                    GoogleBaseAuthConnection,
                                    GoogleInstalledAppAuthConnection,
                                    GoogleServiceAcctAuthConnection,
                                    GoogleGCEServiceAcctAuthConnection,
                                    GoogleOAuth2Credential,
                                    GoogleBaseConnection,
                                    _utcnow,
                                    _utc_timestamp)
from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.utils.py3 import httplib


# Skip some tests if cryptography is unavailable
try:
    from cryptography.hazmat.primitives.hashes import SHA256
except ImportError:
    SHA256 = None


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
PEM_KEY = os.path.join(SCRIPT_PATH, 'fixtures', 'google', 'pkey.pem')
JSON_KEY = os.path.join(SCRIPT_PATH, 'fixtures', 'google', 'pkey.json')
with open(JSON_KEY, 'r') as f:
    KEY_STR = json.loads(f.read())['private_key']


GCE_PARAMS = ('email@developer.gserviceaccount.com', 'key')
GCE_PARAMS_PEM_KEY = ('email@developer.gserviceaccount.com', PEM_KEY)
GCE_PARAMS_JSON_KEY = ('email@developer.gserviceaccount.com', JSON_KEY)
GCE_PARAMS_KEY = ('email@developer.gserviceaccount.com', KEY_STR)
GCE_PARAMS_IA = ('client_id', 'client_secret')
GCE_PARAMS_GCE = ('foo', 'bar')
# GOOG + 16 alphanumeric chars
GCS_S3_PARAMS_20 = ('GOOG0123456789ABCXYZ',
                    # 40 base64 chars
                    '0102030405060708091011121314151617181920')
# GOOG + 20 alphanumeric chars
GCS_S3_PARAMS_24 = ('GOOGDF5OVRRGU4APFNSTVCXI',
                    # 40 base64 chars
                    '0102030405060708091011121314151617181920')
# GOOG + 57 alphanumeric chars
GCS_S3_PARAMS_61 = (
    'GOOGDF5OVRRGU4APFNSTVCXIRRGU4AP56789ABCX56789ABCXRRGU4APFNSTV',
    # 40 base64 chars
    '0102030405060708091011121314151617181920'
)

STUB_UTCNOW = _utcnow()

STUB_TOKEN = {
    'access_token': 'tokentoken',
    'token_type': 'Bearer',
    'expires_in': 3600
}

STUB_IA_TOKEN = {
    'access_token': 'installedapp',
    'token_type': 'Bearer',
    'expires_in': 3600,
    'refresh_token': 'refreshrefresh'
}

STUB_REFRESH_TOKEN = {
    'access_token': 'refreshrefresh',
    'token_type': 'Bearer',
    'expires_in': 3600
}

STUB_TOKEN_FROM_FILE = {
    'access_token': 'token_from_file',
    'token_type': 'Bearer',
    'expire_time': _utc_timestamp(STUB_UTCNOW +
                                  datetime.timedelta(seconds=3600)),
    'expires_in': 3600
}


class MockJsonResponse(object):
    def __init__(self, body):
        self.object = body


class GoogleTestCase(LibcloudTestCase):
    """
    Assists in making Google tests hermetic and deterministic.

    Add anything that needs to be mocked here. Create a patcher with the
    suffix '_patcher'.

    e.g.
        _foo_patcher = mock.patch('module.submodule.class.foo', ...)

    Patchers are started at setUpClass and stopped at tearDownClass.

    Ideally, you should make a note in the thing being mocked, for clarity.
    """
    PATCHER_SUFFIX = '_patcher'

    _utcnow_patcher = mock.patch(
        'libcloud.common.google._utcnow', return_value=STUB_UTCNOW)

    _authtype_is_gce_patcher = mock.patch(
        'libcloud.common.google.GoogleAuthType._is_gce', return_value=False)

    _read_token_file_patcher = mock.patch(
        'libcloud.common.google.GoogleOAuth2Credential._get_token_from_file',
        return_value=STUB_TOKEN_FROM_FILE
    )

    _write_token_file_patcher = mock.patch(
        'libcloud.common.google.GoogleOAuth2Credential._write_token_to_file')

    _ia_get_code_patcher = mock.patch(
        'libcloud.common.google.GoogleInstalledAppAuthConnection.get_code',
        return_value=1234
    )

    @classmethod
    def setUpClass(cls):
        super(GoogleTestCase, cls).setUpClass()

        for patcher in [a for a in dir(cls) if a.endswith(cls.PATCHER_SUFFIX)]:
            getattr(cls, patcher).start()

    @classmethod
    def tearDownClass(cls):
        super(GoogleTestCase, cls).tearDownClass()

        for patcher in [a for a in dir(cls) if a.endswith(cls.PATCHER_SUFFIX)]:
            getattr(cls, patcher).stop()


class GoogleBaseAuthConnectionTest(GoogleTestCase):
    """
    Tests for GoogleBaseAuthConnection
    """

    def setUp(self):
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        self.mock_scopes = ['foo', 'bar']
        kwargs = {'scopes': self.mock_scopes}
        self.conn = GoogleInstalledAppAuthConnection(*GCE_PARAMS,
                                                     **kwargs)

    def test_scopes(self):
        self.assertEqual(self.conn.scopes, 'foo bar')

    def test_add_default_headers(self):
        old_headers = {}
        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'accounts.google.com'}
        new_headers = self.conn.add_default_headers(old_headers)
        self.assertEqual(new_headers, expected_headers)

    def test_token_request(self):
        request_body = {'code': 'asdf', 'client_id': self.conn.user_id,
                        'client_secret': self.conn.key,
                        'redirect_uri': self.conn.redirect_uri,
                        'grant_type': 'authorization_code'}
        new_token = self.conn._token_request(request_body)
        self.assertEqual(new_token['access_token'],
                         STUB_IA_TOKEN['access_token'])
        exp = STUB_UTCNOW + datetime.timedelta(
            seconds=STUB_IA_TOKEN['expires_in'])
        self.assertEqual(new_token['expire_time'], _utc_timestamp(exp))


class GoogleInstalledAppAuthConnectionTest(GoogleTestCase):
    """
    Tests for GoogleInstalledAppAuthConnection
    """

    def setUp(self):
        GoogleInstalledAppAuthConnection.conn_class = GoogleAuthMockHttp
        self.mock_scopes = ['https://www.googleapis.com/auth/foo']
        kwargs = {'scopes': self.mock_scopes}
        self.conn = GoogleInstalledAppAuthConnection(*GCE_PARAMS,
                                                     **kwargs)

    def test_refresh_token(self):
        # This token info doesn't have a refresh token, so a new token will be
        # requested
        token_info1 = {'access_token': 'tokentoken', 'token_type': 'Bearer',
                       'expires_in': 3600}
        new_token1 = self.conn.refresh_token(token_info1)
        self.assertEqual(new_token1['access_token'],
                         STUB_IA_TOKEN['access_token'])

        # This token info has a refresh token, so it will be able to be
        # refreshed.
        token_info2 = {'access_token': 'tokentoken', 'token_type': 'Bearer',
                       'expires_in': 3600, 'refresh_token': 'refreshrefresh'}
        new_token2 = self.conn.refresh_token(token_info2)
        self.assertEqual(new_token2['access_token'],
                         STUB_REFRESH_TOKEN['access_token'])

        # Both sets should have refresh info
        self.assertTrue('refresh_token' in new_token1)
        self.assertTrue('refresh_token' in new_token2)


class GoogleAuthTypeTest(GoogleTestCase):

    def test_guess(self):
        self.assertEqual(GoogleAuthType.guess_type(GCE_PARAMS_IA[0]),
                         GoogleAuthType.IA)
        with mock.patch.object(GoogleAuthType, '_is_gce', return_value=True):
            # Since _is_gce currently depends on the environment, not on
            # parameters, other auths should override GCE. It does not make
            # sense for IA auth to happen on GCE, which is why it's left out.
            self.assertEqual(GoogleAuthType.guess_type(GCE_PARAMS[0]),
                             GoogleAuthType.SA)
            self.assertEqual(
                GoogleAuthType.guess_type(GCS_S3_PARAMS_20[0]),
                GoogleAuthType.GCS_S3)
            self.assertEqual(
                GoogleAuthType.guess_type(GCS_S3_PARAMS_24[0]),
                GoogleAuthType.GCS_S3)
            self.assertEqual(
                GoogleAuthType.guess_type(GCS_S3_PARAMS_61[0]),
                GoogleAuthType.GCS_S3)
            self.assertEqual(GoogleAuthType.guess_type(GCE_PARAMS_GCE[0]),
                             GoogleAuthType.GCE)


class GoogleOAuth2CredentialTest(GoogleTestCase):

    def test_init_oauth2(self):
        kwargs = {'auth_type': GoogleAuthType.IA}
        cred = GoogleOAuth2Credential(*GCE_PARAMS, **kwargs)

        # If there is a viable token file, this gets used first
        self.assertEqual(cred.token, STUB_TOKEN_FROM_FILE)

        # No token file, get a new token. Check that it gets written to file.
        with mock.patch.object(GoogleOAuth2Credential, '_get_token_from_file',
                               return_value=None):
            cred = GoogleOAuth2Credential(*GCE_PARAMS, **kwargs)
            expected = STUB_IA_TOKEN
            expected['expire_time'] = cred.token['expire_time']
            self.assertEqual(cred.token, expected)
            cred._write_token_to_file.assert_called_once_with()

    def test_refresh(self):
        args = list(GCE_PARAMS) + [GoogleAuthType.GCE]
        cred = GoogleOAuth2Credential(*args)
        cred._refresh_token = mock.Mock()

        # Test getting an unexpired access token.
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        cred.token = {'access_token': 'Access Token!',
                      'expire_time': _utc_timestamp(tomorrow)}
        cred.access_token
        self.assertFalse(cred._refresh_token.called)

        # Test getting an expired access token.
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        cred.token = {'access_token': 'Access Token!',
                      'expire_time': _utc_timestamp(yesterday)}
        cred.access_token
        self.assertTrue(cred._refresh_token.called)

    def test_auth_connection(self):
        # Test a bogus auth type
        self.assertRaises(GoogleAuthError, GoogleOAuth2Credential, *GCE_PARAMS,
                          **{'auth_type': 'XX'})
        # Try to create an OAuth2 credential when dealing with a GCS S3
        # interoperability auth type.
        self.assertRaises(GoogleAuthError, GoogleOAuth2Credential, *GCE_PARAMS,
                          **{'auth_type': GoogleAuthType.GCS_S3})

        kwargs = {}

        if SHA256:
            kwargs['auth_type'] = GoogleAuthType.SA
            cred1 = GoogleOAuth2Credential(*GCE_PARAMS_PEM_KEY, **kwargs)
            self.assertTrue(isinstance(cred1.oauth2_conn,
                                       GoogleServiceAcctAuthConnection))

            cred1 = GoogleOAuth2Credential(*GCE_PARAMS_JSON_KEY, **kwargs)
            self.assertTrue(isinstance(cred1.oauth2_conn,
                                       GoogleServiceAcctAuthConnection))

            cred1 = GoogleOAuth2Credential(*GCE_PARAMS_KEY, **kwargs)
            self.assertTrue(isinstance(cred1.oauth2_conn,
                                       GoogleServiceAcctAuthConnection))

        kwargs['auth_type'] = GoogleAuthType.IA
        cred2 = GoogleOAuth2Credential(*GCE_PARAMS_IA, **kwargs)
        self.assertTrue(isinstance(cred2.oauth2_conn,
                                   GoogleInstalledAppAuthConnection))

        kwargs['auth_type'] = GoogleAuthType.GCE
        cred3 = GoogleOAuth2Credential(*GCE_PARAMS_GCE, **kwargs)
        self.assertTrue(isinstance(cred3.oauth2_conn,
                                   GoogleGCEServiceAcctAuthConnection))


class GoogleBaseConnectionTest(GoogleTestCase):
    """
    Tests for GoogleBaseConnection
    """

    def setUp(self):
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        self.mock_scopes = ['https://www.googleapis.com/auth/foo']
        kwargs = {'scopes': self.mock_scopes,
                  'auth_type': GoogleAuthType.IA}
        self.conn = GoogleBaseConnection(*GCE_PARAMS, **kwargs)

    def test_add_default_headers(self):
        old_headers = {}
        new_expected_headers = {'Content-Type': 'application/json',
                                'Host': 'www.googleapis.com'}
        new_headers = self.conn.add_default_headers(old_headers)
        self.assertEqual(new_headers, new_expected_headers)

    def test_pre_connect_hook(self):
        old_params = {}
        old_headers = {}
        auth_str = '%s %s' % (STUB_TOKEN_FROM_FILE['token_type'],
                              STUB_TOKEN_FROM_FILE['access_token'])
        new_expected_params = {}
        new_expected_headers = {'Authorization': auth_str}
        new_params, new_headers = self.conn.pre_connect_hook(old_params,
                                                             old_headers)
        self.assertEqual(new_params, new_expected_params)
        self.assertEqual(new_headers, new_expected_headers)

    def test_encode_data(self):
        data = {'key': 'value'}
        json_data = '{"key": "value"}'
        encoded_data = self.conn.encode_data(data)
        self.assertEqual(encoded_data, json_data)

    def test_has_completed(self):
        body1 = {"endTime": "2013-06-26T10:05:07.630-07:00",
                 "id": "3681664092089171723",
                 "kind": "compute#operation",
                 "status": "DONE",
                 "targetId": "16211908079305042870"}
        body2 = {"endTime": "2013-06-26T10:05:07.630-07:00",
                 "id": "3681664092089171723",
                 "kind": "compute#operation",
                 "status": "RUNNING",
                 "targetId": "16211908079305042870"}
        response1 = MockJsonResponse(body1)
        response2 = MockJsonResponse(body2)
        self.assertTrue(self.conn.has_completed(response1))
        self.assertFalse(self.conn.has_completed(response2))

    def test_get_poll_request_kwargs(self):
        body = {"endTime": "2013-06-26T10:05:07.630-07:00",
                "id": "3681664092089171723",
                "kind": "compute#operation",
                "selfLink": "https://www.googleapis.com/operations-test"}
        response = MockJsonResponse(body)
        expected_kwargs = {'action':
                           'https://www.googleapis.com/operations-test'}
        kwargs = self.conn.get_poll_request_kwargs(response, None, {})
        self.assertEqual(kwargs, expected_kwargs)

    def test_morph_action_hook(self):
        self.conn.request_path = '/compute/apiver/project/project-name'
        action1 = ('https://www.googleapis.com/compute/apiver/project'
                   '/project-name/instances')
        action2 = '/instances'
        expected_request = '/compute/apiver/project/project-name/instances'
        request1 = self.conn.morph_action_hook(action1)
        request2 = self.conn.morph_action_hook(action2)
        self.assertEqual(request1, expected_request)
        self.assertEqual(request2, expected_request)


class GoogleAuthMockHttp(MockHttp):
    """
    Mock HTTP Class for Google Auth Connections.
    """
    json_hdr = {'content-type': 'application/json; charset=UTF-8'}

    def _o_oauth2_token(self, method, url, body, headers):
        if 'code' in body:
            body = json.dumps(STUB_IA_TOKEN)
        elif 'refresh_token' in body:
            body = json.dumps(STUB_REFRESH_TOKEN)
        else:
            body = json.dumps(STUB_TOKEN)
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
