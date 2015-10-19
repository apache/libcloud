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

from mock import MagicMock

from libcloud.dns.base import Record, Zone
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_DURABLEDNS
from libcloud.utils.py3 import httplib
from libcloud.dns.drivers.durabledns import DurableDNSDriver
from libcloud.dns.drivers.durabledns import ZONE_EXTRA_PARAMS_DEFAULT_VALUES
from libcloud.dns.drivers.durabledns import DEFAULT_TTL
from libcloud.dns.drivers.durabledns import RECORD_EXTRA_PARAMS_DEFAULT_VALUES


class DurableDNSTests(LibcloudTestCase):

    def setUp(self):
        DurableDNSDriver.connectionCls.conn_classes = \
            (None, DurableDNSMockHttp)
        DurableDNSMockHttp.type = None
        self.driver = DurableDNSDriver(*DNS_PARAMS_DURABLEDNS)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 10)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.AAAA in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.HINFO in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.NS in record_types)
        self.assertTrue(RecordType.PTR in record_types)
        self.assertTrue(RecordType.RP in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.TXT in record_types)

    def test_list_zones(self):
        extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                 'serial': '1437473456', 'refresh': '13000', 'retry': 7200,
                 'expire': 1300, 'minimum': 13, 'xfer': '127.0.0.1',
                 'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=extra)
        self.driver.get_zone = MagicMock(return_value=zone)
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)
        zone = zones[0]
        self.assertEqual(zone.id, 'myzone.com.')
        self.assertEqual(zone.domain, 'myzone.com.')
        self.assertEqual(zone.ttl, 1300)
        self.assertEqual(zone.extra['ns'], 'ns1.durabledns.com.')
        self.assertEqual(zone.extra['mbox'], 'mail.myzone.com')
        self.assertEqual(zone.extra['serial'], '1437473456')
        self.assertEqual(zone.extra['refresh'], '13000')
        self.assertEqual(zone.extra['retry'], 7200)
        self.assertEqual(zone.extra['expire'], 1300)
        self.assertEqual(zone.extra['minimum'], 13)
        self.assertEqual(zone.extra['xfer'], '127.0.0.1')
        self.assertEqual(zone.extra['update_acl'], '127.0.0.1')
        self.assertEqual(len(zone.extra.keys()), 9)

    def test_list_records(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        extra = {'aux': 1, 'ttl': 3600}
        record = Record(id='353286987', type='A', zone=zone,
                        name='record1', data='192.168.0.1',
                        driver=self, extra=extra)
        self.driver.get_record = MagicMock(return_value=record)
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)
        self.assertEqual(record.id, '353286987')
        self.assertEqual(record.name, 'record1')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '192.168.0.1')
        self.assertEqual(record.zone, zone)
        self.assertEqual(record.extra['aux'], 1)
        self.assertEqual(record.extra['ttl'], 3600)

    def test_list_records_zone_does_not_exist(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.list_records(zone=zone)
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, zone.id)
        else:
            self.fail('Exception was not thrown')

    def test_get_zone(self):
        zone = self.driver.get_zone(zone_id='myzone.com.')
        self.assertEqual(zone.id, 'myzone.com.')
        self.assertEqual(zone.domain, 'myzone.com.')
        self.assertEqual(zone.ttl, 1300)
        self.assertEqual(zone.extra['ns'], 'ns1.durabledns.com.')
        self.assertEqual(zone.extra['mbox'], 'mail.myzone.com')
        self.assertEqual(zone.extra['serial'], '1437473456')
        self.assertEqual(zone.extra['refresh'], '13000')
        self.assertEqual(zone.extra['retry'], 7200)
        self.assertEqual(zone.extra['expire'], 1300)
        self.assertEqual(zone.extra['minimum'], 13)
        self.assertEqual(zone.extra['xfer'], '127.0.0.1/32')
        self.assertEqual(zone.extra['update_acl'],
                         '127.0.0.1/32,127.0.0.100/32')
        self.assertEqual(len(zone.extra.keys()), 9)

    def test_get_zone_does_not_exist(self):
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='nonexistentzone.com.')
        except ZoneDoesNotExistError:
            e = sys.exc_info()[1]
            self.assertEqual(e.zone_id, 'nonexistentzone.com.')
        else:
            self.fail('Exception was not thrown')

    def test_get_record(self):
        record = self.driver.get_record(zone_id='myzone.com.',
                                        record_id='record1')
        self.assertEqual(record.id, '353286987')
        self.assertEqual(record.name, 'record1')
        self.assertEqual(record.type, 'A')
        self.assertEqual(record.data, '192.168.0.1')
        self.assertEqual(record.extra['aux'], 1)
        self.assertEqual(record.extra['ttl'], 3600)

    def test_get_record_zone_does_not_exist(self):
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.get_record(zone_id='nonexistentzone.com.',
                                   record_id='record1')
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_record_record_does_not_exist(self):
        DurableDNSMockHttp.type = 'RECORD_DOES_NOT_EXIST'
        try:
            self.driver.get_record(zone_id='', record_id='')
        except RecordDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_with_extra_param(self):
        DurableDNSMockHttp.type = 'WITH_EXTRA_PARAMS'
        zone = self.driver.create_zone(domain='myzone.com.', ttl=4000,
                                       extra={'mbox': 'mail.myzone.com',
                                              'minimum': 50000})
        extra = ZONE_EXTRA_PARAMS_DEFAULT_VALUES
        self.assertEqual(zone.id, 'myzone.com.')
        self.assertEqual(zone.domain, 'myzone.com.')
        self.assertEqual(zone.ttl, 4000)
        self.assertEqual(zone.extra['ns'], extra['ns'])
        self.assertEqual(zone.extra['mbox'], 'mail.myzone.com')
        self.assertEqual(zone.extra['serial'], '1437473456')
        self.assertEqual(zone.extra['refresh'], extra['refresh'])
        self.assertEqual(zone.extra['retry'], extra['retry'])
        self.assertEqual(zone.extra['expire'], extra['expire'])
        self.assertEqual(zone.extra['minimum'], 50000)
        self.assertEqual(zone.extra['xfer'], extra['xfer'])
        self.assertEqual(zone.extra['update_acl'], extra['update_acl'])
        self.assertEqual(len(zone.extra.keys()), 9)

    def test_create_zone_no_extra_param(self):
        DurableDNSMockHttp.type = 'NO_EXTRA_PARAMS'
        zone = self.driver.create_zone(domain='myzone.com.')
        extra = ZONE_EXTRA_PARAMS_DEFAULT_VALUES
        self.assertEqual(zone.id, 'myzone.com.')
        self.assertEqual(zone.domain, 'myzone.com.')
        self.assertEqual(zone.ttl, DEFAULT_TTL)
        self.assertEqual(zone.extra['ns'], extra['ns'])
        self.assertEqual(zone.extra['mbox'], extra['mbox'])
        self.assertEqual(zone.extra['serial'], '1437473456')
        self.assertEqual(zone.extra['refresh'], extra['refresh'])
        self.assertEqual(zone.extra['retry'], extra['retry'])
        self.assertEqual(zone.extra['expire'], extra['expire'])
        self.assertEqual(zone.extra['minimum'], extra['minimum'])
        self.assertEqual(zone.extra['xfer'], extra['xfer'])
        self.assertEqual(zone.extra['update_acl'], extra['update_acl'])
        self.assertEqual(len(zone.extra.keys()), 9)

    def test_create_zone_zone_already_exist(self):
        DurableDNSMockHttp.type = 'ZONE_ALREADY_EXIST'
        try:
            self.driver.create_zone(domain='myzone.com.')
        except ZoneAlreadyExistsError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_record_no_extra_param(self):
        zone = self.driver.list_zones()[0]
        DurableDNSMockHttp.type = 'NO_EXTRA_PARAMS'
        record = self.driver.create_record(name='record1', zone=zone,
                                           type=RecordType.A, data='1.2.3.4')

        self.assertEqual(record.id, '353367855')
        self.assertEqual(record.name, 'record1')
        self.assertEqual(record.zone, zone)
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertEqual(record.extra.get('aux'),
                         RECORD_EXTRA_PARAMS_DEFAULT_VALUES.get('aux'))
        self.assertEqual(record.extra.get('ttl'),
                         RECORD_EXTRA_PARAMS_DEFAULT_VALUES.get('ttl'))

    def test_create_record_with_extra_param(self):
        zone = self.driver.list_zones()[0]
        DurableDNSMockHttp.type = 'WITH_EXTRA_PARAMS'
        record = self.driver.create_record(name='record1', zone=zone,
                                           type=RecordType.A, data='1.2.3.4',
                                           extra={'ttl': 4000})

        self.assertEqual(record.id, '353367855')
        self.assertEqual(record.name, 'record1')
        self.assertEqual(record.zone, zone)
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertEqual(record.extra.get('aux'),
                         RECORD_EXTRA_PARAMS_DEFAULT_VALUES.get('aux'))
        self.assertEqual(record.extra.get('ttl'), 4000)

    def test_create_record_zone_does_not_exist(self):
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='deletedzone.com.', domain='deletedzone.com.',
                    type='master', ttl=1300, driver=self.driver, extra=z_extra)
        try:
            self.driver.create_record(name='record1', zone=zone,
                                      type=RecordType.A, data='1.2.3.4')
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_update_zone(self):
        # We'll assume that this zone has been created before. So will have
        # a serial number in his extra attributes. Later we are going to
        # check that after the update, serial number should change to new one.
        DurableDNSMockHttp.type = 'UPDATE_ZONE'
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1', 'serial': '1437473456',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='deletedzone.com.', domain='deletedzone.com.',
                    type='master', ttl=1300, driver=self.driver, extra=z_extra)
        new_extra = {'minimum': 5000, 'expire': 8000}
        updated_zone = self.driver.update_zone(zone, zone.domain,
                                               type=zone.type, ttl=4000,
                                               extra=new_extra)

        self.assertEqual(updated_zone.id, 'myzone.com.')
        self.assertEqual(updated_zone.domain, 'myzone.com.')
        self.assertEqual(updated_zone.ttl, 4000)
        self.assertEqual(updated_zone.extra['ns'], z_extra['ns'])
        self.assertEqual(updated_zone.extra['mbox'], z_extra['mbox'])
        self.assertEqual(updated_zone.extra['serial'], '1437475078')
        self.assertEqual(updated_zone.extra['refresh'], z_extra['refresh'])
        self.assertEqual(updated_zone.extra['retry'], z_extra['retry'])
        self.assertEqual(updated_zone.extra['expire'], 8000)
        self.assertEqual(updated_zone.extra['minimum'], 5000)
        self.assertEqual(updated_zone.extra['xfer'], z_extra['xfer'])
        self.assertEqual(updated_zone.extra['update_acl'],
                         z_extra['update_acl'])
        self.assertEqual(len(updated_zone.extra.keys()), 9)

    def test_update_zone_zone_does_not_exist(self):
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1', 'serial': '1437473456',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='deletedzone.com.', domain='deletedzone.com.',
                    type='master', ttl=1300, driver=self.driver, extra=z_extra)
        try:
            self.driver.update_zone(zone, zone.domain)
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_update_record(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        extra = {'aux': 1, 'ttl': 3600}
        record = Record(id='353286987', type='A', zone=zone,
                        name='record1', data='192.168.0.1',
                        driver=self, extra=extra)
        new_extra = {'aux': 0, 'ttl': 4500}
        updated_record = self.driver.update_record(record, record.name,
                                                   record.type, record.data,
                                                   extra=new_extra)

        self.assertEqual(updated_record.data, '192.168.0.1')
        self.assertEqual(updated_record.id, '353286987')
        self.assertEqual(updated_record.name, 'record1')
        self.assertEqual(updated_record.zone, record.zone)
        self.assertEqual(updated_record.type, RecordType.A)
        self.assertEqual(updated_record.extra.get('aux'), 0)
        self.assertEqual(updated_record.extra.get('ttl'), 4500)

    def test_update_record_zone_does_not_exist(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        extra = {'aux': 1, 'ttl': 3600}
        record = Record(id='353286987', type='A', zone=zone,
                        name='record1', data='192.168.0.1',
                        driver=self, extra=extra)
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.update_record(record, record.name, record.type,
                                      record.data)
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_zone(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_zone_zone_does_not_exist(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_record(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        extra = {'aux': 1, 'ttl': 3600}
        record = Record(id='353286987', type='A', zone=zone,
                        name='record1', data='192.168.0.1',
                        driver=self, extra=extra)
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)

    def test_delete_record_record_does_not_exist(self):
        z_extra = {'ns': 'ns1.durabledns.com.', 'mbox': 'mail.myzone.com',
                   'refresh': '13000', 'retry': 7200, 'expire': 1300,
                   'minimum': 13, 'xfer': '127.0.0.1',
                   'update_acl': '127.0.0.1'}
        zone = Zone(id='myzone.com.', domain='myzone.com.', type='master',
                    ttl=1300, driver=self.driver, extra=z_extra)
        extra = {'aux': 1, 'ttl': 3600}
        record = Record(id='353286987', type='A', zone=zone,
                        name='record1', data='192.168.0.1',
                        driver=self, extra=extra)
        DurableDNSMockHttp.type = 'RECORD_DOES_NOT_EXIST'
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_record_zone_does_not_exist(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[0]
        DurableDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'
        try:
            self.driver.delete_record(record=record)
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')


class DurableDNSMockHttp(MockHttpTestCase):
    fixtures = DNSFileFixtures('durabledns')

    def _services_dns_listZones_php(self, method, url, body, headers):
        body = self.fixtures.load('list_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_listRecords_php(self, method, url, body, headers):
        body = self.fixtures.load('list_records.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_listRecords_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                          body, headers):
        body = self.fixtures.load('list_records_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getZone_php(self, method, url, body, headers):
        body = self.fixtures.load('get_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getZone_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                      body, headers):
        body = self.fixtures.load('get_zone_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getRecord_php(self, method, url, body, headers):
        body = self.fixtures.load('get_record.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getRecord_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('get_record_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getRecord_php_RECORD_DOES_NOT_EXIST(self, method, url,
                                                          body, headers):
        body = self.fixtures.load('get_record_RECORD_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createZone_php_WITH_EXTRA_PARAMS(self, method, url, body,
                                                       headers):
        body = self.fixtures.load('create_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getZone_php_WITH_EXTRA_PARAMS(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('get_zone_WITH_EXTRA_PARAMS.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createZone_php_NO_EXTRA_PARAMS(self, method, url, body,
                                                     headers):
        body = self.fixtures.load('create_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getZone_php_NO_EXTRA_PARAMS(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('get_zone_NO_EXTRA_PARAMS.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createZone_php_ZONE_ALREADY_EXIST(self, method, url,
                                                        body, headers):
        body = self.fixtures.load('create_zone_ZONE_ALREADY_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createRecord_php_NO_EXTRA_PARAMS(self, method, url, body,
                                                       headers):
        body = self.fixtures.load('create_record_NO_EXTRA_PARAMS.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createRecord_php_WITH_EXTRA_PARAMS(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('create_record_WITH_EXTRA_PARAMS.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_createRecord_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                           body, headers):
        body = self.fixtures.load('create_record_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_updateZone_php_UPDATE_ZONE(self, method, url,
                                                 body, headers):
        body = self.fixtures.load('update_zone_UPDATE_ZONE.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_getZone_php_UPDATE_ZONE(self, method, url,
                                              body, headers):
        body = self.fixtures.load('get_zone_UPDATE_ZONE.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_updateZone_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('update_zone_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_updateRecord_php(self, method, url, body, headers):
        body = self.fixtures.load('update_record.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_updateRecord_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                           body, headers):
        body = self.fixtures.load('update_record_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_deleteZone_php(self, method, url, body, headers):
        body = self.fixtures.load('delete_zone.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_deleteZone_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                         body, headers):
        body = self.fixtures.load('delete_zone_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_deleteRecord_php(self, method, url, body, headers):
        body = self.fixtures.load('delete_record.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_deleteRecord_php_RECORD_DOES_NOT_EXIST(self, method, url,
                                                             body, headers):
        body = self.fixtures.load('delete_record_RECORD_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _services_dns_deleteRecord_php_ZONE_DOES_NOT_EXIST(self, method, url,
                                                           body, headers):
        body = self.fixtures.load('delete_record_ZONE_DOES_NOT_EXIST.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
