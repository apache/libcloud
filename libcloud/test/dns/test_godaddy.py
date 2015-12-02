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
from libcloud.dns.drivers.godaddy import GoDaddyDNSDriver
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_GODADDY
from libcloud.dns.base import Zone, RecordType


class GoDaddyTests(unittest.TestCase):

    def setUp(self):
        GoDaddyMockHttp.type = None
        GoDaddyDNSDriver.connectionCls.conn_classes = (
            None, GoDaddyMockHttp)
        self.driver = GoDaddyDNSDriver(*DNS_PARAMS_GODADDY)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 5)
        self.assertEqual(zones[0].id, '177184419')
        self.assertEqual(zones[0].domain, 'aperture-platform.com')

    def test_ex_check_availability(self):
        check = self.driver.ex_check_availability("wazzlewobbleflooble.com")
        self.assertEqual(check.available, True)
        self.assertEqual(check.price, 14.99)

    def test_ex_list_tlds(self):
        tlds = self.driver.ex_list_tlds()
        self.assertEqual(len(tlds), 331)
        self.assertEqual(tlds[0].name, 'academy')
        self.assertEqual(tlds[0].type, 'GENERIC')

    def test_ex_get_purchase_schema(self):
        schema = self.driver.ex_get_purchase_schema('com')
        self.assertEqual(schema['id'],
                         'https://api.godaddy.com/DomainPurchase#')

    def test_ex_get_agreements(self):
        ags = self.driver.ex_get_agreements('com')
        self.assertEqual(len(ags), 1)
        self.assertEqual(ags[0].title, 'Domain Name Registration Agreement')

    def test_ex_purchase_domain(self):
        fixtures = DNSFileFixtures('godaddy')
        document = fixtures.load('purchase_request.json')
        order = self.driver.ex_purchase_domain(document)
        self.assertEqual(order.order_id, 1)

    def test_list_records(self):
        zone = Zone(id='177184419',
                    domain='aperture-platform.com',
                    type='master',
                    ttl=None,
                    driver=self.driver)
        records = self.driver.list_records(zone)
        self.assertEqual(len(records), 14)
        self.assertEqual(records[0].type, RecordType.A)
        self.assertEqual(records[0].name, '@')
        self.assertEqual(records[0].data, '50.63.202.42')
        self.assertEqual(records[0].id, '@:A')

    def test_get_record(self):
        record = self.driver.get_record(
            'aperture-platform.com',
            'www:A')
        self.assertEqual(record.id, 'www:A')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '50.63.202.42')

    def test_create_record(self):
        zone = Zone(id='177184419',
                    domain='aperture-platform.com',
                    type='master',
                    ttl=None,
                    driver=self.driver)
        record = self.driver.create_record(
            zone=zone,
            name='www',
            type=RecordType.A,
            data='50.63.202.42'
        )
        self.assertEqual(record.id, 'www:A')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '50.63.202.42')

    def test_update_record(self):
        record = self.driver.get_record(
            'aperture-platform.com',
            'www:A')
        record = self.driver.update_record(
            record=record,
            name='www',
            type=RecordType.A,
            data='50.63.202.22'
        )
        self.assertEqual(record.id, 'www:A')
        self.assertEqual(record.name, 'www')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '50.63.202.22')

    def test_get_zone(self):
        zone = self.driver.get_zone('aperture-platform.com')
        self.assertEqual(zone.id, '177184419')
        self.assertEqual(zone.domain, 'aperture-platform.com')

    def test_delete_zone(self):
        zone = Zone(id='177184419',
                    domain='aperture-platform.com',
                    type='master',
                    ttl=None,
                    driver=self.driver)
        self.driver.delete_zone(zone)


class GoDaddyMockHttp(MockHttp):
    fixtures = DNSFileFixtures('godaddy')

    def _v1_domains(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_aperture_platform_com(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_aperture_platform_com.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_aperture_platform_com_records(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_aperture_platform_com_records.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_available(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_available.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_tlds(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_tlds.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_aperture_platform_com_records_A_www(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_aperture_platform_com_records_A_www.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_purchase_schema_com(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_purchase_schema_com.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_agreements(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_agreements.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_domains_purchase(self, method, url, body, headers):
        body = self.fixtures.load('v1_domains_purchase.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
