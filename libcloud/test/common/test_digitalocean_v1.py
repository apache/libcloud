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

import sys
import unittest

from libcloud.common.types import InvalidCredsError
from libcloud.common.digitalocean import DigitalOceanBaseDriver
from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.file_fixtures import FileFixtures
from libcloud.test.secrets import DIGITALOCEAN_v1_PARAMS
from libcloud.utils.py3 import httplib


class DigitalOceanTests(LibcloudTestCase):

    def setUp(self):
        DigitalOceanBaseDriver.connectionCls.conn_classes = \
            (None, DigitalOceanMockHttp)
        DigitalOceanMockHttp.type = None
        self.driver = DigitalOceanBaseDriver(*DIGITALOCEAN_v1_PARAMS)

    def test_authentication(self):
        DigitalOceanMockHttp.type = 'UNAUTHORIZED'
        self.assertRaises(InvalidCredsError, self.driver.ex_get_event,
                          '12345670')

    def test_ex_account_info(self):
        self.assertRaises(NotImplementedError, self.driver.ex_account_info)

    def test_ex_list_events(self):
        self.assertRaises(NotImplementedError, self.driver.ex_list_events)

    def test_ex_get_event(self):
        action = self.driver.ex_get_event('12345670')
        self.assertEqual(action["status"], "OK")
        self.assertEqual(action["event"]["id"], 12345670)
        self.assertEqual(action["event"]["event_type_id"], 1)

    def test__paginated_request(self):
        self.assertRaises(NotImplementedError, self.driver._paginated_request,
                          '/v1/anything', 'anything')


class DigitalOceanMockHttp(MockHttpTestCase):
    fixtures = FileFixtures('common', 'digitalocean')

    response = {
        None: httplib.OK,
        'CREATE': httplib.CREATED,
        'DELETE': httplib.NO_CONTENT,
        'EMPTY': httplib.OK,
        'NOT_FOUND': httplib.NOT_FOUND,
        'UNAUTHORIZED': httplib.UNAUTHORIZED,
        'UPDATE': httplib.OK
    }

    def _v1_events_12345670_UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load(
            '_v1_events_12345670_UNAUTHORIZED.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v1_events_12345670(self, method, url, body, headers):
        body = self.fixtures.load('_v1_events_12345670.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])


if __name__ == '__main__':
    sys.exit(unittest.main())
