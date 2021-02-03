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

from libcloud.common.types import ProviderError
from libcloud.dns.drivers.auroradns import AuroraDNSDriver
from libcloud.dns.drivers.auroradns import AuroraDNSHealthCheckType
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.base import Zone
from libcloud.test import LibcloudTestCase
from libcloud.test import MockHttp
from libcloud.test import unittest
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_AURORADNS
from libcloud.utils.py3 import httplib


class AuroraDNSDriverTests(LibcloudTestCase):

    def setUp(self):
        AuroraDNSDriver.connectionCls.conn_class = AuroraDNSDriverMockHttp
        AuroraDNSDriverMockHttp.type = None
        self.driver = AuroraDNSDriver(*DNS_PARAMS_AURORADNS)

    def test_403_status_code(self):
        AuroraDNSDriverMockHttp.type = "HTTP_FORBIDDEN"

        with self.assertRaises(ProviderError) as ctx:
            self.driver.list_zones()

        self.assertEqual(ctx.exception.value, "Authorization failed")
        self.assertEqual(ctx.exception.http_code, 403)

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

    def test_res_to_record(self):
        res = {'id': 2,
               'name': 'www',
               'type': 'AAAA',
               'content': '2001:db8:100',
               'created': 1234,
               'modified': 2345,
               'disabled': False,
               'ttl': 1800,
               'prio': 10}

        zone = Zone(id=1,
                    domain='example.com',
                    type=None,
                    ttl=60,
                    driver=self.driver)

        record = self.driver._AuroraDNSDriver__res_to_record(zone, res)
        self.assertEqual(res['name'], record.name)
        self.assertEqual(res['ttl'], record.extra['ttl'])
        self.assertEqual(res['prio'], record.extra['priority'])
        self.assertEqual(res['type'], record.type)
        self.assertEqual(res['content'], record.data)
        self.assertEqual(zone, record.zone)
        self.assertEqual(self.driver, record.driver)

    def test_record_types(self):
        types = self.driver.list_record_types()
        self.assertEqual(len(types), 12)
        self.assertTrue(RecordType.A in types)
        self.assertTrue(RecordType.AAAA in types)
        self.assertTrue(RecordType.MX in types)
        self.assertTrue(RecordType.NS in types)
        self.assertTrue(RecordType.SOA in types)
        self.assertTrue(RecordType.TXT in types)
        self.assertTrue(RecordType.CNAME in types)
        self.assertTrue(RecordType.SRV in types)
        self.assertTrue(RecordType.DS in types)
        self.assertTrue(RecordType.SSHFP in types)
        self.assertTrue(RecordType.PTR in types)
        self.assertTrue(RecordType.TLSA in types)

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)
        for zone in zones:
            self.assertTrue(zone.domain.startswith('auroradns'))

    def test_create_zone(self):
        zone = self.driver.create_zone('example.com')
        self.assertEqual(zone.domain, 'example.com')

    def test_get_zone(self):
        zone = self.driver.get_zone('example.com')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.id, 'ffb62570-8414-4578-a346-526b44e320b7')

    def test_delete_zone(self):
        zone = self.driver.get_zone('example.com')
        self.assertTrue(self.driver.delete_zone(zone))

    def test_create_record(self):
        zone = self.driver.get_zone('example.com')
        record = zone.create_record(name='localhost',
                                    type=RecordType.A,
                                    data='127.0.0.1',
                                    extra={'ttl': 900})
        self.assertEqual(record.id, '5592f1ff')
        self.assertEqual(record.name, 'localhost')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.extra['ttl'], 900)

    def test_get_record(self):
        zone = self.driver.get_zone('example.com')
        record = self.driver.get_record(zone.id, '5592f1ff')
        self.assertEqual(record.id, '5592f1ff')
        self.assertEqual(record.name, 'localhost')
        self.assertEqual(record.data, '127.0.0.1')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.extra['ttl'], 900)
        self.assertEqual(record.extra['priority'], None)

    def test_update_record(self):
        ttl = 900
        zone = self.driver.get_zone('example.com')
        record = self.driver.get_record(zone.id, '5592f1ff')
        record = record.update(extra={'ttl': ttl})
        self.assertEqual(record.extra['ttl'], ttl)

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
        except Exception:
            raise

    def test_delete_zone_non_exist(self):
        try:
            self.driver.delete_zone(Zone(id=1, domain='nonexists.example.com',
                                         type='NATIVE', driver=AuroraDNSDriver,
                                         ttl=3600))
            self.fail('expected a ZoneDoesNotExistError')
        except ZoneDoesNotExistError:
            pass
        except Exception:
            raise

    def test_create_zone_already_exist(self):
        try:
            self.driver.create_zone('exists.example.com')
            self.fail('expected a ZoneAlreadyExistsError')
        except ZoneAlreadyExistsError:
            pass
        except Exception:
            raise

    def test_list_records_non_exist(self):
        try:
            self.driver.list_records(Zone(id=1, domain='nonexists.example.com',
                                          type='NATIVE', driver=AuroraDNSDriver,
                                          ttl=3600))
            self.fail('expected a ZoneDoesNotExistError')
        except ZoneDoesNotExistError:
            pass
        except Exception:
            raise

    def test_get_record_non_exist(self):
        try:
            self.driver.get_record(1, 1)
            self.fail('expected a RecordDoesNotExistError')
        except RecordDoesNotExistError:
            pass
        except Exception:
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


class AuroraDNSDriverMockHttp(MockHttp):
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

    def _zones_HTTP_FORBIDDEN(self, method, url, body, headers):
        body = "{}"
        return (httplib.FORBIDDEN, body, {}, httplib.responses[httplib.FORBIDDEN])

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
