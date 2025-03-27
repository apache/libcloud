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

from libcloud.dns.types import RecordType, ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.utils.py3 import httplib
from libcloud.test.secrets import DNS_GANDI
from libcloud.dns.drivers.gandi import GandiDNSDriver
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.common.test_gandi import BaseGandiMockHttp


class GandiTests(unittest.TestCase):
    def setUp(self):
        GandiDNSDriver.connectionCls.conn_class = GandiMockHttp
        GandiMockHttp.type = None
        GandiMockHttp.history.clear()
        self.driver = GandiDNSDriver(*DNS_GANDI)

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 10)
        self.assertTrue(RecordType.A in record_types)

    def test_list_zones(self):
        zones = self.driver.list_zones()

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        self.assertIn("<methodName>domain.zone.list</", sent.body)

        self.assertEqual(len(zones), 5)

        zone = zones[0]
        self.assertEqual(zone.id, "47234")
        self.assertEqual(zone.type, "master")
        self.assertEqual(zone.domain, "t.com")

    def test_list_records(self):
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.record.list</", data)
        self.assertIn("<value><int>47234</int></", data)

        self.assertEqual(len(records), 4)

        record = records[1]
        self.assertEqual(record.name, "www")
        self.assertEqual(record.id, "A:www")
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, "208.111.35.173")

        record = records[3]
        self.assertEqual(record.name, "")
        self.assertEqual(record.id, "MX:")
        self.assertEqual(record.type, RecordType.MX)
        self.assertEqual(record.data, "aspmx.l.google.com")
        self.assertEqual(record.extra["priority"], 15)
        self.assertEqual(record.extra["ttl"], 86400)

    def test_get_zone(self):
        zone = self.driver.get_zone(zone_id="47234")

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.info</", data)
        self.assertIn("<value><int>47234</int></", data)

        self.assertEqual(zone.id, "47234")
        self.assertEqual(zone.type, "master")
        self.assertEqual(zone.domain, "t.com")

    def test_get_record(self):
        record = self.driver.get_record(zone_id="47234", record_id="CNAME:t.com")
        self.assertEqual(record.name, "wibble")
        self.assertEqual(record.type, RecordType.CNAME)
        self.assertEqual(record.data, "t.com")

    def test_list_records_zone_does_not_exist(self):
        zone = self.driver.list_zones()[0]

        GandiMockHttp.type = "ZONE_DOES_NOT_EXIST"

        try:
            self.driver.list_records(zone=zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, zone.id)
        else:
            self.fail("Exception was not thrown")

    def test_get_zone_does_not_exist(self):
        GandiMockHttp.type = "ZONE_DOES_NOT_EXIST"

        try:
            self.driver.get_zone(zone_id="47234")
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, "47234")
        else:
            self.fail("Exception was not thrown")

    def test_get_record_zone_does_not_exist(self):
        GandiMockHttp.type = "ZONE_DOES_NOT_EXIST"

        try:
            self.driver.get_record(zone_id="4444", record_id="CNAME:t.com")
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail("Exception was not thrown")

    def test_get_record_record_does_not_exist(self):
        GandiMockHttp.type = "RECORD_DOES_NOT_EXIST"

        try:
            self.driver.get_record(zone_id="47234", record_id="CNAME:t.com")
        except RecordDoesNotExistError:
            pass
        else:
            self.fail("Exception was not thrown")

    def test_create_zone(self):
        zone = self.driver.create_zone(domain="t.com", type="master", ttl=None, extra=None)

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.create</", data)
        self.assertIn("<value><string>t.com</string></", data)

        self.assertEqual(zone.id, "47234")
        self.assertEqual(zone.domain, "t.com")

    def test_update_zone(self):
        pre_zone = self.driver.get_zone(zone_id="47234")
        zone = self.driver.update_zone(pre_zone, domain="other.com")

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.update</", data)
        self.assertIn("<value><int>47234</int></", data)
        self.assertIn("<value><string>other.com</string></", data)

        self.assertEqual(pre_zone.domain, "t.com")

        self.assertEqual(zone.id, "47234")
        self.assertEqual(zone.type, "master")
        self.assertEqual(zone.domain, "other.com")

    def test_create_record(self):
        zone = self.driver.list_zones()[0]
        GandiMockHttp.history.clear()

        record = self.driver.create_record(
            name="www",
            zone=zone,
            type=RecordType.A,
            data="127.0.0.1",
            extra={"ttl": 30},
        )

        # [0] domain.version.new
        # [1] domain.zone.record.add
        # [2] domain.version.set
        sent = GandiMockHttp.history[1]
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.record.add</", data)
        self.assertIn(f"<value><int>{zone.id}</int></", data)
        self.assertIn("<value><string>www</string></", data)
        self.assertIn("<value><string>127.0.0.1</string></", data)
        self.assertIn("<value><int>30</int></", data)

        self.assertEqual(record.id, "A:www")
        self.assertEqual(record.name, "www")
        self.assertEqual(record.zone, zone)
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, "127.0.0.1")

    def test_update_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[1]
        GandiMockHttp.history.clear()

        params = {
            "record": record,
            "name": "www",
            "type": RecordType.A,
            "data": "127.0.0.1",
            "extra": {"ttl": 30},
        }
        updated_record = self.driver.update_record(**params)

        # [0] domain.version.new
        # [1] domain.zone.record.delete
        # [2] domain.zone.record.add
        # [3] domain.version.set
        sent = GandiMockHttp.history[2]
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.record.add</", data)
        self.assertIn(f"<value><int>{zone.id}</int></", data)
        self.assertIn("<value><string>www</string></", data)
        self.assertIn("<value><string>A</string></", data)
        self.assertIn("<value><string>127.0.0.1</string></", data)
        self.assertIn("<value><int>30</int></", data)

        self.assertEqual(record.data, "208.111.35.173")

        self.assertEqual(updated_record.id, "A:www")
        self.assertEqual(updated_record.name, "www")
        self.assertEqual(updated_record.zone, record.zone)
        self.assertEqual(updated_record.type, RecordType.A)
        self.assertEqual(updated_record.data, "127.0.0.1")

    def test_delete_zone(self):
        zone = self.driver.list_zones()[0]
        status = self.driver.delete_zone(zone=zone)

        sent = GandiMockHttp.history.pop()
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.delete</", data)
        self.assertIn(f"<value><int>{zone.id}</int></", data)

        self.assertTrue(status)

    def test_delete_zone_does_not_exist(self):
        zone = self.driver.list_zones()[0]

        GandiMockHttp.type = "ZONE_DOES_NOT_EXIST"

        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError as e:
            self.assertEqual(e.zone_id, zone.id)
        else:
            self.fail("Exception was not thrown")

    def test_delete_record(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[0]
        GandiMockHttp.history.clear()

        status = self.driver.delete_record(record=record)

        # [0] domain.version.new
        # [1] domain.zone.record.delete
        # [2] domain.version.set
        sent = GandiMockHttp.history[1]
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.url, "/xmlrpc/")
        data = sent.body.replace(">/n<", "><")
        self.assertIn("<methodName>domain.zone.record.delete</", data)
        self.assertIn(f"<value><int>{zone.id}</int></", data)
        self.assertIn("<value><int>1</int></", data)
        self.assertIn(f"<value><string>{record.name}</string></", data)

        self.assertTrue(status)

    def test_delete_record_does_not_exist(self):
        zone = self.driver.list_zones()[0]
        record = self.driver.list_records(zone=zone)[0]
        GandiMockHttp.type = "RECORD_DOES_NOT_EXIST"
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError as e:
            self.assertEqual(e.record_id, record.id)
        else:
            self.fail("Exception was not thrown")


