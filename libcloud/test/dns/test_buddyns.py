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

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_BUDDYNS
from libcloud.dns.drivers.buddyns import BuddyNSDNSDriver
from libcloud.utils.py3 import httplib
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.base import Zone


class BuddyNSDNSTests(unittest.TestCase):
    def setUp(self):
        BuddyNSMockHttp.type = None
        BuddyNSDNSDriver.connectionCls.conn_class = BuddyNSMockHttp
        self.driver = BuddyNSDNSDriver(*DNS_PARAMS_BUDDYNS)
        self.test_zone = Zone(id='test.com', type='master', ttl=None,
                              domain='test.com', extra={}, driver=self)

    def test_list_zones_empty(self):
        BuddyNSMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        BuddyNSMockHttp.type = 'LIST_ZONES'
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 2)

        zone = zones[0]
        self.assertEqual(zone.id, 'microsoft.com')
        self.assertIsNone(zone.type)
        self.assertEqual(zone.domain, 'microsoft.com')
        self.assertIsNone(zone.ttl)

        zone = zones[1]
        self.assertEqual(zone.id, 'google.de')
        self.assertIsNone(zone.type)
        self.assertEqual(zone.domain, 'google.de')
        self.assertIsNone(zone.ttl)

    def test_delete_zone_zone_does_not_exist(self):
        BuddyNSMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'

        try:
            self.driver.delete_zone(zone=self.test_zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_delete_zone_success(self):
        BuddyNSMockHttp.type = 'DELETE_ZONE_SUCCESS'
        status = self.driver.delete_zone(zone=self.test_zone)

        self.assertTrue(status)

    def test_get_zone_zone_does_not_exist(self):
        BuddyNSMockHttp.type = 'GET_ZONE_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='zonedoesnotexist.com')
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'zonedoesnotexist.com')
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        BuddyNSMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='myexample.com')

        self.assertEqual(zone.id, 'myexample.com')
        self.assertEqual(zone.domain, 'myexample.com')
        self.assertIsNone(zone.type)
        self.assertIsNone(zone.ttl)
        self.assertEqual(zone.driver, self.driver)

    def test_create_zone_success(self):
        BuddyNSMockHttp.type = 'CREATE_ZONE_SUCCESS'
        zone = self.driver.create_zone(domain='microsoft.com')

        self.assertEqual(zone.id, 'microsoft.com')
        self.assertEqual(zone.domain, 'microsoft.com')
        self.assertIsNone(zone.type),
        self.assertIsNone(zone.ttl)

    def test_create_zone_zone_already_exists(self):
        BuddyNSMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'

        try:
            self.driver.create_zone(domain='newzone.com',
                                    extra={'master': '13.0.0.1'})
        except ZoneAlreadyExistsError as e:
            self.assertEqual(e.zone_id, 'newzone.com')
        else:
            self.fail('Exception was not thrown')


class BuddyNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('buddyns')

    def _api_v2_zone_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_LIST_ZONES(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_zonedoesnotexist_com_GET_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return 404, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_myexample_com_GET_ZONE_SUCCESS(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_test_com_DELETE_ZONE_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('delete_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_test_com_DELETE_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_CREATE_ZONE_SUCCESS(self, method,
                                         url, body, headers):
        body = self.fixtures.load('create_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _api_v2_zone_CREATE_ZONE_ZONE_ALREADY_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_already_exists.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]


if __name__ == '__main__':
    sys.exit(unittest.main())
