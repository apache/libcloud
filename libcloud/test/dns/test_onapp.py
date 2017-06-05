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

from libcloud.dns.drivers.onapp import OnAppDNSDriver
from libcloud.dns.types import RecordType
from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_ONAPP
from libcloud.utils.py3 import httplib
from libcloud.common.exceptions import BaseHTTPError


class OnAppDNSTests(LibcloudTestCase):

    def setUp(self):
        OnAppDNSDriver.connectionCls.conn_class = OnAppDNSMockHttp
        OnAppDNSMockHttp.type = None
        self.driver = OnAppDNSDriver(*DNS_PARAMS_ONAPP)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 8)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.AAAA in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.NS in record_types)
        self.assertTrue(RecordType.SOA in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.TXT in record_types)

    def test_list_zones_success(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

        zone1 = zones[0]
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 1200)
        self.assertHasKeys(zone1.extra, ['user_id', 'cdn_reference',
                                         'created_at', 'updated_at'])

        zone2 = zones[1]
        self.assertEqual(zone2.id, '2')
        self.assertEqual(zone2.type, 'master')
        self.assertEqual(zone2.domain, 'example.net')
        self.assertEqual(zone2.ttl, 1200)
        self.assertHasKeys(zone2.extra, ['user_id', 'cdn_reference',
                                         'created_at', 'updated_at'])

    def test_get_zone_success(self):
        zone1 = self.driver.get_zone(zone_id='1')
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 1200)
        self.assertHasKeys(zone1.extra, ['user_id', 'cdn_reference',
                                         'created_at', 'updated_at'])

    def test_get_zone_not_found(self):
        OnAppDNSMockHttp.type = 'NOT_FOUND'
        try:
            self.driver.get_zone(zone_id='3')
        except BaseHTTPError:
            self.assertRaises(Exception)

    def test_create_zone_success(self):
        OnAppDNSMockHttp.type = 'CREATE'
        zone = self.driver.create_zone(domain='example.com')
        self.assertEqual(zone.id, '1')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, 1200)
        self.assertEqual(zone.type, 'master')
        self.assertHasKeys(zone.extra, ['user_id', 'cdn_reference',
                                        'created_at', 'updated_at'])

    def test_delete_zone(self):
        zone = self.driver.get_zone(zone_id='1')
        OnAppDNSMockHttp.type = 'DELETE'
        self.assertTrue(self.driver.delete_zone(zone))

    def test_list_records_success(self):
        zone = self.driver.get_zone(zone_id='1')
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 5)

        record1 = records[0]
        self.assertEqual(record1.id, '111222')
        self.assertEqual(record1.name, '@')
        self.assertEqual(record1.type, RecordType.A)
        self.assertEqual(record1.ttl, 3600)
        self.assertEqual(record1.data['ip'], '123.156.189.1')

        record2 = records[2]
        self.assertEqual(record2.id, '111224')
        self.assertEqual(record2.name, 'mail')
        self.assertEqual(record1.ttl, 3600)
        self.assertEqual(record2.type, RecordType.CNAME)
        self.assertEqual(record2.data['hostname'], 'examplemail.com')

        record3 = records[4]
        self.assertEqual(record3.id, '111226')
        self.assertEqual(record3.name, '@')
        self.assertEqual(record3.type, RecordType.MX)
        self.assertEqual(record3.data['hostname'], 'mx2.examplemail.com')

    def test_get_record_success(self):
        record = self.driver.get_record(zone_id='1',
                                        record_id='123')
        self.assertEqual(record.id, '123')
        self.assertEqual(record.name, '@')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data['ip'], '123.156.189.1')

    def test_create_record_success(self):
        zone = self.driver.get_zone(zone_id='1')
        OnAppDNSMockHttp.type = 'CREATE'
        record = self.driver.create_record(name='blog', zone=zone,
                                           type=RecordType.A,
                                           data='123.156.189.2')
        self.assertEqual(record.id, '111227')
        self.assertEqual(record.name, 'blog')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data['ip'], '123.156.189.2')
        self.assertEqual(record.data['ttl'], 3600)

    def test_update_record_success(self):
        record = self.driver.get_record(zone_id='1',
                                        record_id='123')
        OnAppDNSMockHttp.type = 'UPDATE'
        extra = {'ttl': 4500}
        record1 = self.driver.update_record(record=record, name='@',
                                            type=record.type,
                                            data='123.156.189.2',
                                            extra=extra)
        self.assertEqual(record.data['ip'], '123.156.189.1')
        self.assertEqual(record.ttl, 3600)
        self.assertEqual(record1.data['ip'], '123.156.189.2')
        self.assertEqual(record1.ttl, 4500)

    def test_delete_record_success(self):
        record = self.driver.get_record(zone_id='1',
                                        record_id='123')
        OnAppDNSMockHttp.type = 'DELETE'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)


class OnAppDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('onapp')

    def _dns_zones_json(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_json(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_3_json_NOT_FOUND(self, method, url, body, headers):
        body = self.fixtures.load('dns_zone_not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _dns_zones_json_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_json_DELETE(self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {},
                httplib.responses[httplib.NO_CONTENT])

    def _dns_zones_1_records_json(self, method, url, body, headers):
        body = self.fixtures.load('list_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_records_123_json(self, method, url, body, headers):
        body = self.fixtures.load('get_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_records_json_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_records_123_json_UPDATE(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('get_record_after_update.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            return (httplib.NO_CONTENT, '', {},
                    httplib.responses[httplib.NO_CONTENT])

    def _dns_zones_1_json_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dns_zones_1_records_123_json_DELETE(self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {},
                httplib.responses[httplib.NO_CONTENT])


if __name__ == '__main__':
    sys.exit(unittest.main())
