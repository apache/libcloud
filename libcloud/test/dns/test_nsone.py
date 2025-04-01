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
from libcloud.dns.base import Zone, Record
from libcloud.dns.types import (
    RecordType,
    ZoneDoesNotExistError,
    ZoneAlreadyExistsError,
    RecordDoesNotExistError,
    RecordAlreadyExistsError,
)
from libcloud.utils.py3 import httplib
from libcloud.common.nsone import NsOneException
from libcloud.test.secrets import DNS_PARAMS_NSONE
from libcloud.dns.drivers.nsone import NsOneDNSDriver
from libcloud.test.file_fixtures import DNSFileFixtures


class NsOneTests(unittest.TestCase):
    def setUp(self):
        NsOneMockHttp.type = None
        NsOneMockHttp.history.clear()
        NsOneDNSDriver.connectionCls.conn_class = NsOneMockHttp
        self.driver = NsOneDNSDriver(*DNS_PARAMS_NSONE)
        self.example_zone = Zone(
            id="example.com",
            type="master",
            ttl=None,
            domain="example.com",
            extra={},
            driver=self,
        )
        self.test_zone = Zone(
            id="test.com",
            type="master",
            ttl=None,
            domain="test.com",
            extra={},
            driver=self,
        )
        self.test_record = Record(
            id="A",
            type=RecordType.A,
            name="test.com",
            zone=self.test_zone,
            data="127.0.0.1",
            driver=self,
            extra={},
        )

    def test_list_zones_empty(self):
        NsOneMockHttp.type = "EMPTY_ZONES_LIST"
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])

    def test_list_zones_success(self):
        zones = self.driver.list_zones()

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v1/zones")

        self.assertEqual(len(zones), 2)

        zone = zones[0]
        self.assertEqual(zone.id, "example.com")
        self.assertIsNone(zone.type)
        self.assertEqual(zone.domain, "example.com")
        self.assertEqual(zone.ttl, 3600)

        zone = zones[1]
        self.assertEqual(zone.id, "nsoneisgreat.com")
        self.assertIsNone(zone.type)
        self.assertEqual(zone.domain, "nsoneisgreat.com")
        self.assertEqual(zone.ttl, 3600)

    def test_delete_zone_zone_does_not_exist(self):
        NsOneMockHttp.type = "DELETE_ZONE_ZONE_DOES_NOT_EXIST"

        try:
            self.driver.delete_zone(zone=self.test_zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail("Exception was not thrown")

    def test_delete_zone_success(self):
        NsOneMockHttp.type = "DELETE_ZONE_SUCCESS"
        status = self.driver.delete_zone(zone=self.test_zone)

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "DELETE")
        self.assertEqual(sent.url, "/v1/zones/test.com")

        self.assertTrue(status)

    def test_get_zone_zone_does_not_exist(self):
        NsOneMockHttp.type = "GET_ZONE_ZONE_DOES_NOT_EXIST"
        try:
            self.driver.get_zone(zone_id="zonedoesnotexist.com")
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, "zonedoesnotexist.com")
        else:
            self.fail("Exception was not thrown")

    def test_get_zone_success(self):
        NsOneMockHttp.type = "GET_ZONE_SUCCESS"
        zone = self.driver.get_zone(zone_id="example.com")

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v1/zones/example.com")

        self.assertEqual(zone.id, "example.com")
        self.assertEqual(zone.domain, "example.com")
        self.assertIsNone(zone.type),
        self.assertEqual(zone.ttl, 3600)

    def test_create_zone_success(self):
        NsOneMockHttp.type = "CREATE_ZONE_SUCCESS"
        zone = self.driver.create_zone(domain="newzone.com")

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "PUT")
        self.assertEqual(sent.url, "/v1/zones/newzone.com")
        self.assertEqual(sent.json["zone"], "newzone.com")

        self.assertEqual(zone.id, "newzone.com")
        self.assertEqual(zone.domain, "newzone.com")
        self.assertIsNone(zone.type),
        self.assertEqual(zone.ttl, 3600)

    def test_create_zone_zone_already_exists(self):
        NsOneMockHttp.type = "CREATE_ZONE_ZONE_ALREADY_EXISTS"

        try:
            self.driver.create_zone(domain="newzone.com")
        except ZoneAlreadyExistsError as e:
            self.assertEqual(e.zone_id, "newzone.com")
        else:
            self.fail("Exception was not thrown")

    def test_get_record_record_does_not_exist(self):
        NsOneMockHttp.type = "GET_RECORD_DOES_NOT_EXIST"

        try:
            self.driver.get_record(zone_id="example.com", record_id="A")
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, "A")
        else:
            self.fail("Exception was not thrown")

    def test_get_record_success(self):
        NsOneMockHttp.type = "GET_RECORD_SUCCESS"
        record = self.driver.get_record(zone_id="example.com", record_id="A:www")

        # [0] /v1/zones/example.com
        # [1] /v1/zones/example.com/www.example.com/A
        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v1/zones/example.com/www.example.com/A")

        self.assertEqual(record.id, "A:www")
        self.assertEqual(record.name, "www.example.com")
        self.assertEqual(record.data, ["1.1.1.1"])
        self.assertEqual(record.type, RecordType.A)

    def test_list_records_zone_does_not_exist(self):
        NsOneMockHttp.type = "LIST_RECORDS_ZONE_DOES_NOT_EXIST"

        try:
            self.driver.list_records(zone=self.test_zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, self.test_zone.id)
        else:
            self.fail("Exception was not thrown")

    def test_list_records_empty(self):
        NsOneMockHttp.type = "LIST_RECORDS_EMPTY"
        records = self.driver.list_records(zone=self.test_zone)

        self.assertEqual(records, [])

    def test_list_records_success(self):
        NsOneMockHttp.type = "LIST_RECORDS_SUCCESS"
        records = self.driver.list_records(zone=self.example_zone)

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.url, "/v1/zones/example.com")

        self.assertEqual(len(records), 2)

        arecord = records[1]
        self.assertEqual(arecord.id, "A:www")
        self.assertEqual(arecord.name, "www.example.com")
        self.assertEqual(arecord.type, RecordType.A)
        self.assertEqual(arecord.data, ["1.2.3.4"])

    def test_create_record_success(self):
        NsOneMockHttp.type = "CREATE_RECORD_SUCCESS"
        arecord = self.driver.create_record(
            self.test_record.name,
            self.test_record.zone,
            self.test_record.type,
            self.test_record.data,
            self.test_record.extra,
        )

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "PUT")
        self.assertEqual(sent.url, "/v1/zones/test.com/test.com/A")
        self.assertEqual(sent.json["zone"], "test.com")
        self.assertEqual(sent.json["domain"], "test.com")
        self.assertEqual(sent.json["type"], "A")
        self.assertIn({"answer": ["127.0.0.1"]}, sent.json["answers"])

        self.assertEqual(arecord.id, "A")
        self.assertEqual(arecord.name, "test.com")
        self.assertEqual(arecord.type, RecordType.A)
        self.assertEqual(arecord.data, ["127.0.0.1"])

    def test_create_record_already_exists(self):
        NsOneMockHttp.type = "CREATE_RECORD_ALREADY_EXISTS"
        try:
            self.driver.create_record(
                self.test_record.name,
                self.test_record.zone,
                self.test_record.type,
                self.test_record.data,
                self.test_record.extra,
            )
        except RecordAlreadyExistsError as err:
            self.assertEqual(err.value, "record already exists")
        else:
            self.fail("Exception was not thrown")

    def test_create_record_zone_not_found(self):
        NsOneMockHttp.type = "CREATE_RECORD_ZONE_NOT_FOUND"
        try:
            self.driver.create_record(
                self.test_record.name,
                self.test_record.zone,
                self.test_record.type,
                self.test_record.data,
                self.test_record.extra,
            )
        except NsOneException as err:
            self.assertEqual(err.message, "zone not found")
        else:
            self.fail("Exception was not thrown")

    def test_delete_record_record_does_not_exist(self):
        NsOneMockHttp.type = "DELETE_RECORD_RECORD_DOES_NOT_EXIST"

        try:
            self.driver.delete_record(record=self.test_record)
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, self.test_record.id)
        else:
            self.fail("Exception was not thrown")

    def test_delete_record_success(self):
        NsOneMockHttp.type = "DELETE_RECORD_SUCCESS"
        status = self.driver.delete_record(record=self.test_record)

        sent = NsOneMockHttp.history.pop()
        self.assertEqual(sent.method, "DELETE")
        self.assertEqual(sent.url, "/v1/zones/test.com/test.com/A")

        self.assertTrue(status)


