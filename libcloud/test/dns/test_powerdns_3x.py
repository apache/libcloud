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
import json

from libcloud.utils.py3 import httplib

from libcloud.dns.base import Record, Zone
from libcloud.dns.drivers.powerdns import PowerDNSDriver
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordType

from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_POWERDNS_3X

class PowerDNSTestCase(LibcloudTestCase):

    def setUp(self):
        #PowerDNSDriver.connectionCls.conn_classes = (PowerDNSMockHttp,
        #                                             PowerDNSMockHttp)
        #PowerDNSMockHttp.type = None
        self.driver = PowerDNSDriver(*DNS_PARAMS_POWERDNS_3X)

        self.test_zone = Zone(id='example.com.', domain='example.com',
                              driver=self.driver, type='master', ttl=None,
                              extra={})
        self.test_record = Record(id=None, name='', data='192.0.2.1',
                                  type=RecordType.A, zone=self.test_zone,
                                  driver=self.driver, extra={})

    def test_10_create_zone(self):
        extra = {'nameservers': ['ns1.example.com', 'ns2.example.com']}
        zone = self.driver.create_zone('example.com', extra=extra)
        self.assertEqual(zone.id, 'example.com.')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)

    def test_20_create_zone_record(self):
        record = self.test_zone.create_record(name='example.com',
                                              type=RecordType.A,
                                              data='127.0.0.1',
                                              extra={'ttl': 86400})
        self.assertEqual(record.name, 'example.com')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 86400)

    def test_21_create_record(self):
        record = self.test_zone.create_record(name='newrecord.example.com',
                                              type=RecordType.A,
                                              data='192.0.5.4',
                                              extra={'ttl': 86400})
        self.assertEqual(record.name, 'newrecord.example.com')
        self.assertEqual(record.data, '192.0.5.4')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 86400)

    def test_30_create_sameid_record(self):
        record = self.test_zone.create_record(name='newrecord.example.com',
                                              type=RecordType.A,
                                              data='192.0.5.10',
                                              extra={'ttl': 86400})
        self.assertEqual(record.name, 'newrecord.example.com')
        self.assertEqual(record.data, '192.0.5.10')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 86400)

    def test_30_udpate_zone_record(self):
        records = self.test_zone.list_records()
        record = None
        for r in records:
            if r.id == "A:example.com":
                record = r
        self.assertEqual(record.data, '127.0.0.1')

        new_record = record.update(name=record.name, type=record.type,
            data='127.0.0.2', extra=record.extra)
        self.assertEqual(new_record.data, '127.0.0.2')

    def test_40_update_sameid_record(self):
        records = []
        for r in self.test_zone.list_records():
            if r.id == "A:newrecord.example.com":
                records.append(r)

        record = records[0]
        self.assertEqual(record.id, "A:newrecord.example.com")

        new_record = record.update(name=record.name, type=record.type,
            data='192.0.5.100', extra=record.extra)
        self.assertEqual(new_record.data, '192.0.5.100')

    def test_41_create_multiple_mx_record(self):
        record1 = self.test_zone.create_record(name='example.com',
                                              type=RecordType.MX,
                                              data='newrecord.example.com',
                                              extra={'ttl': 86400, 'priority':10})
        record2 = self.test_zone.create_record(name='example.com',
                                              type=RecordType.MX,
                                              data='newrecord1.example.com',
                                              extra={'ttl': 86400, 'priority':20})
        record3 = self.test_zone.create_record(name='example.com',
                                              type=RecordType.MX,
                                              data='newrecord2.example.com',
                                              extra={'ttl': 86400, 'priority':30})
        self.assertEqual(record1.name, 'example.com')
        self.assertEqual(record1.data, 'newrecord.example.com')
        self.assertEqual(record1.type, RecordType.MX)
        self.assertEqual(record1.ttl, 86400)
        self.assertEqual(record1.extra['priority'], 10)

    def test_42_update_mx_record(self):
        records = self.test_zone.list_records()
        records = self.driver.ex_filter_records(records,
                        id='MX:example.com', extra__priority=10)
        self.assertEqual(len(records), 1)
        record = records[0]

        new_record = record.update(name=record.name, data=record.data, type=record.type,
            extra={'priority':100})
        self.assertEqual(new_record.extra['priority'], 100)

    def test_40_get_record(self):
        record_id = 'NS:example.com'
        record = self.driver.ex_get_record('example.com', record_id)
        self.assertEqual(record.id, record_id)

    def test_40_get_zone(self):
        zone = self.driver.get_zone('example.com')
        self.assertEqual(zone.id, 'example.com.')

    def test_50_delete_sameid_record(self):
        records = []
        for r in self.test_zone.list_records():
            if r.id == "A:newrecord.example.com":
                records.append(r)

        self.assertEqual(len(records), 2)
        record = records[0]
        self.assertEqual(record.id, "A:newrecord.example.com")

        result = record.delete()
        self.assertEqual(result, True)

    def test_51_delete_record(self):
        records = []
        for r in self.test_zone.list_records():
            if r.id == "A:newrecord.example.com":
                records.append(r)

        record = records[0]
        self.assertEqual(len(records), 1)
        self.assertEqual(record.id, "A:newrecord.example.com")

        result = record.delete()
        self.assertEqual(result, True)

    def test_60_delete_zone(self):
        result = self.test_zone.delete()
        self.assertEqual(result, True)



