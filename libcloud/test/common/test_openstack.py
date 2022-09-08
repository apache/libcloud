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
from unittest.mock import Mock, patch

from libcloud.common.base import LibcloudConnection
from libcloud.common.openstack import OpenStackBaseConnection


class OpenStackBaseConnectionTest(unittest.TestCase):
    def setUp(self):
        self.timeout = 10
        OpenStackBaseConnection.conn_class = Mock()
        self.connection = OpenStackBaseConnection(
            "foo", "bar", timeout=self.timeout, ex_force_auth_url="https://127.0.0.1"
        )
        self.connection.driver = Mock()
        self.connection.driver.name = "OpenStackDriver"

    def tearDown(self):
        OpenStackBaseConnection.conn_class = LibcloudConnection

    def test_base_connection_timeout(self):
        self.connection.connect()
        self.assertEqual(self.connection.timeout, self.timeout)
        self.connection.conn_class.assert_called_with(
            host="127.0.0.1", secure=1, port=443, timeout=10
        )

    def test_set_microversion(self):
        self.connection.service_type = "compute"
        self.connection._ex_force_microversion = "2.67"
        headers = self.connection.add_default_headers({})
        self.assertEqual(headers["OpenStack-API-Version"], "compute 2.67")

        self.connection.service_type = "compute"
        self.connection._ex_force_microversion = "volume 2.67"
        headers = self.connection.add_default_headers({})
        self.assertNotIn("OpenStack-API-Version", headers)

        self.connection.service_type = "volume"
        self.connection._ex_force_microversion = "volume 2.67"
        headers = self.connection.add_default_headers({})
        self.assertEqual(headers["OpenStack-API-Version"], "volume 2.67")

    @patch("libcloud.common.base.ConnectionUserAndKey.request")
    def test_request(self, mock_request):
        OpenStackBaseConnection.conn_class._raw_data = ""
        OpenStackBaseConnection.default_content_type = "application/json"
        expected_response = Mock()
        mock_request.return_value = expected_response
        response = self.connection.request(
            "/path", data="somedata", headers={"h1": "v1"}, method="POST"
        )
        self.assertEqual(response, expected_response)
        mock_request.assert_called_with(
            action="/path",
            params={},
            data="somedata",
            method="POST",
            headers={"h1": "v1", "Content-Type": "application/json"},
            raw=False,
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
