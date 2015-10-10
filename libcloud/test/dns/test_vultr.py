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

from libcloud.dns.drivers.vultr import VultrDNSDriver
from libcloud.dns.types import RecordType
from libcloud.utils.py3 import httplib
from libcloud.test import MockHttp
from libcloud.test.secrets import VULTR_PARAMS
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError
from libcloud.dns.base import Zone, Record


class VultrTests(unittest.TestCase):

    def setUp(self):
        VultrMockHttp.type = None
        VultrDNSDriver.connectionCls.conn_classes = (
            None, VultrMockHttp)
        self.driver = VultrDNSDriver(*VULTR_PARAMS)
        self.test_zone = Zone(id='test.com', type='master', ttl=None,
                              domain='test.com', extra={}, driver=self)
        self.test_record = Record(id='31', type=RecordType.A, name='test',
                                  zone=self.test_zone, data='127.0.0.1',
                                  driver=self, extra={})

    def test_list_zones_empty(self):
        VultrMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 4)

        zone = zones[0]
        self.assertEqual(zone.id, 'example.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, None)

        zone = zones[1]
        self.assertEqual(zone.id, 'zupo.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'zupo.com')
        self.assertEqual(zone.ttl, None)

        zone = zones[2]
        self.assertEqual(zone.id, 'oltjano.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'oltjano.com')
        self.assertEqual(zone.ttl, None)

        zone = zones[3]
        self.assertEqual(zone.id, '13.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, '13.com')
        self.assertEqual(zone.ttl, None)

    def test_get_zone_zone_does_not_exist(self):
        VultrMockHttp.type = 'GET_ZONE_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='test.com')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'test.com')
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        VultrMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='zupo.com')

        self.assertEqual(zone.id, 'zupo.com')
        self.assertEqual(zone.domain, 'zupo.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.ttl, None)

    def test_delete_zone_zone_does_not_exist(self):
        VultrMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'

        try:
            self.driver.delete_zone(zone=self.test_zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_delete_zone_success(self):
        zone = self.driver.list_zones()[0]
        status = self.driver.delete_zone(zone=zone)

        self.assertTrue(status)

    def test_create_zone_success(self):
        zone = self.driver.create_zone(domain='test.com',
                                       extra={'serverip': '127.0.0.1'})

        self.assertEqual(zone.id, 'test.com')
        self.assertEqual(zone.domain, 'test.com')
        self.assertEqual(zone.type, 'master'),
        self.assertEqual(zone.ttl, None)

    def test_create_zone_zone_already_exists(self):
        VultrMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'

        try:
            self.driver.create_zone(domain='example.com',
                                    extra={'serverip': '127.0.0.1'})
        except ZoneAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'example.com')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_record_does_not_exist(self):
        VultrMockHttp.type = 'GET_RECORD_RECORD_DOES_NOT_EXIST'

        try:
            self.driver.get_record(zone_id='zupo.com', record_id='1300')
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '1300')
        else:
            self.fail('Exception was not thrown')

    def test_list_records_zone_does_not_exist(self):
        VultrMockHttp.type = 'LIST_RECORDS_ZONE_DOES_NOT_EXIST'

        try:
            self.driver.list_records(zone=self.test_zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_list_records_empty(self):
        VultrMockHttp.type = 'EMPTY_RECORDS_LIST'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)

        self.assertEqual(records, [])

    def test_list_records_success(self):
        zone = self.driver.get_zone(zone_id='zupo.com')
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)

        arecord = records[0]
        self.assertEqual(arecord.id, '13')
        self.assertEqual(arecord.name, 'arecord')
        self.assertEqual(arecord.type, RecordType.A)
        self.assertEqual(arecord.data, '127.0.0.1')

    def test_get_record_success(self):
        VultrMockHttp.type = 'GET_RECORD'
        record = self.driver.get_record(zone_id='zupo.com', record_id='1300')

        self.assertEqual(record.id, '1300')
        self.assertEqual(record.name, 'zupo')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.type, RecordType.A)

    def test_delete_record_record_does_not_exist(self):
        VultrMockHttp.type = 'DELETE_RECORD_RECORD_DOES_NOT_EXIST'

        try:
            self.driver.delete_record(record=self.test_record)
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, self.test_record.id)
        else:
            self.fail('Exception was not thrown')

    def test_delete_record_success(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[0]
        status = self.driver.delete_record(record=record)

        self.assertTrue(status)


class VultrMockHttp(MockHttp):
    fixtures = DNSFileFixtures('vultr')

    def _v1_dns_list(self, method, url, body, headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records(self, method, url, body, headers):
        body = self.fixtures.load('list_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_GET_ZONE_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_GET_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_EMPTY_RECORDS_LIST(self, method, url, body, headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records_EMPTY_RECORDS_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_records_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_GET_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records_GET_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('get_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_GET_RECORD_RECORD_DOES_NOT_EXIST(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records_GET_RECORD_RECORD_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('list_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_delete_domain(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_delete_record(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_create_domain(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_CREATE_ZONE_ZONE_ALREADY_EXISTS(self, method, url, body,
                                                     headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_create_domain_CREATE_ZONE_ZONE_ALREADY_EXISTS(self, method,
                                                              url, body,
                                                              headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_DELETE_ZONE_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                     headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_delete_domain_DELETE_ZONE_ZONE_DOES_NOT_EXIST(self, method,
                                                              url, body,
                                                              headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records_DELETE_RECORD_RECORD_DOES_NOT_EXIST(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('list_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_delete_record_DELETE_RECORD_RECORD_DOES_NOT_EXIST(self, method,
                                                                  url, body,
                                                                  headers):
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_DELETE_RECORD_RECORD_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('test_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_list_LIST_RECORDS_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_dns_records_LIST_RECORDS_ZONE_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
