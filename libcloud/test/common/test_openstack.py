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
import sys
import unittest
try:
    from lxml import etree
except ImportError:
    etree = None

from mock import Mock
import requests_mock

from libcloud.common.base import LibcloudConnection
from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.openstack import OpenStackResponse
from libcloud.utils.py3 import PY25


class OpenStackBaseConnectionTest(unittest.TestCase):
    def setUp(self):
        self.timeout = 10
        OpenStackBaseConnection.conn_class = Mock()
        self.connection = OpenStackBaseConnection('foo', 'bar',
                                                  timeout=self.timeout,
                                                  ex_force_auth_url='https://127.0.0.1')
        self.connection.driver = Mock()
        self.connection.driver.name = 'OpenStackDriver'

    def tearDown(self):
        OpenStackBaseConnection.conn_class = LibcloudConnection

    def test_base_connection_timeout(self):
        self.connection.connect()
        self.assertEqual(self.connection.timeout, self.timeout)
        if PY25:
            self.connection.conn_class.assert_called_with(host='127.0.0.1',
                                                          port=443)
        else:
            self.connection.conn_class.assert_called_with(host='127.0.0.1',
                                                          secure=1,
                                                          port=443,
                                                          timeout=10)


class OpenStackResponseTest(unittest.TestCase):
    def test_lxml_from_unicode_with_encoding_declaration(self):
        if etree is None:
            return
        connection = Mock()
        response_text = u'''<?xml version="1.0" encoding="UTF-8"?>
<account name="AUTH_73f0aa26640f4971864919d0eb0f0880">
    <container>
        <name>janeausten</name>
        <count>2</count>
        <bytes>33</bytes>
    </container>
    <container>
        <name>marktwain</name>
        <count>1</count>
        <bytes>14</bytes>
    </container>
</account>'''
        with requests_mock.Mocker() as m:
            m.get('https://127.0.0.1',
                  text=response_text,
                  headers={'content-type': 'application/xml'})
            response = OpenStackResponse(requests.get('https://127.0.0.1'),
                                         connection)
            body = response.parse_body()
            self.assertIsNotNone(body)
            self.assertIsInstance(body, etree._Element)


if __name__ == '__main__':
    sys.exit(unittest.main())
