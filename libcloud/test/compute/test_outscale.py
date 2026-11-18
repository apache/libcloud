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

import json
import inspect
import unittest
from unittest.mock import Mock

from libcloud.compute.base import NodeDriver, NodeLocation
from libcloud.compute.drivers.outscale import OutscaleNodeDriver


class OutscaleNodeDriverTest(unittest.TestCase):
    STANDARD_METHODS_UNDER_TEST = {
        "attach_volume",
        "create_image",
        "create_key_pair",
        "create_node",
        "create_volume",
        "create_volume_snapshot",
        "delete_image",
        "delete_key_pair",
        "destroy_node",
        "destroy_volume",
        "destroy_volume_snapshot",
        "detach_volume",
        "get_image",
        "get_key_pair",
        "list_images",
        "list_key_pairs",
        "list_locations",
        "list_nodes",
        "list_volume_snapshots",
        "list_volumes",
        "reboot_node",
        "start_node",
        "stop_node",
    }

    def setUp(self):
        self.driver = OutscaleNodeDriver("key", "secret")
        self._set_response({}, status_code=400)

    def _set_response(self, payload, status_code=200):
        response = Mock(status_code=400)
        response.status_code = status_code
        response.json.return_value = payload
        self.driver._call_api = Mock(return_value=response)

    def test_all_standard_methods_are_covered(self):
        standard_methods = {
            name
            for name, method in NodeDriver.__dict__.items()
            if inspect.isfunction(method) and not name.startswith("_")
        }
        implemented_methods = {
            name
            for name, method in OutscaleNodeDriver.__dict__.items()
            if inspect.isfunction(method) and name in standard_methods
        }

        self.assertEqual(implemented_methods, self.STANDARD_METHODS_UNDER_TEST)

    def test_list_locations(self):
        expected = [Mock()]
        self.driver._to_locations = Mock(return_value=expected)
        self._set_response({"Locations": [{"Code": "eu-west-2a"}]})

        result = self.driver.list_locations()

        self.assertEqual(result, expected)
        self.driver._to_locations.assert_called_once_with([{"Code": "eu-west-2a"}])
        self.driver._call_api.assert_called_once_with("ReadLocations", '{"DryRun": false}')

    def test_create_node(self):
        image = Mock(id="ami-1")
        expected = Mock()
        self.driver._to_node = Mock(return_value=expected)
        self._set_response({"Vms": [{"VmId": "vm-1"}]})

        result = self.driver.create_node(name=None, size=None, image=image)

        self.assertEqual(result, expected)
        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "CreateVms")
        self.assertEqual(json.loads(data)["ImageId"], image.id)

    def test_node_power_operations(self):
        node = Mock(id="vm-1")
        operations = {
            "reboot_node": "RebootVms",
            "start_node": "StartVms",
            "stop_node": "StopVms",
        }

        for method_name, action in operations.items():
            with self.subTest(method=method_name):
                self._set_response({})
                result = getattr(self.driver, method_name)(node)

                self.assertTrue(result)
                actual_action, data = self.driver._call_api.call_args.args
                self.assertEqual(actual_action, action)
                self.assertEqual(json.loads(data)["VmIds"], [node.id])

    def test_list_nodes(self):
        expected = [Mock()]
        self.driver._to_nodes = Mock(return_value=expected)
        self._set_response({"Vms": [{"VmId": "vm-1"}]})

        result = self.driver.list_nodes()

        self.assertEqual(result, expected)
        self.driver._to_nodes.assert_called_once_with([{"VmId": "vm-1"}])
        self.driver._call_api.assert_called_once_with("ReadVms", "{}")

    def test_destroy_node(self):
        node = Mock(id="vm-1")
        self._set_response({})

        self.assertTrue(self.driver.destroy_node(node))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "DeleteVms")
        self.assertEqual(json.loads(data)["VmIds"], node.id)

    def test_create_image(self):
        node = Mock(id="vm-1")
        expected = Mock()
        self.driver._to_node_image = Mock(return_value=expected)
        self._set_response({"Image": {"ImageId": "ami-1"}})

        result = self.driver.create_image(node, "image-name", "description")

        self.assertEqual(result, expected)
        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "CreateImage")
        self.assertEqual(json.loads(data)["VmId"], node.id)

    def test_list_images(self):
        images = [{"ImageId": "ami-1"}]
        self._set_response({"Images": images})

        self.assertEqual(self.driver.list_images(), images)
        self.assertEqual(self.driver._call_api.call_args.args[0], "ReadImages")

    def test_get_image(self):
        expected = Mock()
        self.driver._to_node_image = Mock(return_value=expected)
        self._set_response({"Images": [{"ImageId": "ami-1"}]})

        result = self.driver.get_image("ami-1")

        self.assertEqual(result, expected)
        self.driver._to_node_image.assert_called_once_with({"ImageId": "ami-1"})

    def test_delete_image(self):
        image = Mock(id="ami-1")
        self._set_response({})

        self.assertTrue(self.driver.delete_image(image))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "DeleteImage")
        self.assertEqual(json.loads(data)["ImageId"], image.id)

    def test_create_key_pair(self):
        expected = Mock()
        self.driver._to_key_pair = Mock(return_value=expected)
        self._set_response({"Keypair": {"KeypairName": "key-name"}})

        result = self.driver.create_key_pair("key-name")

        self.assertEqual(result, expected)
        self.driver._to_key_pair.assert_called_once_with({"KeypairName": "key-name"})

    def test_list_key_pairs(self):
        expected = [Mock()]
        self.driver._to_key_pairs = Mock(return_value=expected)
        self._set_response({"Keypairs": [{"KeypairName": "key-name"}]})

        result = self.driver.list_key_pairs()

        self.assertEqual(result, expected)
        self.driver._to_key_pairs.assert_called_once_with([{"KeypairName": "key-name"}])

    def test_get_key_pair(self):
        expected = Mock()
        self.driver._to_key_pair = Mock(return_value=expected)
        self._set_response({"Keypairs": [{"KeypairName": "key-name"}]})

        result = self.driver.get_key_pair("key-name")

        self.assertEqual(result, expected)
        self.driver._to_key_pair.assert_called_once_with({"KeypairName": "key-name"})

    def test_delete_key_pair(self):
        key_pair = Mock(name="key-name")
        key_pair.name = "key-name"
        self._set_response({})

        self.assertTrue(self.driver.delete_key_pair(key_pair))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "DeleteKeypair")
        self.assertEqual(json.loads(data)["KeypairName"], key_pair.name)

    def test_create_volume_snapshot(self):
        volume = Mock(id="vol-1")
        expected = Mock()
        self.driver._to_snapshot = Mock(return_value=expected)
        self._set_response({"Volume": {"SnapshotId": "snap-1"}})

        result = self.driver.create_volume_snapshot(volume, name="snapshot")

        self.assertEqual(result, expected)
        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "CreateSnapshot")
        self.assertEqual(json.loads(data)["VolumeId"], volume.id)

    def test_list_volume_snapshots(self):
        volume = Mock(id="vol-1")
        expected = [Mock()]
        self.driver._to_snapshots = Mock(return_value=expected)
        self._set_response({"Snapshots": [{"SnapshotId": "snap-1"}]})

        result = self.driver.list_volume_snapshots(volume)

        self.assertEqual(result, expected)
        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "ReadSnapshots")
        self.assertEqual(data["Filters"]["VolumeIds"], [volume.id])

    def test_destroy_volume_snapshot(self):
        snapshot = Mock(id="snap-1")
        self._set_response({})

        self.assertTrue(self.driver.destroy_volume_snapshot(snapshot))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "DeleteSnapshot")
        self.assertEqual(json.loads(data)["SnapshotId"], snapshot.id)

    def test_create_volume_uses_location_as_subregion(self):
        location = NodeLocation(
            id="eu-west-2a",
            name="eu-west-2a, France",
            country="France",
            driver=self.driver,
        )
        expected = Mock()
        self.driver._to_volume = Mock(return_value=expected)
        self._set_response({"Volume": {"VolumeId": "vol-1"}})

        result = self.driver.create_volume(size=10, name="volume", location=location)

        self.assertEqual(result, expected)
        _, data = self.driver._call_api.call_args.args
        self.assertEqual(json.loads(data)["SubregionName"], location.id)

    def test_create_volume_prefers_explicit_subregion(self):
        location = NodeLocation(
            id="eu-west-2a",
            name="eu-west-2a, France",
            country="France",
            driver=self.driver,
        )

        self.driver.create_volume(
            size=10,
            name="volume",
            location=location,
            ex_subregion_name="eu-west-2b",
        )

        _, data = self.driver._call_api.call_args.args
        self.assertEqual(json.loads(data)["SubregionName"], "eu-west-2b")

    def test_create_volume_requires_location_or_subregion(self):
        with self.assertRaisesRegex(ValueError, "location or ex_subregion_name is required"):
            self.driver.create_volume(size=10, name="volume")

        self.driver._call_api.assert_not_called()

    def test_list_volumes(self):
        expected = [Mock()]
        self.driver._to_volumes = Mock(return_value=expected)
        self._set_response({"Volumes": [{"VolumeId": "vol-1"}]})

        result = self.driver.list_volumes()

        self.assertEqual(result, expected)
        self.driver._to_volumes.assert_called_once_with([{"VolumeId": "vol-1"}])

    def test_destroy_volume(self):
        volume = Mock(id="vol-1")
        self._set_response({})

        self.assertTrue(self.driver.destroy_volume(volume))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "DeleteVolume")
        self.assertEqual(json.loads(data)["VolumeId"], volume.id)

    def test_attach_volume(self):
        node = Mock(id="vm-1")
        volume = Mock(id="vol-1")
        self._set_response({})

        self.assertTrue(self.driver.attach_volume(node, volume, device="/dev/sdb"))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "LinkVolume")
        self.assertEqual(
            json.loads(data),
            {
                "VmId": node.id,
                "VolumeId": volume.id,
                "DeviceName": "/dev/sdb",
            },
        )

    def test_detach_volume(self):
        volume = Mock(id="vol-1")
        self._set_response({})

        self.assertTrue(self.driver.detach_volume(volume, ex_force_unlink=True))

        action, data = self.driver._call_api.call_args.args
        self.assertEqual(action, "UnlinkVolume")
        self.assertEqual(json.loads(data)["VolumeId"], volume.id)
        self.assertTrue(json.loads(data)["ForceUnlink"])


if __name__ == "__main__":
    unittest.main()
