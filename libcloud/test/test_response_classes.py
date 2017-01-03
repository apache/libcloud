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

import requests
import requests_mock

from libcloud.common.base import XmlResponse, JsonResponse
from libcloud.common.types import MalformedResponseError
from libcloud.httplib_ssl import LibcloudConnection


class ResponseClassesTests(unittest.TestCase):
    def setUp(self):
        self.mock_connection = LibcloudConnection(host='mock.com', port=80)
        self.mock_connection.driver = None

    def test_XmlResponse_class(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/2', text='<foo>bar</foo>')
            response_obj = requests.get('mock://test.com/2')
            response = XmlResponse(response=response_obj,
                                   connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed.tag, 'foo')
        self.assertEqual(parsed.text, 'bar')

    def test_XmlResponse_class_malformed_response(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text='<foo>')
            response_obj = requests.get('mock://test.com/')
            try:
                XmlResponse(response=response_obj,
                            connection=self.mock_connection)
            except MalformedResponseError:
                pass
            else:
                self.fail('Exception was not thrown')

    def test_XmlResponse_class_zero_length_body_strip(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text=' ')
            response_obj = requests.get('mock://test.com/')
            response = XmlResponse(response=response_obj,
                                   connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, '')

    def test_JsonResponse_class_success(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text='{"foo": "bar"}')
            response_obj = requests.get('mock://test.com/')
            response = JsonResponse(response=response_obj,
                                    connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, {'foo': 'bar'})

    def test_JsonResponse_class_malformed_response(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text='{"foo": "bar"')
            response_obj = requests.get('mock://test.com/')
            try:
                JsonResponse(response=response_obj,
                             connection=self.mock_connection)
            except MalformedResponseError:
                pass
            else:
                self.fail('Exception was not thrown')

    def test_JsonResponse_class_zero_length_body_strip(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text=' ')
            response_obj = requests.get('mock://test.com/')
            response = JsonResponse(response=response_obj,
                                    connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, '')


if __name__ == '__main__':
    sys.exit(unittest.main())
