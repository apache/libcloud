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

from libcloud.dns.drivers.digitalocean import DigitalOceanDNSDriver
from libcloud.dns.types import RecordType
from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DIGITALOCEAN_v2_PARAMS
from libcloud.utils.py3 import httplib


class DigitalOceanDNSTests(LibcloudTestCase):

    def setUp(self):
        DigitalOceanDNSDriver.connectionCls.conn_classes = \
            (None, DigitalOceanDNSMockHttp)
        DigitalOceanDNSMockHttp.type = None
        self.driver = DigitalOceanDNSDriver(*DIGITALOCEAN_v2_PARAMS)

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertTrue(len(zones) >= 1)

    def test_get_zone(self):
        zone = self.driver.get_zone('testdomain')
        self.assertEqual(zone.id, 'testdomain')

    def test_get_zone_not_found(self):
        DigitalOceanDNSMockHttp.type = 'NOT_FOUND'
        self.assertRaises(Exception, self.driver.get_zone, 'testdomain')

    def test_list_records(self):
        zone = self.driver.get_zone('testdomain')
        records = self.driver.list_records(zone)
        self.assertTrue(len(records) >= 1)

    def test_get_record(self):
        record = self.driver.get_record('testdomain', '1234564')
        self.assertEqual(record.id, '1234564')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '123.45.67.89')

    def test_get_record_not_found(self):
        DigitalOceanDNSMockHttp.type = 'NOT_FOUND'
        self.assertRaises(Exception, self.driver.get_zone, 'testdomain')

    def test_create_zone(self):
        DigitalOceanDNSMockHttp.type = 'CREATE'
        zone = self.driver.create_zone('testdomain')
        self.assertEqual(zone.id, 'testdomain')

    def test_create_record(self):
        zone = self.driver.get_zone('testdomain')

        DigitalOceanDNSMockHttp.type = 'CREATE'
        record = self.driver.create_record('sub', zone,
                                           RecordType.A, '234.56.78.90')
        self.assertEqual(record.id, '1234565')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '234.56.78.90')

    def test_update_record(self):
        record = self.driver.get_record('testdomain', '1234564')

        DigitalOceanDNSMockHttp.type = 'UPDATE'
        record = self.driver.update_record(record, data="234.56.78.90")
        self.assertEqual(record.id, '1234564')
        self.assertEqual(record.data, "234.56.78.90")

    def test_delete_zone(self):
        zone = self.driver.get_zone('testdomain')

        DigitalOceanDNSMockHttp.type = 'DELETE'
        self.assertTrue(self.driver.delete_zone(zone))

    def test_delete_record(self):
        record = self.driver.get_record('testdomain', '1234564')

        DigitalOceanDNSMockHttp.type = 'DELETE'
        self.assertTrue(self.driver.delete_record(record))


class DigitalOceanDNSMockHttp(MockHttpTestCase):
    fixtures = DNSFileFixtures('digitalocean')

    response = {
        None: httplib.OK,
        'CREATE': httplib.CREATED,
        'DELETE': httplib.NO_CONTENT,
        'EMPTY': httplib.OK,
        'NOT_FOUND': httplib.NOT_FOUND,
        'UNAUTHORIZED': httplib.UNAUTHORIZED,
        'UPDATE': httplib.OK
    }

    def _v2_domains(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_CREATE.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_EMPTY.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_UNAUTHORIZED.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_testdomain.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_DELETE(self, method, url, body, headers):
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_NOT_FOUND(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_testdomain_NOT_FOUND.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records(self, method, url, body, headers):
        body = self.fixtures.load('_v2_domains_testdomain_records.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_CREATE(self, method, url,
                                              body, headers):
        body = self.fixtures.load('_v2_domains_testdomain_records_CREATE.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234560(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234560.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234561(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234561.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234562(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234562.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234563(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234563.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234564(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234564.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234564_DELETE(
            self, method, url, body, headers):
        self.type = 'DELETE'
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234564_NOT_FOUND(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234564_NOT_FOUND.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

    def _v2_domains_testdomain_records_1234564_UPDATE(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_v2_domains_testdomain_records_1234564_UPDATE.json')
        return (self.response[self.type], body, {},
                httplib.responses[self.response[self.type]])

if __name__ == '__main__':
    sys.exit(unittest.main())
