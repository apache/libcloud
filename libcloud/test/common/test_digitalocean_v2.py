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
from libcloud.test.secrets import DIGITALOCEAN_v2_PARAMS
from libcloud.utils.py3 import httplib


class DigitalOceanTests(LibcloudTestCase):

    def setUp(self):
        DigitalOceanBaseDriver.connectionCls.conn_classes = \
            (None, DigitalOceanMockHttp)
        DigitalOceanMockHttp.type = None
        self.driver = DigitalOceanBaseDriver(*DIGITALOCEAN_v2_PARAMS)

    def test_authentication(self):
        DigitalOceanMockHttp.type = 'UNAUTHORIZED'
        self.assertRaises(InvalidCredsError, self.driver.ex_account_info)

    def test_ex_account_info(self):
        account_info = self.driver.ex_account_info()
        self.assertEqual(account_info['uuid'],
                         'a1234567890b1234567890c1234567890d12345')
        self.assertTrue(account_info['email_verified'])
        self.assertEqual(account_info['email'], 'user@domain.tld')
        self.assertEqual(account_info['droplet_limit'], 10)

    def test_ex_list_events(self):
        events = self.driver.ex_list_events()
        self.assertEqual(events, [])

    def test_ex_get_event(self):
        action = self.driver.ex_get_event('12345670')
        self.assertEqual(action["id"], 12345670)
        self.assertEqual(action["status"], "completed")
        self.assertEqual(action["type"], "power_on")

    def test__paginated_request(self):
        DigitalOceanMockHttp.type = 'page_1'
        actions = self.driver._paginated_request('/v2/actions', 'actions')
        self.assertEqual(actions[0]['id'], 12345671)
        self.assertEqual(actions[0]['status'], 'completed')


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

    def _v2_account(self, method, url, body, headers):
        body = self.fixtures.load('_v2_account.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_account_UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_account_UNAUTHORIZED.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_actions(self, method, url, body, headers):
        body = self.fixtures.load('_v2_actions.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_actions_12345670(self, method, url, body, headers):
        body = self.fixtures.load('_v2_actions_12345670.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_actions_page_1(self, method, url, body, headers):
        body = self.fixtures.load('_v2_actions_page_1.json')
        return (self.response[None], body, {},
                httplib.responses[self.response[None]])


if __name__ == '__main__':
    sys.exit(unittest.main())