class GandiMockHttp(BaseGandiMockHttp):
    fixtures = DNSFileFixtures("gandi")
    keep_history = True

    def _xmlrpc__domain_zone_create(self, method, url, body, headers):
        body = self.fixtures.load("create_zone.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_update(self, method, url, body, headers):
        body = self.fixtures.load("update_zone.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_list(self, method, url, body, headers):
        body = self.fixtures.load("list_zones.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_list(self, method, url, body, headers):
        body = self.fixtures.load("list_records.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_add(self, method, url, body, headers):
        body = self.fixtures.load("create_record.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_delete(self, method, url, body, headers):
        body = self.fixtures.load("delete_zone.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_info(self, method, url, body, headers):
        body = self.fixtures.load("get_zone.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_delete(self, method, url, body, headers):
        body = self.fixtures.load("delete_record.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_update(self, method, url, body, headers):
        body = self.fixtures.load("create_record.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_version_new(self, method, url, body, headers):
        body = self.fixtures.load("new_version.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_version_set(self, method, url, body, headers):
        body = self.fixtures.load("new_version.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_list_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_doesnt_exist.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_info_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_doesnt_exist.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_list_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_doesnt_exist.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_delete_ZONE_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("zone_doesnt_exist.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_list_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("list_records_empty.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_info_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("list_zones.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_record_delete_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("delete_record_doesnotexist.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_version_new_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("new_version.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc__domain_zone_version_set_RECORD_DOES_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load("new_version.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
