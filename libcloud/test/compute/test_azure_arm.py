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
from libcloud.utils.iso8601 import UTC


class AzureNodeDriverTests(LibcloudTestCase):

    TENANT_ID = 'e3cf3c98-a978-465f-8254-9d541eeea73c'
    SUBSCRIPTION_ID = '35867a13-9915-428e-a146-97f3039bba98'
    APPLICATION_ID = '8038bf1e-2ccc-4103-8d0c-03cabdb6319c'
    APPLICATION_PASS = 'p4ssw0rd'

    def setUp(self):
        Azure = get_driver(Provider.AZURE_ARM)
        Azure.connectionCls.conn_class = AzureMockHttp
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS,
                            region='eastus')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        assert len(nodes) == 1

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual([l.name for l in locations],
                         ["East US",
                          "East US 2",
                          "West US",
                          "Central US",
                          "North Central US",
                          "South Central US",
                          "North Europe",
                          "West Europe",
                          "East Asia",
                          "Southeast Asia",
                          "Japan East",
                          "Japan West",
                          'Australia East',
                          'Australia Southeast',
                          'Brazil South',
                          'South India',
                          'Central India',
                          'Canada Central',
                          'Canada East',
                          'West US 2',
                          'West Central US',
                          'UK South',
                          'UK West',
                          'Korea Central',
                          'Korea South'])

    def test_sizes_returned_successfully(self):
        sizes = self.driver.list_sizes(location=self.driver.list_locations()[0])
        size_names = [size.name for size in sizes]
        self.assertTrue('Standard_DS1_v2' in size_names)
        location = self.driver.list_locations()[0]
        sizes = self.driver.list_sizes(location=location)
        size_names = [size.name for size in sizes]
        self.assertTrue('Standard_DS1_v2' in size_names)

    def test_ex_get_ratecard(self):
        ratecard = self.driver.ex_get_ratecard('0026P')
        self.assertEqual(set(ratecard.keys()),
                         set(['Currency',
                              'Locale',
                              'IsTaxIncluded',
                              'OfferTerms',
                              'Meters']))

    def test_start_node(self):
        node = self.driver.list_nodes()[0]
        assert self.driver.ex_start_node(node) is not None

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        assert node.reboot()

    def test_ex_list_publishers(self):
        publishers = self.driver.ex_list_publishers()
        _, names = zip(*publishers)
        assert "cloudbees" in names

    def test_offers(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0][0])
        _, names = zip(*offers)
        assert "voipnow" in names

    def test_offers_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        _, names = zip(*offers)
        assert "voipnow" in names

    def test_list_skus(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0][0])
        _, names = zip(*skus)
        assert "vnp360-single" in names

    def test_list_skus_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        _, names = zip(*skus)
        assert "vnp360-single" in names

    def test_list_image_versions(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        image_versions = self.driver.ex_list_image_versions(skus[0][0])
        _, names = zip(*image_versions)
        assert "3.6.0" in names

    def test_list_image_versions_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        image_versions = self.driver.ex_list_image_versions(skus[0])
        _, names = zip(*image_versions)
        assert "3.6.0" in names

    def test_list_resource_groups(self):
        resource_groups = self.driver.ex_list_resource_groups()
        test_group = resource_groups[2]
        assert test_group.id == '/subscriptions/35867a13-9915-428e-a146-97f3039bba98/resourceGroups/salt-dev-master'
        assert test_group.name == 'salt-dev-master'

    def test_ex_list_network_security_groups(self):
        resource_groups = self.driver.ex_list_resource_groups()
        net_groups = self.driver.ex_list_network_security_groups(resource_groups[2].name)
        assert len(net_groups) == 0

    def test_ex_list_network_security_groups_obj(self):
        """
        Test that you can send an AzureResourceGroup instance instead of the name
        """
        resource_groups = self.driver.ex_list_resource_groups()
        net_groups = self.driver.ex_list_network_security_groups(resource_groups[2])
        assert len(net_groups) == 0

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
    driver = get_driver(Provider.AZURE_ARM)
    fixtures = ('compute', 'azure_arm')
    mode = 'static'
    base_url = ('https://login.microsoftonline.com/',
                'https://management.azure.com/')


if __name__ == '__main__':
    sys.exit(unittest.main())
