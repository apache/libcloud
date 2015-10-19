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

from libcloud.utils.py3 import httplib
from libcloud.dns.drivers.liquidweb import LiquidWebDNSDriver
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_LIQUIDWEB
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.types import RecordType
from libcloud.dns.base import Zone, Record


class LiquidWebTests(unittest.TestCase):

    def setUp(self):
        LiquidWebMockHttp.type = None
        LiquidWebDNSDriver.connectionCls.conn_classes = (
            None, LiquidWebMockHttp)
        self.driver = LiquidWebDNSDriver(*DNS_PARAMS_LIQUIDWEB)
        self.test_zone = Zone(id='11', type='master', ttl=None,
                              domain='example.com', extra={},
                              driver=self.driver)
        self.test_record = Record(id='13', type=RecordType.A,
                                  name='example.com', zone=self.test_zone,
                                  data='127.0.0.1', driver=self, extra={})

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_zones_empty(self):
        LiquidWebMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 3)

        zone = zones[0]
        self.assertEqual(zone.id, '378451')
        self.assertEqual(zone.domain, 'blogtest.com')
        self.assertEqual(zone.type, 'NATIVE')
        self.assertEqual(zone.driver, self.driver)
        self.assertEqual(zone.ttl, None)

        second_zone = zones[1]
        self.assertEqual(second_zone.id, '378449')
        self.assertEqual(second_zone.domain, 'oltjanotest.com')
        self.assertEqual(second_zone.type, 'NATIVE')
        self.assertEqual(second_zone.driver, self.driver)
        self.assertEqual(second_zone.ttl, None)

        third_zone = zones[2]
        self.assertEqual(third_zone.id, '378450')
        self.assertEqual(third_zone.domain, 'pythontest.com')
        self.assertEqual(third_zone.type, 'NATIVE')
        self.assertEqual(third_zone.driver, self.driver)
        self.assertEqual(third_zone.ttl, None)

    def test_get_zone_zone_does_not_exist(self):
        LiquidWebMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='13')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        LiquidWebMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='13')

        self.assertEqual(zone.id, '13')
        self.assertEqual(zone.domain, 'blogtest.com')
        self.assertEqual(zone.type, 'NATIVE')
        self.assertEqual(zone.ttl, None)
        self.assertEqual(zone.driver, self.driver)

    def test_delete_zone_success(self):
        LiquidWebMockHttp.type = 'DELETE_ZONE_SUCCESS'
        zone = self.test_zone
        status = self.driver.delete_zone(zone=zone)

        self.assertEqual(status, True)

    def test_delete_zone_zone_does_not_exist(self):
        LiquidWebMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'
        zone = self.test_zone
        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '11')
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        LiquidWebMockHttp.type = 'CREATE_ZONE_SUCCESS'
        zone = self.driver.create_zone(domain='test.com')

        self.assertEqual(zone.id, '13')
        self.assertEqual(zone.domain, 'test.com')
        self.assertEqual(zone.type, 'NATIVE')
        self.assertEqual(zone.ttl, None)
        self.assertEqual(zone.driver, self.driver)

    def test_create_zone_zone_zone_already_exists(self):
        LiquidWebMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'
        try:
            self.driver.create_zone(domain='test.com')
        except ZoneAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'test.com')
        else:
            self.fail('Exception was not thrown')

    def test_list_records_empty(self):
        LiquidWebMockHttp.type = 'EMPTY_RECORDS_LIST'
        zone = self.test_zone
        records = self.driver.list_records(zone=zone)

        self.assertEqual(records, [])

    def test_list_records_success(self):
        LiquidWebMockHttp.type = 'LIST_RECORDS_SUCCESS'
        zone = self.test_zone
        records = self.driver.list_records(zone=zone)

        self.assertEqual(len(records), 3)

        record = records[0]
        self.assertEqual(record.id, '13')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.name, 'nerd.domain.com')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.zone, self.test_zone)
        self.assertEqual(record.zone.id, '11')

        second_record = records[1]
        self.assertEqual(second_record.id, '11')
        self.assertEqual(second_record.type, 'A')
        self.assertEqual(second_record.name, 'thisboy.domain.com')
        self.assertEqual(second_record.data, '127.0.0.1')
        self.assertEqual(second_record.zone, self.test_zone)

        third_record = records[2]
        self.assertEqual(third_record.id, '10')
        self.assertEqual(third_record.type, 'A')
        self.assertEqual(third_record.name, 'visitor.domain.com')
        self.assertEqual(third_record.data, '127.0.0.1')
        self.assertEqual(third_record.zone, self.test_zone)

    def test_get_record_record_does_not_exist(self):
        LiquidWebMockHttp.type = 'GET_RECORD_RECORD_DOES_NOT_EXIST'
        try:
            self.driver.get_record(zone_id='13', record_id='13')
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_success(self):
        LiquidWebMockHttp.type = 'GET_RECORD_SUCCESS'
        record = self.driver.get_record(zone_id='13', record_id='13')

        self.assertEqual(record.id, '13')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.name, 'nerd.domain.com')
        self.assertEqual(record.data, '127.0.0.1')

    def test_update_record_success(self):
        LiquidWebMockHttp.type = 'GET_RECORD_SUCCESS'
        record = self.driver.get_record(zone_id='13', record_id='13')
        self.assertEqual(record.id, '13')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.name, 'nerd.domain.com')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.extra.get('ttl'), 300)
        LiquidWebMockHttp.type = ''
        record1 = self.driver.update_record(record=record, name=record.name,
                                            type=record.type,
                                            data=record.data,
                                            extra={'ttl': 5600})
        self.assertEqual(record1.id, '13')
        self.assertEqual(record1.type, 'A')
        self.assertEqual(record1.name, 'nerd.domain.com')
        self.assertEqual(record1.data, '127.0.0.1')
        self.assertEqual(record1.extra.get('ttl'), 5600)

    def test_delete_record_success(self):
        LiquidWebMockHttp.type = 'DELETE_RECORD_SUCCESS'
        record = self.test_record
        status = self.driver.delete_record(record=record)

        self.assertEqual(status, True)

    def test_delete_record_RECORD_DOES_NOT_EXIST_ERROR(self):
        LiquidWebMockHttp.type = 'DELETE_RECORD_RECORD_DOES_NOT_EXIST'
        record = self.test_record
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_create_record_success(self):
        pass

    def test_record_already_exists_error(self):
        pass


