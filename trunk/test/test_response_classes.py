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
import httplib

from mock import Mock

from libcloud.common.base import XmlResponse, JsonResponse
from libcloud.common.types import MalformedResponseError


class ResponseClassesTests(unittest.TestCase):
    def setUp(self):
        self._mock_response = Mock()
        self._mock_response.getheaders.return_value = []
        self._mock_response.status = httplib.OK
        self._mock_connection = Mock()

    def test_XmlResponse_class(self):
        self._mock_response.read.return_value = '<foo>bar</foo>'
        response = XmlResponse(response=self._mock_response,
                               connection=self._mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed.tag, 'foo')
        self.assertEqual(parsed.text, 'bar')

    def test_XmlResponse_class_malformed_response(self):
        self._mock_response.read.return_value = '<foo>'

        try:
            XmlResponse(response=self._mock_response,
                         connection=self._mock_connection)
        except MalformedResponseError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_XmlResponse_class_zero_length_body_strip(self):
        self._mock_response.read.return_value = ' '

        response = XmlResponse(response=self._mock_response,
                               connection=self._mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, '')

    def test_JsonResponse_class_success(self):
        self._mock_response.read.return_value = '{"foo": "bar"}'
        response = JsonResponse(response=self._mock_response,
                                connection=self._mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, {'foo': 'bar'})

    def test_JsonResponse_class_malformed_response(self):
        self._mock_response.read.return_value = '{"foo": "bar'

        try:
            JsonResponse(response=self._mock_response,
                         connection=self._mock_connection)
        except MalformedResponseError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_JsonResponse_class_zero_length_body_strip(self):
        self._mock_response.read.return_value = ' '

        response = JsonResponse(response=self._mock_response,
                                connection=self._mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, '')


if __name__ == '__main__':
    sys.exit(unittest.main())
