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

import requests
import unittest
import sys

try:
    from lxml import etree
except ImportError:
    etree = None

import mock
import requests_mock

from libcloud.common.base import LazyObject
from libcloud.common.base import XmlResponse
from libcloud.common.types import MalformedResponseError
from libcloud.test import LibcloudTestCase


class LazyObjectTest(LibcloudTestCase):
    class A(LazyObject):
        def __init__(self, x, y=None):
            self.x = x
            self.y = y

    def test_lazy_init(self):
        # Test normal init
        a = self.A(1, y=2)
        self.assertTrue(isinstance(a, self.A))

        # Test lazy init
        with mock.patch.object(self.A,
                               '__init__', return_value=None) as mock_init:
            a = self.A.lazy(3, y=4)
            self.assertTrue(isinstance(a, self.A))  # Proxy is a subclass of A
            mock_init.assert_not_called()

            # Since we have a mock init, an A object doesn't actually get
            # created. But, we can still call __dict__ on the proxy, which will
            # init the lazy object.
            self.assertEqual(a.__dict__, {})
            mock_init.assert_called_once_with(3, y=4)

    def test_setattr(self):
        a = self.A.lazy('foo', y='bar')
        a.z = 'baz'
        wrapped_lazy_obj = object.__getattribute__(a, '_lazy_obj')
        self.assertEqual(a.z, 'baz')
        self.assertEqual(wrapped_lazy_obj.z, 'baz')


class XmlResponseTest(unittest.TestCase):
    def test_lxml_from_unicode_with_encoding_declaration(self):
        if etree is None:
            return
        connection = mock.Mock()
        response_text = u'<?xml version="1.0" encoding="UTF-8"?>\n<Response>' \
                        '<Errors><Error><Code>InvalidSnapshot.NotFound</Code><Message>' \
                        'Snapshot does not exist</Message></Error></Errors><RequestID>' \
                        'd65ede94-44d9-40c4-992b-23aafd611797</RequestID></Response>'
        with requests_mock.Mocker() as m:
            m.get('https://127.0.0.1',
                  text=response_text,
                  headers={'content-type': 'application/xml'})
            response = XmlResponse(requests.get('https://127.0.0.1'),
                                   connection)
            body = response.parse_body()
            self.assertIsNotNone(body)
            self.assertIsInstance(body, etree._Element)

    def test_parse_error_raises_exception_on_empty_body(self):
        if etree is None:
            return
        connection = mock.Mock()
        response_text = ''
        with requests_mock.Mocker() as m:
            m.get('https://127.0.0.1',
                  text=response_text,
                  headers={'content-type': 'application/xml'})
            response = XmlResponse(requests.get('https://127.0.0.1'),
                                   connection)
            response.parse_zero_length_body = True

            with self.assertRaises(MalformedResponseError):
                response.parse_error()


if __name__ == '__main__':
    sys.exit(unittest.main())
