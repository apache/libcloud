# -*- coding: utf-8 -*-
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

from libcloud.utils.py3 import httplib
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.common.base import Connection, Response, JsonResponse, XmlResponse
from libcloud.test import MockHttp


class FileFixturesTests(unittest.TestCase):

    def test_success(self):
        f = ComputeFileFixtures('meta')
        self.assertEqual("Hello, World!", f.load('helloworld.txt'))

    def test_failure(self):
        f = ComputeFileFixtures('meta')
        self.assertRaises(IOError, f.load, 'nil')

    def test_unicode(self):
        f = ComputeFileFixtures('meta')
        self.assertEqual(u"Ś", f.load('unicode.txt'))


class MockHttpFileFixturesTests(unittest.TestCase):
    """
    Test the behaviour of MockHttp
    """
    def setUp(self):
        Connection.conn_class = TestMockHttp
        Connection.responseCls = Response
        self.connection = Connection()

    def test_unicode_response(self):
        r = self.connection.request("/unicode")
        self.assertEqual(r.parse_body(), u"Ś")

    def test_json_unicode_response(self):
        self.connection.responseCls = JsonResponse
        r = self.connection.request("/unicode/json")
        self.assertEqual(r.object, {'test': u"Ś"})

    def test_xml_unicode_response(self):
        self.connection.responseCls = XmlResponse
        response = self.connection.request("/unicode/xml")
        self.assertEqual(response.object.text, u"Ś")


class TestMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('meta')

    def _unicode(self, method, url, body, headers):
        body = self.fixtures.load('unicode.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _unicode_json(self, method, url, body, headers):
        body = self.fixtures.load('unicode.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _unicode_xml(self, method, url, body, headers):
        body = self.fixtures.load('unicode.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ascii(self, method, url, body, headers):
        body = self.fixtures.load('helloworld.txt')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
