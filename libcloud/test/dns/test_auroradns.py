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
import json

from libcloud.dns.drivers.auroradns import AuroraDNSDriver
from libcloud.dns.drivers.auroradns import AuroraDNSHealthCheckType
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.base import Zone
from libcloud.test import LibcloudTestCase
from libcloud.test import MockHttpTestCase
from libcloud.test import unittest
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_AURORADNS
from libcloud.utils.py3 import httplib


class AuroraDNSDriverTests(LibcloudTestCase):

    def setUp(self):
        AuroraDNSDriver.connectionCls.conn_classes = (None,
                                                      AuroraDNSDriverMockHttp)
        AuroraDNSDriverMockHttp.type = None
        self.driver = AuroraDNSDriver(*DNS_PARAMS_AURORADNS)

    def test_merge_extra_data(self):
        rdata = {
            'name': 'localhost',
            'type': RecordType.A,
            'content': '127.0.0.1'
        }

        params = {'ttl': 900,
                  'prio': 0,
                  'health_check_id': None,
                  'disabled': False}

        for param in params:
            extra = {
                param: params[param]
            }

            data = self.driver._AuroraDNSDriver__merge_extra_data(rdata, extra)
            self.assertEqual(data['content'], '127.0.0.1')
            self.assertEqual(data['type'], RecordType.A)
            self.assertEqual(data[param], params[param])
            self.assertEqual(data['name'], 'localhost')

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

    def test_create_zone(self):
        zone = self.driver.create_zone('example.com')
        self.assertEquals(zone.domain, 'example.com')

    def test_get_zone(self):
        zone = self.driver.get_zone('example.com')
        self.assertEquals(zone.domain, 'example.com')
        self.assertEquals(zone.id, 'ffb62570-8414-4578-a346-526b44e320b7')

    def test_delete_zone(self):
        zone = self.driver.get_zone('example.com')
        self.assertTrue(self.driver.delete_zone(zone))

    def test_create_record(self):
        zone = self.driver.get_zone('example.com')
        record = zone.create_record(name='localhost',
                                    type=RecordType.A,
                                    data='127.0.0.1',
                                    extra={'ttl': 900})
        self.assertEquals(record.id, '5592f1ff')
        self.assertEquals(record.name, 'localhost')
        self.assertEquals(record.data, '127.0.0.1')
        self.assertEquals(record.type, RecordType.A)
        self.assertEquals(record.extra['ttl'], 900)

    def test_get_record(self):
        zone = self.driver.get_zone('example.com')
        record = self.driver.get_record(zone.id, '5592f1ff')
        self.assertEquals(record.id, '5592f1ff')
        self.assertEquals(record.name, 'localhost')
        self.assertEquals(record.data, '127.0.0.1')
        self.assertEquals(record.type, RecordType.A)
        self.assertEquals(record.extra['ttl'], 900)
        self.assertEquals(record.extra['prio'], None)

    def test_update_record(self):
        ttl = 900
        zone = self.driver.get_zone('example.com')
        record = self.driver.get_record(zone.id, '5592f1ff')
        record = record.update(extra={'ttl': ttl})
        self.assertEquals(record.extra['ttl'], ttl)

    def test_delete_record(self):
        zone = self.driver.get_zone('example.com')
        record = self.driver.get_record(zone.id, '5592f1ff')
        self.assertTrue(record.delete())

    def test_list_records(self):
        zone = self.driver.get_zone('example.com')
        for record in zone.list_records():
            self.assertEqual(record.extra['ttl'], 3600)
            self.assertEqual(record.extra['disabled'], False)

    def test_get_zone_non_exist(self):
        try:
            self.driver.get_zone('nonexists.example.com')
            self.fail('expected a ZoneDoesNotExistError')
        except ZoneDoesNotExistError:
            pass
        except:
            raise

    def test_delete_zone_non_exist(self):
        try:
            self.driver.delete_zone(Zone(id=1, domain='nonexists.example.com',
                                         type='NATIVE', driver=AuroraDNSDriver,
                                         ttl=3600))
            self.fail('expected a ZoneDoesNotExistError')
        except ZoneDoesNotExistError:
            pass
        except:
            raise

    def test_create_zone_already_exist(self):
        try:
            self.driver.create_zone('exists.example.com')
            self.fail('expected a ZoneAlreadyExistsError')
        except ZoneAlreadyExistsError:
            pass
        except:
            raise

    def test_list_records_non_exist(self):
        try:
            self.driver.list_records(Zone(id=1, domain='nonexists.example.com',
                                          type='NATIVE', driver=AuroraDNSDriver,
                                          ttl=3600))
            self.fail('expected a ZoneDoesNotExistError')
        except ZoneDoesNotExistError:
            pass
        except:
            raise

    def test_get_record_non_exist(self):
        try:
            self.driver.get_record(1, 1)
            self.fail('expected a RecordDoesNotExistError')
        except RecordDoesNotExistError:
            pass
        except:
            raise

    def test_create_health_check(self):
        zone = self.driver.get_zone('example.com')

        type = AuroraDNSHealthCheckType.HTTP
        hostname = "www.pcextreme.nl"
        ipaddress = "109.72.87.252"
        port = 8080
        interval = 10
        threshold = 3

        check = self.driver.ex_create_healthcheck(zone=zone,
                                                  type=type,
                                                  hostname=hostname,
                                                  port=port,
                                                  path=None,
                                                  interval=interval,
                                                  threshold=threshold,
                                                  ipaddress=ipaddress)

        self.assertEqual(check.interval, interval)
        self.assertEqual(check.threshold, threshold)
        self.assertEqual(check.port, port)
        self.assertEqual(check.type, type)
        self.assertEqual(check.hostname, hostname)
        self.assertEqual(check.path, "/")
        self.assertEqual(check.ipaddress, ipaddress)

    def test_list_health_checks(self):
        zone = self.driver.get_zone('example.com')
        checks = self.driver.ex_list_healthchecks(zone)

        self.assertEqual(len(checks), 3)

        for check in checks:
            self.assertEqual(check.interval, 60)
            self.assertEqual(check.type, AuroraDNSHealthCheckType.HTTP)