class NsOneMockHttp(MockHttp):
    fixtures = DNSFileFixtures("nsone")
    keep_history = True

    def _v1_zones_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load("empty_zones_list.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones(self, method, url, body, headers):
        body = self.fixtures.load("list_zones.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_GET_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("get_zone_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_zonedoesnotexist_com_GET_ZONE_ZONE_DOES_NOT_EXIST(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("zone_does_not_exist.json")

        return 404, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_DELETE_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("delete_zone_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_DELETE_ZONE_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_does_not_exist.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_newzone_com_CREATE_ZONE_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("create_zone_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_newzone_com_CREATE_ZONE_ZONE_ALREADY_EXISTS(self, method, url, body, headers):
        body = self.fixtures.load("zone_already_exists.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_LIST_RECORDS_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("get_zone_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_LIST_RECORDS_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load("list_records_empty.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_LIST_RECORDS_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_does_not_exist.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_test_com_A_DELETE_RECORD_RECORD_DOES_NOT_EXIST(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("record_does_not_exist.json")

        return 404, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_test_com_A_DELETE_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("delete_record_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_www_example_com_A_GET_RECORD_SUCCESS(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("get_record_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_GET_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("get_zone_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_example_com_A_GET_RECORD_DOES_NOT_EXIST(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("record_does_not_exist.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_example_com_GET_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        return self._v1_zones_example_com_GET_RECORD_SUCCESS(method, url, body, headers)

    def _v1_zones_test_com_test_com_A_CREATE_RECORD_SUCCESS(self, method, url, body, headers):
        body = self.fixtures.load("create_record_success.json")

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_test_com_A_CREATE_RECORD_ALREADY_EXISTS(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("create_record_already_exists.json")

        return 404, body, {}, httplib.responses[httplib.OK]

    def _v1_zones_test_com_test_com_A_CREATE_RECORD_ZONE_NOT_FOUND(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("create_record_zone_not_found.json")

        return 404, body, {}, httplib.responses[httplib.OK]


if __name__ == "__main__":
    sys.exit(unittest.main())
