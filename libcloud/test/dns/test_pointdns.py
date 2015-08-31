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

from libcloud.dns.types import RecordType
from libcloud.dns.drivers.pointdns import PointDNSDriver

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_POINTDNS


class PointDNSTests(unittest.TestCase):
    def setUp(self):
        PointDNSDriver.connectionCls.conn_classes = (
            None, PointDNSMockHttp)
        PointDNSMockHttp.type = None
        self.driver = PointDNSDriver(*DNS_PARAMS_POINTDNS)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 10)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.AAAA in record_types)
        self.assertTrue(RecordType.ALIAS in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.NS in record_types)
        self.assertTrue(RecordType.PTR in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.SSHFP in record_types)
        self.assertTrue(RecordType.TXT in record_types)

    def test_list_zones_success(self):
        PointDNSMockHttp.type = 'GET'
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

        zone1 = zones[0]
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['group', 'user-id'])

        zone2 = zones[1]
        self.assertEqual(zone2.id, '2')
        self.assertEqual(zone2.type, 'master')
        self.assertEqual(zone2.domain, 'example2.com')
        self.assertEqual(zone2.ttl, 3600)
        self.assertHasKeys(zone2.extra, ['group', 'user-id'])

    def test_list_records_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)

        record1 = records[0]
        self.assertEqual(record1.id, '141')
        self.assertEqual(record1.name, 'site.example.com')
        self.assertEqual(record1.type, RecordType.A)
        self.assertEqual(record1.data, '1.2.3.4')
        self.assertHasKeys(record1.extra, ['ttl', 'zone_id', 'aux'])

        record2 = records[1]
        self.assertEqual(record2.id, '150')
        self.assertEqual(record2.name, 'site.example1.com')
        self.assertEqual(record2.type, RecordType.A)
        self.assertEqual(record2.data, '1.2.3.6')
        self.assertHasKeys(record2.extra, ['ttl', 'zone_id', 'aux'])

    def test_get_zone_success(self):
        PointDNSMockHttp.type = 'GET'
        zone1 = self.driver.get_zone(zone_id='1')
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['group', 'user-id'])

    def test_get_record_success(self):
        PointDNSMockHttp.type = 'GET'
        record = self.driver.get_record(zone_id='1',
                                        record_id='141')
        self.assertEqual(record.id, '141')
        self.assertEqual(record.name, 'site.example.com')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertHasKeys(record.extra, ['ttl', 'zone_id', 'aux'])

    def test_create_zone_success(self):
        PointDNSMockHttp.type = 'CREATE'
        zone = self.driver.create_zone(domain='example.com')
        self.assertEqual(zone.id, '2')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, 3600)
        self.assertEqual(zone.type, 'master')
        self.assertHasKeys(zone.extra, ['group', 'user-id'])

    def test_create_record_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE'
        record = self.driver.create_record(name='site.example.com', zone=zone,
                                           type=RecordType.A,
                                           data='1.2.3.4')
        self.assertEqual(record.id, '143')
        self.assertEqual(record.name, 'site.example.com')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertHasKeys(record.extra, ['ttl', 'zone_id', 'aux'])

    def test_update_record_success(self):
        PointDNSMockHttp.type = 'GET'
        record = self.driver.get_record(zone_id='1',
                                        record_id='141')
        PointDNSMockHttp.type = 'UPDATE'
        extra = {'ttl': 4500}
        record1 = self.driver.update_record(record=record, name='updated.com',
                                            type=RecordType.A, data='1.2.3.5',
                                            extra=extra)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertEqual(record.extra.get('ttl'), 3600)
        self.assertEqual(record1.data, '1.2.3.5')
        self.assertEqual(record1.extra.get('ttl'), 4500)

    def test_delete_zone_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_record_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)
        record = records[1]
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)


class PointDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('pointdns')

    def _zones_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_GET_1.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_example_com_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_example_com_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_example_com_records_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_141_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_141_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_141_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_141_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_150_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_150_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
