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

from libcloud.http import LibcloudConnection
from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.dns.types import RecordType
from libcloud.utils.py3 import httplib
from libcloud.test.secrets import DIGITALOCEAN_v2_PARAMS
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.common.digitalocean import DigitalOceanBaseDriver, DigitalOcean_v2_BaseDriver
from libcloud.dns.drivers.digitalocean import DigitalOceanDNSDriver


class DigitalOceanDNSTests(LibcloudTestCase):
    def setUp(self):
        DigitalOceanBaseDriver.connectionCls.conn_class = DigitalOceanDNSMockHttp
        DigitalOcean_v2_BaseDriver.connectionCls.conn_class = DigitalOceanDNSMockHttp
        DigitalOceanDNSDriver.connectionCls.conn_class = DigitalOceanDNSMockHttp
        DigitalOceanDNSMockHttp.type = None
        DigitalOceanDNSMockHttp.history.clear()
        self.driver = DigitalOceanDNSDriver(*DIGITALOCEAN_v2_PARAMS)

    def tearDown(self):
        LibcloudConnection.type = None
        DigitalOceanDNSMockHttp.type = None
        DigitalOceanDNSMockHttp.history.clear()

    def test_list_zones(self):
        zones = self.driver.list_zones()

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v2/domains")

        self.assertTrue(len(zones) >= 1)

    def test_get_zone(self):
        zone = self.driver.get_zone("testdomain")

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v2/domains/testdomain")

        self.assertEqual(zone.id, "testdomain")

    def test_get_zone_not_found(self):
        DigitalOceanDNSMockHttp.type = "NOT_FOUND"
        self.assertRaises(Exception, self.driver.get_zone, "testdomain")

    def test_list_records(self):
        zone = self.driver.get_zone("testdomain")
        records = self.driver.list_records(zone)

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v2/domains/testdomain/records")

        self.assertTrue(len(records) >= 1)
        self.assertEqual(records[1].ttl, 1800)
        self.assertEqual(records[4].ttl, None)

    def test_get_record(self):
        record = self.driver.get_record("testdomain", "1234564")

        # [0] '/v2/domains/testdomain/records/1234564'
        # [1] '/v2/domains/testdomain'
        sent = DigitalOceanDNSMockHttp.history[0]
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v2/domains/testdomain/records/1234564")

        self.assertEqual(record.id, "1234564")
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, "123.45.67.89")
        self.assertEqual(record.ttl, 1800)

    def test_get_record_not_found(self):
        DigitalOceanDNSMockHttp.type = "NOT_FOUND"
        self.assertRaises(Exception, self.driver.get_zone, "testdomain")

    def test_create_zone(self):
        DigitalOceanDNSMockHttp.type = "CREATE"
        zone = self.driver.create_zone("testdomain")

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/v2/domains")
        self.assertEqual(sent.json["name"], "testdomain")

        self.assertEqual(zone.id, "testdomain")

    def test_create_record(self):
        zone = self.driver.get_zone("testdomain")

        DigitalOceanDNSMockHttp.type = "CREATE"
        record = self.driver.create_record(
            "sub", zone, RecordType.A, "234.56.78.90", extra={"ttl": 60}
        )

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, f"/v2/domains/{zone.domain}/records")
        self.assertEqual(sent.json["type"], "A")
        self.assertEqual(sent.json["name"], "sub")
        self.assertEqual(sent.json["data"], "234.56.78.90")
        self.assertEqual(sent.json["ttl"], 60)

        self.assertEqual(record.id, "1234565")
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, "234.56.78.90")
        self.assertEqual(record.ttl, 60)

    def test_update_record(self):
        record = self.driver.get_record("testdomain", "1234564")

        DigitalOceanDNSMockHttp.type = "UPDATE"
        record = self.driver.update_record(record, data="234.56.78.90", extra={"ttl": 60})

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertIn(sent.method, {"PATCH", "PUT"})
        self.assertEqual(sent.url, f"/v2/domains/testdomain/records/{record.id}")
        self.assertEqual(sent.json["type"], "A")
        self.assertEqual(sent.json["name"], "@")
        self.assertEqual(sent.json["data"], "234.56.78.90")
        self.assertEqual(sent.json["ttl"], 60)

        self.assertEqual(record.id, "1234564")
        self.assertEqual(record.data, "234.56.78.90")
        self.assertEqual(record.ttl, 60)

    def test_delete_zone(self):
        zone = self.driver.get_zone("testdomain")

        DigitalOceanDNSMockHttp.type = "DELETE"
        self.assertTrue(self.driver.delete_zone(zone))

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertEqual(sent.method, "DELETE")
        self.assertEqual(sent.url, f"/v2/domains/{zone.domain}")

    def test_delete_record(self):
        record = self.driver.get_record("testdomain", "1234564")

        DigitalOceanDNSMockHttp.type = "DELETE"
        self.assertTrue(self.driver.delete_record(record))

        sent = DigitalOceanDNSMockHttp.history.pop()
        self.assertIn(sent.method, "DELETE")
        self.assertEqual(sent.url, f"/v2/domains/testdomain/records/{record.id}")


class DigitalOceanDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures("digitalocean")
    keep_history = True

    response_map = {
        None: httplib.OK,
        "CREATE": httplib.CREATED,
        "DELETE": httplib.NO_CONTENT,
        "EMPTY": httplib.OK,
        "NOT_FOUND": httplib.NOT_FOUND,
        "UNAUTHORIZED": httplib.UNAUTHORIZED,
        "UPDATE": httplib.OK,
        "UNPROCESSABLE": httplib.UNPROCESSABLE_ENTITY,
    }

    def _v2_domains(self, method, url, body, headers):
        body = self.fixtures.load("_v2_domains.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_CREATE(self, method, url, body, headers):
        if body is None:
            body = self.fixtures.load("_v2_domains_UNPROCESSABLE_ENTITY.json")
            return (
                self.response_map["UNPROCESSABLE"],
                body,
                {},
                httplib.responses[self.response_map["UNPROCESSABLE"]],
            )
        body = self.fixtures.load("_v2_domains_CREATE.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain(self, method, url, body, headers):
        body = self.fixtures.load("_v2_domains_testdomain.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_DELETE(self, method, url, body, headers):
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_NOT_FOUND(self, method, url, body, headers):
        body = self.fixtures.load("_v2_domains_testdomain_NOT_FOUND.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_records(self, method, url, body, headers):
        body = self.fixtures.load("_v2_domains_testdomain_records.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_records_CREATE(self, method, url, body, headers):
        if body is None:
            body = self.fixtures.load("_v2_domains_UNPROCESSABLE_ENTITY.json")
            return (
                self.response_map["UNPROCESSABLE"],
                body,
                {},
                httplib.responses[self.response_map["UNPROCESSABLE"]],
            )
        body = self.fixtures.load("_v2_domains_testdomain_records_CREATE.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_records_1234564(self, method, url, body, headers):
        body = self.fixtures.load("_v2_domains_testdomain_records_1234564.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_records_1234564_DELETE(self, method, url, body, headers):
        self.type = "DELETE"
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )

    def _v2_domains_testdomain_records_1234564_UPDATE(self, method, url, body, headers):
        if body is None:
            body = self.fixtures.load("_v2_domains_UNPROCESSABLE_ENTITY.json")
            return (
                self.response_map["UNPROCESSABLE"],
                body,
                {},
                httplib.responses[self.response_map["UNPROCESSABLE"]],
            )
        body = self.fixtures.load("_v2_domains_testdomain_records_1234564_UPDATE.json")
        return (
            self.response_map[self.type],
            body,
            {},
            httplib.responses[self.response_map[self.type]],
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
