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

from datetime import datetime

from libcloud.common.osc import OSCRequestSignerAlgorithmV4
from libcloud.test import LibcloudTestCase

import unittest
from libcloud.compute.providers import Provider
from libcloud.compute.providers import get_driver


class OSCRequestSignerAlgorithmV4TestCase(LibcloudTestCase):
    def setUp(self):
        cls = get_driver(Provider.OUTSCALE)
        self.driver = cls(key='my_key', secret='my_secret',
                          region="my_region", service="my_service")
        self.now = datetime(2015, 3, 4, hour=17, minute=34, second=52)
        self.version = "latest"
        self.signer = OSCRequestSignerAlgorithmV4(
            access_key=self.driver.key,
            access_secret=self.driver.secret,
            version=self.version,
            connection=self.driver.connection
        )

    def test_v4_signature_contains_user_id(self):
        action = "ReadImages"
        headers = self.signer.get_request_headers(
            action=action,
            data="{}",
            service_name=self.driver.service_name,
            region=self.driver.region
        )
        self.assertIn('Credential=my_key/', headers["Authorization"])

    def test_v4_signature_contains_credential_scope(self):
        action = "ReadImages"
        headers = self.signer.get_request_headers(
            action=action,
            data="{}",
            service_name=self.driver.service_name,
            region=self.driver.region
        )
        self.assertIn(
            'Credential=my_key/{}/my_region/my_service/osc4_request'.format(
                datetime.utcnow().strftime('%Y%m%d')
            ),
            headers["Authorization"]
        )

    def test_v4_signature_contains_signed_headers(self):
        action = "ReadImages"
        headers = self.signer.get_request_headers(
            action=action,
            data="{}",
            service_name=self.driver.service_name,
            region=self.driver.region
        )
        self.assertIn(
            'SignedHeaders=content-type;host;x-osc-date',
            headers["Authorization"]
        )

    def test_get_signed_headers_contains_all_headers_lowercased(self):
        path = "my_region/my_service/outscale.com"
        headers = {
            'Content-Type': "application/json; charset=utf-8",
            'X-Osc-Date': self.now,
            'Host': path,
        }
        signed_headers = self.signer._get_signed_headers(headers)
        self.assertIn('content-type', signed_headers)
        self.assertIn('host', signed_headers)
        self.assertIn('x-osc-date', signed_headers)

    def test_get_signed_headers_concats_headers_sorted_lexically(self):
        path = "my_region/my_service/outscale.com"
        headers = {
            'Content-Type': "application/json; charset=utf-8",
            'X-Osc-Date': self.now,
            'Host': path,
        }
        signed_headers = self.signer._get_signed_headers(headers)
        self.assertEqual(signed_headers, 'content-type;host;x-osc-date')

    def test_get_credential_scope(self):
        scope = self.signer._get_credential_scope(self.now)
        self.assertEqual(scope,
                         '20150304/my_region/my_service/osc4_request')

    def test_get_canonical_headers_joins_all_headers(self):
        headers = {
            'Content-Type': "application/json; charset=utf-8",
            'X-Osc-Date': self.now,
            'Host': "my_region/my_service/outscale.com",
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'content-type:application/json; charset=utf-8\n'
                         'host:my_region/my_service/outscale.com\n'
                         'x-osc-date:2015-03-04 17:34:52\n')

    def test_get_canonical_headers_sorts_headers_lexically(self):
        headers = {
            'accept-encoding': 'gzip,deflate',
            'host': 'my_host',
            '1st-header': '2',
            'x-osc-date': '20150304T173452Z',
            'user-agent': 'my-ua'
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         '1st-header:2\n'
                         'accept-encoding:gzip,deflate\n'
                         'host:my_host\n'
                         'user-agent:my-ua\n'
                         'x-osc-date:20150304T173452Z\n')

    def test_get_canonical_headers_lowercases_headers_names(self):
        headers = {
            'Accept-Encoding': 'GZIP,DEFLATE',
            'User-Agent': 'My-UA'
        }
        self.assertEqual(self.signer._get_canonical_headers(headers),
                         'accept-encoding:GZIP,DEFLATE\n'
                         'user-agent:My-UA\n')


if __name__ == '__main__':
    unittest.main()