class LiquidWebMockHttp(MockHttp):
    fixtures = DNSFileFixtures('liquidweb')

    def _v1_Network_DNS_Zone_list(self, method, url, body, headers):
        body = self.fixtures.load('zones_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_list_EMPTY_ZONES_LIST(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('empty_zones_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_details_ZONE_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_details_GET_ZONE_SUCCESS(self, method, url,
                                                      body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_delete_DELETE_ZONE_SUCCESS(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('delete_zone_success.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_delete_DELETE_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_create_CREATE_ZONE_SUCCESS(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('create_zone_success.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_create_CREATE_ZONE_ZONE_ALREADY_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load('duplicate_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_list_EMPTY_RECORDS_LIST(self, method, url, body,
                                                       headers):
        body = self.fixtures.load('empty_records_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_list_LIST_RECORDS_SUCCESS(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('records_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_details_GET_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_details_GET_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Zone_details_GET_RECORD_SUCCESS(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_details_GET_RECORD_SUCCESS(self, method, url,
                                                          body, headers):
        body = self.fixtures.load('get_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_delete_DELETE_RECORD_SUCCESS(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('delete_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_delete_DELETE_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_create_CREATE_RECORD_SUCCESS(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_ALREADY_EXISTS_ERROR(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_Network_DNS_Record_update(self, method, url, body, headers):

        body = self.fixtures.load('update_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