class AuroraDNSDriverMockHttp(MockHttpTestCase):
    fixtures = DNSFileFixtures('auroradns')

    def _zones(self, method, url, body, headers):
        if method == 'POST':
            body_json = json.loads(body)
            if body_json['name'] == 'exists.example.com':
                return (httplib.CONFLICT, body, {},
                        httplib.responses[httplib.CONFLICT])
            body = self.fixtures.load('zone_example_com.json')
        else:
            body = self.fixtures.load('zone_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_example_com(self, method, url, body, headers):
        body = None
        if method == 'GET':
            body = self.fixtures.load('zone_example_com.json')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_nonexists_example_com(self, method, url, body, headers):
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_ffb62570_8414_4578_a346_526b44e320b7(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('zone_example_com.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_ffb62570_8414_4578_a346_526b44e320b7_records(self, method, url,
                                                            body, headers):
        if method == 'POST':
            body = self.fixtures.load('zone_example_com_record_localhost.json')
        else:
            body = self.fixtures.load('zone_example_com_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_ffb62570_8414_4578_a346_526b44e320b7_health_checks(self, method,
                                                                  url, body,
                                                                  headers):
        if method == 'POST':
            body = self.fixtures.load('zone_example_com_health_check.json')
        else:
            body = self.fixtures.load('zone_example_com_health_checks.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1(self, method, url, body, headers):
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_records(self, method, url, body, headers):
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_records_1(self, method, url, body, headers):
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_ffb62570_8414_4578_a346_526b44e320b7_records_5592f1ff(self,
                                                                     method,
                                                                     url,
                                                                     body,
                                                                     headers):
        body = None
        if method == 'GET':
            body = self.fixtures.load('zone_example_com_record_localhost.json')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
