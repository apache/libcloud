import sys
import unittest


from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_DNSPOD
from libcloud.dns.drivers.dnspod import DNSPodDNSDriver
from libcloud.utils.py3 import httplib
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError,\
    RecordType, RecordDoesNotExistError, RecordAlreadyExistsError
from libcloud.dns.base import Zone, Record


class DNSPodDNSTests(unittest.TestCase):
    def setUp(self):
        DNSPodMockHttp.type = None
        DNSPodDNSDriver.connectionCls.conn_classes = (None, DNSPodMockHttp)
        self.driver = DNSPodDNSDriver(*DNS_PARAMS_DNSPOD)
        self.test_zone = Zone(id='11', type='master', ttl=None,
                              domain='test.com', extra={}, driver=self.driver)
        self.test_record = Record(id='13', type=RecordType.A,
                                  name='example.com', zone=self.test_zone,
                                  data='127.0.0.1', driver=self, extra={})

    def test_one_equals_one(self):
        self.assertEqual(1, 1)

    def test_list_zones_empty(self):
        DNSPodMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        DNSPodMockHttp.type = 'LIST_ZONES'
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 1)

        zone = zones[0]
        self.assertEqual(zone.id, '6')
        self.assertEqual(zone.domain, 'dnspod.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.driver, self.driver)
        self.assertEqual(zone.ttl, '600')

    def test_get_zone_zone_does_not_exist(self):
        DNSPodMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='13')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        DNSPodMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='6')

        self.assertEqual(zone.id, '6')
        self.assertEqual(zone.domain, 'dnspod.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, '600')
        self.assertEqual(zone.driver, self.driver)

    def test_delete_zone_success(self):
        DNSPodMockHttp.type = 'DELETE_ZONE_SUCCESS'
        zone = self.test_zone
        status = self.driver.delete_zone(zone=zone)

        self.assertEqual(status, True)

    def test_delete_zone_zone_does_not_exist(self):
        DNSPodMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'
        zone = self.test_zone
        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '11')
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        DNSPodMockHttp.type = 'CREATE_ZONE_SUCCESS'
        zone = self.driver.create_zone(domain='example.org')

        self.assertEqual(zone.id, '3')
        self.assertEqual(zone.domain, 'api2.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)
        self.assertEqual(zone.driver, self.driver)

    def test_create_zone_zone_zone_already_exists(self):
        DNSPodMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'
        try:
            self.driver.create_zone(domain='test.com')
        except ZoneAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'test.com')
        else:
            self.fail('Exception was not thrown')

    def test_list_records_success(self):
        DNSPodMockHttp.type = 'LIST_RECORDS_SUCCESS'
        zone = self.test_zone
        records = self.driver.list_records(zone=zone)
        first_record = records[0]

        self.assertEqual(len(records), 5)
        self.assertEqual(first_record.zone, zone)
        self.assertEqual(first_record.type, 'A')
        self.assertEqual(first_record.name, '@')
        self.assertEqual(first_record.id, '50')

    def test_get_record_success(self):
        DNSPodMockHttp.type = 'GET_RECORD_SUCCESS'
        record = self.driver.get_record(zone_id='31', record_id='31')

        self.assertEqual(record.id, '50')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.name, '@')
        self.assertEqual(record.data, '96.126.115.73')

    def test_delete_record_success(self):
        DNSPodMockHttp.type = 'DELETE_RECORD_SUCCESS'
        record = self.test_record
        status = self.driver.delete_record(record=record)

        self.assertEqual(status, True)

    def test_delete_record_RECORD_DOES_NOT_EXIST_ERROR(self):
        DNSPodMockHttp.type = 'DELETE_RECORD_RECORD_DOES_NOT_EXIST'
        record = self.test_record
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_create_record_success(self):
        DNSPodMockHttp.type = 'CREATE_RECORD_SUCCESS'
        record = self.driver.create_record(name='@', zone=self.test_zone,
                                           type='A', data='96.126.115.73',
                                           extra={'ttl': 13,
                                                  'record_line': 'default'})
        self.assertEqual(record.id, '50')
        self.assertEqual(record.name, '@')
        self.assertEqual(record.data, '96.126.115.73')
        self.assertEqual(record.ttl, None)

    def test_create_record_already_exists_error(self):
        DNSPodMockHttp.type = 'RECORD_EXISTS'
        try:
            self.driver.create_record(name='@', zone=self.test_zone,
                                      type='A', data='92.126.115.73',
                                      extra={'ttl': 13,
                                             'record_line': 'default'})
        except RecordAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.value, '@')
        else:
            self.fail('Exception was not thrown')


class DNSPodMockHttp(MockHttp):
    fixtures = DNSFileFixtures('dnspod')

    def _Domain_List_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_List_LIST_ZONES(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Info_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return 404, body, {}, httplib.responses[httplib.OK]

    def _Domain_Info_GET_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Remove_DELETE_ZONE_SUCCESS(self, method, url,
                                           body, headers):
        body = self.fixtures.load('delete_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Remove_DELETE_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Create_CREATE_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('create_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Create_CREATE_ZONE_ZONE_ALREADY_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_already_exists.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_List_LIST_RECORDS_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('list_records.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Info_GET_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('get_record.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Info_GET_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Remove_DELETE_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('delete_record_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Remove_DELETE_RECORD_RECORD_DOES_NOT_EXIST(self, method,
                                                           url, body, headers):
        body = self.fixtures.load('delete_record_record_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Create_CREATE_RECORD_SUCCESS(self, method,
                                             url, body, headers):
        body = self.fixtures.load('get_record.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Domain_Info_CREATE_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Info_CREATE_RECORD_SUCCESS(self, method,
                                           url, body, headers):
        body = self.fixtures.load('get_record.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _Record_Create_RECORD_EXISTS(self, method, url, body, headers):
        body = self.fixtures.load('record_already_exists.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]


if __name__ == '__main__':
    sys.exit(unittest.main())
