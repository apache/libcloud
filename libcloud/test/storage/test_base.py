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
import errno
import hashlib

from libcloud.utils.py3 import httplib
from io import BytesIO

import mock
from mock import Mock

from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import b
from libcloud.utils.py3 import PY2
from libcloud.utils.py3 import assertRaisesRegex

from libcloud.storage.base import StorageDriver
from libcloud.storage.base import DEFAULT_CONTENT_TYPE

from libcloud.test import unittest
from libcloud.test import MockHttp
from libcloud.test import BodyStream
from libcloud.test.storage.base import BaseRangeDownloadMockHttp


class BaseMockRawResponse(MockHttp):
    def _(self, method, url, body, headers):
        body = 'ab'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def root(self, method, url, body, headers):
        body = 'ab'
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class BaseStorageTests(unittest.TestCase):
    def setUp(self):
        self.send_called = 0
        StorageDriver.connectionCls.conn_class = BaseMockRawResponse

        self.driver1 = StorageDriver('username', 'key', host='localhost')
        self.driver1.supports_chunked_encoding = True

        self.driver2 = StorageDriver('username', 'key', host='localhost')
        self.driver2.supports_chunked_encoding = False

        self.driver1.strict_mode = False
        self.driver1.strict_mode = False

    def test__upload_object_iterator_must_have_next_method(self):

        valid_iterators = [BytesIO(b('134')), StringIO('bar')]
        invalid_iterators = ['foobar', '', False, True, 1, object()]

        kwargs = {'object_name': 'foo', 'content_type': 'foo/bar',
                  'request_path': '/', 'headers': {}}

        for value in valid_iterators:
            kwargs['stream'] = value
            self.driver1._upload_object(**kwargs)

        for value in invalid_iterators:
            kwargs['stream'] = value

            try:
                self.driver1._upload_object(**kwargs)
            except AttributeError:
                pass
            else:
                self.fail('Exception was not thrown')

    def test__upload_object_does_not_stream_response(self):
        resp = self.driver1._upload_object(
            object_name='foo',
            content_type='foo/bar',
            request_path='/',
            stream=iter(b'foo'))
        mock_response = resp["response"].response._response
        response_streamed = mock_response.request.stream
        assert response_streamed is False

    def test__get_hash_function(self):
        self.driver1.hash_type = 'md5'
        func = self.driver1._get_hash_function()
        self.assertTrue(func)

        self.driver1.hash_type = 'sha1'
        func = self.driver1._get_hash_function()
        self.assertTrue(func)

        try:
            self.driver1.hash_type = 'invalid-hash-function'
            func = self.driver1._get_hash_function()
        except RuntimeError:
            pass
        else:
            self.fail('Invalid hash type but exception was not thrown')

    def test_upload_no_content_type_supplied_or_detected(self):
        iterator = StringIO()

        # strict_mode is disabled, default content type should be used
        self.driver1.connection = Mock()

        self.driver1._upload_object(object_name='test',
                                    content_type=None,
                                    request_path='/',
                                    stream=iterator)

        headers = self.driver1.connection.request.call_args[-1]['headers']
        self.assertEqual(headers['Content-Type'], DEFAULT_CONTENT_TYPE)

        # strict_mode is enabled, exception should be thrown

        self.driver1.strict_mode = True
        expected_msg = ('File content-type could not be guessed for "test" '
                        'and no content_type value is provided')
        assertRaisesRegex(self, AttributeError, expected_msg,
                          self.driver1._upload_object,
                          object_name='test',
                          content_type=None,
                          request_path='/',
                          stream=iterator)

    @mock.patch('libcloud.utils.files.exhaust_iterator')
    @mock.patch('libcloud.utils.files.read_in_chunks')
    def test_upload_object_hash_calculation_is_efficient(self, mock_read_in_chunks,
                                                         mock_exhaust_iterator):
        # Verify that we don't buffer whole file in memory when calculating
        # object has when iterator has __next__ method, but instead read and
        # calculate hash in chunks
        size = 100

        self.driver1.connection = Mock()

        # stream has __next__ method and next() method
        mock_read_in_chunks.return_value = 'a' * size

        iterator = BodyStream('a' * size)
        self.assertTrue(hasattr(iterator, '__next__'))
        self.assertTrue(hasattr(iterator, 'next'))

        self.assertEqual(mock_read_in_chunks.call_count, 0)
        self.assertEqual(mock_exhaust_iterator.call_count, 0)

        result = self.driver1._upload_object(object_name='test1',
                                             content_type=None,
                                             request_path='/',
                                             stream=iterator)

        hasher = hashlib.md5()
        hasher.update(b('a') * size)
        expected_hash = hasher.hexdigest()

        self.assertEqual(result['data_hash'], expected_hash)
        self.assertEqual(result['bytes_transferred'], size)

        headers = self.driver1.connection.request.call_args[-1]['headers']
        self.assertEqual(headers['Content-Type'], DEFAULT_CONTENT_TYPE)

        self.assertEqual(mock_read_in_chunks.call_count, 1)
        self.assertEqual(mock_exhaust_iterator.call_count, 0)

        # stream has only has next() method
        mock_read_in_chunks.return_value = 'b' * size

        iterator = iter([str(v) for v in ['b' * size]])

        if PY2:
            self.assertFalse(hasattr(iterator, '__next__'))
            self.assertTrue(hasattr(iterator, 'next'))
        else:
            self.assertTrue(hasattr(iterator, '__next__'))
            self.assertFalse(hasattr(iterator, 'next'))

        self.assertEqual(mock_read_in_chunks.call_count, 1)
        self.assertEqual(mock_exhaust_iterator.call_count, 0)

        self.assertEqual(mock_read_in_chunks.call_count, 1)
        self.assertEqual(mock_exhaust_iterator.call_count, 0)

        result = self.driver1._upload_object(object_name='test2',
                                             content_type=None,
                                             request_path='/',
                                             stream=iterator)

        hasher = hashlib.md5()
        hasher.update(b('b') * size)
        expected_hash = hasher.hexdigest()

        self.assertEqual(result['data_hash'], expected_hash)
        self.assertEqual(result['bytes_transferred'], size)

        headers = self.driver1.connection.request.call_args[-1]['headers']
        self.assertEqual(headers['Content-Type'], DEFAULT_CONTENT_TYPE)

        self.assertEqual(mock_read_in_chunks.call_count, 2)
        self.assertEqual(mock_exhaust_iterator.call_count, 0)

    def test_upload_object_via_stream_illegal_seek_errors_are_ignored(self):
        # Illegal seek errors should be ignored
        size = 100

        self.driver1.connection = Mock()

        seek_error = OSError('Illegal seek')
        seek_error.errno = 29
        assert errno.ESPIPE == 29

        iterator = BodyStream('a' * size)
        iterator.seek = mock.Mock(side_effect=seek_error)

        result = self.driver1._upload_object(object_name='test1',
                                             content_type=None,
                                             request_path='/',
                                             stream=iterator)

        hasher = hashlib.md5()
        hasher.update(b('a') * size)
        expected_hash = hasher.hexdigest()

        self.assertEqual(result['data_hash'], expected_hash)
        self.assertEqual(result['bytes_transferred'], size)

        # But others shouldn't
        self.driver1.connection = Mock()

        seek_error = OSError('Other error')
        seek_error.errno = 21

        iterator = BodyStream('b' * size)
        iterator.seek = mock.Mock(side_effect=seek_error)

        self.assertRaisesRegex(OSError, 'Other error',
                               self.driver1._upload_object,
                               object_name='test1',
                               content_type=None,
                               request_path='/',
                               stream=iterator)

    def test_get_standard_range_str(self):
        result = self.driver1._get_standard_range_str(0, 5)
        self.assertEqual(result, 'bytes=0-4')

        result = self.driver1._get_standard_range_str(0)
        self.assertEqual(result, 'bytes=0-')
        result = self.driver1._get_standard_range_str(0, 1)

        self.assertEqual(result, 'bytes=0-0')

        result = self.driver1._get_standard_range_str(200)
        self.assertEqual(result, 'bytes=200-')

        result = self.driver1._get_standard_range_str(10, 200)
        self.assertEqual(result, 'bytes=10-199')

        result = self.driver1._get_standard_range_str(10, 11)
        self.assertEqual(result, 'bytes=10-10')

        result = self.driver1._get_standard_range_str(10, 11, True)
        self.assertEqual(result, 'bytes=10-11')


class BaseRangeDownloadMockHttpTestCase(unittest.TestCase):
    def test_get_start_and_end_bytes_from_range_str(self):
        mock_http = BaseRangeDownloadMockHttp(None, None)
        body = '0123456789'

        range_str = 'bytes=1-'
        result = mock_http._get_start_and_end_bytes_from_range_str(range_str, body)
        self.assertEqual(result, (1, len(body)))
        range_str = 'bytes=1-5'

        result = mock_http._get_start_and_end_bytes_from_range_str(range_str, body)
        self.assertEqual(result, (1, 5))

        range_str = 'bytes=3-5'
        result = mock_http._get_start_and_end_bytes_from_range_str(range_str, body)
        self.assertEqual(result, (3, 5))


if __name__ == '__main__':
    sys.exit(unittest.main())
