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
from libcloud.test import unittest

from libcloud.utils.py3 import httplib
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError
from libcloud.dns.drivers.softlayer import SoftLayerDNSDriver
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import SOFTLAYER_PARAMS
from libcloud.utils.py3 import xmlrpclib


class SoftLayerTests(unittest.TestCase):

    def setUp(self):
        SoftLayerDNSDriver.connectionCls.conn_classes = (
            SoftLayerDNSMockHttp, SoftLayerDNSMockHttp)
        SoftLayerDNSMockHttp.type = None
        self.driver = SoftLayerDNSDriver(*SOFTLAYER_PARAMS)

    def test_create_zone(self):
        zone = self.driver.create_zone(domain='bar.com')
        self.assertEqual(zone.id, '123')
        self.assertEqual(zone.domain, 'bar.com')

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 1)

        zone = zones[0]
        self.assertEqual(zone.id, '123')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'bar.com')

    def test_get_zone(self):
        zone = self.driver.get_zone(zone_id='123')
        self.assertEqual(zone.id, '123')
        self.assertEqual(zone.type, 'master')
        self.assertEqual(zone.domain, 'bar.com')

    def test_get_zone_does_not_exist(self):
        SoftLayerDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'

        with self.assertRaises(ZoneDoesNotExistError):
            self.driver.get_zone(zone_id='333')

    def test_delete_zone(self):
        zone = self.driver.list_zones()[0]
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_zone_does_not_exist(self):
        zone = self.driver.list_zones()[0]

        SoftLayerDNSMockHttp.type = 'ZONE_DOES_NOT_EXIST'

        with self.assertRaises(ZoneDoesNotExistError):
            self.driver.delete_zone(zone=zone)

    def test_list_records(self):
        zone = self.driver.list_zones()[0]

        records = zone.list_records()

        self.assertEqual(records[0].id, '50772366')
        self.assertEqual(records[0].type, RecordType.SOA)
        self.assertEqual(records[0].data, 'ns1.softlayer.com.')
        self.assertEqual(
            records[0].extra,
            {
                'mxPriority': '',
                'expire': 604800,
                'retry': 300,
                'refresh': 3600,
                'ttl': 86400
            }
        )
        self.assertEqual(records[1].id, '50772367')
        self.assertEqual(records[1].type, RecordType.NS)
        self.assertEqual(records[1].data, 'ns1.softlayer.com.')

        self.assertEqual(records[2].id, '50772368')
        self.assertEqual(records[2].type, RecordType.NS)
        self.assertEqual(records[2].data, 'ns2.softlayer.com.')

        self.assertEqual(records[3].id, '50772365')
        self.assertEqual(records[3].type, RecordType.A)
        self.assertEqual(records[3].data, '127.0.0.1')

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 10)
        self.assertTrue(RecordType.A in record_types)

    def test_get_record(self):
        record = self.driver.get_record(zone_id='123', record_id='50772366')

        self.assertEqual(record.id, '50772366')
        self.assertEqual(record.type, RecordType.SOA)
        self.assertEqual(record.data, 'ns1.softlayer.com.')

    def test_get_record_record_does_not_exist(self):
        SoftLayerDNSMockHttp.type = 'RECORD_DOES_NOT_EXIST'

        with self.assertRaises(RecordDoesNotExistError):
            self.driver.get_record(zone_id='123',
                                   record_id='1')

    def test_delete_record(self):
        record = self.driver.get_record(zone_id='123', record_id='50772366')
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)

    def test_delete_record_does_not_exist(self):
        record = self.driver.get_record(zone_id='123', record_id='50772366')

        SoftLayerDNSMockHttp.type = 'RECORD_DOES_NOT_EXIST'

        with self.assertRaises(RecordDoesNotExistError):
            self.driver.delete_record(record=record)

    def test_create_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.create_record(
            name='www', zone=zone,
            type=RecordType.A, data='127.0.0.1',
            extra={'ttl': 30}
        )

        self.assertEqual(record.id, '50772870')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.zone, zone)
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '127.0.0.1')

    def test_update_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[1]

        SoftLayerDNSMockHttp.type = 'CHANGED'
        params = {
            'record': record,
            'name': 'www',
            'type': RecordType.A,
            'data': '1.1.1.1',
            'extra': {'ttl': 30}}
        updated_record = self.driver.update_record(**params)

        self.assertEqual(record.data, 'ns1.softlayer.com.')

        self.assertEqual(updated_record.id, '123')
        self.assertEqual(updated_record.name, 'www')
        self.assertEqual(updated_record.zone, record.zone)
        self.assertEqual(updated_record.type, RecordType.A)
        self.assertEqual(updated_record.data, '1.1.1.1')


class SoftLayerDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('softlayer')

    def _get_method_name(self, type, use_param, qs, path):
        return "_xmlrpc"

    def _xmlrpc(self, method, url, body, headers):
        params, meth_name = xmlrpclib.loads(body)
        url = url.replace("/", "_")
        meth_name = "%s_%s" % (url, meth_name)
        return getattr(self, meth_name)(method, url, body, headers)

    def _xmlrpc_v3_SoftLayer_Dns_Domain_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Dns_Domain_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_getByDomainName(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Dns_Domain_getByDomainName.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_getObject(
            self, method, url, body, headers):
        fixture = {
            None: 'v3_SoftLayer_Dns_Domain_getObject.xml',
            'ZONE_DOES_NOT_EXIST': 'not_found.xml',
        }[self.type]
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_deleteObject(
            self, method, url, body, headers):
        fixture = {
            None: 'v3_SoftLayer_Dns_Domain_deleteObject.xml',
            'ZONE_DOES_NOT_EXIST': 'not_found.xml',
        }[self.type]
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_getResourceRecords(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Dns_Domain_getResourceRecords.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_ResourceRecord_getObject(
            self, method, url, body, headers):
        fixture = {
            None: 'v3_SoftLayer_Dns_Domain_ResourceRecord_getObject.xml',
            'RECORD_DOES_NOT_EXIST': 'not_found.xml',
            'CHANGED': 'v3_SoftLayer_Dns_Domain_ResourceRecord_getObject_changed.xml',
        }[self.type]
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_ResourceRecord_deleteObject(
            self, method, url, body, headers):
        fixture = {
            None: 'v3_SoftLayer_Dns_Domain_ResourceRecord_deleteObject.xml',
            'RECORD_DOES_NOT_EXIST': 'not_found.xml',
        }[self.type]
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_ResourceRecord_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Dns_Domain_ResourceRecord_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Dns_Domain_ResourceRecord_editObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Dns_Domain_ResourceRecord_editObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
