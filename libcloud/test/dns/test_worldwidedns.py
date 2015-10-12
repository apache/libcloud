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

from libcloud.dns.types import RecordType, ZoneDoesNotExistError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.drivers.worldwidedns import WorldWideDNSDriver
from libcloud.dns.drivers.worldwidedns import WorldWideDNSError
from libcloud.common.worldwidedns import NonExistentDomain
from libcloud.common.worldwidedns import InvalidDomainName

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_WORLDWIDEDNS


class WorldWideDNSTests(unittest.TestCase):
    def setUp(self):
        WorldWideDNSDriver.connectionCls.conn_classes = (
            None, WorldWideDNSMockHttp)
        WorldWideDNSMockHttp.type = None
        self.driver = WorldWideDNSDriver(*DNS_PARAMS_WORLDWIDEDNS)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 6)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.TXT in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.NS in record_types)

    def test_list_zones_success(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 1)

        zone = zones[0]
        self.assertEqual(zone.id, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.ttl, '43200')
        self.assertHasKeys(zone.extra, ['HOSTMASTER', 'REFRESH', 'RETRY',
                                        'EXPIRE', 'SECURE', 'S1', 'T1', 'D1',
                                        'S2', 'T2', 'D2', 'S3', 'T3', 'D3'])

    def test_list_records_success(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)

        www = records[0]
        self.assertEqual(www.id, '1')
        self.assertEqual(www.name, 'www')
        self.assertEqual(www.type, RecordType.A)
        self.assertEqual(www.data, '0.0.0.0')
        self.assertEqual(www.extra, {})

    def test_list_records_zone_does_not_exist(self):
        WorldWideDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            zone = self.driver.list_zones()[0]
            self.driver.list_records(zone=zone)
        except NonExistentDomain:
            e = sys.exc_info()[1]
            self.assertEqual(e.code, 405)
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        zone = self.driver.get_zone(zone_id='niteowebsponsoredthisone.com')
        self.assertEqual(zone.id, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.ttl, '43200')
        self.assertHasKeys(zone.extra, ['HOSTMASTER', 'REFRESH', 'RETRY',
                                        'EXPIRE', 'SECURE', 'S1', 'T1', 'D1',
                                        'S2', 'T2', 'D2', 'S3', 'T3', 'D3'])

    def test_get_zone_does_not_exist(self):
        WorldWideDNSMockHttp.type = 'GET_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='unexistentzone')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'unexistentzone')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_success(self):
        record = self.driver.get_record(zone_id='niteowebsponsoredthisone.com',
                                        record_id='1')
        self.assertEqual(record.id, '1')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '0.0.0.0')
        self.assertEqual(record.extra, {})

    def test_get_record_zone_does_not_exist(self):
        try:
            self.driver.get_record(zone_id='unexistentzone',
                                   record_id='3585100')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'unexistentzone')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_record_does_not_exist(self):
        try:
            self.driver.get_record(zone_id='niteowebsponsoredthisone.com',
                                   record_id='3585100')
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '3585100')
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        zone = self.driver.create_zone(domain='niteowebsponsoredthisone.com',
                                       type='master')
        self.assertEqual(zone.id, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.domain, 'niteowebsponsoredthisone.com')
        self.assertEqual(zone.ttl, '43200')
        self.assertEqual(zone.type, 'master')

    def test_create_zone_validaton_error(self):
        WorldWideDNSMockHttp.type = 'VALIDATION_ERROR'

        try:
            self.driver.create_zone(domain='foo.%.com', type='master',
                                    ttl=None, extra=None)
        except InvalidDomainName:
            e = sys.exc_info()[1]
            self.assertEqual(e.code, 410)
        else:
            self.fail('Exception was not thrown')

    def test_update_zone_success(self):
        zone = self.driver.list_zones()[0]
        WorldWideDNSMockHttp.type = 'UPDATE_ZONE'
        updated_zone = self.driver.update_zone(zone=zone,
                                               domain='niteowebsponsoredthisone.com',  # noqa
                                               ttl=3800,
                                               extra={'HOSTMASTER':
                                                      'mail.niteowebsponsoredthisone.com'})  # noqa

        self.assertEqual(zone.extra['HOSTMASTER'],
                         'hostmaster.niteowebsponsoredthisone.com')

        self.assertEqual(updated_zone.id, zone.id)
        self.assertEqual(updated_zone.domain, 'niteowebsponsoredthisone.com')
        self.assertEqual(updated_zone.type, zone.type)
        self.assertEqual(updated_zone.ttl, '3800')
        self.assertEqual(updated_zone.extra['HOSTMASTER'],
                         'mail.niteowebsponsoredthisone.com')
        self.assertEqual(updated_zone.extra['REFRESH'], zone.extra['REFRESH'])
        self.assertEqual(updated_zone.extra['RETRY'], zone.extra['RETRY'])
        self.assertEqual(updated_zone.extra['EXPIRE'], zone.extra['EXPIRE'])
        self.assertEqual(updated_zone.extra['SECURE'], zone.extra['SECURE'])
        self.assertEqual(updated_zone.extra['S1'], zone.extra['S1'])
        self.assertEqual(updated_zone.extra['T1'], zone.extra['T1'])
        self.assertEqual(updated_zone.extra['D1'], zone.extra['D1'])
        self.assertEqual(updated_zone.extra['S2'], zone.extra['S2'])
        self.assertEqual(updated_zone.extra['T2'], zone.extra['T2'])
        self.assertEqual(updated_zone.extra['D2'], zone.extra['D2'])
        self.assertEqual(updated_zone.extra['S3'], zone.extra['S3'])
        self.assertEqual(updated_zone.extra['T3'], zone.extra['T3'])
        self.assertEqual(updated_zone.extra['D3'], zone.extra['D3'])

    def test_create_record_success(self):
        zone = self.driver.list_zones()[0]
        WorldWideDNSMockHttp.type = 'CREATE_RECORD'
        record = self.driver.create_record(name='domain4', zone=zone,
                                           type=RecordType.A, data='0.0.0.4',
                                           extra={'entry': 4})

        self.assertEqual(record.id, '4')
        self.assertEqual(record.name, 'domain4')
        self.assertNotEqual(record.zone.extra.get('S4'), zone.extra.get('S4'))
        self.assertNotEqual(record.zone.extra.get('D4'), zone.extra.get('D4'))
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '0.0.0.4')

    def test_create_record_finding_entry(self):
        zone = self.driver.list_zones()[0]
        WorldWideDNSMockHttp.type = 'CREATE_RECORD'
        record = self.driver.create_record(name='domain4', zone=zone,
                                           type=RecordType.A, data='0.0.0.4')
        WorldWideDNSMockHttp.type = 'CREATE_SECOND_RECORD'
        zone = record.zone
        record2 = self.driver.create_record(name='domain1', zone=zone,
                                            type=RecordType.A, data='0.0.0.1')
        self.assertEqual(record.id, '4')
        self.assertEqual(record2.id, '5')

    def test_create_record_max_entry_reached(self):
        zone = self.driver.list_zones()[0]
        WorldWideDNSMockHttp.type = 'CREATE_RECORD_MAX_ENTRIES'
        record = self.driver.create_record(name='domain40', zone=zone,
                                           type=RecordType.A, data='0.0.0.40')
        WorldWideDNSMockHttp.type = 'CREATE_RECORD'
        zone = record.zone
        try:
            self.driver.create_record(
                name='domain41', zone=zone, type=RecordType.A, data='0.0.0.41')
        except WorldWideDNSError:
            e = sys.exc_info()[1]
            self.assertEqual(e.value, 'All record entries are full')
        else:
            self.fail('Exception was not thrown')

    def test_create_record_max_entry_reached_give_entry(self):
        WorldWideDNSMockHttp.type = 'CREATE_RECORD_MAX_ENTRIES'
        zone = self.driver.list_zones()[0]
        record = self.driver.get_record(zone.id, '23')
        self.assertEqual(record.id, '23')
        self.assertEqual(record.name, 'domain23')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '0.0.0.23')

        # No matter if we have all entries full, if we choose a specific
        # entry, the record will be replaced with the new one.
        WorldWideDNSMockHttp.type = 'CREATE_RECORD_MAX_ENTRIES_WITH_ENTRY'
        record = self.driver.create_record(name='domain23b', zone=zone,
                                           type=RecordType.A, data='0.0.0.41',
                                           extra={'entry': 23})
        zone = record.zone
        self.assertEqual(record.id, '23')
        self.assertEqual(record.name, 'domain23b')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '0.0.0.41')

    def test_update_record_success(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.get_record(zone.id, '1')
        WorldWideDNSMockHttp.type = 'UPDATE_RECORD'
        record = self.driver.update_record(record=record, name='domain1',
                                           type=RecordType.A, data='0.0.0.1',
                                           extra={'entry': 1})

        self.assertEqual(record.id, '1')
        self.assertEqual(record.name, 'domain1')
        self.assertNotEqual(record.zone.extra.get('S1'), zone.extra.get('S1'))
        self.assertNotEqual(record.zone.extra.get('D1'), zone.extra.get('D1'))
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '0.0.0.1')

    def test_delete_zone_success(self):
        zone = self.driver.list_zones()[0]
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_zone_does_not_exist(self):
        zone = self.driver.list_zones()[0]

        WorldWideDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'

        try:
            self.driver.delete_zone(zone=zone)
        except NonExistentDomain:
            e = sys.exc_info()[1]
            self.assertEqual(e.code, 405)
        else:
            self.fail('Exception was not thrown')

    def test_delete_record_success(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)
        record = records[1]
        WorldWideDNSMockHttp.type = 'DELETE_RECORD'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)


class WorldWideDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('worldwidedns')

    def _api_dns_list_asp(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list_domain_asp')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                              headers):
        return (httplib.OK, '405', {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_GET_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                  headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _api_dns_new_domain_asp(self, method, url, body, headers):
        return (httplib.OK, '200', {}, httplib.responses[httplib.OK])

    def _api_dns_new_domain_asp_VALIDATION_ERROR(self, method, url, body,
                                                 headers):
        return (httplib.OK, '410', {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp(self, method, url, body, headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_asp_UPDATE_ZONE(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_UPDATE_ZONE(self, method, url, body, headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_UPDATE_ZONE(self, method, url, body,
                                             headers):
        body = self.fixtures.load('api_dns_list_domain_asp_UPDATE_ZONE')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_CREATE_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_CREATE_SECOND_RECORD(self, method, url, body,
                                               headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_CREATE_RECORD(self, method, url, body, headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_modify_asp_CREATE_SECOND_RECORD(self, method, url, body,
                                                 headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_CREATE_RECORD(self, method, url, body,
                                               headers):
        body = self.fixtures.load('api_dns_list_domain_asp_CREATE_RECORD')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_CREATE_SECOND_RECORD(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'api_dns_list_domain_asp_CREATE_SECOND_RECORD')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_CREATE_RECORD_MAX_ENTRIES(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'api_dns_list_domain_asp_CREATE_RECORD_MAX_ENTRIES')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_CREATE_RECORD_MAX_ENTRIES(self, method, url, body,
                                                      headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_asp_CREATE_RECORD_MAX_ENTRIES(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_CREATE_RECORD_MAX_ENTRIES_WITH_ENTRY(self,
                                                                      method,
                                                                      url,
                                                                      body,
                                                                      headers):
        body = self.fixtures.load(
            '_api_dns_modify_asp_CREATE_RECORD_MAX_ENTRIES_WITH_ENTRY')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_CREATE_RECORD_MAX_ENTRIES_WITH_ENTRY(self, method,
                                                                 url, body,
                                                                 headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_asp_CREATE_RECORD_MAX_ENTRIES_WITH_ENTRY(self, method,
                                                               url, body,
                                                               headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_UPDATE_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_UPDATE_RECORD(self, method, url, body, headers):
        return (httplib.OK, '211\r\n212\r\n213', {},
                httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_UPDATE_RECORD(self, method, url, body,
                                               headers):
        body = self.fixtures.load('api_dns_list_domain_asp_UPDATE_RECORD')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_delete_domain_asp(self, method, url, body, headers):
        return (httplib.OK, '200', {}, httplib.responses[httplib.OK])

    def _api_dns_delete_domain_asp_ZONE_DOES_NOT_EXIST(self, method, url, body,
                                                       headers):
        return (httplib.OK, '405', {}, httplib.responses[httplib.OK])

    def _api_dns_list_asp_DELETE_RECORD(self, method, url, body, headers):
        body = self.fixtures.load('api_dns_list')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_dns_modify_asp_DELETE_RECORD(self, method, url, body, headers):
        return (httplib.OK, '200', {}, httplib.responses[httplib.OK])

    def _api_dns_list_domain_asp_DELETE_RECORD(self, method, url, body,
                                               headers):
        body = self.fixtures.load('api_dns_list_domain_asp_DELETE_RECORD')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
