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

from libcloud.test import MockHttp
from libcloud.utils.py3 import httplib
from libcloud.dns.drivers.vultr import VultrDNSDriver, VultrDNSDriverV2
from libcloud.test.file_fixtures import DNSFileFixtures


class VultrTests(unittest.TestCase):
    def setUp(self):
        VultrMockHttp.type = None
        VultrDNSDriverV2.connectionCls.conn_class = VultrMockHttp
        self.driver = VultrDNSDriver("foo")

    def test_correct_class_is_used(self):
        self.assertIsInstance(self.driver, VultrDNSDriverV2)

    def test_unknown_api_version(self):
        self.assertRaises(NotImplementedError, VultrDNSDriver, "foo", api_version="3")

    def test_list_zones(self):
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)
        zone = zones[0]
        self.assertEqual(zone.id, "example.com")
        self.assertEqual(zone.domain, "example.com")
        self.assertEqual(zone.extra["date_created"], "2021-09-07T09:52:18+00:00")

    def test_create_zone(self):
        zone = self.driver.create_zone("example.com")
        self.assertEqual(zone.id, "example.com")
        self.assertEqual(zone.domain, "example.com")
        self.assertEqual(zone.extra["date_created"], "2021-09-07T10:28:34+00:00")

    def test_get_zone(self):
        zone = self.driver.get_zone("example.com")
        self.assertEqual(zone.id, "example.com")
        self.assertEqual(zone.domain, "example.com")
        self.assertEqual(zone.extra["date_created"], "2021-09-07T09:52:18+00:00")

    def test_delete_zone(self):
        zone = self.driver.get_zone("example.com")
        response = self.driver.delete_zone(zone)
        self.assertTrue(response)

    def test_list_records(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone)
        self.assertEqual(len(records), 5)
        record = records[0]
        self.assertEqual(record.id, "123")
        self.assertEqual(record.name, "")
        self.assertEqual(record.type, "NS")
        self.assertEqual(record.data, "ns1.vultr.com")

    def test_create_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.create_record("test1", zone, "A", "192.168.0.11")
        self.assertEqual(record.id, "123")
        self.assertEqual(record.zone.domain, zone.domain)
        self.assertEqual(record.type, "A")
        self.assertEqual(record.name, "test1")
        self.assertEqual(record.extra["priority"], 1)

    def test_update_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone)[0]
        response = self.driver.update_record(
            record, name="test", data="192.168.0.0", extra=dict(ttl=300, priority=1)
        )
        self.assertTrue(response)

    def test_get_record(self):
        zone = self.driver.list_zones()[0]
        temp = self.driver.list_records(zone)[0]
        record = self.driver.get_record(zone.domain, temp.id)
        self.assertEqual(record.id, "123")
        self.assertEqual(record.zone.domain, zone.domain)
        self.assertEqual(record.type, "NS")
        self.assertEqual(record.name, "")
        self.assertEqual(record.extra["priority"], -1)
        self.assertEqual(record.ttl, 300)

    def test_delete_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone)[0]
        response = self.driver.delete_record(record)
        self.assertTrue(response)


class VultrMockHttp(MockHttp):
    fixtures = DNSFileFixtures("vultr_v2")

    def _v2_domains(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("list_zones.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == "POST":
            body = self.fixtures.load("create_zone.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_domains_example_com(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("get_zone.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])

    def _v2_domains_example_com_records(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("list_records.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        if method == "POST":
            body = self.fixtures.load("create_record.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_domains_example_com_records_123(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("get_record.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "DELETE":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])
        elif method == "PATCH":
            return (httplib.NO_CONTENT, body, {}, httplib.responses[httplib.NO_CONTENT])


if __name__ == "__main__":
    sys.exit(unittest.main())
