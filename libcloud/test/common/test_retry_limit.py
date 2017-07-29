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

import socket
import ssl

import mock
from mock import Mock, patch, MagicMock
from datetime import datetime

from libcloud.utils.misc import TRANSIENT_SSL_ERROR
from libcloud.common.base import Connection
from libcloud.test import unittest

CONFLICT_RESPONSE_STATUS = [
    ('status', '429'), ('reason', 'CONFLICT'),
    ('retry_after', '3'),
    ('content-type', 'application/json')]
SIMPLE_RESPONSE_STATUS = ('HTTP/1.1', 429, 'CONFLICT')


@patch('os.environ', {'LIBCLOUD_RETRY_FAILED_HTTP_REQUESTS': True})
class FailedRequestRetryTestCase(unittest.TestCase):

    def test_retry_connection(self):
        connection = Connection(
            timeout=1,
            retry_delay=0.2)
        connection.connection = Mock(request=Mock(
            side_effect=socket.gaierror('')))

        self.assertRaises(socket.gaierror, connection.request, '/')
        self.assertEqual(connection.connection.request.call_count, 6)

    def test_retry_connection_backoff(self):
        connection = Connection(
            timeout=10,
            retry_delay=0.1,
            backoff=2)
        connection.connection = Mock(request=Mock(
            side_effect=socket.gaierror('')))

        with patch('time.sleep') as sleep_fn:
            sleep_fn.side_effect = [None, None, None, None, None, StopIteration]

            self.assertRaises(StopIteration, connection.request, '/')
            self.assertEqual(connection.connection.request.call_count, 6)
            self.assertEqual(sleep_fn.call_count, 6)
            self.assertEqual(sleep_fn.call_args_list, [
                mock.call(i) for i in (0.1, 0.2, 0.4, 0.8, 1.6, 3.2)
            ])

    @patch('libcloud.utils.misc.datetime')
    def test_retry_connection_timeout(self, datetime_obj):
        connection = Connection(
            timeout=65,
            retry_delay=20)
        connection.connection = Mock(request=Mock(
            side_effect=socket.gaierror('')))
        datetime_obj.now.side_effect = [
            datetime(2017, 7, 28, 0, 26, 10, 0),
            datetime(2017, 7, 28, 0, 26, 10, 0),
            datetime(2017, 7, 28, 0, 26, 30, 0),
            datetime(2017, 7, 28, 0, 26, 50, 0),
            datetime(2017, 7, 28, 0, 27, 10, 0),
            datetime(2017, 7, 28, 0, 27, 30, 0),
        ]

        with patch('time.sleep') as sleep_fn:
            self.assertRaises(socket.gaierror, connection.request, '/')
            self.assertEqual(sleep_fn.call_args_list, [
                mock.call(i) for i in (20, 20, 20, 5)
            ])

    def test_retry_connection_with_iterable_retry_delay(self):
        connection = Connection(
            timeout=20,
            retry_delay=(1, 1, 3, 5),
            backoff=1)
        connection.connection = Mock(request=Mock(
            side_effect=socket.gaierror('')))

        with patch('time.sleep') as sleep_fn:
            sleep_fn.side_effect = [None, None, None, None, None, StopIteration]

            self.assertRaises(StopIteration, connection.request, '/')
            self.assertEqual(connection.connection.request.call_count, 6)
            self.assertEqual(sleep_fn.call_count, 6)
            self.assertEqual(sleep_fn.call_args_list, [
                mock.call(i) for i in (1, 1, 3, 5, 5, 5)
            ])

    def test_retry_connection_ssl_error(self):
        conn = Connection(timeout=1, retry_delay=0.1)

        with patch.object(conn, 'connect', Mock()):
            with patch.object(conn, 'connection') as connection:
                connection.request = MagicMock(
                    __name__='request',
                    side_effect=ssl.SSLError(TRANSIENT_SSL_ERROR))

                self.assertRaises(ssl.SSLError, conn.request, '/')
                self.assertGreater(connection.request.call_count, 1)

if __name__ == '__main__':
    unittest.main()
