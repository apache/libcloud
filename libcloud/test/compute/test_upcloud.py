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


import re
import sys
import json
import base64

from libcloud.test import MockHttp, LibcloudTestCase, unittest
from libcloud.compute import providers
from libcloud.utils.py3 import httplib, ensure_string
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import (
    Node,
    NodeSize,
    NodeImage,
    NodeLocation,
    StorageVolume,
    NodeAuthSSHKey,
)
from libcloud.test.secrets import UPCLOUD_PARAMS
from libcloud.compute.types import Provider, NodeState
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.drivers.upcloud import UpcloudDriver, UpcloudResponse


class UpcloudPersistResponse(UpcloudResponse):
    def parse_body(self):
        import os

        path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                os.path.pardir,
                "compute",
                "fixtures",
                "upcloud",
            )
        )
        filename = "api" + self.request.path_url.replace("/", "_").replace(".", "_") + ".json"
        filename = os.path.join(path, filename)
        if not os.path.exists(filename):
            with open(filename, "w+") as f:
                f.write(self.body)
        return super().parse_body()


class UpcloudAuthenticationTests(LibcloudTestCase):
    def setUp(self):
        UpcloudDriver.connectionCls.conn_class = UpcloudMockHttp
        self.driver = UpcloudDriver("nosuchuser", "nopwd")

    def test_authentication_fails(self):
        with self.assertRaises(InvalidCredsError):
            self.driver.list_locations()

    def test_authentication_with_api_token(self):
        driver = UpcloudDriver(token="test-token")
        driver.list_locations()

        self.assertEqual(UpcloudMockHttp.last_authorization, "Bearer test-token")

    def test_authentication_requires_basic_credentials_or_token(self):
        with self.assertRaises(ValueError):
            UpcloudDriver()


