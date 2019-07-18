# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
from mock import MagicMock


from libcloud.test import MockHttp
from libcloud.utils.py3 import httplib
from libcloud.dns.drivers.zonomi import ZonomiDNSDriver
from libcloud.test.secrets import DNS_PARAMS_ZONOMI
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.types import RecordAlreadyExistsError
from libcloud.dns.base import Zone, Record


class ZonomiTests(unittest.TestCase):

    def setUp(self):
        ZonomiDNSDriver.connectionCls.conn_class = ZonomiMockHttp
        ZonomiMockHttp.type = None
        self.driver = ZonomiDNSDriver(*DNS_PARAMS_ZONOMI)
        self.test_zone = Zone(id='zone.com', domain='zone.com',
                              driver=self.driver, type='master', ttl=None,
                              extra={})
        self.test_record = Record(id='record.zone.com', name='record.zone.com',
                                  data='127.0.0.1', type='A',
                                  zone=self.test_zone, driver=self,
                                  extra={})

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 3)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.TXT in record_types)

    def test_list_zones_empty(self):
        ZonomiMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 3)

        zone = zones[0]
        self.assertEqual(zone.id, 'thegamertest.com')
        self.assertEqual(zone.domain, 'thegamertest.com')
        self.assertEqual(zone.type, 'master')
        self.assertIsNone(zone.ttl)
        self.assertEqual(zone.driver, self.driver)

        second_zone = zones[1]
        self.assertEqual(second_zone.id, 'lonelygamer.com')
        self.assertEqual(second_zone.domain, 'lonelygamer.com')
        self.assertEqual(second_zone.type, 'master')
        self.assertIsNone(second_zone.ttl)
        self.assertEqual(second_zone.driver, self.driver)

        third_zone = zones[2]
        self.assertEqual(third_zone.id, 'gamertest.com')
        self.assertEqual(third_zone.domain, 'gamertest.com')
        self.assertEqual(third_zone.type, 'master')
        self.assertIsNone(third_zone.ttl)
        self.assertEqual(third_zone.driver, self.driver)

    def test_get_zone_GET_ZONE_DOES_NOT_EXIST(self):
        ZonomiMockHttp.type = 'GET_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone('testzone.com')
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'testzone.com')
        else:
            self.fail('Exception was not thrown.')

    def test_get_zone_GET_ZONE_SUCCESS(self):
        ZonomiMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='gamertest.com')

        self.assertEqual(zone.id, 'gamertest.com')
        self.assertEqual(zone.domain, 'gamertest.com')
        self.assertEqual(zone.type, 'master')
        self.assertIsNone(zone.ttl)
        self.assertEqual(zone.driver, self.driver)

    def test_delete_zone_DELETE_ZONE_DOES_NOT_EXIST(self):
        ZonomiMockHttp.type = 'DELETE_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.delete_zone(zone=self.test_zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown.')

    def test_delete_zone_delete_zone_success(self):
        ZonomiMockHttp.type = 'DELETE_ZONE_SUCCESS'
        status = self.driver.delete_zone(zone=self.test_zone)

        self.assertEqual(status, True)

    def test_create_zone_already_exists(self):
        ZonomiMockHttp.type = 'CREATE_ZONE_ALREADY_EXISTS'
        try:
            self.driver.create_zone(domain='gamertest.com')
        except ZoneAlreadyExistsError as e:
            self.assertEqual(e.zone_id, 'gamertest.com')
        else:
            self.fail('Exception was not thrown.')

    def test_create_zone_create_zone_success(self):
        ZonomiMockHttp.type = 'CREATE_ZONE_SUCCESS'

        zone = self.driver.create_zone(domain='myzone.com')

        self.assertEqual(zone.id, 'myzone.com')
        self.assertEqual(zone.domain, 'myzone.com')
        self.assertEqual(zone.type, 'master')
        self.assertIsNone(zone.ttl)

    def test_list_records_empty_list(self):
        ZonomiMockHttp.type = 'LIST_RECORDS_EMPTY_LIST'
        pass

    def test_list_records_success(self):
        ZonomiMockHttp.type = 'LIST_RECORDS_SUCCESS'
        records = self.driver.list_records(zone=self.test_zone)

        self.assertEqual(len(records), 4)

        record = records[0]
        self.assertEqual(record.id, 'zone.com')
        self.assertEqual(record.type, 'SOA')
        self.assertEqual(record.data,
                         'ns1.zonomi.com. soacontact.zonomi.com. 13')
        self.assertEqual(record.name, 'zone.com')
        self.assertEqual(record.zone, self.test_zone)

        second_record = records[1]
        self.assertEqual(second_record.id, 'zone.com')
        self.assertEqual(second_record.name, 'zone.com')
        self.assertEqual(second_record.type, 'NS')
        self.assertEqual(second_record.data, 'ns1.zonomi.com')
        self.assertEqual(second_record.zone, self.test_zone)

        third_record = records[2]
        self.assertEqual(third_record.id, 'oltjano')
        self.assertEqual(third_record.name, 'oltjano')
        self.assertEqual(third_record.type, 'A')
        self.assertEqual(third_record.data, '127.0.0.1')
        self.assertEqual(third_record.zone, self.test_zone)

        fourth_record = records[3]
        self.assertEqual(fourth_record.id, 'zone.com')
        self.assertEqual(fourth_record.name, 'zone.com')
        self.assertEqual(fourth_record.type, 'NS')
        self.assertEqual(fourth_record.data, 'ns5.zonomi.com')
        self.assertEqual(fourth_record.zone, self.test_zone)

    def test_get_record_does_not_exist(self):
        ZonomiMockHttp.type = 'GET_RECORD_DOES_NOT_EXIST'
        zone = Zone(id='zone.com', domain='zone.com', type='master',
                    ttl=None, driver=self.driver)
        self.driver.get_zone = MagicMock(return_value=zone)
        record_id = 'nonexistent'
        try:
            self.driver.get_record(record_id=record_id,
                                   zone_id='zone.com')
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, record_id)
        else:
            self.fail('Exception was not thrown.')

    def test_get_record_success(self):
        ZonomiMockHttp.type = 'GET_RECORD_SUCCESS'
        zone = Zone(id='zone.com', domain='zone.com', type='master',
                    ttl=None, driver=self.driver)
        self.driver.get_zone = MagicMock(return_value=zone)
        record = self.driver.get_record(record_id='oltjano',
                                        zone_id='zone.com')

        self.assertEqual(record.id, 'oltjano')
        self.assertEqual(record.name, 'oltjano')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '127.0.0.1')

    def test_delete_record_does_not_exist(self):
        ZonomiMockHttp.type = 'DELETE_RECORD_DOES_NOT_EXIST'
        record = self.test_record
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, record.id)
        else:
            self.fail('Exception was not thrown.')

    def test_delete_record_success(self):
        ZonomiMockHttp.type = 'DELETE_RECORD_SUCCESS'
        record = self.test_record
        status = self.driver.delete_record(record=record)

        self.assertEqual(status, True)

    def test_create_record_already_exists(self):
        zone = self.test_zone
        ZonomiMockHttp.type = 'CREATE_RECORD_ALREADY_EXISTS'
        try:
            self.driver.create_record(name='createrecord', type='A',
                                      data='127.0.0.1', zone=zone, extra={})
        except RecordAlreadyExistsError as e:
            self.assertEqual(e.record_id, 'createrecord')
        else:
            self.fail('Exception was not thrown.')

    def test_create_record_success(self):
        ZonomiMockHttp.type = 'CREATE_RECORD_SUCCESS'
        zone = self.test_zone
        record = self.driver.create_record(name='createrecord',
                                           zone=zone, type='A',
                                           data='127.0.0.1', extra={})

        self.assertEqual(record.id, 'createrecord')
        self.assertEqual(record.name, 'createrecord')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.zone, zone)

    def test_convert_to_slave(self):
        zone = self.test_zone
        result = self.driver.ex_convert_to_secondary(zone, '1.2.3.4')
        self.assertTrue(result)

    def test_convert_to_slave_couldnt_convert(self):
        zone = self.test_zone
        ZonomiMockHttp.type = 'COULDNT_CONVERT'
        try:
            self.driver.ex_convert_to_secondary(zone, '1.2.3.4')
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'zone.com')
        else:
            self.fail('Exception was not thrown.')

    def test_convert_to_master(self):
        zone = self.test_zone
        result = self.driver.ex_convert_to_master(zone)
        self.assertTrue(result)

    def test_convert_to_master_couldnt_convert(self):
        zone = self.test_zone
        ZonomiMockHttp.type = 'COULDNT_CONVERT'
        try:
            self.driver.ex_convert_to_master(zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, 'zone.com')
        else:
            self.fail('Exception was not thrown.')


