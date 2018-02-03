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


class PowerDNSTestCase(LibcloudTestCase):

    def setUp(self):
        PowerDNSDriver.connectionCls.conn_class = PowerDNSMockHttp
        PowerDNSMockHttp.type = None
        self.driver = PowerDNSDriver('testsecret')

        self.test_zone = Zone(id='example.com.', domain='example.com',
                              driver=self.driver, type='master', ttl=None,
                              extra={})
        self.test_record = Record(id=None, name='', data='192.0.2.1',
                                  type=RecordType.A, zone=self.test_zone,
                                  driver=self.driver, extra={})

    def test_create_record(self):
        record = self.test_zone.create_record(name='newrecord.example.com',
                                              type=RecordType.A,
                                              data='192.0.5.4',
                                              extra={'ttl': 86400})
        self.assertEqual(record.id, None)
        self.assertEqual(record.name, 'newrecord.example.com')
        self.assertEqual(record.data, '192.0.5.4')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 86400)

    def test_create_zone(self):
        extra = {'nameservers': ['ns1.example.org', 'ns2.example.org']}
        zone = self.driver.create_zone('example.org', extra=extra)
        self.assertEqual(zone.id, 'example.org.')
        self.assertEqual(zone.domain, 'example.org')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)

    def test_delete_record(self):
        self.assertTrue(self.test_record.delete())

    def test_delete_zone(self):
        self.assertTrue(self.test_zone.delete())

    def test_get_record(self):
        with self.assertRaises(NotImplementedError):
            self.driver.get_record('example.com.', '12345')

    def test_get_zone(self):
        zone = self.driver.get_zone('example.com.')
        self.assertEqual(zone.id, 'example.com.')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.type, None)
        self.assertEqual(zone.ttl, None)

    def test_list_record_types(self):
        result = self.driver.list_record_types()
        self.assertEqual(len(result), 23)

    def test_list_records(self):
        records = self.driver.list_records(self.test_zone)
        self.assertEqual(len(records), 4)

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(zones[0].id, 'example.com.')
        self.assertEqual(zones[0].domain, 'example.com')
        self.assertEqual(zones[0].type, None)
        self.assertEqual(zones[0].ttl, None)
        self.assertEqual(zones[1].id, 'example.net.')
        self.assertEqual(zones[1].domain, 'example.net')
        self.assertEqual(zones[1].type, None)
        self.assertEqual(zones[1].ttl, None)

    def test_update_record(self):
        record = self.driver.update_record(self.test_record,
                                           name='newrecord.example.com',
                                           type=RecordType.A,
                                           data='127.0.0.1',
                                           extra={'ttl': 300})
        self.assertEqual(record.id, None)
        self.assertEqual(record.name, 'newrecord.example.com')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 300)

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
