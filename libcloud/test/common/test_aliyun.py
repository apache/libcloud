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

from libcloud.common import aliyun
from libcloud.common.aliyun import AliyunRequestSignerAlgorithmV1_0
from libcloud.test import LibcloudTestCase


class AliyunRequestSignerAlgorithmV1_0TestCase(LibcloudTestCase):

    def setUp(self):
        self.signer = AliyunRequestSignerAlgorithmV1_0('testid', 'testsecret',
                                                       '1.0')

    def test_sign_request(self):
        params = {'TimeStamp': '2012-12-26T10:33:56Z',
                  'Format': 'XML',
                  'AccessKeyId': 'testid',
                  'Action': 'DescribeRegions',
                  'SignatureMethod': 'HMAC-SHA1',
                  'RegionId': 'region1',
                  'SignatureNonce': 'NwDAxvLU6tFE0DVb',
                  'Version': '2014-05-26',
                  'SignatureVersion': '1.0'}
        method = 'GET'
        path = '/'

        expected = 'K9fCVP6Jrklpd3rLYKh1pfrrFNo='
        self.assertEqual(expected,
                         self.signer._sign_request(params, method, path))


class AliyunCommonTestCase(LibcloudTestCase):

    def test_percent_encode(self):
        data = {
            'abc': 'abc',
            ' *~': '%20%2A~'
        }
        for key in data:
            self.assertEqual(data[key], aliyun._percent_encode(key))


if __name__ == '__main__':
    sys.exit(unittest.main())
