import sys
import unittest

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_NSONE
from libcloud.dns.drivers.nsone import NsOneDNSDriver
from libcloud.utils.py3 import httplib
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError,\
    RecordDoesNotExistError, RecordType
from libcloud.dns.base import Zone, Record


class NsOneTests(unittest.TestCase):
    def setUp(self):
        NsOneMockHttp.type = None
        NsOneDNSDriver.connectionCls.conn_classes = (None, NsOneMockHttp)
        self.driver = NsOneDNSDriver(*DNS_PARAMS_NSONE)
        self.test_zone = Zone(id='test.com', type='master', ttl=None,
                              domain='test.com', extra={}, driver=self)
        self.test_record = Record(id='13', type=RecordType.A,
                                  name='example.com', zone=self.test_zone,
                                  data='127.0.0.1', driver=self, extra={})

    def test_list_zones_empty(self):
        NsOneMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()

        self.assertEqual(len(zones), 2)

        zone = zones[0]
        self.assertEqual(zone.id, '520422af9f782d37dffb588b')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, 3600)

        zone = zones[1]
        self.assertEqual(zone.id, '520422c99f782d37dffb5892')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.domain, 'nsoneisgreat.com')
        self.assertEqual(zone.ttl, 3600)

    def test_delete_zone_zone_does_not_exist(self):
        NsOneMockHttp.type = 'DELETE_ZONE_ZONE_DOES_NOT_EXIST'

        try:
            self.driver.delete_zone(zone=self.test_zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_delete_zone_success(self):
        NsOneMockHttp.type = 'DELETE_ZONE_SUCCESS'
        status = self.driver.delete_zone(zone=self.test_zone)

        self.assertTrue(status)

    def test_get_zone_zone_does_not_exist(self):
        NsOneMockHttp.type = 'GET_ZONE_ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='zonedoesnotexist.com')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'zonedoesnotexist.com')
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        NsOneMockHttp.type = 'CREATE_ZONE_SUCCESS'
        zone = self.driver.create_zone(domain='newzone.com')

        self.assertEqual(zone.id, '52051b2c9f782d58bb4df41b')
        self.assertEqual(zone.domain, 'newzone.com')
        self.assertEqual(zone.type, None),
        self.assertEqual(zone.ttl, 3600)

    def test_create_zone_zone_already_exists(self):
        NsOneMockHttp.type = 'CREATE_ZONE_ZONE_ALREADY_EXISTS'

        try:
            self.driver.create_zone(domain='newzone.com')
        except ZoneAlreadyExistsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'newzone.com')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_record_does_not_exist(self):
        NsOneMockHttp.type = 'GET_RECORD_DOES_NOT_EXIST'

        try:
            self.driver.get_record(zone_id='getrecord.com', record_id='A')
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, 'A')
        else:
            self.fail('Exception was not thrown')

    def test_get_record_success(self):
        NsOneMockHttp.type = 'GET_RECORD_SUCCESS'
        record = self.driver.get_record(zone_id='getrecord.com', record_id='A')

        self.assertEqual(record.id, '520519509f782d58bb4df419')
        self.assertEqual(record.name, 'www.example.com')
        self.assertEqual(record.data, ['1.1.1.1'])
        self.assertEqual(record.type, RecordType.A)

    def test_list_records_zone_does_not_exist(self):
        NsOneMockHttp.type = 'LIST_RECORDS_ZONE_DOES_NOT_EXIST'

        try:
            self.driver.list_records(zone=self.test_zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_list_records_empty(self):
        NsOneMockHttp.type = 'LIST_RECORDS_EMPTY'
        records = self.driver.list_records(zone=self.test_zone)

        self.assertEqual(records, [])

    def test_list_records_success(self):
        NsOneMockHttp.type = 'LIST_RECORDS_SUCCESS'
        records = self.driver.list_records(zone=self.test_zone)
        self.assertEqual(len(records), 2)

        arecord = records[1]
        self.assertEqual(arecord.id, '520519509f782d58bb4df419')
        self.assertEqual(arecord.name, 'www.example.com')
        self.assertEqual(arecord.type, RecordType.A)
        self.assertEqual(arecord.data, ['1.2.3.4'])

    def test_delete_record_record_does_not_exist(self):
        NsOneMockHttp.type = 'DELETE_RECORD_RECORD_DOES_NOT_EXIST'

        try:
            self.driver.delete_record(record=self.test_record)
        except RecordDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.record_id, self.test_record.id)
        else:
            self.fail('Exception was not thrown')

    def test_delete_record_success(self):
        NsOneMockHttp.type = 'DELETE_RECORD_SUCCESS'
        status = self.driver.delete_record(record=self.test_record)

        self.assertTrue(status)


class NsOneMockHttp(MockHttp):
    fixtures = DNSFileFixtures('nsone')

    def _v1_zones_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_getzone_com_GET_ZONE_SUCCESS(self, method, url, body,
                                               headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_zonedoesnotexist_com_GET_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return 404, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_DELETE_ZONE_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('delete_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_DELETE_ZONE_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_newzone_com_CREATE_ZONE_SUCCESS(self, method,
                                                  url, body, headers):
        body = self.fixtures.load('create_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_newzone_com_CREATE_ZONE_ZONE_ALREADY_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_already_exists.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_LIST_RECORDS_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_LIST_RECORDS_EMPTY(
            self, method, url, body, headers):
        body = self.fixtures.load('list_records_empty.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_LIST_RECORDS_ZONE_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('zone_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_example_com_A_DELETE_RECORD_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')

        return 404, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_example_com_A_DELETE_RECORD_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('delete_record_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_getrecord_com_getrecord_com_A_GET_RECORD_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('get_record_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_getrecord_com_GET_RECORD_SUCCESS(
            self, method, url, body, headers):
        body = self.fixtures.load('get_zone_success.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_getrecord_com_getrecord_com_A_GET_RECORD_DOES_NOT_EXIST(
            self, method, url, body, headers):
        body = self.fixtures.load('record_does_not_exist.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

if __name__ == '__main__':
    sys.exit(unittest.main())
