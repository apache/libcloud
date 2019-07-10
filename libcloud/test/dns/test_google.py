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

from libcloud.utils.py3 import httplib

from libcloud.dns.types import ZoneDoesNotExistError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.drivers.google import GoogleDNSDriver
from libcloud.common.google import GoogleBaseAuthConnection

from libcloud.test.common.test_google import GoogleAuthMockHttp, GoogleTestCase
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_GOOGLE, DNS_KEYWORD_PARAMS_GOOGLE


class GoogleTests(GoogleTestCase):

    def setUp(self):
        GoogleDNSMockHttp.test = self
        GoogleDNSDriver.connectionCls.conn_class = GoogleDNSMockHttp
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        GoogleDNSMockHttp.type = None
        kwargs = DNS_KEYWORD_PARAMS_GOOGLE.copy()
        kwargs['auth_type'] = 'IA'
        self.driver = GoogleDNSDriver(*DNS_PARAMS_GOOGLE, **kwargs)

    def test_default_scopes(self):
        self.assertIsNone(self.driver.scopes)

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

    def test_list_records(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)

    def test_get_zone(self):
        zone = self.driver.get_zone('example-com')
        self.assertEqual(zone.id, 'example-com')
        self.assertEqual(zone.domain, 'example.com.')

    def test_get_zone_does_not_exist(self):
        GoogleDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'

        try:
            self.driver.get_zone('example-com')
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'example-com')
        else:
            self.fail('Exception not thrown')

    def test_get_record(self):
        GoogleDNSMockHttp.type = 'FILTER_ZONES'
        zone = self.driver.list_zones()[0]
        record = self.driver.get_record(zone.id, "A:foo.example.com.")
        self.assertEqual(record.id, 'A:foo.example.com.')
        self.assertEqual(record.name, 'foo.example.com.')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.zone.id, 'example-com')

    def test_get_record_zone_does_not_exist(self):
        GoogleDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'

        try:
            self.driver.get_record('example-com', 'a:a')
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'example-com')
        else:
            self.fail('Exception not thrown')

    def test_get_record_record_does_not_exist(self):
        GoogleDNSMockHttp.type = 'RECORD_DOES_NOT_EXIST'
        try:
            self.driver.get_record('example-com', "A:foo")
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, 'A:foo')
        else:
            self.fail('Exception not thrown')

    def test_create_zone(self):
        extra = {'description': 'new domain for example.org'}
        zone = self.driver.create_zone('example.org.', extra)
        self.assertEqual(zone.domain, 'example.org.')
        self.assertEqual(zone.extra['description'], extra['description'])
        self.assertEqual(len(zone.extra['nameServers']), 4)

    def test_delete_zone(self):
        zone = self.driver.get_zone('example-com')
        res = self.driver.delete_zone(zone)
        self.assertTrue(res)

    def test_ex_bulk_record_changes(self):
        zone = self.driver.get_zone('example-com')
        records = self.driver.ex_bulk_record_changes(zone, {})

        self.assertEqual(records['additions'][0].name, 'foo.example.com.')
        self.assertEqual(records['additions'][0].type, 'A')

        self.assertEqual(records['deletions'][0].name, 'bar.example.com.')
        self.assertEqual(records['deletions'][0].type, 'A')


class GoogleDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('google')

    def _dns_v1_projects_project_name_managedZones(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('zone_create.json')
        else:
            body = self.fixtures.load('zone_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_FILTER_ZONES(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_rrsets_FILTER_ZONES(
            self, method, url, body, headers):
        body = self.fixtures.load('record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_rrsets(
            self, method, url, body, headers):
        body = self.fixtures.load('records_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('managed_zones_1.json')
        elif method == 'DELETE':
            body = None
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_changes(
            self, method, url, body, headers):
        body = self.fixtures.load('record_changes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('get_zone_does_not_exists.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _dns_v1_projects_project_name_managedZones_example_com_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('managed_zones_1.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_rrsets_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('no_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_v1_projects_project_name_managedZones_example_com_rrsets_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('get_zone_does_not_exists.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _dns_v1_projects_project_name_managedZones_example_com_FILTER_ZONES(
            self, method, url, body, headers):
        body = self.fixtures.load('zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
