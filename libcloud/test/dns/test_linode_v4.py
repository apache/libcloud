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
import pdb

from libcloud.utils.py3 import httplib

from libcloud.common.linode import LinodeException
from libcloud.dns.types import RecordType, ZoneDoesNotExistError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.drivers.linode import LinodeDNSDriver, LinodeDNSDriverV4

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_LINODE


class LinodeTests(unittest.TestCase):
    def setUp(self):
        LinodeDNSDriverV4.connectionCls.conn_class = LinodeMockHttpV4
        LinodeMockHttpV4.type = None
        self.driver = LinodeDNSDriver(*DNS_PARAMS_LINODE)

    def test_correct_class_is_used(self):
        self.assertIsInstance(self.driver, LinodeDNSDriverV4)

    def test_unknown_api_version(self):
        self.assertRaises(NotImplementedError, LinodeDNSDriver,
                          'foo', api_version='2.0')

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 3)
        zone = zones[0]
        self.assertEqual(zone.id, '123')
        self.assertEqual(zone.domain, 'test.com')
        self.assertEqual(zone.ttl, 300)
        self.assertEqual(zone.extra['soa_email'], 'admin@test.com')

    def test_list_records(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone)
        self.assertEqual(len(records), 6)
        record = records[0]
        self.assertEqual(record.id, '123')
        self.assertEqual(record.data, 'mail.test.com')
        self.assertEqual(record.ttl, 300)

    def test_get_zone(self):
        zone = self.driver.get_zone('123')
        self.assertEqual(zone.id, '123')
        self.assertEqual(zone.domain, 'test.com')
        self.assertEqual(zone.extra['soa_email'], 'admin@test.com')

    def test_get_zone_not_found(self):
        LinodeMockHttpV4.type = 'ZONE_DOES_NOT_EXIST'
        with self.assertRaises(Exception):
            self.driver.get_zone('123')

    def test_get_record_A_RECORD(self):
        LinodeMockHttpV4.type = 'A_RECORD'
        record = self.driver.get_record('123', '123')
        self.assertEqual(record.id, '123')
        self.assertEqual(record.name, 'test.example.com')
        self.assertEqual(record.type, 'A')

    def test_get_record_MX_RECORD(self):
        LinodeMockHttpV4.type = 'MX_RECORD'
        record = self.driver.get_record('123', '123')
        self.assertEqual(record.id, '123')
        self.assertEqual(record.data, 'mail.example.com')
        self.assertEqual(record.type, 'MX')

    def test_create_zone(self):
        domain = 'example.com'
        ttl = 300
        extra = {
            'soa_email': 'admin@example.com'
        }
        zone = self.driver.create_zone(domain=domain, ttl=ttl, extra=extra)
        self.assertEqual(zone.ttl, 300)
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.extra['soa_email'], 'admin@example.com')

    def test_create_record(self):
        zone = self.driver.list_zones()[0]
        name = 'test'
        type = RecordType.A
        data = '200.150.100.50'
        record = self.driver.create_record(name, zone, type, data)
        self.assertEqual(record.id, '123')
        self.assertEqual(record.name, name)
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, data)

    def test_update_zone(self):
        zone = self.driver.list_zones()[0]
        domain = 'example.com'
        ttl = 300
        extra = {
            'description': 'Testing',
            'soa_email': 'admin@example.com'
        }
        updated_zone = self.driver.update_zone(zone, domain, ttl=ttl, extra=extra)
        self.assertEqual(updated_zone.domain, domain)
        self.assertEqual(updated_zone.ttl, ttl)
        self.assertEqual(updated_zone.extra['soa_email'], extra['soa_email'])
        self.assertEqual(updated_zone.extra['description'], extra['description'])

    def test_update_record(self):
        LinodeMockHttpV4.type = 'A_RECORD'
        record = self.driver.get_record('123', '123')
        name = 'test'
        data = '200.150.100.50'
        extra = {
            'ttl_sec': 3600
        }
        updated = self.driver.update_record(record, name=name, data=data, extra=extra)
        self.assertEqual(updated.name, name)
        self.assertEqual(updated.ttl, extra['ttl_sec'])
        self.assertEqual(updated.data, data)

    def test_delete_zone(self):
        zone = self.driver.list_zones()[0]
        self.assertTrue(self.driver.delete_zone(zone))

    def test_delete_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone)[0]
        self.assertTrue(self.driver.delete_record(record))


class LinodeMockHttpV4(MockHttp):
    fixtures = DNSFileFixtures('linode_v4')

    def _v4_domains(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_zones.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_zone.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_records(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_records.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'POST':
            body = self.fixtures.load('create_record.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('get_zone.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'PUT':
            body = self.fixtures.load('update_zone.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'DELETE':
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = '{ "errors":[{"reason":"Not found"}]}'
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _v4_domains_123_A_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_MX_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_records_123_A_RECORD(self, method, url,
                                             body, headers):
        if method == 'GET':
            body = self.fixtures.load('get_record_A.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == 'PUT':
            body = self.fixtures.load('update_record.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_records_123_MX_RECORD(self, method, url,
                                              body, headers):
        body = self.fixtures.load('get_record_MX.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v4_domains_123_records_123(self, method, url, body, headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