class UpcloudDriverTests(LibcloudTestCase):
    def setUp(self):
        UpcloudDriver.connectionCls.conn_class = UpcloudMockHttp
        # UpcloudDriver.connectionCls.responseCls = UpcloudPersistResponse
        self.driver = UpcloudDriver(*UPCLOUD_PARAMS)

    def test_creating_driver(self):
        cls = providers.get_driver(Provider.UPCLOUD)
        self.assertIs(cls, UpcloudDriver)

    def test_features(self):
        features = self.driver.features["create_node"]
        self.assertIn("ssh_key", features)
        self.assertIn("generates_password", features)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) >= 1)
        expected_node_location = NodeLocation(
            id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver
        )
        self.assert_object(expected_node_location, objects=locations)

    def test_list_sizes(self):
        location = NodeLocation(id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver)
        sizes = self.driver.list_sizes(location)
        self.assertTrue(len(sizes) >= 1)
        expected_node_size = NodeSize(
            id="1xCPU-1GB",
            name="1xCPU-1GB",
            ram=1024,
            disk=30,
            bandwidth=2048,
            price=2.232,
            driver=self.driver,
            extra={"core_number": 1, "storage_tier": "maxiops"},
        )
        self.assert_object(expected_node_size, objects=sizes)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)
        expected_node_image = NodeImage(
            id="01000000-0000-4000-8000-000010010101",
            name="Windows Server 2003 R2 Standard (CD 1)",
            driver=self.driver,
            extra={
                "access": "public",
                "license": 0,
                "size": 1,
                "state": "online",
                "type": "cdrom",
            },
        )
        self.assert_object(expected_node_image, objects=images)

    def test_create_node_from_template(self):
        image = NodeImage(
            id="01000000-0000-4000-8000-000030060200",
            name="Ubuntu Server 16.04 LTS (Xenial Xerus)",
            extra={"type": "template"},
            driver=self.driver,
        )
        location = NodeLocation(id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver)
        size = NodeSize(
            id="1xCPU-1GB",
            name="1xCPU-1GB",
            ram=1024,
            disk=30,
            bandwidth=2048,
            extra={"storage_tier": "maxiops"},
            price=None,
            driver=self.driver,
        )
        node = self.driver.create_node(
            name="test_server",
            size=size,
            image=image,
            location=location,
            ex_hostname="myhost.somewhere",
        )

        self.assertTrue(
            re.match(
                "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
                node.id,
            )
        )
        self.assertEqual(node.name, "test_server")
        self.assertEqual(node.state, NodeState.STARTING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)
        self.assertTrue(len(node.extra["password"]) > 0)
        self.assertTrue(len(node.extra["vnc_password"]) > 0)

    def test_create_node_with_ssh_keys(self):
        image = NodeImage(
            id="01000000-0000-4000-8000-000030060200",
            name="Ubuntu Server 16.04 LTS (Xenial Xerus)",
            extra={"type": "template"},
            driver=self.driver,
        )
        location = NodeLocation(id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver)
        size = NodeSize(
            id="1xCPU-1GB",
            name="1xCPU-1GB",
            ram=1024,
            disk=30,
            bandwidth=2048,
            extra={"storage_tier": "maxiops"},
            price=None,
            driver=self.driver,
        )

        auth = NodeAuthSSHKey("publikey")
        node = self.driver.create_node(
            name="test_server", size=size, image=image, location=location, auth=auth
        )
        self.assertTrue(
            re.match(
                "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
                node.id,
            )
        )
        self.assertEqual(node.name, "test_server")
        self.assertEqual(node.state, NodeState.STARTING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)

    def test_create_node_with_extra_storage_devices(self):
        image = NodeImage(
            id="01000000-0000-4000-8000-000030060200",
            name="Ubuntu Server 16.04 LTS (Xenial Xerus)",
            extra={"type": "template"},
            driver=self.driver,
        )
        location = NodeLocation(id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver)
        size = NodeSize(
            id="1xCPU-1GB",
            name="1xCPU-1GB",
            ram=1024,
            disk=30,
            bandwidth=2048,
            extra={"storage_tier": "maxiops"},
            price=None,
            driver=self.driver,
        )
        extra_storage = {
            "action": "create",
            "title": "data",
            "size": 25,
            "tier": "maxiops",
        }

        self.driver.create_node(
            name="test_server",
            size=size,
            image=image,
            location=location,
            ex_storage_devices=[extra_storage],
        )

        storage_devices = UpcloudMockHttp.last_request_body["server"]["storage_devices"][
            "storage_device"
        ]
        self.assertEqual(len(storage_devices), 2)
        self.assertEqual(storage_devices[1], extra_storage)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 2)

        volume = volumes[0]
        self.assertIsInstance(volume, StorageVolume)
        self.assertEqual(volume.id, "01eff7ad-168e-413e-83b0-054f6a28fa23")
        self.assertEqual(volume.name, "Operating system disk")
        self.assertEqual(volume.size, 10)
        self.assertEqual(volume.extra["tier"], "hdd")
        self.assertEqual(volume.extra["zone"], "uk-lon1")

    def test_create_volume(self):
        location = NodeLocation(id="fi-hel1", name="Helsinki #1", country="FI", driver=self.driver)
        volume = self.driver.create_volume(
            size=50,
            name="data",
            location=location,
            ex_tier="maxiops",
        )

        self.assertEqual(volume.id, "01d4fcd4-e446-433b-8a9c-551a1284952e")
        self.assertEqual(volume.name, "data")
        self.assertEqual(volume.size, 50)
        request_storage = UpcloudMockHttp.last_request_body["storage"]
        self.assertEqual(request_storage["tier"], "maxiops")
        self.assertNotIn("encrypted", request_storage)
        self.assertNotIn("labels", request_storage)

    def test_create_volume_requires_location(self):
        with self.assertRaises(ValueError):
            self.driver.create_volume(size=50, name="data")

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.list_volumes()[1]

        success = self.driver.attach_volume(node, volume, device="scsi")

        self.assertTrue(success)
        request_device = UpcloudMockHttp.last_request_body["storage_device"]
        self.assertEqual(request_device["storage"], volume.id)
        self.assertEqual(request_device["address"], "scsi")
        self.assertEqual(request_device["boot_disk"], "0")

    def test_detach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.list_volumes()[1]
        self.assertTrue(self.driver.detach_volume(volume, ex_node=node, ex_address="scsi:0:0"))

        request_device = UpcloudMockHttp.last_request_body["storage_device"]
        self.assertEqual(request_device["address"], "scsi:0:0")

    def test_detach_volume_requires_node_and_address(self):
        volume = self.driver.list_volumes()[1]
        with self.assertRaises(ValueError):
            self.driver.detach_volume(volume)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[1]
        self.assertTrue(self.driver.destroy_volume(volume))

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()

        self.assertTrue(len(nodes) >= 1)
        node = nodes[0]
        self.assertEqual(node.name, "test_server")
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertTrue(len(node.public_ips) > 0)
        self.assertTrue(len(node.private_ips) > 0)
        self.assertEqual(node.driver, self.driver)

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        success = self.driver.reboot_node(nodes[0])
        self.assertTrue(success)

    def test_start_node(self):
        nodes = self.driver.list_nodes()
        success = self.driver.start_node(nodes[0])

        self.assertTrue(success)
        self.assertIsNone(UpcloudMockHttp.last_request_body)

    def test_stop_node(self):
        nodes = self.driver.list_nodes()
        success = self.driver.stop_node(nodes[0], ex_stop_type="soft", ex_timeout=60)

        self.assertTrue(success)
        self.assertEqual(
            UpcloudMockHttp.last_request_body,
            {"stop_server": {"stop_type": "soft", "timeout": 60}},
        )

    def test_destroy_node(self):
        if UpcloudDriver.connectionCls.conn_class == UpcloudMockHttp:
            nodes = [
                Node(
                    id="00893c98_5d5a_4363_b177_88df518a2b60",
                    name="",
                    state="",
                    public_ips=[],
                    private_ips=[],
                    driver=self.driver,
                )
            ]
        else:
            nodes = self.driver.list_nodes()
        success = self.driver.destroy_node(nodes[0])
        self.assertTrue(success)

    def assert_object(self, expected_object, objects):
        same_data = any([self.objects_equals(expected_object, obj) for obj in objects])
        self.assertTrue(same_data, "Objects does not match")

    def objects_equals(self, expected_obj, obj):
        for name in vars(expected_obj):
            expected_data = getattr(expected_obj, name)
            actual_data = getattr(obj, name)
            same_data = self.data_equals(expected_data, actual_data)
            if not same_data:
                break
        return same_data

    def data_equals(self, expected_data, actual_data):
        if isinstance(expected_data, dict):
            return self.dicts_equals(expected_data, actual_data)
        else:
            return expected_data == actual_data

    def dicts_equals(self, d1, d2):
        dict_keys_same = set(d1.keys()) == set(d2.keys())
        if not dict_keys_same:
            return False

        for key in d1.keys():
            if d1[key] != d2[key]:
                return False

        return True


