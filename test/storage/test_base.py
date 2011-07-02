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
import hashlib

from StringIO import StringIO
from mock import Mock

from libcloud.storage.base import StorageDriver

from test import StorageMockHttp # pylint: disable-msg=E0611

class BaseStorageTests(unittest.TestCase):
    def setUp(self):
        self.send_called = 0
        StorageDriver.connectionCls.conn_classes = (None, StorageMockHttp)
        self.driver = StorageDriver('username', 'key', host='localhost')

    def test__upload_object_iterator_must_have_next_method(self):
        class Iterator(object):
            def next(self):
                pass

        class Iterator2(file):
            def __init__(self):
                pass

        class SomeClass(object):
            pass

        valid_iterators = [ Iterator(), Iterator2(), StringIO('bar') ]
        invalid_iterators = [ 'foobar', '', False, True, 1, object() ]

        def upload_func(*args, **kwargs):
            return True, 'barfoo', 100

        kwargs = {'object_name': 'foo', 'content_type': 'foo/bar',
                   'upload_func': upload_func, 'upload_func_kwargs': {},
                   'request_path': '/', 'headers': {}}

        for value in valid_iterators:
            kwargs['iterator'] = value
            self.driver._upload_object(**kwargs)

        for value in invalid_iterators:
            kwargs['iterator'] = value

            try:
                self.driver._upload_object(**kwargs)
            except AttributeError:
                pass
            else:
                self.fail('Exception was not thrown')

    def test_upload_zero_bytes_long_object_via_stream(self):
        iterator = Mock()
        iterator.next.side_effect = StopIteration()

        def mock_send(data):
            self.send_called += 1

        response = Mock()
        response.connection.connection.send = mock_send

        # Normal
        success, data_hash, bytes_transferred = \
                 self.driver._stream_data(response=response, iterator=iterator,
                                          chunked=False, calculate_hash=True)

        self.assertTrue(success)
        self.assertEqual(data_hash, hashlib.md5('').hexdigest())
        self.assertEqual(bytes_transferred, 0)
        self.assertEqual(self.send_called, 1)

        # Chunked
        success, data_hash, bytes_transferred = \
                 self.driver._stream_data(response=response, iterator=iterator,
                                          chunked=True, calculate_hash=True)

        self.assertTrue(success)
        self.assertEqual(data_hash, hashlib.md5('').hexdigest())
        self.assertEqual(bytes_transferred, 0)
        self.assertEqual(self.send_called, 5)


if __name__ == '__main__':
    sys.exit(unittest.main())
