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

from libcloud.dns.types import RecordType
from libcloud.dns.drivers.dnsimple import DNSimpleDNSDriver

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_DNSIMPLE


class DNSimpleDNSTests(unittest.TestCase):
    def setUp(self):
        DNSimpleDNSDriver.connectionCls.conn_class = DNSimpleDNSMockHttp
        DNSimpleDNSMockHttp.type = None
        self.driver = DNSimpleDNSDriver(*DNS_PARAMS_DNSIMPLE)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 15)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.AAAA in record_types)
        self.assertTrue(RecordType.ALIAS in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.HINFO in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.NAPTR in record_types)
        self.assertTrue(RecordType.NS in record_types)
        self.assertTrue('POOL' in record_types)
        self.assertTrue(RecordType.SPF in record_types)
        self.assertTrue(RecordType.SOA in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.SSHFP in record_types)
        self.assertTrue(RecordType.TXT in record_types)
        self.assertTrue(RecordType.URL in record_types)

    def test_list_zones_success(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

        zone1 = zones[0]
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['registrant_id', 'user_id',
                                         'unicode_name', 'token', 'state',
                                         'language', 'lockable', 'auto_renew',
                                         'whois_protected', 'record_count',
                                         'service_count', 'expires_on',
                                         'created_at', 'updated_at'])

        zone2 = zones[1]
        self.assertEqual(zone2.id, '2')
        self.assertEqual(zone2.type, 'master')
        self.assertEqual(zone2.domain, 'example.com')
        self.assertEqual(zone2.ttl, 3600)
        self.assertHasKeys(zone2.extra, ['registrant_id', 'user_id',
                                         'unicode_name', 'token', 'state',
                                         'language', 'lockable', 'auto_renew',
                                         'whois_protected', 'record_count',
                                         'service_count', 'expires_on',
                                         'created_at', 'updated_at'])

    def test_list_records_success(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)

        record1 = records[0]
        self.assertEqual(record1.id, '31')
        self.assertEqual(record1.name, '')
        self.assertEqual(record1.type, RecordType.A)
        self.assertEqual(record1.data, '1.2.3.4')
        self.assertHasKeys(record1.extra, ['ttl', 'created_at', 'updated_at',
                                           'domain_id', 'priority'])

        record2 = records[1]
        self.assertEqual(record2.id, '2')
        self.assertEqual(record2.name, 'www')
        self.assertEqual(record2.type, RecordType.CNAME)
        self.assertEqual(record2.data, 'example.com')
        self.assertHasKeys(record2.extra, ['ttl', 'created_at', 'updated_at',
                                           'domain_id', 'priority'])

        record3 = records[2]
        self.assertEqual(record3.id, '32')
        self.assertEqual(record3.name, '')
        self.assertEqual(record3.type, RecordType.MX)
        self.assertEqual(record3.data, 'mail.example.com')
        self.assertHasKeys(record3.extra, ['ttl', 'created_at', 'updated_at',
                                           'domain_id', 'priority'])

    def test_get_zone_success(self):
        zone1 = self.driver.get_zone(zone_id='1')
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['registrant_id', 'user_id',
                                         'unicode_name', 'token', 'state',
                                         'language', 'lockable', 'auto_renew',
                                         'whois_protected', 'record_count',
                                         'service_count', 'expires_on',
                                         'created_at', 'updated_at'])

    def test_get_record_success(self):
        record = self.driver.get_record(zone_id='1',
                                        record_id='123')
        self.assertEqual(record.id, '123')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.CNAME)
        self.assertEqual(record.data, 'example.com')
        self.assertHasKeys(record.extra, ['ttl', 'created_at', 'updated_at',
                                          'domain_id', 'priority'])

    def test_create_zone_success(self):
        DNSimpleDNSMockHttp.type = 'CREATE'
        zone = self.driver.create_zone(domain='example.com')
        self.assertEqual(zone.id, '1')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, 3600)
        self.assertEqual(zone.type, 'master')
        self.assertHasKeys(zone.extra, ['registrant_id', 'user_id',
                                        'unicode_name', 'token', 'state',
                                        'language', 'lockable', 'auto_renew',
                                        'whois_protected', 'record_count',
                                        'service_count', 'expires_on',
                                        'created_at', 'updated_at'])

    def test_create_record_success(self):
        zone = self.driver.list_zones()[0]
        DNSimpleDNSMockHttp.type = 'CREATE'
        record = self.driver.create_record(name='domain4', zone=zone,
                                           type=RecordType.MX,
                                           data='mail.example.com')
        self.assertEqual(record.id, '172')
        self.assertEqual(record.name, '')
        self.assertEqual(record.type, RecordType.MX)
        self.assertEqual(record.data, 'mail.example.com')
        self.assertHasKeys(record.extra, ['ttl', 'created_at', 'updated_at',
                                          'domain_id', 'priority'])

    def test_update_record_success(self):
        record = self.driver.get_record(zone_id='1',
                                        record_id='123')
        DNSimpleDNSMockHttp.type = 'UPDATE'
        extra = {'ttl': 4500}
        record1 = self.driver.update_record(record=record, name='www',
                                            type=record.type,
                                            data='updated.com',
                                            extra=extra)
        self.assertEqual(record.data, 'example.com')
        self.assertEqual(record.extra.get('ttl'), 3600)
        self.assertEqual(record1.data, 'updated.com')
        self.assertEqual(record1.extra.get('ttl'), 4500)

    def test_delete_zone_success(self):
        zone = self.driver.list_zones()[0]
        DNSimpleDNSMockHttp.type = 'DELETE_200'
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_zone_success_future_implementation(self):
        zone = self.driver.list_zones()[0]
        DNSimpleDNSMockHttp.type = 'DELETE_204'
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_record_success(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)
        record = records[1]
        DNSimpleDNSMockHttp.type = 'DELETE_200'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)

    def test_delete_record_success_future_implementation(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 3)
        record = records[1]
        DNSimpleDNSMockHttp.type = 'DELETE_204'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)


class DNSimpleDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('dnsimple')

    def _v1_domains(self, method, url, body, headers):
        body = self.fixtures.load('list_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create_domain.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1(self, method, url, body, headers):
        body = self.fixtures.load('get_domain.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1_records(self, method, url, body, headers):
        body = self.fixtures.load('list_domain_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1_records_123(self, method, url, body, headers):
        body = self.fixtures.load('get_domain_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1_records_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create_domain_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1_records_123_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('update_domain_record.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_1_DELETE_200(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _v1_domains_1_DELETE_204(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.NO_CONTENT])

    def _v1_domains_1_records_2_DELETE_200(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _v1_domains_1_records_2_DELETE_204(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.NO_CONTENT])


if __name__ == '__main__':
    sys.exit(unittest.main())
