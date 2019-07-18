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

from libcloud.common.types import LibcloudError
from libcloud.test import unittest

from libcloud.dns.drivers.cloudflare import CloudFlareDNSDriver
from libcloud.dns.drivers.cloudflare import ZONE_EXTRA_ATTRIBUTES
from libcloud.dns.drivers.cloudflare import RECORD_EXTRA_ATTRIBUTES
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.utils.py3 import httplib, urlparse
from libcloud.test.secrets import DNS_PARAMS_CLOUDFLARE
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test import MockHttp


class CloudFlareDNSDriverTestCase(unittest.TestCase):

    def setUp(self):
        CloudFlareDNSDriver.connectionCls.conn_class = CloudFlareMockHttp
        CloudFlareDNSDriver.ZONES_PAGE_SIZE = 5
        CloudFlareDNSDriver.RECORDS_PAGE_SIZE = 5
        CloudFlareDNSDriver.MEMBERSHIPS_PAGE_SIZE = 5
        CloudFlareMockHttp.type = None
        CloudFlareMockHttp.use_param = 'a'
        self.driver = CloudFlareDNSDriver(*DNS_PARAMS_CLOUDFLARE)

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 9)
        self.assertTrue(RecordType.A in record_types)

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 1)

        zone = zones[0]
        self.assertEqual(zone.id, '1234')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.type, 'master')

        for attribute_name in ZONE_EXTRA_ATTRIBUTES:
            self.assertTrue(attribute_name in zone.extra)

    def test_get_record(self):
        record = self.driver.get_record('1234', '364797364')

        self.assertEqual(record.id, '364797364')
        self.assertIsNone(record.name)
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '192.30.252.153')

    def test_get_record_record_doesnt_exist(self):
        with self.assertRaises(RecordDoesNotExistError):
            self.driver.get_record('1234', '0000')

    def test_get_record_record_is_invalid(self):
        with self.assertRaises(LibcloudError):
            self.driver.get_record('1234', 'invalid')

    def test_list_records(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 9)

        record = records[0]
        self.assertEqual(record.id, '364797364')
        self.assertIsNone(record.name)
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '192.30.252.153')

        for attribute_name in RECORD_EXTRA_ATTRIBUTES:
            self.assertTrue(attribute_name in record.extra)

        record = records[4]
        self.assertEqual(record.id, '364982413')
        self.assertEqual(record.name, 'yesyes')
        self.assertEqual(record.type, 'CNAME')
        self.assertEqual(record.data, 'verify.bing.com')

        for attribute_name in RECORD_EXTRA_ATTRIBUTES:
            self.assertTrue(attribute_name in record.extra)

    def test_get_zone(self):
        zone = self.driver.get_zone(zone_id='1234')
        self.assertEqual(zone.id, '1234')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.type, 'master')

    def test_get_zone_zone_doesnt_exist(self):
        with self.assertRaises(ZoneDoesNotExistError):
            self.driver.get_zone('0000')

    def test_get_zone_zone_is_invalid(self):
        with self.assertRaises(LibcloudError):
            self.driver.get_zone('invalid')

    def test_create_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.create_record(name='test5', zone=zone,
                                           type=RecordType.A,
                                           data='127.0.0.3',
                                           extra={'proxied': True})
        self.assertEqual(record.id, '412561327')
        self.assertEqual(record.name, 'test5')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '127.0.0.3')

    def test_create_record_with_property_that_cant_be_set(self):
        zone = self.driver.list_zones()[0]

        record = self.driver.create_record(name='test5', zone=zone,
                                           type=RecordType.A,
                                           data='127.0.0.3',
                                           extra={'locked': True})

        self.assertNotEqual(record.extra['locked'], True)

    def test_update_record(self):
        zone = self.driver.list_zones()[0]
        record = zone.list_records()[0]
        updated_record = self.driver.update_record(record=record,
                                                   name='test6',
                                                   type=RecordType.A,
                                                   data='127.0.0.4',
                                                   extra={'proxied': True})

        self.assertEqual(updated_record.name, 'test6')
        self.assertEqual(updated_record.type, 'A')
        self.assertEqual(updated_record.data, '127.0.0.4')
        self.assertEqual(updated_record.extra['proxied'], True)

    def test_update_record_with_property_that_cant_be_updated(self):
        zone = self.driver.list_zones()[0]
        record = zone.list_records()[0]

        updated_record = self.driver.update_record(record=record,
                                                   data='127.0.0.4',
                                                   extra={'locked': True})

        self.assertNotEqual(updated_record.extra['locked'], True)

    def test_delete_record(self):
        zone = self.driver.list_zones()[0]
        record = zone.list_records()[0]
        result = self.driver.delete_record(record=record)
        self.assertTrue(result)

    def test_delete_zone(self):
        zone = self.driver.list_zones()[0]
        result = self.driver.delete_zone(zone=zone)
        self.assertTrue(result)

    def test_create_zone(self):
        zone = self.driver.create_zone(domain='example2.com',
                                       extra={'jump_start': False})
        self.assertEqual(zone.id, '6789')
        self.assertEqual(zone.domain, 'example2.com')

    def test_create_zone_with_explicit_account(self):
        zone = self.driver.create_zone(
            domain='example2.com',
            extra={'account': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'})
        self.assertEqual(zone.id, '6789')
        self.assertEqual(zone.domain, 'example2.com')

    def test_update_zone(self):
        zone = self.driver.list_zones()[0]

        updated_zone = self.driver.update_zone(zone=zone,
                                               domain='',
                                               extra={'paused': True})

        self.assertEqual(zone.id, updated_zone.id)
        self.assertEqual(zone.domain, updated_zone.domain)
        self.assertEqual(zone.type, updated_zone.type)
        self.assertEqual(zone.ttl, updated_zone.ttl)

        for key in set(zone.extra) | set(updated_zone.extra):
            if key in ('paused', 'modified_on'):
                self.assertNotEqual(zone.extra[key], updated_zone.extra[key])
            else:
                self.assertEqual(zone.extra[key], updated_zone.extra[key])

    def test_update_zone_with_property_that_cant_be_updated(self):
        zone = self.driver.list_zones()[0]

        updated_zone = self.driver.update_zone(zone, domain='',
                                               extra={'owner': 'owner'})

        self.assertEqual(zone, updated_zone)

    def test_update_zone_with_no_property(self):
        zone = self.driver.list_zones()[0]

        updated_zone = self.driver.update_zone(zone, domain='', extra=None)

        self.assertEqual(zone, updated_zone)

    def test_update_zone_with_more_than_one_property(self):
        zone = self.driver.list_zones()[0]

        updated_zone = self.driver.update_zone(
            zone, domain='', extra={'paused': True, 'plan': None})

        self.assertEqual(zone, updated_zone)


class CloudFlareMockHttp(MockHttp):
    fixtures = DNSFileFixtures('cloudflare')

    def _client_v4_memberships(self, method, url, body, headers):
        if method not in {'GET'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('memberships_{}.json'.format(method))

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _client_v4_zones(self, method, url, body, headers):
        if method not in {'GET', 'POST'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('zones_{}.json'.format(method))

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _client_v4_zones_1234(self, method, url, body, headers):
        if method not in {'GET', 'PATCH', 'DELETE'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('zone_{}.json'.format(method))

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _client_v4_zones_0000(self, method, url, body, headers):
        if method not in {'GET'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('zone_{}_404.json'.format(method))

        return (httplib.NOT_FOUND, body, {}, httplib.responses[httplib.NOT_FOUND])

    def _client_v4_zones_invalid(self, method, url, body, headers):
        if method not in {'GET'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('zone_{}_400.json'.format(method))

        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _client_v4_zones_1234_dns_records(self, method, url, body, headers):
        if method not in {'GET', 'POST'}:
            raise AssertionError('Unsupported method')

        url = urlparse.urlparse(url)
        if method == 'GET' and url.query:
            query = urlparse.parse_qs(url.query)
            page = query['page'][0]
            body = self.fixtures.load('records_{}_{}.json'.format(method, page))
        else:
            body = self.fixtures.load('records_{}.json'.format(method))

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _client_v4_zones_1234_dns_records_0000(self, method, url, body, headers):
        if method not in {'GET'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('record_{}_404.json'.format(method))

        return (httplib.NOT_FOUND, body, {}, httplib.responses[httplib.NOT_FOUND])

    def _client_v4_zones_1234_dns_records_invalid(self, method, url, body, headers):
        if method not in {'GET'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('record_{}_400.json'.format(method))

        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _client_v4_zones_1234_dns_records_364797364(self, method, url, body, headers):
        if method not in {'GET', 'PUT', 'DELETE'}:
            raise AssertionError('Unsupported method')

        body = self.fixtures.load('record_{}.json'.format(method))

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
