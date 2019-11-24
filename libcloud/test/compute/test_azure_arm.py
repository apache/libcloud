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
# limitations under the License.import libcloud

import json
import sys
import functools
from datetime import datetime

import mock

from libcloud.common.exceptions import BaseHTTPError
from libcloud.common.types import LibcloudError
from libcloud.compute.base import (NodeLocation, NodeSize, VolumeSnapshot,
                                   StorageVolume)
from libcloud.compute.drivers.azure_arm import AzureImage, NodeAuthPassword
from libcloud.compute.providers import get_driver
from libcloud.compute.types import (NodeState, Provider, StorageVolumeState,
                                    VolumeSnapshotState)
from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test import unittest
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.utils.iso8601 import UTC
from libcloud.utils.py3 import httplib


class AzureNodeDriverTests(LibcloudTestCase):

    TENANT_ID = '77777777-7777-7777-7777-777777777777'
    SUBSCRIPTION_ID = '99999999'
    APPLICATION_ID = '55555555-5555-5555-5555-555555555555'
    APPLICATION_PASS = 'p4ssw0rd'

    def setUp(self):
        Azure = get_driver(Provider.AZURE_ARM)
        Azure.connectionCls.conn_class = AzureMockHttp
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS)

    def tearDown(self):
        AzureMockHttp.responses = []

    def test_get_image(self):
        # Default storage suffix
        image = self.driver.get_image(image_id='http://www.example.com/foo/image_name')
        self.assertEqual(image.id, 'https://www.blob.core.windows.net/foo/image_name')
        self.assertEqual(image.name, 'image_name')

        # Custom storage suffix
        self.driver.connection.storage_suffix = '.core.chinacloudapi.cn'
        image = self.driver.get_image(image_id='http://www.example.com/foo/image_name')
        self.assertEqual(image.id, 'https://www.blob.core.chinacloudapi.cn/foo/image_name')
        self.assertEqual(image.name, 'image_name')

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual([l.name for l in locations],
                         ["East US",
                          "East US 2",
                          "West US",
                          "Central US",
                          "South Central US",
                          "North Europe",
                          "West Europe",
                          "East Asia",
                          "Southeast Asia",
                          "Japan East",
                          "Japan West"])

    def test_sizes_returned_successfully(self):
        location = self.driver.list_locations()[0]
        sizes = self.driver.list_sizes(location=location)
        self.assertEqual([l.name for l in sizes],
                         ["Standard_A0",
                          "Standard_A1",
                          "Standard_A2"])

    def test_ex_get_ratecard(self):
        ratecard = self.driver.ex_get_ratecard('0026P')
        self.assertEqual(set(ratecard.keys()),
                         {'Currency', 'Locale', 'IsTaxIncluded',
                          'OfferTerms', 'Meters'})

    def test_create_node(self):
        location = NodeLocation('any_location', '', '', self.driver)
        size = NodeSize('any_size', '', 0, 0, 0, 0, driver=self.driver)
        image = AzureImage('1', '1', 'ubuntu', 'pub', location.id, self.driver)
        auth = NodeAuthPassword('any_password')

        node = self.driver.create_node(
            'test-node-1',
            size,
            image,
            auth,
            location=location,
            ex_resource_group='000000',
            ex_storage_account='000000',
            ex_user_name='any_user',
            ex_network='000000',
            ex_subnet='000000',
            ex_use_managed_disks=True
        )
        hardware_profile = node.extra['properties']['hardwareProfile']
        os_profile = node.extra['properties']['osProfile']
        storage_profile = node.extra['properties']['storageProfile']

        self.assertEqual(node.name, 'test-node-1')
        self.assertEqual(node.state, NodeState.UPDATING)
        self.assertEqual(node.private_ips, ['10.0.0.1'])
        self.assertEqual(node.public_ips, [])
        self.assertEqual(node.extra['location'], location.id)
        self.assertEqual(hardware_profile['vmSize'], size.id)
        self.assertEqual(os_profile['adminUsername'], 'any_user')
        self.assertEqual(os_profile['adminPassword'], 'any_password')
        self.assertTrue('managedDisk' in storage_profile['osDisk'])
        self.assertTrue('diskSizeGB' not in storage_profile['osDisk'])
        self.assertTrue(storage_profile['imageReference'], {
            'publisher': image.publisher,
            'offer': image.offer,
            'sku': image.sku,
            'version': image.version
        })

    def test_create_node_ex_disk_size(self):
        location = NodeLocation('any_location', '', '', self.driver)
        size = NodeSize('any_size', '', 0, 0, 0, 0, driver=self.driver)
        image = AzureImage('1', '1', 'ubuntu', 'pub', location.id, self.driver)
        auth = NodeAuthPassword('any_password')

        node = self.driver.create_node(
            'test-node-1',
            size,
            image,
            auth,
            location=location,
            ex_resource_group='000000',
            ex_storage_account='000000',
            ex_user_name='any_user',
            ex_network='000000',
            ex_subnet='000000',
            ex_disk_size=100,
            ex_use_managed_disks=True
        )
        hardware_profile = node.extra['properties']['hardwareProfile']
        os_profile = node.extra['properties']['osProfile']
        storage_profile = node.extra['properties']['storageProfile']

        self.assertEqual(node.name, 'test-node-1')
        self.assertEqual(node.state, NodeState.UPDATING)
        self.assertEqual(node.private_ips, ['10.0.0.1'])
        self.assertEqual(node.public_ips, [])
        self.assertEqual(node.extra['location'], location.id)
        self.assertEqual(hardware_profile['vmSize'], size.id)
        self.assertEqual(os_profile['adminUsername'], 'any_user')
        self.assertEqual(os_profile['adminPassword'], 'any_password')
        self.assertTrue('managedDisk' in storage_profile['osDisk'])
        self.assertEqual(storage_profile['osDisk']['diskSizeGB'], 100)
        self.assertTrue(storage_profile['imageReference'], {
            'publisher': image.publisher,
            'offer': image.offer,
            'sku': image.sku,
            'version': image.version
        })

    @mock.patch('time.sleep', return_value=None)
    def test_destroy_node(self, time_sleep_mock):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # OK to the DELETE request
            lambda f: (httplib.OK, None, {}, 'OK'),
            # 404 means node is gone
            lambda f: error(BaseHTTPError, code=404, message='Not found'),
        ]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_destroy_node__node_not_found(self):
        """
        This simulates the case when destroy_node is being called for the 2nd
        time because some related resource failed to clean up, so the DELETE
        operation on the node will return 204 (because it was already deleted)
        but the method should return success.
        """
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # 204 (No content) to the DELETE request on a deleted/non-existent node
            lambda f: error(BaseHTTPError, code=204, message='No content'),
        ]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    @mock.patch('time.sleep', return_value=None)
    def test_destroy_node__retry(self, time_sleep_mock):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # 202 - The delete will happen asynchronously
            lambda f: error(BaseHTTPError, code=202, message='Deleting'),
            # 200 means the node is still here - Try 1
            lambda f: (httplib.OK, None, {}, 'OK'),
            # 200 means the node is still here - Try 2
            lambda f: (httplib.OK, None, {}, 'OK'),
            # 200 means the node is still here - Try 3
            lambda f: (httplib.OK, None, {}, 'OK'),
            # 404 means node is gone - 4th retry: success!
            lambda f: error(BaseHTTPError, code=404, message='Not found'),
        ]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)
        self.assertEqual(4, time_sleep_mock.call_count)  # Retries

    @mock.patch('time.sleep', return_value=None)
    def test_destroy_node__destroy_nic_retries(self, time_sleep_mock):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        err = BaseHTTPError(code=400, message='[NicInUse] Cannot destroy')
        with mock.patch.object(self.driver, 'ex_destroy_nic') as m:
            m.side_effect = [err] * 5 + [True]  # 5 errors before a success
            ret = self.driver.destroy_node(node)
            self.assertTrue(ret)
            self.assertEqual(6, m.call_count)  # 6th call was a success

            m.side_effect = [err] * 10 + [True]  # 10 errors before a success
            with self.assertRaises(BaseHTTPError):
                self.driver.destroy_node(node)
                self.assertEqual(10, m.call_count)  # try 10 times & fail

    @mock.patch('time.sleep', return_value=None)
    def test_destroy_node__async(self, time_sleep_mock):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # 202 - The delete will happen asynchronously
            lambda f: error(BaseHTTPError, code=202, message='Deleting'),
            # 404 means node is gone
            lambda f: error(BaseHTTPError, code=404, message='Not found'),
        ]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    @mock.patch('time.sleep', return_value=None)
    def test_destroy_node__nic_not_cleaned_up(self, time_sleep_mock):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # OK to the DELETE request
            lambda f: (httplib.OK, None, {}, 'OK'),
            # 404 means node is gone
            lambda f: error(BaseHTTPError, code=404, message='Not found'),
            # 500 - transient error when trying to clean up the NIC
            lambda f: error(BaseHTTPError, code=500, message="Cloud weather"),
        ]
        with self.assertRaises(BaseHTTPError):
            self.driver.destroy_node(node)

    def test_destroy_node__failed(self):
        def error(e, **kwargs):
            raise e(**kwargs)
        node = self.driver.list_nodes()[0]
        AzureMockHttp.responses = [
            # 403 - There was some problem with your request
            lambda f: error(BaseHTTPError, code=403, message='Forbidden'),
        ]
        with self.assertRaises(BaseHTTPError):
            self.driver.destroy_node(node)

    @mock.patch('libcloud.compute.drivers.azure_arm.AzureNodeDriver'
                '._fetch_power_state', return_value=NodeState.UPDATING)
    def test_list_nodes(self, fps_mock):
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 1)

        self.assertEqual(nodes[0].name, 'test-node-1')
        self.assertEqual(nodes[0].state, NodeState.UPDATING)
        self.assertEqual(nodes[0].private_ips, ['10.0.0.1'])
        self.assertEqual(nodes[0].public_ips, [])

        fps_mock.assert_called()

    @mock.patch('libcloud.compute.drivers.azure_arm.AzureNodeDriver'
                '._fetch_power_state', return_value=NodeState.UPDATING)
    def test_list_nodes__no_fetch_power_state(self, fps_mock):
        nodes = self.driver.list_nodes(ex_fetch_power_state=False)

        self.assertEqual(len(nodes), 1)

        self.assertEqual(nodes[0].name, 'test-node-1')
        self.assertNotEqual(nodes[0].state, NodeState.UPDATING)
        self.assertEqual(nodes[0].private_ips, ['10.0.0.1'])
        self.assertEqual(nodes[0].public_ips, [])

        fps_mock.assert_not_called()

    def test_create_volume(self):
        location = self.driver.list_locations()[-1]
        volume = self.driver.create_volume(
            2, 'test-disk-1', location,
            ex_resource_group='000000',
            ex_tags={'description': 'MyVolume'}
        )

        self.assertEqual(volume.size, 2)
        self.assertEqual(volume.name, 'test-disk-1')
        self.assertEqual(volume.extra['name'], 'test-disk-1')
        self.assertEqual(volume.extra['tags'], {'description': 'MyVolume'})
        self.assertEqual(volume.extra['location'], location.id)
        self.assertEqual(
            volume.extra['properties']['creationData']['createOption'],
            'Empty')
        self.assertEqual(
            volume.extra['properties']['provisioningState'],
            'Succeeded')
        self.assertEqual(
            volume.extra['properties']['diskState'],
            'Attached')
        self.assertEqual(volume.state, StorageVolumeState.INUSE)

    def test_create_volume__with_snapshot(self):
        location = self.driver.list_locations()[0]
        snap_id = (
            '/subscriptions/99999999-9999-9999-9999-999999999999'
            '/resourceGroups/000000/providers/Microsoft.Compute'
            '/snapshots/test-snap-1'
        )
        snapshot = VolumeSnapshot(id=snap_id, size=2, driver=self.driver)

        volume = self.driver.create_volume(
            2, 'test-disk-1', location,
            snapshot=snapshot,
            ex_resource_group='000000',
            ex_tags={'description': 'MyVolume'}
        )

        self.assertEqual(
            volume.extra['properties']['creationData']['createOption'],
            'Copy')
        self.assertEqual(
            volume.extra['properties']['creationData']['sourceUri'],
            snap_id)

    def test_create_volume__required_kw(self):
        location = self.driver.list_locations()[0]
        fn = functools.partial(self.driver.create_volume, 2, 'test-disk-1')

        self.assertRaises(ValueError, fn)
        self.assertRaises(ValueError, fn, location=location)
        self.assertRaises(ValueError, fn, ex_resource_group='000000')

        ret_value = fn(ex_resource_group='000000', location=location)
        self.assertTrue(isinstance(ret_value, StorageVolume))

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()

        self.assertEqual(len(volumes), 3)

        self.assertEqual(volumes[0].name, 'test-disk-1')
        self.assertEqual(volumes[0].size, 31)
        self.assertEqual(
            volumes[0].extra['properties']['provisioningState'],
            'Succeeded')
        self.assertEqual(
            volumes[0].extra['properties']['diskState'],
            'Attached')
        self.assertEqual(volumes[0].state, StorageVolumeState.INUSE)

        self.assertEqual(volumes[1].name, 'test-disk-2')
        self.assertEqual(volumes[1].size, 31)
        self.assertEqual(
            volumes[1].extra['properties']['provisioningState'],
            'Updating')
        self.assertEqual(
            volumes[1].extra['properties']['diskState'],
            'Unattached')
        self.assertEqual(volumes[1].state, StorageVolumeState.UPDATING)

        self.assertEqual(volumes[2].name, 'test-disk-3')
        self.assertEqual(volumes[2].size, 10)
        self.assertEqual(
            volumes[2].extra['properties']['provisioningState'],
            'Succeeded')
        self.assertEqual(
            volumes[2].extra['properties']['diskState'],
            'Unattached')
        self.assertEqual(StorageVolumeState.AVAILABLE, volumes[2].state)

    def test_list_volumes__with_resource_group(self):
        volumes = self.driver.list_volumes(ex_resource_group='111111')

        self.assertEqual(len(volumes), 1)

        self.assertEqual(volumes[0].name, 'test-disk-3')
        self.assertEqual(volumes[0].size, 10)
        self.assertEqual(
            volumes[0].extra['properties']['provisioningState'],
            'Succeeded')
        self.assertEqual(
            volumes[0].extra['properties']['diskState'],
            'Unattached')
        self.assertEqual(volumes[0].state, StorageVolumeState.AVAILABLE)

    def test_attach_volume(self):
        volumes = self.driver.list_volumes()
        node = self.driver.list_nodes()[0]

        self.driver.attach_volume(node, volumes[0], ex_lun=0)
        self.driver.attach_volume(node, volumes[1], ex_lun=15)
        self.driver.attach_volume(node, volumes[2])

        data_disks = node.extra['properties']['storageProfile']['dataDisks']
        luns = [disk['lun'] for disk in data_disks]
        self.assertTrue(len(data_disks), len(volumes))
        self.assertTrue(set(luns), {0, 1, 15})

        volumes = self.driver.list_volumes()
        node = self.driver.list_nodes()[0]
        for count in range(64):
            self.driver.attach_volume(node, volumes[0])
        data_disks = node.extra['properties']['storageProfile']['dataDisks']
        luns = [disk['lun'] for disk in data_disks]
        self.assertTrue(len(data_disks), 64)
        self.assertTrue(set(luns), set(range(64)))

    def test_resize_volume(self):
        volume = self.driver.list_volumes()[0]
        original_size = volume.size

        volume = self.driver.ex_resize_volume(
            volume, volume.size + 8, '000000'
        )
        new_size = volume.size

        self.assertEqual(new_size, original_size + 8)

    def test_detach_volume(self):
        volumes = self.driver.list_volumes()
        node = self.driver.list_nodes()[0]

        for volume in volumes:
            self.driver.attach_volume(node, volume)

        data_disks = node.extra['properties']['storageProfile']['dataDisks']
        self.assertEqual(len(data_disks), len(volumes))

        for volume in volumes:
            self.driver.detach_volume(volume, ex_node=node)

        data_disks = node.extra['properties']['storageProfile']['dataDisks']
        self.assertEqual(len(data_disks), 0)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        ret_value = self.driver.destroy_volume(volume)
        self.assertTrue(ret_value)

    def test_create_volume_snapshot(self):
        location = self.driver.list_locations()[-1]
        volume = self.driver.list_volumes()[0]

        snap = self.driver.create_volume_snapshot(
            volume, 'test-snap-1',
            location=location,
            ex_resource_group='000000'
        )
        self.assertEqual(snap.name, 'test-snap-1')
        self.assertEqual(snap.extra['name'], 'test-snap-1')
        self.assertEqual(snap.size, 1)
        self.assertEqual(snap.extra['source_id'], volume.id)
        self.assertEqual(snap.state, VolumeSnapshotState.CREATING)
        self.assertEqual(snap.extra['location'], location.id)
        self.assertEqual(
            snap.extra['properties']['provisioningState'],
            'Creating')
        self.assertEqual(
            snap.extra['properties']['diskState'],
            'Unattached')
        # 2017-03-09T14:28:27.8655868+00:00"
        self.assertEqual(
            datetime(2017, 3, 9, 14, 28, 27, 865586, tzinfo=UTC),
            snap.created)

    def test_create_volume_snapshot__required_kw(self):
        location = self.driver.list_locations()[0]
        volume = self.driver.list_volumes()[0]

        fn = functools.partial(self.driver.create_volume_snapshot, volume)

        self.assertRaises(ValueError, fn)
        self.assertRaises(ValueError, fn, name='test-snap-1')
        self.assertRaises(ValueError, fn, location=location)
        self.assertRaises(ValueError, fn, ex_resource_group='000000')

        ret_value = fn(
            name='test-snap-1',
            ex_resource_group='000000',
            location=location
        )
        self.assertTrue(isinstance(ret_value, VolumeSnapshot))

    def test_list_snapshots(self):
        snaps = self.driver.list_snapshots()
        self.assertEqual(len(snaps), 4)

        self.assertEqual(snaps[0].name, 'test-snap-1')
        self.assertEqual(snaps[0].extra['name'], 'test-snap-1')
        self.assertEqual(snaps[0].state, VolumeSnapshotState.CREATING)
        self.assertEqual(
            snaps[0].extra['source_id'],
            '/subscriptions/99999999-9999-9999-9999-999999999999'
            '/resourceGroups/000000/providers/Microsoft.Compute'
            '/disks/test-disk-1')
        self.assertEqual(snaps[0].size, 1)
        self.assertEqual(snaps[0].extra['tags']['test_snap'], 'test')
        self.assertTrue(isinstance(snaps[3].created, datetime))

        self.assertEqual(snaps[3].name, 'test-snap-4')
        self.assertEqual(snaps[3].extra['name'], 'test-snap-4')
        self.assertEqual(snaps[3].state, VolumeSnapshotState.ERROR)
        self.assertEqual(
            snaps[3].extra['source_id'],
            '/subscriptions/99999999-9999-9999-9999-999999999999'
            '/resourceGroups/111111/providers/Microsoft.Compute'
            '/disks/test-disk-4')
        self.assertEqual(snaps[3].size, 2)
        self.assertTrue(isinstance(snaps[3].created, datetime))

    def test_list_snapshots_in_resource_group(self):

        snaps = self.driver.list_snapshots(ex_resource_group='111111')
        self.assertEqual(len(snaps), 2)

        self.assertEqual(snaps[0].name, 'test-snap-3')
        self.assertEqual(snaps[0].extra['name'], 'test-snap-3')
        self.assertEqual(snaps[0].state, VolumeSnapshotState.ERROR)
        self.assertEqual(
            snaps[0].extra['source_id'],
            '/subscriptions/99999999-9999-9999-9999-999999999999'
            '/resourceGroups/111111/providers/Microsoft.Compute'
            '/disks/test-disk-3')
        self.assertEqual(snaps[0].size, 2)
        self.assertTrue(isinstance(snaps[0].created, datetime))

    def test_list_volume_snapshots(self):
        volume = self.driver.list_volumes()[0]
        self.assertTrue(volume.name == 'test-disk-1')

        snapshots = self.driver.list_volume_snapshots(volume)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].name, 'test-snap-1')
        self.assertEqual(volume.id, snapshots[0].extra['source_id'])

    def test_destroy_volume_snapshot(self):
        snapshot = self.driver.list_snapshots()[0]
        res_value = snapshot.destroy()
        self.assertTrue(res_value)

    def test_delete_public_ip(self):
        location = self.driver.list_locations()[0]
        public_ip = self.driver.ex_create_public_ip(name='test_public_ip',
                                                    resource_group='REVIZOR',
                                                    location=location)
        res_value = self.driver.ex_delete_public_ip(public_ip)
        self.assertTrue(res_value)

    def test_update_network_profile(self):
        nics = self.driver.ex_list_nics()
        node = self.driver.list_nodes()[0]
        network_profile = node.extra['properties']['networkProfile']
        primary_nic_exists = False
        num_nics_before = len(network_profile["networkInterfaces"])

        for nic in network_profile["networkInterfaces"]:
            if "properties" in nic and nic["properties"]["primary"]:
                primary_nic_exists = True
        if not primary_nic_exists:
            network_profile["networkInterfaces"][0]["properties"] = {
                "primary": True}
        network_profile["networkInterfaces"].append({"id": nics[0].id})
        self.driver.ex_update_network_profile_of_node(
            node, network_profile)

        network_profile = node.extra['properties']['networkProfile']
        num_nics_after = len(network_profile["networkInterfaces"])

        self.assertEqual(num_nics_after, num_nics_before + 1)

    def test_update_nic_properties(self):
        nics = self.driver.ex_list_nics()
        nic_to_update = nics[0]
        nic_properties = nic_to_update.extra
        ip_configs = nic_properties['ipConfigurations']
        ip_configs[0]['properties']['primary'] = True
        updated_nic = self.driver.ex_update_nic_properties(
            nic_to_update, resource_group='REVIZOR', properties=nic_properties)
        self.assertTrue(
            updated_nic.extra['ipConfigurations'][0]['properties']['primary'])

    def test_check_ip_address_availability(self):
        networks = self.driver.ex_list_networks()
        result = self.driver.ex_check_ip_address_availability(
            'REVIZOR', networks[0], '0.0.0.0')
        self.assertFalse(result['available'])

    def test_get_instance_vhd(self):
        with mock.patch.object(self.driver, '_ex_delete_old_vhd'):
            # Default storage suffix
            vhd_url = self.driver._get_instance_vhd(name='test1',
                                                    ex_resource_group='000000',
                                                    ex_storage_account='sga1')
            self.assertEqual(vhd_url, 'https://sga1.blob.core.windows.net/vhds/test1-os_0.vhd')

            # Custom storage suffix
            self.driver.connection.storage_suffix = '.core.chinacloudapi.cn'
            vhd_url = self.driver._get_instance_vhd(name='test1',
                                                    ex_resource_group='000000',
                                                    ex_storage_account='sga1')
            self.assertEqual(vhd_url, 'https://sga1.blob.core.chinacloudapi.cn/vhds/test1-os_0.vhd')

    def test_get_instance_vhd__retries_ten_times(self):
        with mock.patch.object(self.driver, '_ex_delete_old_vhd') as m:
            # 10 retries are OK
            m.side_effect = [False] * 9 + [True]
            vhd_url = self.driver._get_instance_vhd(name='test1',
                                                    ex_resource_group='000000',
                                                    ex_storage_account='sga1')
            self.assertEqual(vhd_url, 'https://sga1.blob.core.windows.net/vhds/test1-os_9.vhd')
            # Fail on the 11th
            m.side_effect = [False] * 10 + [True]
            with self.assertRaises(LibcloudError):
                self.driver._get_instance_vhd(name='test1',
                                              ex_resource_group='000000',
                                              ex_storage_account='sga1')


class AzureMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('azure_arm')
    # List of callables to be run in order as responses. Fixture
    # passed as argument.
    responses = []

    def _update(self, fixture, body):
        for key, value in body.items():
            if isinstance(value, dict):
                fixture[key] = self._update(fixture.get(key, {}), value)
            else:
                fixture[key] = body[key]
        return fixture

    def __getattr__(self, n):
        def fn(method, url, body, headers):
            # Note: We use shorter fixture name so we don't exceed 143
            # character limit for file names
            file_name = n.replace('99999999_9999_9999_9999_999999999999',
                                  AzureNodeDriverTests.SUBSCRIPTION_ID)
            fixture = self.fixtures.load(file_name + ".json")

            if method in ('POST', 'PUT'):
                try:
                    body = json.loads(body)
                    fixture_tmp = json.loads(fixture)
                    fixture_tmp = self._update(fixture_tmp, body)
                    fixture = json.dumps(fixture_tmp)
                except ValueError:
                    pass
            if (not n.endswith('_oauth2_token')) and len(self.responses) > 0:
                f = self.responses.pop(0)
                return f(fixture)
            else:
                return (httplib.OK, fixture, headers,
                        httplib.responses[httplib.OK])
        return fn


if __name__ == '__main__':
    sys.exit(unittest.main())