class ZonomiMockHttp(MockHttp):
    fixtures = DNSFileFixtures('zonomi')

    def _app_dns_dyndns_jsp_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_GET_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('list_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_GET_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_DELETE_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                       headers):
        body = self.fixtures.load('delete_zone_does_not_exist.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_DELETE_ZONE_SUCCESS(self, method, url, body,
                                                headers):
        body = self.fixtures.load('delete_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_addzone_jsp_CREATE_ZONE_SUCCESS(self, method, url, body,
                                                 headers):
        body = self.fixtures.load('create_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_addzone_jsp_CREATE_ZONE_ALREADY_EXISTS(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('create_zone_already_exists.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_LIST_RECORDS_EMPTY_LIST(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('list_records_empty_list.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_LIST_RECORDS_SUCCESS(self, method, url, body,
                                                 headers):
        body = self.fixtures.load('list_records.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_DELETE_RECORD_SUCCESS(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('delete_record.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_DELETE_RECORD_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('delete_record_does_not_exist.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_CREATE_RECORD_SUCCESS(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('create_record.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_CREATE_RECORD_ALREADY_EXISTS(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('create_record_already_exists.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_GET_RECORD_SUCCESS(self, method, url, body,
                                               headers):
        body = self.fixtures.load('list_records.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_dyndns_jsp_GET_RECORD_DOES_NOT_EXIST(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('list_records.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_converttosecondary_jsp(self, method, url, body, headers):
        body = self.fixtures.load('converted_to_slave.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_converttosecondary_jsp_COULDNT_CONVERT(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('couldnt_convert.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_converttomaster_jsp(self, method, url, body, headers):
        body = self.fixtures.load('converted_to_master.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _app_dns_converttomaster_jsp_COULDNT_CONVERT(self, method, url,
                                                     body, headers):
        body = self.fixtures.load('couldnt_convert.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
