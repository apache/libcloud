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
    SUBSCRIPTION_ID = '99999999-9999-9999-9999-999999999999'
    APPLICATION_ID = '55555555-5555-5555-5555-555555555555'
    APPLICATION_PASS = 'p4ssw0rd'

    def setUp(self):
        Azure = get_driver(Provider.AZURE_ARM)
        Azure.connectionCls.conn_class = AzureMockHttp
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS)

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
                         set(['Currency',
                              'Locale',
                              'IsTaxIncluded',
                              'OfferTerms',
                              'Meters']))

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
        self.assertTrue(storage_profile['imageReference'], {
            'publisher': image.publisher,
            'offer': image.offer,
            'sku': image.sku,
            'version': image.version
        })

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 1)

        self.assertEqual(nodes[0].name, 'test-node-1')
        self.assertEqual(nodes[0].state, NodeState.UPDATING)
        self.assertEqual(nodes[0].private_ips, ['10.0.0.1'])
        self.assertEqual(nodes[0].public_ips, [])

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
        self.assertTrue(set(luns), set([0, 1, 15]))

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


class AzureMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('azure_arm')

    def _update(self, fixture, body):
        for key, value in body.items():
            if isinstance(value, dict):
                fixture[key] = self._update(fixture.get(key, {}), value)
            else:
                fixture[key] = body[key]
        return fixture

    def __getattr__(self, n):
        def fn(method, url, body, headers):
            fixture = self.fixtures.load(n + ".json")

            if method in ('POST', 'PUT'):
                try:
                    body = json.loads(body)
                    fixture_tmp = json.loads(fixture)
                    fixture_tmp = self._update(fixture_tmp, body)
                    fixture = json.dumps(fixture_tmp)
                except ValueError:
                    pass
            return (httplib.OK, fixture, headers,
                    httplib.responses[httplib.OK])
        return fn


if __name__ == '__main__':
    sys.exit(unittest.main())
