import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.dns.drivers.luadns import LuadnsDNSDriver
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_LUADNS
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.types import RecordType
from libcloud.dns.base import Zone, Record


class LuadnsTests(unittest.TestCase):

    def setUp(self):
        LuadnsMockHttp.type = None
        LuadnsDNSDriver.connectionCls.conn_classes = (
            None, LuadnsMockHttp)
        self.driver = LuadnsDNSDriver(*DNS_PARAMS_LUADNS)
        self.test_zone = Zone(id='11', type='master', ttl=None,
                              domain='example.com', extra={},
                              driver=self.driver)
        self.test_record = Record(id='13', type=RecordType.A,
                                  name='example.com', zone=self.test_zone,
                                  data='127.0.0.1', driver=self, extra={})

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary,
                            'key "%s" not in dictionary' % key)

    def test_list_zones_empty(self):
        LuadnsMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 2)

        zone = zones[0]
        self.assertEqual(zone.id, '1')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.driver, self.driver)
        self.assertEqual(zone.ttl, None)

        second_zone = zones[1]
        self.assertEqual(second_zone.id, '2')
        self.assertEqual(second_zone.domain, 'example.net')
        self.assertEqual(second_zone.type, None)
        self.assertEqual(second_zone.driver, self.driver)
        self.assertEqual(second_zone.ttl, None)

    def test_get_zone_zone_does_not_exist(self):
        LuadnsMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='13')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_get_zone_success(self):
        LuadnsMockHttp.type = 'GET_ZONE_SUCCESS'
        zone = self.driver.get_zone(zone_id='31')

        self.assertEqual(zone.id, '31')
        self.assertEqual(zone.domain, 'example.org')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)
        self.assertEqual(zone.driver, self.driver)

    def test_delete_zone_success(self):
        LuadnsMockHttp.type = 'DELETE_ZONE_SUCCESS'
        zone = self.test_zone
        status = self.driver.delete_zone(zone=zone)

        self.assertEqual(status, True)

    def test_delete_zone_zone_does_not_exist(self):
        LuadnsMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'
        zone = self.test_zone
        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, '11')
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        LuadnsMockHttp.type = 'CREATE_ZONE_SUCCESS'
        zone = self.driver.create_zone(domain='example.org')

        self.assertEqual(zone.id, '3')
        self.assertEqual(zone.domain, 'example.org')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)
        self.assertEqual(zone.driver, self.driver)

    def test_create_zone_zone_zone_already_exists(self):
        LuadnsMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'
        try:
            self.driver.create_zone(domain='test.com')
        except ZoneAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'test.com')
        else:
            self.fail('Exception was not thrown')

    def test_list_records_empty(self):
        LuadnsMockHttp.type = 'EMPTY_RECORDS_LIST'
        zone = self.test_zone
        records = self.driver.list_records(zone=zone)

        self.assertEqual(records, [])

    def test_list_records_success(self):
        LuadnsMockHttp.type = 'LIST_RECORDS_SUCCESS'
        zone = self.test_zone
        records = self.driver.list_records(zone=zone)

        self.assertEqual(len(records), 2)

        record = records[0]
        self.assertEqual(record.id, '6683')
        self.assertEqual(record.type, 'NS')
        self.assertEqual(record.name, 'example.org.')
        self.assertEqual(record.data, 'b.ns.luadns.net.')
        self.assertEqual(record.zone, self.test_zone)
        self.assertEqual(record.zone.id, '11')

        second_record = records[1]
        self.assertEqual(second_record.id, '6684')
        self.assertEqual(second_record.type, 'NS')
        self.assertEqual(second_record.name, 'example.org.')
        self.assertEqual(second_record.data, 'a.ns.luadns.net.')
        self.assertEqual(second_record.zone, self.test_zone)

    def test_get_record_record_does_not_exist(self):
        LuadnsMockHttp.type = 'GET_RECORD_RECORD_DOES_NOT_EXIST'
        try:
            self.driver.get_record(zone_id='31', record_id='31')
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '31')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_success(self):
        LuadnsMockHttp.type = 'GET_RECORD_SUCCESS'
        record = self.driver.get_record(zone_id='31', record_id='31')

        self.assertEqual(record.id, '31')
        self.assertEqual(record.type, 'MX')
        self.assertEqual(record.name, 'example.com.')
        self.assertEqual(record.data, '10 mail.example.com.')

    def test_delete_record_success(self):
        LuadnsMockHttp.type = 'DELETE_RECORD_SUCCESS'
        record = self.test_record
        status = self.driver.delete_record(record=record)

        self.assertEqual(status, True)

    def test_delete_record_RECORD_DOES_NOT_EXIST_ERROR(self):
        LuadnsMockHttp.type = 'DELETE_RECORD_RECORD_DOES_NOT_EXIST'
        record = self.test_record
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, '13')
        else:
            self.fail('Exception was not thrown')

    def test_create_record_success(self):
        LuadnsMockHttp.type = 'CREATE_RECORD_SUCCESS'
        record = self.driver.create_record(name='test.com.',
                                           zone=self.test_zone,
                                           type='A',
                                           data='127.0.0.1',
                                           extra={'ttl': 13})
        self.assertEqual(record.id, '31')
        self.assertEqual(record.name, 'test.com.')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.ttl, None)

    def test_record_already_exists_error(self):
        pass


class LuadnsMockHttp(MockHttp):
    fixtures = DNSFileFixtures('luadns')

    def _v1_zones(self, method, url, body, headers):
        body = self.fixtures.load('zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_EMPTY_ZONES_LIST(self, method, url, body,
                                   headers):
        body = self.fixtures.load('empty_zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_13_ZONE_DOES_NOT_EXIST(self, method, url,
                                         body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_31_GET_ZONE_SUCCESS(self, method, url,
                                      body, headers):
        body = self.fixtures.load('get_zone.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_DELETE_ZONE_SUCCESS(self, method, url,
                                         body, headers):
        body = self.fixtures.load('delete_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_DELETE_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_CREATE_ZONE_SUCCESS(self, method, url,
                                      body, headers):
        body = self.fixtures.load('create_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_CREATE_ZONE_ZONE_ALREADY_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_already_exists.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_records_EMPTY_RECORDS_LIST(self, method, url, body,
                                                headers):
        body = self.fixtures.load('empty_records_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_records_LIST_RECORDS_SUCCESS(self, method, url,
                                                  body, headers):
        body = self.fixtures.load('records_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_31_records_31_GET_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_31_GET_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):

        body = self.fixtures.load('get_zone.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_31_GET_RECORD_SUCCESS(self, method, url,
                                        body, headers):
        body = self.fixtures.load('get_zone.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_31_records_31_GET_RECORD_SUCCESS(self, method, url,
                                                   body, headers):
        body = self.fixtures.load('get_record.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_records_13_DELETE_RECORD_SUCCESS(self, method, url,
                                                      body, headers):
        body = self.fixtures.load('delete_record_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_records_13_DELETE_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_11_records_CREATE_RECORD_SUCCESS(self, method, url,
                                                   body, headers):
        body = self.fixtures.load('create_record_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]


if __name__ == '__main__':
    sys.exit(unittest.main())
