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
from libcloud.dns.types import RecordType, ZoneDoesNotExistError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.drivers.gandi_live import GandiLiveDNSDriver
from libcloud.dns.base import Zone, Record
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_GANDI_LIVE
from libcloud.test.common.test_gandi_live import BaseGandiLiveMockHttp


class GandiLiveTests(unittest.TestCase):

    def setUp(self):
        GandiLiveDNSDriver.connectionCls.conn_class = GandiLiveMockHttp
        GandiLiveMockHttp.type = None
        self.driver = GandiLiveDNSDriver(*DNS_GANDI_LIVE)
        self.test_zone = Zone(id='example.com', type='master', ttl=None,
                              domain='example.com', extra={}, driver=self)
        self.test_record = Record(id='A:bob', type=RecordType.A,
                                  name='bob', zone=self.test_zone,
                                  data='127.0.0.1', driver=self, extra={})

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)
        zone = zones[0]
        self.assertEqual(zone.id, 'example.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'example.com')
        self.assertIsNone(zone.ttl)
        zone = zones[1]
        self.assertEqual(zone.id, 'example.net')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'example.net')
        self.assertIsNone(zone.ttl)

    def test_create_zone(self):
        zone = self.driver.create_zone('example.org',
                                       extra={'name': 'Example'})
        self.assertEqual(zone.id, 'example.org')
        self.assertEqual(zone.domain, 'example.org')

    def test_get_zone(self):
        zone = self.test_zone
        self.assertEqual(zone.id, 'example.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'example.com')
        self.assertIsNone(zone.ttl)

    def test_update_zone(self):
        zone = self.test_zone
        self.driver.update_zone(zone, extra={'zone_uuid': 12346})
        self.assertEqual(zone.id, 'example.com')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'example.com')
        self.assertIsNone(zone.ttl)

    def test_update_zone_noop(self):
        zone = self.test_zone
        updated_zone = self.driver.update_zone(zone, domain='dontmatter.com')
        self.assertIsNone(updated_zone)

    def test_delete_zone(self):
        pass

    def test_list_records(self):
        records = self.driver.list_records(self.test_zone)
        self.assertEqual(len(records), 3)
        record = records[0]
        self.assertEqual(record.id, 'A:@')
        self.assertEqual(record.name, '@')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, ['127.0.0.1'])
        record = records[1]
        self.assertEqual(record.id, 'CNAME:www')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.CNAME)
        self.assertEqual(record.data, ['bob.example.com.'])
        record = records[2]
        self.assertEqual(record.id, 'A:bob')
        self.assertEqual(record.name, 'bob')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, ['127.0.1.1'])

    def test_get_record(self):
        record = self.driver.get_record(self.test_zone.id, 'A:bob')
        self.assertEqual(record.id, 'A:bob')
        self.assertEqual(record.name, 'bob')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, ['127.0.1.1'])

    def test_create_record(self):
        record = self.driver.create_record('alice', self.test_zone, 'AAAA',
                                           '::1',
                                           extra={'ttl': 100})
        self.assertEqual(record.id, 'AAAA:alice')
        self.assertEqual(record.name, 'alice')
        self.assertEqual(record.type, RecordType.AAAA)
        self.assertEqual(record.data, ['::1'])

    def test_update_record(self):
        record = self.driver.update_record(self.test_record, 'bob',
                                           RecordType.A, '192.168.0.2',
                                           {'ttl': 200})
        self.assertEqual(record.id, 'A:bob')
        self.assertEqual(record.name, 'bob')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, ['192.168.0.2'])

    def test_delete_record(self):
        success = self.driver.delete_record(self.test_record)
        self.assertTrue(success)

    def test_export_bind(self):
        bind_export = self.driver.export_zone_to_bind_format(self.test_zone)
        bind_lines = bind_export.decode('utf8').split('\n')
        self.assertEqual(bind_lines[0], '@ 10800 IN A 127.0.0.1')


class GandiLiveMockHttp(BaseGandiLiveMockHttp):
    fixtures = DNSFileFixtures('gandi_live')

    def _json_domains_get(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_domains_example_com_get(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_zones_post(self, method, url, body, headers):
        body = self.fixtures.load('create_zone.json')
        return (httplib.OK, body, {'Location': '/zones/54321'},
                httplib.responses[httplib.OK])

    def _json_domains_post(self, method, url, body, headers):
        body = self.fixtures.load('create_domain.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_domains_example_com_patch(self, method, url, body, headers):
        body = self.fixtures.load('update_zone.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_domains_example_com_records_get(self, method, url, body,
                                              headers):
        body = self.fixtures.load('list_records.json')
        if headers is not None and 'Accept' in headers:
            if headers['Accept'] == 'text/plain':
                body = self.fixtures.load('list_records_bind.txt')
        return (httplib.OK, body, {'Content-Type': 'text/plain'},
                httplib.responses[httplib.OK])

    def _json_domains_example_com_records_bob_A_get(self, method, url,
                                                    body, headers):
        body = self.fixtures.load('get_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_domains_example_com_records_post(self, method, url, body,
                                               headers):
        body = self.fixtures.load('create_record.json')
        return (httplib.OK, body,
                {'Location': '/zones/12345/records/alice/AAAA'},
                httplib.responses[httplib.OK])

    def _json_domains_example_com_records_bob_A_put(self, method, url,
                                                    body, headers):
        body = self.fixtures.load('update_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_domains_example_com_records_bob_A_delete(self, method, url,
                                                       body, headers):
        body = self.fixtures.load('delete_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
