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
from unittest.mock import patch

from libcloud.http import LibcloudConnection
from libcloud.test import no_internet
from libcloud.utils.py3 import httplib
from libcloud.test.secrets import OVH_PARAMS
from libcloud.common.exceptions import BaseHTTPError
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import NodeState
from libcloud.compute.drivers.ovh import OvhNodeDriver
from libcloud.test.common.test_ovh import BaseOvhMockHttp


class OvhMockHttp(BaseOvhMockHttp):
    """Fixtures needed for tests related to rating model"""

    fixtures = ComputeFileFixtures("ovh")

    def _json_1_0_auth_time_get(self, method, url, body, headers):
        body = self.fixtures.load("auth_time_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_region_get(self, method, url, body, headers):
        body = self.fixtures.load("region_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_get(self, method, url, body, headers):
        body = self.fixtures.load("flavor_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_region_SBG1_get(self, method, url, body, headers):
        body = self.fixtures.load("flavor_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_flavor_foo_id_get(self, method, url, body, headers):
        body = self.fixtures.load("flavor_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_image_get(self, method, url, body, headers):
        body = self.fixtures.load("image_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_image_foo_id_get(self, method, url, body, headers):
        body = self.fixtures.load("image_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_sshkey_region_SBG1_get(self, method, url, body, headers):
        body = self.fixtures.load("ssh_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_sshkey_post(self, method, url, body, headers):
        body = self.fixtures.load("ssh_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_ssh_mykey_get(self, method, url, body, headers):
        body = self.fixtures.load("ssh_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_get(self, method, url, body, headers):
        body = self.fixtures.load("instance_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_foo_get(self, method, url, body, headers):
        body = self.fixtures.load("instance_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_foo_delete(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_post(self, method, url, body, headers):
        body = self.fixtures.load("instance_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_get(self, method, url, body, headers):
        body = self.fixtures.load("volume_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_post(self, method, url, body, headers):
        body = self.fixtures.load("volume_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_get(self, method, url, body, headers):
        body = self.fixtures.load("volume_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_delete(self, method, url, body, headers):
        return (httplib.OK, "", {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_attach_post(self, method, url, body, headers):
        body = self.fixtures.load("volume_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_detach_post(self, method, url, body, headers):
        body = self.fixtures.load("volume_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_snapshot_region_SBG_1_get(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("volume_snapshot_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_snapshot_get(self, method, url, body, headers):
        body = self.fixtures.load("volume_snapshot_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_snapshot_foo_get(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("volume_snapshot_get_details.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_snapshot_foo_snap_delete(
        self, method, url, body, headers
    ):
        return (httplib.OK, None, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_volume_foo_snapshot__post(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("volume_snapshot_get_details.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_subsidiaryPrice_ovhSubsidiary_US_flavorId_foo_id_get(
        self, method, url, body, headers
    ):
        return self._json_1_0_cloud_subsidiaryPrice_flavorId_foo_id_ovhSubsidiary_US_get(
            method, url, body, headers
        )

    def _json_1_0_cloud_subsidiaryPrice_flavorId_foo_id_ovhSubsidiary_US_get(
        self, method, url, body, headers
    ):
        body = self.fixtures.load("pricing_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_cloud_project_project_id_instance_get_invalid_app_key_error(
        self, method, url, body, headers
    ):
        body = '{"message":"Invalid application key"}'
        return (httplib.UNAUTHORIZED, body, {}, httplib.responses[httplib.OK])

    # VPS mock handlers

    def _json_1_0_vps_get(self, method, url, body, headers):
        body = self.fixtures.load("vps_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_get(self, method, url, body, headers):
        body = self.fixtures.load("vps_get_detail.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_reboot_post(self, method, url, body, headers):
        body = self.fixtures.load("vps_reboot_post.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_start_post(self, method, url, body, headers):
        body = self.fixtures.load("vps_start_post.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_stop_post(self, method, url, body, headers):
        body = self.fixtures.load("vps_stop_post.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_rebuild_post(self, method, url, body, headers):
        body = self.fixtures.load("vps_rebuild_post.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_vps_testvps_images_available_get(self, method, url, body, headers):
        body = self.fixtures.load("vps_images_available_get.json")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


@patch("libcloud.common.ovh.OvhConnection._timedelta", 42)
class OvhTests(unittest.TestCase):
    def setUp(self):
        OvhNodeDriver.connectionCls.conn_class = OvhMockHttp
        OvhMockHttp.type = None
        self.driver = OvhNodeDriver(*OVH_PARAMS)

    def test_region_argument(self):
        driver = OvhNodeDriver(*OVH_PARAMS)
        self.assertEqual(driver.connection.host, "api.ovh.com")

        driver = OvhNodeDriver(*OVH_PARAMS, region=None)
        self.assertEqual(driver.connection.host, "api.ovh.com")

        driver = OvhNodeDriver(*OVH_PARAMS, region="ca")

        driver = OvhNodeDriver(*OVH_PARAMS, region="eu")
        self.assertEqual(driver.connection.host, "eu.api.ovh.com")

        driver = OvhNodeDriver(*OVH_PARAMS, region="ca")
        self.assertEqual(driver.connection.host, "ca.api.ovh.com")

    @unittest.skipIf(no_internet(), "Internet is not reachable")
    def test_list_nodes_invalid_region(self):
        OvhNodeDriver.connectionCls.conn_class = LibcloudConnection
        driver = OvhNodeDriver(*OVH_PARAMS, region="invalid")

        expected_msg = r"invalid region argument was passed.*Used host: invalid.api.ovh.com.*"
        self.assertRaisesRegex(ValueError, expected_msg, driver.list_nodes)

        expected_msg = r"invalid region argument was passed.*Used host: invalid.api.ovh.com.*"
        self.assertRaisesRegex(
            ValueError, expected_msg, driver.connection.request_consumer_key, "1"
        )

    def test_invalid_application_key_correct_error(self):
        OvhMockHttp.type = "invalid_app_key_error"
        driver = OvhNodeDriver("appkeyinvalid", "application_secret", "project_id", "consumer_key")

        expected_msg = r"Invalid application key"
        self.assertRaisesRegex(BaseHTTPError, expected_msg, driver.list_nodes)

    def test_list_locations(self):
        images = self.driver.list_locations()
        self.assertTrue(len(images) > 0)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) > 0)

    def test_get_image(self):
        image = self.driver.get_image("foo-id")
        self.assertEqual(image.id, "foo-id")

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) > 0)

    def test_get_size(self):
        size = self.driver.ex_get_size("foo-id")
        self.assertEqual(size.id, "foo-id")

    def test_list_key_pairs(self):
        keys = self.driver.list_sizes()
        self.assertTrue(len(keys) > 0)

    def test_get_key_pair(self):
        location = self.driver.list_locations()[0]
        key = self.driver.get_key_pair("mykey", location)
        self.assertEqual(key.name, "mykey")

    def test_import_key_pair_from_string(self):
        location = self.driver.list_locations()[0]
        key = self.driver.import_key_pair_from_string("mykey", "material", location)
        self.assertEqual(key.name, "mykey")

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(len(nodes) > 0)

    def test_get_node(self):
        node = self.driver.ex_get_node("foo")
        self.assertEqual(node.name, "test_vm")

    def test_create_node(self):
        location = self.driver.list_locations()[0]
        image = self.driver.list_sizes(location)[0]
        size = self.driver.list_sizes(location)[0]
        node = self.driver.create_node(name="test_vm", image=image, size=size, location=location)
        self.assertEqual(node.name, "test_vm")

    def test_resizing_node(self):
        self.assertTrue(self.driver.NODE_STATE_MAP["RESIZE"])

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertTrue(len(volumes) > 0)

    def test_get_volume(self):
        volume = self.driver.ex_get_volume("foo")
        self.assertEqual(volume.name, "testvol")

    def test_create_volume(self):
        location = self.driver.list_locations()[0]
        volume = self.driver.create_volume(size=10, name="testvol", location=location)
        self.assertEqual(volume.name, "testvol")

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        self.driver.destroy_volume(volume)

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.ex_get_volume("foo")
        response = self.driver.attach_volume(node=node, volume=volume)
        self.assertTrue(response)

    def test_detach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.ex_get_volume("foo")
        response = self.driver.detach_volume(ex_node=node, volume=volume)
        self.assertTrue(response)

    def test_ex_list_snapshots(self):
        self.driver.ex_list_snapshots()

    def test_ex_get_volume_snapshot(self):
        self.driver.ex_get_volume_snapshot("foo")

    def test_list_volume_snapshots(self):
        volume = self.driver.ex_get_volume("foo")
        self.driver.list_volume_snapshots(volume)

    def test_create_volume_snapshot(self):
        volume = self.driver.ex_get_volume("foo")
        self.driver.create_volume_snapshot(volume)

    def test_destroy_volume_snapshot(self):
        snapshot = self.driver.ex_get_volume_snapshot("foo")
        result = self.driver.destroy_volume_snapshot(snapshot)
        self.assertTrue(result)

    def test_get_pricing(self):
        self.driver.ex_get_pricing("foo-id")

    # VPS tests

    def test_ex_list_vps(self):
        names = self.driver.ex_list_vps()
        self.assertEqual(len(names), 2)
        self.assertEqual(names[0], "testvps")
        self.assertEqual(names[1], "testvps2")

    def test_ex_get_vps(self):
        node = self.driver.ex_get_vps("testvps")
        self.assertEqual(node.id, "testvps")
        self.assertEqual(node.name, "my-vps")
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(len(node.public_ips), 2)
        self.assertIn("198.51.100.42", node.public_ips)
        self.assertEqual(node.extra["vcore"], 1)
        self.assertEqual(node.extra["memory"], 2048)
        self.assertEqual(node.extra["disk"], 40)
        self.assertEqual(node.extra["zone"], "eu-west-rbx")

    def test_ex_reboot_vps(self):
        result = self.driver.ex_reboot_vps("testvps")
        self.assertTrue(result)

    def test_ex_start_vps(self):
        result = self.driver.ex_start_vps("testvps")
        self.assertTrue(result)

    def test_ex_stop_vps(self):
        result = self.driver.ex_stop_vps("testvps")
        self.assertTrue(result)

    def test_ex_rebuild_vps(self):
        result = self.driver.ex_rebuild_vps("testvps", "img-debian-12")
        self.assertTrue(result)

    def test_ex_rebuild_vps_with_ssh_key(self):
        result = self.driver.ex_rebuild_vps(
            "testvps", "img-debian-12", ssh_key=["ssh-rsa AAAA..."]
        )
        self.assertTrue(result)

    def test_ex_list_vps_images(self):
        images = self.driver.ex_list_vps_images("testvps")
        self.assertEqual(len(images), 3)
        self.assertEqual(images[0].id, "img-debian-12")
        self.assertEqual(images[0].name, "Debian 12")
        self.assertEqual(images[1].id, "img-ubuntu-2404")
        self.assertEqual(images[1].name, "Ubuntu 24.04")

    def test_vps_state_map(self):
        self.assertEqual(self.driver.VPS_STATE_MAP["running"], NodeState.RUNNING)
        self.assertEqual(self.driver.VPS_STATE_MAP["stopped"], NodeState.STOPPED)
        self.assertEqual(self.driver.VPS_STATE_MAP["rebooting"], NodeState.REBOOTING)
        self.assertEqual(self.driver.VPS_STATE_MAP["installing"], NodeState.PENDING)


if __name__ == "__main__":
    sys.exit(unittest.main())
