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
import unittest
from datetime import datetime

import mock

from libcloud.common.aws import AWSRequestSignerAlgorithmV4
from libcloud.common.aws import SignedAWSConnection
from libcloud.common.aws import UNSIGNED_PAYLOAD
from libcloud.test import LibcloudTestCase


class EC2MockDriver(object):
    region_name = 'my_region'


class AWSRequestSignerAlgorithmV4TestCase(LibcloudTestCase):

    def setUp(self):
        SignedAWSConnection.driver = EC2MockDriver()
        SignedAWSConnection.service_name = 'my_service'
        SignedAWSConnection.version = '2013-10-15'
        self.connection = SignedAWSConnection('my_key', 'my_secret')

        self.signer = AWSRequestSignerAlgorithmV4(access_key='my_key',
                                                  access_secret='my_secret',
                                                  version='2013-10-15',
                                                  connection=self.connection)

        SignedAWSConnection.action = '/my_action/'
        SignedAWSConnection.driver = EC2MockDriver()

        self.now = datetime(2015, 3, 4, hour=17, minute=34, second=52)

    def test_v4_signature(self):
        params = {
            'Action': 'DescribeInstances',
            'Version': '2013-10-15'
        }
        headers = {
            'Host': 'ec2.eu-west-1.amazonaws.com',
            'Accept-Encoding': 'gzip,deflate',
            'X-AMZ-Date': '20150304T173452Z',
            'User-Agent': 'libcloud/0.17.0 (Amazon EC2 (eu-central-1)) '
        }
        dt = self.now
        sig = self.signer._get_authorization_v4_header(params=params,
                                                       headers=headers,
                                                       dt=dt,
                                                       method='GET',
                                                       path='/my_action/')
        self.assertEqual(sig, 'AWS4-HMAC-SHA256 '
                              'Credential=my_key/20150304/my_region/my_service/aws4_request, '
                              'SignedHeaders=accept-encoding;host;user-agent;x-amz-date, '
                              'Signature=f9868f8414b3c3f856c7955019cc1691265541f5162b9b772d26044280d39bd3')

    def test_v4_signature_contains_user_id(self):
        sig = self.signer._get_authorization_v4_header(params={}, headers={},
                                                       dt=self.now)
        self.assertIn('Credential=my_key/', sig)

    def test_v4_signature_contains_credential_scope(self):
        with mock.patch('libcloud.common.aws.AWSRequestSignerAlgorithmV4._get_credential_scope') as mock_get_creds:
            mock_get_creds.return_value = 'my_credential_scope'
            sig = self.signer._get_authorization_v4_header(params={}, headers={}, dt=self.now)

        self.assertIn('Credential=my_key/my_credential_scope, ', sig)

    def test_v4_signature_contains_signed_headers(self):
        with mock.patch('libcloud.common.aws.AWSRequestSignerAlgorithmV4._get_signed_headers') as mock_get_headers:
            mock_get_headers.return_value = 'my_signed_headers'
            sig = self.signer._get_authorization_v4_header({}, {}, self.now,
                                                           method='GET',
                                                           path='/')
        self.assertIn('SignedHeaders=my_signed_headers, ', sig)

    def test_v4_signature_contains_signature(self):
        with mock.patch('libcloud.common.aws.AWSRequestSignerAlgorithmV4._get_signature') as mock_get_signature:
            mock_get_signature.return_value = 'my_signature'
            sig = self.signer._get_authorization_v4_header({}, {}, self.now)
        self.assertIn('Signature=my_signature', sig)

    def test_get_signature_(self):
        def _sign(key, msg, hex=False):
            if hex:
                return 'H|%s|%s' % (key, msg)
            else:
                return '%s|%s' % (key, msg)

        with mock.patch('libcloud.common.aws.AWSRequestSignerAlgorithmV4._get_key_to_sign_with') as mock_get_key:
            with mock.patch('libcloud.common.aws.AWSRequestSignerAlgorithmV4._get_string_to_sign') as mock_get_string:
                with mock.patch('libcloud.common.aws._sign', new=_sign):
                    mock_get_key.return_value = 'my_signing_key'
                    mock_get_string.return_value = 'my_string_to_sign'
                    sig = self.signer._get_signature({}, {}, self.now,
                                                     method='GET', path='/', data=None)

        self.assertEqual(sig, 'H|my_signing_key|my_string_to_sign')

    def test_get_string_to_sign(self):
        with mock.patch('hashlib.sha256') as mock_sha256:
            mock_sha256.return_value.hexdigest.return_value = 'chksum_of_canonical_request'
            to_sign = self.signer._get_string_to_sign({}, {}, self.now,
                                                      method='GET', path='/', data=None)

        self.assertEqual(to_sign,
                         'AWS4-HMAC-SHA256\n'
                         '20150304T173452Z\n'
                         '20150304/my_region/my_service/aws4_request\n'
                         'chksum_of_canonical_request')

    def test_get_key_to_sign_with(self):
        def _sign(key, msg, hex=False):
            return '%s|%s' % (key, msg)

        with mock.patch('libcloud.common.aws._sign', new=_sign):
            key = self.signer._get_key_to_sign_with(self.now)

        self.assertEqual(key, 'AWS4my_secret|20150304|my_region|my_service|aws4_request')

    def test_get_signed_headers_contains_all_headers_lowercased(self):
        headers = {'Content-Type': 'text/plain', 'Host': 'my_host', 'X-Special-Header': ''}
        signed_headers = self.signer._get_signed_headers(headers)

        self.assertIn('content-type', signed_headers)
        self.assertIn('host', signed_headers)
        self.assertIn('x-special-header', signed_headers)

    def test_get_signed_headers_concats_headers_sorted_lexically(self):
        headers = {'Host': 'my_host', 'X-Special-Header': '', '1St-Header': '2', 'Content-Type': 'text/plain'}
        signed_headers = self.signer._get_signed_headers(headers)

        self.assertEqual(signed_headers, '1st-header;content-type;host;x-special-header')

    def test_get_credential_scope(self):
        scope = self.signer._get_credential_scope(self.now)
        self.assertEqual(scope, '20150304/my_region/my_service/aws4_request')

    def test_get_canonical_headers_joins_all_headers(self):
        headers = {
            'accept-encoding': 'gzip,deflate',
            'host': 'my_host',
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'accept-encoding:gzip,deflate\n'
                         'host:my_host\n')

    def test_get_canonical_headers_sorts_headers_lexically(self):
        headers = {
            'accept-encoding': 'gzip,deflate',
            'host': 'my_host',
            '1st-header': '2',
            'x-amz-date': '20150304T173452Z',
            'user-agent': 'my-ua'
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         '1st-header:2\n'
                         'accept-encoding:gzip,deflate\n'
                         'host:my_host\n'
                         'user-agent:my-ua\n'
                         'x-amz-date:20150304T173452Z\n')

    def test_get_canonical_headers_lowercases_headers_names(self):
        headers = {
            'Accept-Encoding': 'GZIP,DEFLATE',
            'User-Agent': 'My-UA'
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'accept-encoding:GZIP,DEFLATE\n'
                         'user-agent:My-UA\n')

    def test_get_canonical_headers_trims_header_values(self):
        # TODO: according to AWS spec (and RFC 2616 Section 4.2.) excess whitespace
        # from inside non-quoted strings should be stripped. Now we only strip the
        # start and end of the string. See
        # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        headers = {
            'accept-encoding': '   gzip,deflate',
            'user-agent': 'libcloud/0.17.0 '
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'accept-encoding:gzip,deflate\n'
                         'user-agent:libcloud/0.17.0\n')

    def test_get_request_params_joins_params_sorted_lexically(self):
        self.assertEqual(self.signer._get_request_params({
            'Action': 'DescribeInstances',
            'Filter.1.Name': 'state',
            'Version': '2013-10-15'
        }),
            'Action=DescribeInstances&Filter.1.Name=state&Version=2013-10-15')

    def test_get_canonical_headers_allow_numeric_header_value(self):
        headers = {
            'Accept-Encoding': 'gzip,deflate',
            'Content-Length': 314
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'accept-encoding:gzip,deflate\n'
                         'content-length:314\n')

    def test_get_request_params_allows_integers_as_value(self):
        self.assertEqual(self.signer._get_request_params({'Action': 'DescribeInstances', 'Port': 22}),
                         'Action=DescribeInstances&Port=22')

    def test_get_request_params_urlquotes_params_keys(self):
        self.assertEqual(self.signer._get_request_params({'Action+Reaction': 'DescribeInstances'}),
                         'Action%2BReaction=DescribeInstances')

    def test_get_request_params_urlquotes_params_values(self):
        self.assertEqual(self.signer._get_request_params({
            'Action': 'DescribeInstances&Addresses',
            'Port-Range': '2000 3000'
        }),
            'Action=DescribeInstances%26Addresses&Port-Range=2000%203000')

    def test_get_request_params_urlquotes_params_values_allows_safe_chars_in_value(self):
        # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        self.assertEqual('Action=a~b.c_d-e',
                         self.signer._get_request_params({'Action': 'a~b.c_d-e'}))

    def test_get_payload_hash_returns_digest_of_empty_string_for_GET_requests(self):
        SignedAWSConnection.method = 'GET'
        self.assertEqual(self.signer._get_payload_hash(method='GET'),
                         'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_get_payload_hash_with_data_for_PUT_requests(self):
        SignedAWSConnection.method = 'PUT'
        self.assertEqual(self.signer._get_payload_hash(method='PUT', data='DUMMY'),
                         'ceec12762e66397b56dad64fd270bb3d694c78fb9cd665354383c0626dbab013')

    def test_get_payload_hash_with_empty_data_for_POST_requests(self):
        SignedAWSConnection.method = 'POST'
        self.assertEqual(self.signer._get_payload_hash(method='POST'),
                         UNSIGNED_PAYLOAD)

    def test_get_canonical_request(self):
        req = self.signer._get_canonical_request(
            {'Action': 'DescribeInstances', 'Version': '2013-10-15'},
            {'Accept-Encoding': 'gzip,deflate', 'User-Agent': 'My-UA'},
            method='GET',
            path='/my_action/',
            data=None
        )
        self.assertEqual(req, 'GET\n'
                              '/my_action/\n'
                              'Action=DescribeInstances&Version=2013-10-15\n'
                              'accept-encoding:gzip,deflate\n'
                              'user-agent:My-UA\n'
                              '\n'
                              'accept-encoding;user-agent\n'
                              'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_post_canonical_request(self):
        req = self.signer._get_canonical_request(
            {'Action': 'DescribeInstances', 'Version': '2013-10-15'},
            {'Accept-Encoding': 'gzip,deflate', 'User-Agent': 'My-UA'},
            method='POST',
            path='/my_action/',
            data='{}'
        )
        self.assertEqual(req, 'POST\n'
                              '/my_action/\n'
                              'Action=DescribeInstances&Version=2013-10-15\n'
                              'accept-encoding:gzip,deflate\n'
                              'user-agent:My-UA\n'
                              '\n'
                              'accept-encoding;user-agent\n'
                              '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a')

if __name__ == '__main__':
    sys.exit(unittest.main())