"""
    def test_update_zone(self):
        with self.assertRaises(NotImplementedError):
            self.driver.update_zone(self.test_zone, 'example.net')

    # Test some error conditions

    def test_create_existing_zone(self):
        PowerDNSMockHttp.type = 'EXISTS'
        extra = {'nameservers': ['ns1.example.com', 'ns2.example.com']}
        with self.assertRaises(ZoneAlreadyExistsError):
            self.driver.create_zone('example.com', extra=extra)

    def test_get_missing_zone(self):
        PowerDNSMockHttp.type = 'MISSING'
        with self.assertRaises(ZoneDoesNotExistError):
            self.driver.get_zone('example.com.')

    def test_delete_missing_record(self):
        PowerDNSMockHttp.type = 'MISSING'
        self.assertFalse(self.test_record.delete())

    def test_delete_missing_zone(self):
        PowerDNSMockHttp.type = 'MISSING'
        self.assertFalse(self.test_zone.delete())

"""

class PowerDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('powerdns')
    base_headers = {'content-type': 'application/json'}

    def _servers_localhost_zones(self, method, url, body, headers):
        if method == 'GET':
            # list_zones()
            body = self.fixtures.load('list_zones.json')
        elif method == 'POST':
            # create_zone()
            # Don't bother with a fixture for this operation, because we do
            # nothing with the parsed body anyway.
            body = ''
        else:
            raise NotImplementedError('Unexpected method: %s' % method)
        return (httplib.OK, body, self.base_headers,
                httplib.responses[httplib.OK])

    def _servers_localhost_zones_example_com_(self, method, *args, **kwargs):
        if method == 'GET':
            # list_records()
            body = self.fixtures.load('list_records.json')
        elif method == 'PATCH':
            # create/update/delete_record()
            # Don't bother with a fixture for these operations, because we do
            # nothing with the parsed body anyway.
            body = ''
        elif method == 'DELETE':
            # delete_zone()
            return (httplib.NO_CONTENT, '', self.base_headers,
                    httplib.responses[httplib.NO_CONTENT])
        else:
            raise NotImplementedError('Unexpected method: %s' % method)
        return (httplib.OK, body, self.base_headers,
                httplib.responses[httplib.OK])

    def _servers_localhost_zones_EXISTS(self, method, url, body, headers):
        # create_zone() is a POST. Raise on all other operations to be safe.
        if method != 'POST':
            raise NotImplementedError('Unexpected method: %s' % method)
        payload = json.loads(body)
        domain = payload['name']
        body = json.dumps({'error': "Domain '%s' already exists" % domain})
        return (httplib.UNPROCESSABLE_ENTITY, body, self.base_headers,
                'Unprocessable Entity')

    def _servers_localhost_zones_example_com__MISSING(self, *args, **kwargs):
        return (httplib.UNPROCESSABLE_ENTITY, 'Could not find domain',
                self.base_headers, 'Unprocessable Entity')


if __name__ == '__main__':
    sys.exit(unittest.main())