class UpcloudMockHttp(MockHttp):
    fixtures = ComputeFileFixtures("upcloud")
    last_request_body = None
    last_authorization = None

    def _1_2_zone(self, method, url, body, headers):
        self.__class__.last_authorization = headers["Authorization"]
        auth_type, auth_value = headers["Authorization"].split(" ", 1)

        if auth_type == "Bearer":
            body = self.fixtures.load("api_1_2_zone.json")
            status_code = httplib.OK
        else:
            username, password = ensure_string(base64.b64decode(auth_value)).split(":")
            if username == "nosuchuser" and password == "nopwd":
                body = self.fixtures.load("api_1_2_zone_failed_auth.json")
                status_code = httplib.UNAUTHORIZED
            else:
                body = self.fixtures.load("api_1_2_zone.json")
                status_code = httplib.OK

        return (status_code, body, {}, httplib.responses[httplib.OK])

    def _1_2_plan(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_plan.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_storage_cdrom(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_storage_cdrom.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_storage_template(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_storage_template.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_price(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_price.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server(self, method, url, body, headers):
        if method == "POST":
            dbody = json.loads(body)
            self.__class__.last_request_body = dbody
            storages = dbody["server"]["storage_devices"]["storage_device"]
            if any(["type" in storage and storage["type"] == "cdrom" for storage in storages]):
                body = self.fixtures.load("api_1_2_server_from_cdrom.json")
            else:
                body = self.fixtures.load("api_1_2_server_from_template.json")
        else:
            body = self.fixtures.load("api_1_2_server.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_storage_normal(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_storage_normal.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_storage(self, method, url, body, headers):
        self.__class__.last_request_body = json.loads(body)
        body = self.fixtures.load("api_1_2_storage_create.json")
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc_storage_attach(
        self, method, url, body, headers
    ):
        self.__class__.last_request_body = json.loads(body)
        body = self.fixtures.load("api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc_storage_detach(
        self, method, url, body, headers
    ):
        self.__class__.last_request_body = json.loads(body)
        body = self.fixtures.load("api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_storage_01d4fcd4_e446_433b_8a9c_551a1284952e(self, method, url, body, headers):
        return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc_restart(self, method, url, body, headers):
        body = self.fixtures.load(
            "api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc_restart.json"
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc_start(self, method, url, body, headers):
        self.__class__.last_request_body = body
        body = self.fixtures.load("api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server_00f8c525_7e62_4108_8115_3958df5b43dc_stop(self, method, url, body, headers):
        self.__class__.last_request_body = json.loads(body)
        body = self.fixtures.load("api_1_2_server_00f8c525-7e62-4108-8115-3958df5b43dc.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_2_server_00893c98_5d5a_4363_b177_88df518a2b60(self, method, url, body, headers):
        body = self.fixtures.load("api_1_2_server_00893c98-5d5a-4363-b177-88df518a2b60.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
