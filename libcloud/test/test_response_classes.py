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

from libcloud.common.base import XmlResponse, JsonResponse, Connection
from libcloud.common.types import MalformedResponseError
from libcloud.http import LibcloudConnection


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

    def test_RawResponse_class_read_method(self):
        """
        Test that the RawResponse class includes a response
        property which exhibits the same properties and methods
        as httplib.HTTPResponse for backward compat <1.5.0
        """
        TEST_DATA = '1234abcd'

        conn = Connection(host='mock.com', port=80, secure=False)
        conn.connect()

        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'http://mock.com/raw_data', text=TEST_DATA,
                           headers={'test': 'value'})
            response = conn.request('/raw_data', raw=True)
        data = response.response.read()
        self.assertEqual(data, TEST_DATA)

        header_value = response.response.getheader('test')
        self.assertEqual(header_value, 'value')

        headers = response.response.getheaders()
        self.assertEqual(headers, [('test', 'value')])

        self.assertEqual(response.response.status, 200)

if __name__ == '__main__':
    sys.exit(unittest.main())
