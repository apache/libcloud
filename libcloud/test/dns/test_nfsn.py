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

from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.dns.base import Zone, Record
from libcloud.dns.types import RecordType, ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.utils.py3 import httplib, urlparse
from libcloud.dns.drivers.nfsn import NFSNDNSDriver
from libcloud.test.file_fixtures import DNSFileFixtures


class NFSNTestCase(LibcloudTestCase):
    def setUp(self):
        NFSNDNSDriver.connectionCls.conn_class = NFSNMockHttp
        NFSNMockHttp.type = None
        NFSNMockHttp.history.clear()
        self.driver = NFSNDNSDriver("testid", "testsecret")

        self.test_zone = Zone(
            id="example.com",
            domain="example.com",
            driver=self.driver,
            type="master",
            ttl=None,
            extra={},
        )
        self.test_record = Record(
            id=None,
            name="",
            data="192.0.2.1",
            type=RecordType.A,
            zone=self.test_zone,
            driver=self.driver,
            extra={},
        )

    def test_list_zones(self):
        with self.assertRaises(NotImplementedError):
            self.driver.list_zones()

    def test_create_zone(self):
        with self.assertRaises(NotImplementedError):
            self.driver.create_zone("example.com")

    def test_get_zone(self):
        zone = self.driver.get_zone("example.com")

        sent = NFSNMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/dns/example.com/serial")

        self.assertEqual(zone.id, None)
        self.assertEqual(zone.domain, "example.com")

    def test_delete_zone(self):
        with self.assertRaises(NotImplementedError):
            self.driver.delete_zone(self.test_zone)

    def test_create_record(self):
        NFSNMockHttp.type = "CREATED"
        record = self.test_zone.create_record(
            name="newrecord", type=RecordType.A, data="127.0.0.1", extra={"ttl": 900}
        )

        # [0] /dns/example.com/addRR
        # [1] /dns/example.com/listRRs
        sent = NFSNMockHttp.history.pop(0)
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/dns/example.com/addRR")
        query = urlparse.parse_qs(sent.body)
        self.assertIn("newrecord", query["name"])
        self.assertIn("A", query["type"])
        self.assertIn("127.0.0.1", query["data"])
        self.assertIn("900", query["ttl"])

        self.assertEqual(record.id, None)
        self.assertEqual(record.name, "newrecord")
        self.assertEqual(record.data, "127.0.0.1")
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 900)

    def test_get_record(self):
        with self.assertRaises(NotImplementedError):
            self.driver.get_record("example.com", "12345")

    def test_delete_record(self):
        self.assertTrue(self.test_record.delete())

        sent = NFSNMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/dns/example.com/removeRR")
        query = urlparse.parse_qs(sent.body)
        self.assertIn("A", query["type"])
        self.assertIn("192.0.2.1", query["data"])

    def test_list_records(self):
        records = self.driver.list_records(self.test_zone)

        sent = NFSNMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/dns/example.com/listRRs")

        self.assertEqual(len(records), 2)

    def test_ex_get_records_by(self):
        NFSNMockHttp.type = "ONE_RECORD"
        records = self.driver.ex_get_records_by(self.test_zone, type=RecordType.A)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.name, "")
        self.assertEqual(record.data, "192.0.2.1")
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.ttl, 3600)

    def test_get_zone_not_found(self):
        NFSNMockHttp.type = "NOT_FOUND"
        with self.assertRaises(ZoneDoesNotExistError):
            self.driver.get_zone("example.com")

    def test_delete_record_not_found(self):
        NFSNMockHttp.type = "NOT_FOUND"
        with self.assertRaises(RecordDoesNotExistError):
            self.assertTrue(self.test_record.delete())


class NFSNMockHttp(MockHttp):
    fixtures = DNSFileFixtures("nfsn")
    keep_history = True
    base_headers = {"content-type": "application/x-nfsn-api"}

    def _dns_example_com_addRR_CREATED(self, method, url, body, headers):
        return (httplib.OK, "", self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_listRRs(self, method, url, body, headers):
        body = self.fixtures.load("list_records.json")
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_listRRs_CREATED(self, method, url, body, headers):
        body = self.fixtures.load("list_records_created.json")
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_removeRR(self, method, url, body, headers):
        return (httplib.OK, "", self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_serial(self, method, url, body, headers):
        return (httplib.OK, "12345", self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_listRRs_ONE_RECORD(self, method, url, body, headers):
        body = self.fixtures.load("list_one_record.json")
        return (httplib.OK, body, self.base_headers, httplib.responses[httplib.OK])

    def _dns_example_com_serial_NOT_FOUND(self, method, url, body, headers):
        body = self.fixtures.load("zone_not_found.json")
        return (
            httplib.NOT_FOUND,
            body,
            self.base_headers,
            httplib.responses[httplib.NOT_FOUND],
        )

    def _dns_example_com_removeRR_NOT_FOUND(self, method, url, body, headers):
        body = self.fixtures.load("record_not_removed.json")
        return (
            httplib.NOT_FOUND,
            body,
            self.base_headers,
            httplib.responses[httplib.NOT_FOUND],
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
