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

from libcloud.common.azure import AzureConnection
from libcloud.test import LibcloudTestCase


class AzureConnectionTestCase(LibcloudTestCase):
    def setUp(self):
        self.conn = AzureConnection('user', 'key')

    def test_content_length_is_used_if_set(self):
        headers = {'content-length': '123'}
        method = 'PUT'

        values = self.conn._format_special_header_values(headers, method)

        self.assertEqual(values[2], '123')

    def test_content_length_is_blank_if_new_api_version(self):
        headers = {}
        method = 'PUT'
        self.conn.API_VERSION = '2018-11-09'

        values = self.conn._format_special_header_values(headers, method)

        self.assertEqual(values[2], '')

    def test_content_length_is_zero_if_write_and_old_api_version(self):
        headers = {}
        method = 'PUT'
        self.conn.API_VERSION = '2011-08-18'

        values = self.conn._format_special_header_values(headers, method)

        self.assertEqual(values[2], '0')

    def test_content_length_is_blank_if_read_and_old_api_version(self):
        headers = {}
        method = 'GET'
        self.conn.API_VERSION = '2011-08-18'

        values = self.conn._format_special_header_values(headers, method)

        self.assertEqual(values[2], '')


if __name__ == '__main__':
    sys.exit(unittest.main())
