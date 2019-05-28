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

from mock import Mock, patch, MagicMock

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
        con = Connection(timeout=0.2, retry_delay=0.1)
        con.connection = Mock()
        connect_method = 'libcloud.common.base.Connection.request'

        with patch(connect_method) as mock_connect:
            try:
                mock_connect.side_effect = socket.gaierror('')
                con.request('/')
            except socket.gaierror:
                pass

    def test_retry_connection_ssl_error(self):
        conn = Connection(timeout=0.2, retry_delay=0.1)

        with patch.object(conn, 'connect', Mock()):
            with patch.object(conn, 'connection') as connection:
                connection.request = MagicMock(
                    __name__='request',
                    side_effect=ssl.SSLError(TRANSIENT_SSL_ERROR))

                self.assertRaises(ssl.SSLError, conn.request, '/')
                self.assertGreater(connection.request.call_count, 1)

if __name__ == '__main__':
    unittest.main()
