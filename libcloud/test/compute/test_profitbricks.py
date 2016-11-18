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

from libcloud.utils.py3 import httplib
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.providers import get_driver
from libcloud.test import unittest
from libcloud.test.secrets import PROFIT_BRICKS_PARAMS


class ProfitBricksTests(unittest.TestCase):

    def setUp(self):
        ProfitBricks = get_driver(Provider.PROFIT_BRICKS)
        ProfitBricks.connectionCls.conn_classes = (None, ProfitBricksMockHttp)
        self.driver = ProfitBricks(*PROFIT_BRICKS_PARAMS)

    '''
    Function tests for listing items
    '''

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 7)

    def test_list_images(self):

        '''
        Fetch all images and then fetch with filters
        '''
        all_images = self.driver.list_images()
        hdd_images = self.driver.list_images('HDD')
        cdd_images = self.driver.list_images('CDROM')
        private_images = self.driver.list_images(is_public=False)

        self.assertEqual(len(all_images), 4)
        self.assertEqual(len(hdd_images), 2)
        self.assertEqual(len(cdd_images), 2)
        self.assertEqual(len(private_images), 2)

        image = all_images[0]
        extra = image.extra

        '''
        Standard properties
        '''
        self.assertEqual(image.id, 'img-1')
        self.assertEqual(image.name, 'Test-Image-Two-CDROM')

        '''
        Extra metadata
        '''
        self.assertEqual(extra['created_date'], '2014-11-14T15:22:19Z')
        self.assertEqual(extra['created_by'], 'System')
        self.assertEqual(extra['etag'], '957e0eac7456fa7554e73bf0d18860eb')
        self.assertEqual(extra['last_modified_date'], '2014-11-14T15:22:19Z')
        self.assertEqual(extra['last_modified_by'], 'System')

        '''
        Extra properties
        '''
        self.assertEqual(extra['name'], 'Test-Image-Two-CDROM')
        self.assertEqual(extra['description'], '')
        self.assertEqual(extra['location'], 'us/las')
        self.assertEqual(extra['size'], 4)
        self.assertEqual(extra['cpu_hot_plug'], False)

        self.assertEqual(extra['cpu_hot_unplug'], False)
        self.assertEqual(extra['ram_hot_plug'], False)
        self.assertEqual(extra['ram_hot_unplug'], False)
        self.assertEqual(extra['nic_hot_plug'], False)
        self.assertEqual(extra['nic_hot_unplug'], False)

        self.assertEqual(extra['disc_virtio_hot_plug'], False)
        self.assertEqual(extra['disc_virtio_hot_unplug'], False)
        self.assertEqual(extra['disc_scsi_hot_plug'], False)
        self.assertEqual(extra['disc_scsi_hot_unplug'], False)
        self.assertEqual(extra['licence_type'], 'OTHER')

        self.assertEqual(extra['image_type'], 'CDROM')
        self.assertEqual(extra['public'], True)

    def test_list_locations(self):

        locations = self.driver.list_locations()

        self.assertEqual(len(locations), 3)

        '''
        Standard properties
        '''
        location = locations[0]
        self.assertEqual(location.id, 'de/fkb')
        self.assertEqual(location.name, 'karlsruhe')
        self.assertEqual(location.country, 'de')

    def test_list_nodes(self):

        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 2)

        node = nodes[0]
        extra = node.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            node.id,
            'srv-1'
        )
        self.assertEqual(
            node.name,
            'Test Node.'
        )
        self.assertEqual(
            node.state,
            NodeState.RUNNING
        )
        self.assertEqual(
            node.public_ips,
            []
        )
        self.assertEqual(
            node.private_ips,
            []
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'e7cf186125f51f3d9511754a40dcd12c'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['boot_cdrom'],
            None
        )
        self.assertEqual(
            extra['boot_volume']['id'],
            'bvol-1'
        )
        self.assertEqual(
            extra['boot_volume']['href'],
            (
                '/cloudapi/v3/datacenters/dc-1'
                '/volumes/bvol-1'
            )
        )
        self.assertEqual(
            extra['boot_volume']['properties']['name'],
            'Test Node Volume'
        )
        self.assertEqual(
            extra['boot_volume']['properties']['type'],
            'HDD'
        )
        self.assertEqual(
            extra['boot_volume']['properties']['size'],
            10
        )
        self.assertEqual(
            extra['boot_volume']['properties']['image'],
            'bvol-img'
        )
        self.assertEqual(
            extra['cpu_family'],
            'AMD_OPTERON'
        )

        '''
        Other miscellaneous
        '''
        self.assertEqual(
            len(extra['entities']),
            3
        )
        self.assertNotIn(
            'status_url',
            extra
        )

    def test_ex_list_availability_zones(self):

        zones = self.driver.ex_list_availability_zones()
        self.assertEqual(len(zones), 3)

        zones_sorted = sorted(list(a.name for a in zones))
        zones_expected = ['AUTO', 'ZONE_1', 'ZONE_2']
        self.assertEqual(zones_sorted, zones_expected)

    def test_list_volumes(self):

        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 3)

        volume = volumes[0]
        extra = volume.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            volume.id,
            'bvol-1'
        )
        self.assertEqual(
            volume.name,
            'Test Volume'
        )
        self.assertEqual(
            volume.size,
            10
        )

        '''
        Extra
        '''
        self.assertEqual(
            extra['provisioning_state'],
            NodeState.RUNNING)

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['created_date'],
            '2016-10-18T07:20:41Z'
        )
        self.assertEqual(
            extra['etag'],
            '33f6b8d506e7ad756e8554b915f29c61'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T07:20:41Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Volume'
        )
        self.assertEqual(
            extra['type'],
            'HDD'
        )
        self.assertEqual(
            extra['size'],
            10
        )
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['image'],
            'bvol-img'
        )
        self.assertEqual(
            extra['image_password'],
            None
        )
        self.assertEqual(
            extra['ssh_keys'],
            None
        )
        self.assertEqual(
            extra['bus'],
            'VIRTIO'
        )
        self.assertEqual(
            extra['licence_type'],
            'LINUX'
        )
        self.assertEqual(
            extra['cpu_hot_plug'],
            True
        )

        self.assertEqual(
            extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            extra['nic_hot_unplug'],
            True
        )

        self.assertEqual(
            extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['device_number'],
            1
        )

    def test_ex_list_datacenters(self):

        datacenters = self.driver.ex_list_datacenters()
        self.assertEqual(len(datacenters), 1)

        datacenter = datacenters[0]
        extra = datacenter.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            datacenter.id,
            'dc-1'
        )
        self.assertEqual(
            datacenter.href,
            '/cloudapi/v3/datacenters/dc-1'
        )
        self.assertEqual(
            datacenter.name,
            'Test One.'
        )
        self.assertEqual(
            datacenter.version,
            3
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test One.'
        )
        self.assertEqual(
            extra['description'],
            'A test data center'
        )
        self.assertEqual(
            extra['location'],
            'de/fra'
        )
        self.assertEqual(
            extra['version'],
            3
        )
        self.assertEqual(
            extra['features'],
            ['SSD', 'MULTIPLE_CPU']
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-14T07:24:59Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['etag'],
            'bdddec2287cb7723e86ac088bf644606'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T15:27:25Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )

        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )
        self.assertEqual(
            extra['provisioning_state'],
            NodeState.RUNNING
        )
        self.assertEqual(
            len(extra['entities']),
            4
        )
        self.assertNotIn(
            'status_url',
            extra
        )

    def test_list_snapshots(self):

        volume_snapshots = self.driver.list_snapshots()
        self.assertEqual(len(volume_snapshots), 1)

        snapshot = volume_snapshots[0]

        '''
        Standard properties
        '''
        self.assertEqual(
            snapshot.id,
            'sshot'
        )
        self.assertEqual(
            snapshot.size,
            10
        )
        self.assertEqual(
            snapshot.created,
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.state,
            NodeState.RUNNING)
        self.assertEqual(
            snapshot.name,
            'Balancer Testing 1 Storage-Snapshot-10/26/2016'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            snapshot.extra['name'],
            'Balancer Testing 1 Storage-Snapshot-10/26/2016'
        )
        self.assertEqual(
            snapshot.extra['description'],
            (
                'Created from \"Balancer Testing 1'
                ' Storage\" in Data Center \"Snapshot\"'
            )
        )
        self.assertEqual(
            snapshot.extra['location'],
            'us/las'
        )
        self.assertEqual(
            snapshot.extra['size'],
            10
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['nic_hot_unplug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            snapshot.extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['licence_type'],
            'LINUX'
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            snapshot.extra['created_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['etag'],
            '01873262ac042b5f44ed33b4241225b4'
        )
        self.assertEqual(
            snapshot.extra['last_modified_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['state'],
            'AVAILABLE'
        )

    '''
    Function tests for operations on volume snapshots
    '''

    def test_create_volume_snapshot(self):
        volume = self.driver.ex_describe_volume(
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/vol-2'
            )
        )
        snapshot = self.driver.create_volume_snapshot(volume=volume)

        '''
        Standard properties
        '''
        self.assertEqual(
            snapshot.id,
            'sshot'
        )
        self.assertEqual(
            snapshot.size,
            10
        )
        self.assertEqual(
            snapshot.created,
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.state,
            NodeState.PENDING
        )
        self.assertEqual(
            snapshot.name,
            'Test Created Snapshot'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            snapshot.extra['name'],
            'Test Created Snapshot'
        )
        self.assertEqual(
            snapshot.extra['description'],
            'Test Created Snapshot'
        )
        self.assertEqual(
            snapshot.extra['location'],
            'us/las'
        )
        self.assertEqual(
            snapshot.extra['size'],
            10
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['nic_hot_unplug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_unplug'],
            True
        )

        self.assertEqual(
            snapshot.extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            snapshot.extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['licence_type'],
            'LINUX'
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            snapshot.extra['created_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['etag'],
            '01873262ac042b5f44ed33b4241225b4'
        )
        self.assertEqual(
            snapshot.extra['last_modified_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['state'],
            'BUSY'
        )

    def test_ex_describe_snapshot(self):
        snapshot_w_href = self.driver.ex_describe_snapshot(
            ex_href='/cloudapi/v3/snapshots/sshot'
        )
        snapshot_w_id = self.driver.ex_describe_snapshot(
            ex_snapshot_id='sshot'
        )
        self._verify_snapshot(snapshot=snapshot_w_href)
        self._verify_snapshot(snapshot=snapshot_w_id)

    def _verify_snapshot(self, snapshot):
        '''
        Standard properties
        '''
        self.assertEqual(
            snapshot.id,
            'sshot'
        )
        self.assertEqual(
            snapshot.size,
            10
        )
        self.assertEqual(
            snapshot.created,
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.state,
            NodeState.RUNNING
        )
        self.assertEqual(
            snapshot.name,
            'Test Snapshot'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            snapshot.extra['name'],
            'Test Snapshot'
        )
        self.assertEqual(
            snapshot.extra['description'],
            'Test Snapshot'
        )
        self.assertEqual(
            snapshot.extra['location'],
            'us/las'
        )
        self.assertEqual(
            snapshot.extra['size'],
            10
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['nic_hot_unplug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            snapshot.extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            snapshot.extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            snapshot.extra['licence_type'],
            'LINUX'
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            snapshot.extra['created_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['etag'],
            '01873262ac042b5f44ed33b4241225b4'
        )
        self.assertEqual(
            snapshot.extra['last_modified_date'],
            '2016-10-26T11:38:45Z'
        )
        self.assertEqual(
            snapshot.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            snapshot.extra['state'],
            'AVAILABLE'
        )

    def test_ex_update_snapshot(self):
        snapshot = self.driver.ex_describe_snapshot(
            ex_href='/cloudapi/v3/snapshots/sshot'
        )
        updated = self.driver.ex_update_snapshot(
            snapshot=snapshot,
            name='Updated snapshot',
            description='Upated snapshot',
            cpu_hot_unplug=True
        )

        self.assertEqual(
            updated.name,
            'Updated snapshot'
        )
        self.assertEqual(
            updated.extra['description'],
            'Updated snapshot'
        )
        self.assertEqual(
            updated.extra['cpu_hot_unplug'],
            True
        )

    def test_destroy_volume_snapshot(self):
        snapshot = self.driver.ex_describe_snapshot(
            ex_href='/cloudapi/v3/snapshots/sshot'
        )
        destroyed = self.driver.destroy_volume_snapshot(snapshot)
        self.assertTrue(destroyed)

    '''
    Function tests for operations on nodes (servers)
    '''

    def test_reboot_node(self):
        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/dc-1'
                '/servers/srv-1'
            )
        )
        rebooted = self.driver.reboot_node(node=node)
        self.assertTrue(rebooted)

    def test_create_node(self):
        image = self.driver.ex_describe_image(
            ex_href='/cloudapi/v3/images/img-2'
        )
        datacenter = self.driver.ex_describe_datacenter(
            ex_href='/cloudapi/v3/datacenters/dc-1'
        )
        sizes = self.driver.list_sizes()

        with self.assertRaises(ValueError):
            'Raises value error if no size or ex_ram'
            self.driver.create_node(
                name='Test',
                image=image,
                ex_disk=40,
                ex_cores=1
            )

        with self.assertRaises(ValueError):
            'Raises value error if no size or ex_cores'
            self.driver.create_node(
                name='Test',
                image=image,
                ex_disk=40,
                ex_ram=1024
            )

        with self.assertRaises(ValueError):
            'Raises value error if no size or ex_disk'
            self.driver.create_node(
                name='Test',
                image=image,
                ex_cores=2,
                ex_ram=1024
            )

        with self.assertRaises(ValueError):
            'Raises value error if no ssh keys or password'
            self.driver.create_node(
                name='Test',
                image=image,
                size=sizes[1],
                datacenter=datacenter
            )

        node = self.driver.create_node(
            name='Test',
            image=image,
            size=sizes[1],
            ex_password='dummy1234',
            datacenter=datacenter
        )

        extra = node.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            node.id,
            'srv-2'
        )
        self.assertEqual(
            node.name,
            'Test'
        )
        self.assertEqual(
            node.state,
            NodeState.UNKNOWN
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T13:25:19Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '9bea2412ac556b402a07260fc0d1603f'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T13:25:19Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test'
        )
        self.assertEqual(
            extra['cores'],
            1
        )
        self.assertEqual(
            extra['ram'],
            512
        )
        self.assertEqual(
            extra['availability_zone'],
            'ZONE_1'
        )
        self.assertEqual(
            extra['vm_state'],
            None
        )

        self.assertEqual(
            extra['boot_cdrom'],
            None
        )
        self.assertEqual(
            extra['boot_volume'],
            None
        )
        self.assertEqual(
            extra['cpu_family'],
            'INTEL_XEON'
        )

        '''
        Extra entities
        '''
        self.assertEqual(
            len(extra['entities']['volumes']['items']),
            1
        )

    def test_destroy_node(self):
        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        destroyed = self.driver.destroy_node(
            node=node,
            ex_remove_attached_disks=False
        )
        self.assertTrue(destroyed)

    def test_ex_list_attached_volumes(self):

        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/servers/'
                'srv-1'
            )
        )

        attached_volumes = self.driver.ex_list_attached_volumes(node)
        self.assertEqual(len(attached_volumes), 3)

    def test_attach_volume(self):

        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        volume = self.driver.ex_describe_volume(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/vol-2'
            )
        )

        attached = self.driver.attach_volume(node=node, volume=volume)
        extra = attached.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            attached.id,
            'vol-2'
        )
        self.assertEqual(
            attached.name,
            'Updated storage name'
        )
        self.assertEqual(
            attached.size,
            40
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T13:13:36Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'c1800ce349033f9cd2c095ea1ea4976a'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T13:47:52Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated storage name'
        )
        self.assertEqual(
            extra['type'],
            'HDD'
        )
        self.assertEqual(
            extra['size'],
            40
        )
        self.assertEqual(
            extra['image'],
            'bvol-img'
        )

        self.assertEqual(
            extra['image_password'],
            None
        )
        self.assertEqual(
            extra['ssh_keys'],
            None
        )
        self.assertEqual(
            extra['bus'],
            'VIRTIO'
        )
        self.assertEqual(
            extra['licence_type'],
            'LINUX'
        )
        self.assertEqual(
            extra['cpu_hot_plug'],
            True
        )

        self.assertEqual(
            extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            extra['nic_hot_unplug'],
            True
        )

        self.assertEqual(
            extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['device_number'],
            3
        )

        self.assertNotIn(
            'availability_zone',
            extra
        )

    def test_detach_volume(self):

        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        volume = self.driver.ex_describe_volume(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/vol-2'
            )
        )
        detached = self.driver.detach_volume(
            node=node,
            volume=volume
        )
        self.assertTrue(detached)

    def test_ex_stop_node(self):

        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        stopped = self.driver.ex_stop_node(node)
        self.assertTrue(stopped)

    def test_ex_start_node(self):
        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        started = self.driver.ex_start_node(node)
        self.assertTrue(started)

    def test_ex_describe_node(self):
        node_w_href = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        node_w_id = self.driver.ex_describe_node(
            ex_datacenter_id='dc-1',
            ex_node_id='srv-1'
        )
        self._verify_node(node=node_w_href)
        self._verify_node(node=node_w_id)

    def _verify_node(self, node):
        extra = node.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            node.id,
            'srv-1'
        )
        self.assertEqual(
            node.name,
            'A test node'
        )
        self.assertEqual(
            node.state,
            NodeState.RUNNING
        )
        self.assertEqual(
            node.public_ips,
            []
        )
        self.assertEqual(
            node.private_ips,
            []
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['etag'],
            'e7cf186125f51f3d9511754a40dcd12c')
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['boot_cdrom'],
            None
        )
        self.assertEqual(
            extra['boot_volume']['id'],
            'bvol-1'
        )
        self.assertEqual(
            extra['boot_volume']['href'],
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/bvol-1'
            )
        )
        self.assertEqual(
            extra['boot_volume']['properties']['name'],
            'A test node boot volume'
        )

        self.assertEqual(
            extra['boot_volume']['properties']['type'],
            'HDD'
        )
        self.assertEqual(
            extra['boot_volume']['properties']['size'],
            10
        )
        self.assertEqual(
            extra['boot_volume']['properties']['image'],
            'bvol-img'
        )
        self.assertEqual(
            extra['cpu_family'],
            'AMD_OPTERON'
        )

        '''
        Other miscellaneous
        '''
        self.assertEqual(
            len(extra['entities']),
            3
        )
        self.assertNotIn(
            'status_url',
            extra
        )

    def test_ex_update_node(self):

        node = self.driver.ex_describe_node(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        zones = self.driver.ex_list_availability_zones()
        updated = self.driver.ex_update_node(
            node=node,
            name='Test update',
            cores=4,
            ram=4096,
            availability_zone=zones[0],
            ex_cpu_family='INTEL_XEON'
        )

        extra = updated.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            updated.id,
            'srv-1'
        )
        self.assertEqual(
            updated.name,
            'A test node'
        )
        self.assertEqual(
            updated.state,
            NodeState.RUNNING
        )
        self.assertEqual(
            updated.public_ips,
            []
        )
        self.assertEqual(
            updated.private_ips,
            []
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['etag'],
            'e7cf186125f51f3d9511754a40dcd12c'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T07:28:05Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['boot_cdrom'],
            None
        )
        self.assertEqual(
            extra['boot_volume']['id'],
            'bvol-1'
        )
        self.assertEqual(
            extra['boot_volume']['href'],
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/bvol-1'
            )
        )
        self.assertEqual(
            extra['cpu_family'],
            'AMD_OPTERON'
        )

    '''
    Function tests for operations on volumes
    '''

    def test_create_volume(self):

        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        image = self.driver.ex_describe_image(
            ex_href='/cloudapi/v3/images/img-2'
        )
        created = self.driver.create_volume(
            size=30,
            name='Test volume',
            ex_type='HDD',
            ex_bus_type='IDE',
            ex_datacenter=datacenter,
            image=image,
            ex_password='dummyP8ssw0rdl33t'
        )

        self.assertTrue(created)

    def test_destroy_volume(self):

        volume = self.driver.ex_describe_volume(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/volumes/'
                'vol-2'
            )
        )
        destroyed = self.driver.destroy_volume(volume=volume)

        self.assertTrue(destroyed)

    def test_ex_update_volume(self):

        volume = self.driver.ex_describe_volume(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/vol-2'
            )

        )
        updated = self.driver.ex_update_volume(
            volume=volume,
            ex_storage_name='Updated volume',
            size=48,
            ex_bus_type='VIRTIO'
        )

        extra = updated.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            updated.id,
            'vol-2'
        )
        self.assertEqual(
            updated.name,
            'Updated storage name'
        )
        self.assertEqual(
            updated.size,
            40
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T13:13:36Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'c1800ce349033f9cd2c095ea1ea4976a'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T13:47:52Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated storage name'
        )
        self.assertEqual(
            extra['type'],
            'HDD'
        )
        self.assertEqual(
            extra['size'],
            40
        )
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['image'],
            'bvol-img'
        )

        self.assertEqual(
            extra['image_password'],
            None
        )
        self.assertEqual(
            extra['ssh_keys'],
            None
        )
        self.assertEqual(
            extra['bus'],
            'VIRTIO'
        )
        self.assertEqual(
            extra['licence_type'],
            'LINUX'
        )
        self.assertEqual(
            extra['cpu_hot_plug'],
            True
        )

        self.assertEqual(
            extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            extra['nic_hot_unplug'],
            True
        )

        self.assertEqual(
            extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['device_number'],
            3
        )

        return {}

    def test_ex_describe_volume(self):
        volume_w_href = self.driver.ex_describe_volume(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'volumes/vol-2'
            )
        )
        volume_w_id = self.driver.ex_describe_volume(
            ex_datacenter_id='dc-1',
            ex_volume_id='vol-2'
        )
        self._verify_volume(volume=volume_w_href)
        self._verify_volume(volume=volume_w_id)

    def _verify_volume(self, volume):
        extra = volume.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            volume.id,
            'vol-2'
        )
        self.assertEqual(
            volume.name,
            'Updated storage name'
        )
        self.assertEqual(
            volume.size,
            40
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T13:13:36Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'c1800ce349033f9cd2c095ea1ea4976a'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T13:47:52Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated storage name'
        )
        self.assertEqual(
            extra['type'],
            'HDD'
        )
        self.assertEqual(
            extra['size'],
            40
        )
        self.assertEqual(
            extra['availability_zone'],
            'AUTO'
        )
        self.assertEqual(
            extra['image'],
            'bvol-img'
        )

        self.assertEqual(
            extra['image_password'],
            None
        )
        self.assertEqual(
            extra['ssh_keys'],
            None
        )
        self.assertEqual(
            extra['bus'],
            'VIRTIO'
        )
        self.assertEqual(
            extra['licence_type'],
            'LINUX'
        )
        self.assertEqual(
            extra['cpu_hot_plug'],
            True
        )

        self.assertEqual(
            extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_plug'],
            True
        )
        self.assertEqual(
            extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_plug'],
            True
        )
        self.assertEqual(
            extra['nic_hot_unplug'],
            True
        )

        self.assertEqual(
            extra['disc_virtio_hot_plug'],
            True
        )
        self.assertEqual(
            extra['disc_virtio_hot_unplug'],
            True
        )
        self.assertEqual(
            extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['device_number'],
            3
        )

        self.assertNotIn(
            'status_url',
            extra
        )

    '''
    Function tests for operations on data centers
    '''

    def test_ex_create_datacenter(self):
        location = self.driver.ex_describe_location(ex_location_id='de/fkb')
        datacenter = self.driver.ex_create_datacenter(
            name='Test Data Center',
            location=location,
            description='Test Data Center.'
        )

        extra = datacenter.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            datacenter.id,
            'dc-1'
        )
        self.assertEqual(
            datacenter.href,
            '/cloudapi/v3/datacenters/dc-1'
        )
        self.assertEqual(
            datacenter.name,
            'Test Data Center'
        )
        self.assertEqual(
            datacenter.version,
            None
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-18T17:20:56Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'c2d3d4d9bbdc0fff7d3c5c3864a68a46'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T17:20:56Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Data Center'
        )
        self.assertEqual(
            extra['description'],
            'Test Data Center.'
        )
        self.assertEqual(
            extra['location'],
            'us/las'
        )
        self.assertEqual(
            extra['version'],
            None
        )
        self.assertEqual(
            extra['features'],
            []
        )

        '''
        Miscellaneous properties
        '''
        self.assertNotIn(
            'entities',
            extra
        )
        self.assertEqual(
            extra['provisioning_state'],
            NodeState.PENDING
        )

    def test_ex_destroy_datacenter(self):

        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        destroyed = self.driver.ex_destroy_datacenter(
            datacenter=datacenter
        )
        self.assertTrue(destroyed)

    def test_ex_describe_datacenter(self):
        datacenter_w_href = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        datacenter_w_id = self.driver.ex_describe_datacenter(
            ex_datacenter_id='dc-1'
        )
        self._verify_datacenter(datacenter=datacenter_w_href)
        self._verify_datacenter(datacenter=datacenter_w_id)

    def _verify_datacenter(self, datacenter):
        extra = datacenter.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            datacenter.id,
            'dc-1'
        )
        self.assertEqual(
            datacenter.href,
            '/cloudapi/v3/datacenters/dc-1'
        )
        self.assertEqual(
            datacenter.name,
            'Test Data Center'
        )
        self.assertEqual(
            datacenter.version,
            35
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T11:33:11Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['etag'],
            '53b215b8ec0356a649955dab019845a4'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T15:13:44Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Data Center'
        )
        self.assertEqual(
            extra['description'],
            'This is a test data center.'
        )
        self.assertEqual(
            extra['location'],
            'de/fkb'
        )
        self.assertEqual(
            extra['version'],
            35
        )
        self.assertEqual(
            extra['features'],
            ['SSD', 'MULTIPLE_CPU']
        )

        self.assertNotIn(
            'status_url',
            extra
        )
        self.assertEqual(
            extra['provisioning_state'],
            NodeState.RUNNING
        )
        self.assertEqual(
            len(extra['entities']),
            4
        )

    def test_ex_rename_datacenter(self):

        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        renamed = self.driver.ex_rename_datacenter(
            datacenter=datacenter,
            name='Renamed data center'
        )
        extra = renamed.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            renamed.id,
            'dc-1'
        )
        self.assertEqual(
            renamed.href,
            '/cloudapi/v3/datacenters/dc-1'
        )
        self.assertEqual(
            renamed.name,
            'Test Data Center'
        )
        self.assertEqual(
            renamed.version,
            35
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T11:33:11Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['etag'],
            '53b215b8ec0356a649955dab019845a4'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T15:13:44Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.test'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Data Center'
        )
        self.assertEqual(
            extra['description'],
            'This is a test data center.'
        )
        self.assertEqual(
            extra['location'],
            'de/fkb'
        )
        self.assertEqual(
            extra['version'],
            35
        )
        self.assertEqual(
            extra['features'],
            ['SSD', 'MULTIPLE_CPU']
        )

        self.assertNotIn(
            'status_url',
            extra
        )
        self.assertEqual(
            extra['provisioning_state'],
            NodeState.PENDING
        )
        self.assertEqual(
            len(extra['entities']),
            4
        )

    '''
    Function tests for operations on images
    '''
    def test_ex_describe_image(self):
        image_w_href = self.driver.ex_describe_image(
            ex_href=(
                '/cloudapi/v3/images/'
                'img-2'
            )
        )
        image_w_id = self.driver.ex_describe_image(
            ex_image_id='img-2'
        )
        self._verify_image(image=image_w_href)
        self._verify_image(image=image_w_id)

    def _verify_image(self, image):
        extra = image.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            image.id,
            'img-2'
        )
        self.assertEqual(
            image.name,
            'vivid-server-cloudimg-amd64-disk1.img'
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2015-10-09T12:06:34Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'bbf76112358af2fc5dd1bf21de8988db'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2015-11-11T15:23:20Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'vivid-server-cloudimg-amd64-disk1.img'
        )
        self.assertEqual(
            extra['description'],
            None
        )
        self.assertEqual(
            extra['location'],
            'de/fkb'
        )
        self.assertEqual(
            extra['size'],
            2
        )
        self.assertEqual(
            extra['cpu_hot_plug'],
            False
        )

        self.assertEqual(
            extra['cpu_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_plug'],
            False
        )
        self.assertEqual(
            extra['ram_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_plug'],
            False
        )
        self.assertEqual(
            extra['nic_hot_unplug'],
            False
        )

        self.assertEqual(
            extra['disc_virtio_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_virtio_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_plug'],
            False
        )
        self.assertEqual(
            extra['disc_scsi_hot_unplug'],
            False
        )
        self.assertEqual(
            extra['licence_type'],
            'UNKNOWN'
        )

        self.assertEqual(
            extra['image_type'],
            'HDD'
        )
        self.assertEqual(
            extra['public'],
            False
        )
        self.assertEqual(
            extra['href'],
            '/cloudapi/v3/images/img-2'
        )

    def test_ex_update_image(self):
        image = self.driver.ex_describe_image(
            ex_href=(
                '/cloudapi/v3/images/'
                'img-2'
            )
        )
        updated = self.driver.ex_update_image(
            image=image,
            name='my-updated-image.img'
        )
        extra = updated.extra

        self.assertEqual(
            updated.name,
            'my-updated-image.img'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-11-11T15:23:20Z'
        )

    def test_ex_delete_image(self):
        image = self.driver.ex_describe_image(
            ex_href=(
                '/cloudapi/v3/images/'
                'img-2'
            )
        )
        deleted = self.driver.ex_delete_image(image)
        self.assertTrue(deleted)

    '''
    Function tests for operations on network interfaces
    '''

    def test_ex_list_network_interfaces(self):

        network_interfaces = self.driver.ex_list_network_interfaces()
        self.assertEqual(
            len(network_interfaces),
            4
        )

        network_interface = network_interfaces[0]
        extra = network_interface.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            network_interface.id,
            'nic-1'
        )
        self.assertEqual(
            network_interface.name,
            'Test network interface'
        )
        self.assertEqual(
            network_interface.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/servers/'
                's-3/nics/'
                'nic-1'
            )
        )
        self.assertEqual(
            network_interface.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T15:46:38Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'dbd8216137cf0ec9951170f93fa8fa53'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T18:19:43Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test network interface'
        )
        self.assertEqual(
            extra['mac'],
            '02:01:0b:9d:4d:ce'
        )
        self.assertEqual(
            extra['ips'],
            ['10.15.124.11']
        )
        self.assertEqual(
            extra['dhcp'],
            False
        )
        self.assertEqual(
            extra['lan'],
            2
        )
        self.assertEqual(
            extra['firewall_active'],
            True
        )
        self.assertEqual(
            extra['nat'],
            False
        )

    def test_ex_describe_network_interface(self):
        nic_w_href = self.driver.ex_describe_network_interface(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        nic_w_id = self.driver.ex_describe_network_interface(
            ex_datacenter_id='dc-1',
            ex_server_id='s-3',
            ex_nic_id='nic-2'
        )
        self._verify_network_interface(network_interface=nic_w_href)
        self._verify_network_interface(network_interface=nic_w_id)

    def _verify_network_interface(self, network_interface):
        extra = network_interface.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            network_interface.id,
            'nic-2'
        )
        self.assertEqual(
            network_interface.name,
            'Updated from LibCloud'
        )
        self.assertEqual(
            network_interface.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2'
            )
        )
        self.assertEqual(
            network_interface.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T15:46:38Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'dbd8216137cf0ec9951170f93fa8fa53'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T18:19:43Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated from LibCloud'
        )
        self.assertEqual(
            extra['mac'],
            '02:01:0b:9d:4d:ce'
        )
        self.assertEqual(
            extra['ips'],
            ['10.15.124.11']
        )
        self.assertEqual(
            extra['dhcp'],
            False
        )
        self.assertEqual(
            extra['lan'],
            2
        )
        self.assertEqual(
            extra['firewall_active'],
            True
        )
        self.assertEqual(
            extra['nat'],
            False
        )

        '''
        Miscellaneous
        '''
        self.assertTrue(
            len(extra['entities']),
            1
        )

    def test_ex_create_network_interface(self):

        node = self.driver.ex_describe_node(
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
            )
        )
        network_interface = self.driver.ex_create_network_interface(
            node=node,
            lan_id=1,
            dhcp_active=True,
            nic_name='Creating a test network interface.'
        )
        extra = network_interface.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            network_interface.id,
            'nic-2'
        )
        self.assertEqual(
            network_interface.name,
            'Creating a test network interface.'
        )
        self.assertEqual(
            network_interface.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/srv-1'
                '/nics/nic-2'
            )
        )
        self.assertEqual(
            network_interface.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T08:18:50Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '8679142b0b1b70c8b8c09a8b31e6ded9'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T08:18:50Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Creating a test network interface.'
        )
        self.assertEqual(
            extra['mac'],
            None
        )
        self.assertEqual(
            extra['ips'],
            []
        )
        self.assertEqual(
            extra['dhcp'],
            True
        )
        self.assertEqual(
            extra['lan'],
            1
        )
        self.assertEqual(
            extra['firewall_active'],
            None
        )
        self.assertEqual(
            extra['nat'],
            None
        )

    def test_ex_update_network_interface(self):

        network_interface = self.driver.ex_describe_network_interface(
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        updated = self.driver.ex_update_network_interface(
            network_interface=network_interface,
            name='New network interface', dhcp_active=False
        )

        extra = updated.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            updated.id,
            'nic-2'
        )
        self.assertEqual(
            updated.name,
            'Updated from LibCloud'
        )
        self.assertEqual(
            updated.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2'
            )
        )
        self.assertEqual(
            updated.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T08:18:55Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '56f8d8bbdc84faad4188f647a49a565b'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T09:44:59Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated from LibCloud'
        )
        self.assertEqual(
            extra['mac'],
            '02:01:68:c1:e8:88'
        )
        self.assertEqual(
            extra['ips'],
            ['11.12.13.14']
        )
        self.assertEqual(
            extra['dhcp'],
            True
        )
        self.assertEqual(
            extra['lan'],
            1
        )
        self.assertEqual(
            extra['firewall_active'],
            False
        )
        self.assertEqual(
            extra['nat'],
            False
        )

        self.assertTrue(updated)

    def test_ex_destroy_network_interface(self):

        network_interface = self.driver.ex_describe_network_interface(
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        destroyed = self.driver.ex_destroy_network_interface(
            network_interface=network_interface
        )

        self.assertTrue(destroyed)

    def test_ex_set_inet_access(self):
        network_interface = self.driver.ex_describe_network_interface(
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        updated = self.driver.ex_set_inet_access(
            network_interface=network_interface,
            internet_access=False)

        self.assertTrue(updated)

        return {}

    '''
    Function tests for operations on locations
    '''

    def test_ex_describe_location(self):
        location_w_href = self.driver.ex_describe_location(
            ex_href=(
                '/cloudapi/v3/locations/de/fkb'
            )
        )
        location_w_id = self.driver.ex_describe_location(
            ex_location_id='de/fkb'
        )
        self._verify_location(location=location_w_href)
        self._verify_location(location=location_w_id)

    def _verify_location(self, location):
        self.assertEqual(
            location.id,
            'de/fkb'
        )
        self.assertEqual(
            location.name,
            'karlsruhe'
        )
        self.assertEqual(
            location.country,
            'de'
        )

    '''
    Function tests for operations on firewall rules
    '''

    def test_ex_list_firewall_rules(self):
        network_interface = self.driver.ex_describe_network_interface(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2'
            )
        )
        firewall_rules = self.driver.ex_list_firewall_rules(network_interface)
        self.assertEqual(
            len(firewall_rules),
            3
        )

        firewall_rule = firewall_rules[0]
        extra = firewall_rule.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            firewall_rule.id,
            'fwr-1'
        )
        self.assertEqual(
            firewall_rule.name,
            'Test updated firewall rule'
        )
        self.assertEqual(
            firewall_rule.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2/'
                'firewallrules/fwr-1'
            )
        )
        self.assertEqual(
            firewall_rule.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T11:08:10Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'b91a2e082a7422dafb79d84a07fb2a28'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T11:19:04Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test updated firewall rule'
        )
        self.assertEqual(
            extra['protocol'],
            'TCP'
        )
        self.assertEqual(
            extra['source_mac'],
            None
        )
        self.assertEqual(
            extra['source_ip'],
            None
        )
        self.assertEqual(
            extra['target_ip'],
            None
        )

        self.assertEqual(
            extra['icmp_code'],
            None
        )
        self.assertEqual(
            extra['icmp_type'],
            None
        )
        self.assertEqual(
            extra['port_range_start'],
            80
        )
        self.assertEqual(
            extra['port_range_end'],
            80
        )

    def test_ex_describe_firewall_rule(self):
        firewall_rule_w_href = self.driver.ex_describe_firewall_rule(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/servers/'
                's-3/nics/'
                'nic-2/firewallrules'
                '/fw2'
            )
        )
        firewall_rule_w_id = self.driver.ex_describe_firewall_rule(
            ex_datacenter_id='dc-1',
            ex_server_id='s-3',
            ex_nic_id='nic-2',
            ex_firewall_rule_id='fw2'
        )
        self._verify_firewall_rule(firewall_rule=firewall_rule_w_href)
        self._verify_firewall_rule(firewall_rule=firewall_rule_w_id)

    def _verify_firewall_rule(self, firewall_rule):
        extra = firewall_rule.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            firewall_rule.id,
            'fw2'
        )
        self.assertEqual(
            firewall_rule.name,
            'HTTPs (SSL)'
        )
        self.assertEqual(
            firewall_rule.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/servers/'
                's-3/nics/'
                'nic-2/'
                'firewallrules/fw2'
            )
        )
        self.assertEqual(
            firewall_rule.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T09:55:10Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '00bb5b86562db1ed19ca38697e485160'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T09:55:10Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'HTTPs (SSL)'
        )
        self.assertEqual(
            extra['protocol'],
            'TCP'
        )
        self.assertEqual(
            extra['source_mac'],
            None
        )
        self.assertEqual(
            extra['source_ip'],
            None
        )
        self.assertEqual(
            extra['target_ip'],
            None
        )

        self.assertEqual(
            extra['icmp_code'],
            None
        )
        self.assertEqual(
            extra['icmp_type'],
            None
        )
        self.assertEqual(
            extra['port_range_start'],
            443
        )
        self.assertEqual(
            extra['port_range_end'],
            443
        )

    def test_ex_create_firewall_rule(self):

        network_interface = self.driver.ex_describe_network_interface(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2'
            )
        )

        firewall_rule = self.driver.ex_create_firewall_rule(
            network_interface=network_interface,
            protocol='TCP',
            name='Test created firewall rule',
            port_range_start=80,
            port_range_end=80
        )

        extra = firewall_rule.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            firewall_rule.id,
            'fwr-1'
        )
        self.assertEqual(
            firewall_rule.name,
            'Test created firewall rule'
        )
        self.assertEqual(
            firewall_rule.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2/'
                'firewallrules/fwr-1'
            )
        )
        self.assertEqual(
            firewall_rule.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T11:08:04Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '2a21551ba4adf85d9fb04b05a6938bcc'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T11:08:04Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test created firewall rule'
        )
        self.assertEqual(
            extra['protocol'],
            'TCP'
        )
        self.assertEqual(
            extra['source_mac'],
            None
        )
        self.assertEqual(
            extra['source_ip'],
            None
        )
        self.assertEqual(
            extra['target_ip'],
            None
        )

        self.assertEqual(
            extra['icmp_code'],
            None
        )
        self.assertEqual(
            extra['icmp_type'],
            None
        )
        self.assertEqual(
            extra['port_range_start'],
            80
        )
        self.assertEqual(
            extra['port_range_end'],
            80
        )

    def test_ex_update_firewall_rule(self):

        firewall_rule = self.driver.ex_describe_firewall_rule(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2/'
                'firewallrules/fw2'
            )
        )
        updated = self.driver.ex_update_firewall_rule(
            firewall_rule=firewall_rule,
            name='Test updated firewall rule',
            port_range_start=8080,
            port_range_end=8080
        )

        extra = updated.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            updated.id,
            'fw2'
        )
        self.assertEqual(
            updated.name,
            'HTTPs (SSL)'
        )
        self.assertEqual(
            updated.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2/'
                'firewallrules/fw2'
            )
        )
        self.assertEqual(
            updated.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-19T09:55:10Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '00bb5b86562db1ed19ca38697e485160'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-19T09:55:10Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'HTTPs (SSL)'
        )
        self.assertEqual(
            extra['protocol'],
            'TCP'
        )
        self.assertEqual(
            extra['source_mac'],
            None
        )
        self.assertEqual(
            extra['source_ip'],
            None
        )
        self.assertEqual(
            extra['target_ip'],
            None
        )

        self.assertEqual(
            extra['icmp_code'],
            None
        )
        self.assertEqual(
            extra['icmp_type'],
            None
        )
        self.assertEqual(
            extra['port_range_start'],
            443
        )
        self.assertEqual(
            extra['port_range_end'],
            443
        )

    def test_ex_delete_firewall_rule(self):

        firewall_rule = self.driver.ex_describe_firewall_rule(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2/'
                'firewallrules/fw2'
            )
        )
        deleted = self.driver.ex_delete_firewall_rule(firewall_rule)

        self.assertTrue(deleted)

    '''
    Function tests for operations on lans
    '''

    def test_ex_list_lans(self):
        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        lans = self.driver.ex_list_lans(
            datacenter=datacenter
        )
        lan = lans[0]
        extra = lan.extra
        self.assertEqual(
            len(lans),
            1
        )

        '''
        Standard properties
        '''
        self.assertEqual(
            lan.id,
            '1'
        )
        self.assertEqual(
            lan.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/1'
            )
        )
        self.assertEqual(
            lan.name,
            'Switch for LAN 1'
        )
        self.assertEqual(
            lan.is_public,
            False
        )
        self.assertEqual(
            lan.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-24T08:03:22Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-24T08:03:22Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Switch for LAN 1'
        )
        self.assertEqual(
            extra['is_public'],
            False
        )

        '''
        Miscellaneous
        '''
        self.assertEqual(
            len(extra['entities']),
            1
        )

    def test_ex_create_lan(self):
        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )
        lan = self.driver.ex_create_lan(
            datacenter=datacenter,
            is_public=True
        )
        extra = lan.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            lan.id,
            '10'
        )
        self.assertEqual(
            lan.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        self.assertEqual(
            lan.name,
            'Test Created Lan'
        )
        self.assertEqual(
            lan.is_public,
            True
        )
        self.assertEqual(
            lan.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T11:33:11Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '53b215b8ec0356a649955dab019845a4'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T15:13:44Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Created Lan'
        )
        self.assertEqual(
            extra['is_public'],
            True
        )

    def test_ex_describe_lan(self):
        lan_w_href = self.driver.ex_describe_lan(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        lan_w_id = self.driver.ex_describe_lan(
            ex_datacenter_id='dc-1',
            ex_lan_id='10'
        )
        self._verify_lan(lan=lan_w_href)
        self._verify_lan(lan=lan_w_id)

    def _verify_lan(self, lan):
        extra = lan.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            lan.id,
            '10'
        )
        self.assertEqual(
            lan.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        self.assertEqual(
            lan.name,
            'Test Created Lan'
        )
        self.assertEqual(
            lan.is_public,
            True
        )
        self.assertEqual(
            lan.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T11:33:11Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '53b215b8ec0356a649955dab019845a4'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T15:13:44Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Created Lan'
        )
        self.assertEqual(
            extra['is_public'],
            True
        )

    def test_ex_update_lan(self):
        lan = self.driver.ex_describe_lan(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        updated = self.driver.ex_update_lan(
            lan=lan,
            is_public=True,
            name='Updated Lan'
        )
        extra = updated.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            updated.id,
            '10'
        )
        self.assertEqual(
            updated.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        self.assertEqual(
            updated.name,
            'Test Updated Lan'
        )
        self.assertEqual(
            updated.is_public,
            True
        )
        self.assertEqual(
            updated.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T11:33:11Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '53b215b8ec0356a649955dab019845a4'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-18T15:13:44Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test Updated Lan'
        )
        self.assertEqual(
            extra['is_public'],
            True
        )

    def test_ex_delete_lan(self):
        lan = self.driver.ex_describe_lan(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/lans/10'
            )
        )
        deleted = self.driver.ex_delete_lan(lan)
        self.assertTrue(deleted)

    '''
    Function tests for operations on load balancers
    '''

    def test_ex_list_load_balancers(self):
        load_balancers = self.driver.ex_list_load_balancers()
        self.assertEqual(
            len(load_balancers),
            2
        )

        balancer = load_balancers[0]

        '''
        Standard properties
        '''
        self.assertEqual(
            balancer.id,
            'bal-1'
        )
        self.assertEqual(
            balancer.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )
        self.assertEqual(
            balancer.name,
            'Test One'
        )
        self.assertEqual(
            balancer.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            balancer.extra['created_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            balancer.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            balancer.extra['etag'],
            '71e8df57a58615b9e15400ede4138b41'
        )
        self.assertEqual(
            balancer.extra['last_modified_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            balancer.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            balancer.extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            balancer.extra['name'],
            'Test One'
        )
        self.assertEqual(
            balancer.extra['ip'],
            '111.112.113.114'
        )
        self.assertEqual(
            balancer.extra['dhcp'],
            True
        )

    def test_ex_describe_load_balancer(self):
        load_balancer_w_href = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )

        load_balancer_w_id = self.driver.ex_describe_load_balancer(
            ex_datacenter_id='dc-2',
            ex_load_balancer_id='bal-1'
        )
        self._verify_load_balancer(load_balancer=load_balancer_w_href)
        self._verify_load_balancer(load_balancer=load_balancer_w_id)

    def _verify_load_balancer(self, load_balancer):
        '''
        Standard properties
        '''
        self.assertEqual(
            load_balancer.id,
            'bal-1'
        )
        self.assertEqual(
            load_balancer.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )
        self.assertEqual(
            load_balancer.name,
            'Test One'
        )
        self.assertEqual(
            load_balancer.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            load_balancer.extra['created_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            load_balancer.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            load_balancer.extra['etag'],
            '71e8df57a58615b9e15400ede4138b41'
        )
        self.assertEqual(
            load_balancer.extra['last_modified_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            load_balancer.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            load_balancer.extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            load_balancer.extra['name'],
            'Test One'
        )
        self.assertEqual(
            load_balancer.extra['ip'],
            '111.112.113.114'
        )
        self.assertEqual(
            load_balancer.extra['dhcp'],
            True
        )

    def test_ex_create_load_balancer(self):
        datacenter = self.driver.ex_describe_datacenter(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1'
            )
        )

        created = self.driver.ex_create_load_balancer(
            datacenter=datacenter,
            name='Test load balancer',
            ip='10.11.12.13',
            dhcp=True
        )

        '''
        Standard properties
        '''
        self.assertEqual(
            created.id,
            'bal-1'
        )
        self.assertEqual(
            created.href,
            (
                '/cloudapi/v3/datacenters'
                '/dc-1'
                '/loadbalancers/bal-1'
            )
        )
        self.assertEqual(
            created.name,
            'Test load balancer'
        )
        self.assertEqual(
            created.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            created.extra['created_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            created.extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            created.extra['etag'],
            '71e8df57a58615b9e15400ede4138b41'
        )
        self.assertEqual(
            created.extra['last_modified_date'],
            '2016-10-26T13:02:33Z'
        )
        self.assertEqual(
            created.extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            created.extra['state'],
            'BUSY'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            created.extra['name'],
            'Test load balancer'
        )
        self.assertEqual(
            created.extra['ip'],
            None
        )
        self.assertEqual(
            created.extra['dhcp'],
            True
        )

    def test_ex_update_load_balancer(self):
        load_balancer = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )

        updated = self.driver.ex_update_load_balancer(
            load_balancer=load_balancer,
            name='Updated Load Balancer',
            ip='123.124.125.126',
            dhcp=False
        )

        self.assertEqual(
            updated.name,
            'Updated Load Balancer'
        )
        self.assertEqual(
            updated.extra['ip'],
            '123.124.125.126'
        )
        self.assertEqual(
            updated.extra['dhcp'],
            False
        )

    def test_ex_list_load_balanced_nics(self):
        load_balancer = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )

        network_interfaces = self.driver.ex_list_load_balanced_nics(
            load_balancer
        )
        network_interface = network_interfaces[0]
        extra = network_interface.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            network_interface.id,
            'nic-1'
        )
        self.assertEqual(
            network_interface.name,
            'Test network interface'
        )
        self.assertEqual(
            network_interface.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-1'
            )
        )
        self.assertEqual(
            network_interface.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T15:46:38Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'dbd8216137cf0ec9951170f93fa8fa53'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T18:19:43Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Test network interface'
        )
        self.assertEqual(
            extra['mac'],
            '02:01:0b:9d:4d:ce'
        )
        self.assertEqual(
            extra['ips'],
            ['10.15.124.11']
        )
        self.assertEqual(
            extra['dhcp'],
            False
        )
        self.assertEqual(
            extra['lan'],
            2
        )
        self.assertEqual(
            extra['firewall_active'],
            True
        )
        self.assertEqual(
            extra['nat'],
            False
        )

    def test_ex_describe_load_balanced_nic(self):
        network_interface_w_href = self.driver.ex_describe_network_interface(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3/'
                'nics/nic-2'
            )
        )
        network_interface_w_id = self.driver.ex_describe_network_interface(
            ex_datacenter_id='dc-1',
            ex_server_id='s-3',
            ex_nic_id='nic-2'
        )
        self._verify_load_balanced_nic(
            network_interface=network_interface_w_href
        )
        self._verify_load_balanced_nic(
            network_interface=network_interface_w_id
        )

    def _verify_load_balanced_nic(self, network_interface):
        extra = network_interface.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            network_interface.id,
            'nic-2'
        )
        self.assertEqual(
            network_interface.name,
            'Updated from LibCloud'
        )
        self.assertEqual(
            network_interface.href,
            (
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        self.assertEqual(
            network_interface.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-17T15:46:38Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'dbd8216137cf0ec9951170f93fa8fa53'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-17T18:19:43Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

        '''
        Extra properties
        '''
        self.assertEqual(
            extra['name'],
            'Updated from LibCloud'
        )
        self.assertEqual(
            extra['mac'],
            '02:01:0b:9d:4d:ce'
        )
        self.assertEqual(
            extra['ips'],
            ['10.15.124.11']
        )
        self.assertEqual(
            extra['dhcp'],
            False
        )
        self.assertEqual(
            extra['lan'],
            2
        )
        self.assertEqual(
            extra['firewall_active'],
            True
        )
        self.assertEqual(
            extra['nat'],
            False
        )

    def test_ex_attach_nic_to_load_balancer(self):
        network_interface = self.driver.ex_describe_network_interface(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-1/'
                'servers/s-3'
                '/nics/nic-2'
            )
        )
        load_balancer = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )
        attached = self.driver.ex_attach_nic_to_load_balancer(
            load_balancer=load_balancer,
            network_interface=network_interface
        )
        self.assertTrue(attached)

    def test_ex_remove_nic_from_load_balancer(self):
        network_interface = self.driver.ex_describe_network_interface(
            ex_href=(
                (
                    '/cloudapi/v3/datacenters/'
                    'dc-1/'
                    'servers/s-3/'
                    'nics/nic-2'
                )
            )
        )
        load_balancer = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )
        detached = self.driver.ex_remove_nic_from_load_balancer(
            load_balancer=load_balancer,
            network_interface=network_interface
        )
        self.assertTrue(detached)

    def test_ex_delete_load_balancer(self):
        load_balancer = self.driver.ex_describe_load_balancer(
            ex_href=(
                '/cloudapi/v3/datacenters/'
                'dc-2/'
                'loadbalancers/bal-1'
            )
        )
        deleted = self.driver.ex_delete_load_balancer(load_balancer)
        self.assertTrue(deleted)

    '''
    Function tests for operations on IP blocks
    '''

    def test_ex_list_ip_blocks(self):
        ip_blocks = self.driver.ex_list_ip_blocks()
        self.assertEqual(
            len(ip_blocks),
            2
        )

        ip_block = ip_blocks[0]
        extra = ip_block.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            ip_block.id,
            'ipb-1'
        )
        self.assertEqual(
            ip_block.name,
            'Test IP Block One'
        )
        self.assertEqual(
            ip_block.href,
            '/cloudapi/v3/ipblocks/ipb-1'
        )
        self.assertEqual(
            ip_block.location,
            'de/fkb'
        )
        self.assertEqual(
            ip_block.size,
            2
        )
        self.assertEqual(
            ip_block.ips,
            ['78.137.101.252', '78.137.101.251']
        )
        self.assertEqual(
            ip_block.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-26T15:05:36Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'acbf00bacf7ee48d4b8bc4e7413e1f30'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-26T15:05:36Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

    def test_ex_create_ip_block(self):
        location = self.driver.ex_describe_location(ex_location_id='de/fkb')
        created = self.driver.ex_create_ip_block(
            location=location,
            size=2,
            name='Test Created IP Block'
        )
        extra = created.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            created.id,
            'ipb-1'
        )
        self.assertEqual(
            created.name,
            'Test Created IP Block'
        )
        self.assertEqual(
            created.href,
            '/cloudapi/v3/ipblocks/ipb-1'
        )
        self.assertEqual(
            created.location,
            'de/fkb'
        )
        self.assertEqual(
            created.size,
            2
        )
        self.assertEqual(
            created.ips,
            ['11.12.13.14', '15.16.17.18']
        )
        self.assertEqual(
            created.state,
            NodeState.PENDING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-26T15:05:36Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            'acbf00bacf7ee48d4b8bc4e7413e1f30'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-26T15:05:36Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'BUSY'
        )

    def test_ex_describe_ip_block(self):
        ip_block_w_href = self.driver.ex_describe_ip_block(
            ex_href=(
                '/cloudapi/v3/ipblocks/'
                'ipb-2'
            )
        )
        ip_block_w_id = self.driver.ex_describe_ip_block(
            ex_ip_block_id='ipb-2'
        )
        self._verify_ip_block(ip_block=ip_block_w_href)
        self._verify_ip_block(ip_block=ip_block_w_id)

    def _verify_ip_block(self, ip_block):
        extra = ip_block.extra

        '''
        Standard properties
        '''
        self.assertEqual(
            ip_block.id,
            'ipb-2'
        )
        self.assertEqual(
            ip_block.name,
            'Test IP Block One'
        )
        self.assertEqual(
            ip_block.href,
            (
                '/cloudapi/v3/ipblocks/ipb-2'
            )
        )
        self.assertEqual(
            ip_block.location,
            'de/fkb'
        )
        self.assertEqual(
            ip_block.size,
            1
        )
        self.assertEqual(
            ip_block.ips,
            ['78.137.101.250']
        )
        self.assertEqual(
            ip_block.state,
            NodeState.RUNNING
        )

        '''
        Extra metadata
        '''
        self.assertEqual(
            extra['created_date'],
            '2016-10-26T15:05:12Z'
        )
        self.assertEqual(
            extra['created_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['etag'],
            '43e05b766899950bc8a5aeee0fd89b05'
        )
        self.assertEqual(
            extra['last_modified_date'],
            '2016-10-26T15:05:12Z'
        )
        self.assertEqual(
            extra['last_modified_by'],
            'test@test.te'
        )
        self.assertEqual(
            extra['state'],
            'AVAILABLE'
        )

    def test_ex_delete_ip_block(self):
        ip_block = self.driver.ex_describe_ip_block(
            ex_href=(
                '/cloudapi/v3/ipblocks/'
                'ipb-2'
            )
        )
        deleted = self.driver.ex_delete_ip_block(ip_block)
        self.assertTrue(deleted)


class ProfitBricksMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('profitbricks')

    '''
    Operations on images

    GET     - fetches images
    '''
    def _cloudapi_v3_images(
        self, method, url, body, headers
    ):
        body = self.fixtures.load('list_images.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    '''
    Operations on locations

    GET     - fetches locations
    '''
    def _cloudapi_v3_locations(
        self, method, url, body, headers
    ):
        body = self.fixtures.load('list_locations.json')
        return (
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    '''
    Operations on a data centers

    GET     - fetches data centers
    PATCH   - creates a data center
    '''
    def _cloudapi_v3_datacenters(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_datacenters.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_datacenter.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a data center

    GET     - fetches a data center
    DELETE  - destroys a data center
    PATCH   - updates a data center
    '''
    def _cloudapi_v3_datacenters_dc_1(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_datacenter.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_rename_datacenter.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on data center nodes (servers)

    GET     - fetches a list of nodes (servers) for a data center
    POST    - creates a node (server) for a data center
    '''
    def _cloudapi_v3_datacenters_dc_1_servers(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('list_nodes.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('create_node.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on data center volumes

    GET     - fetches a list of volumes for a data center
    POST    - creates a volume for a data center
    '''
    def _cloudapi_v3_datacenters_dc_1_volumes(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('list_volumes.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('create_volume.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a node (server)

    GET     - fetches a node (server)
    DELETE  - destroys a node (server)
    PATCH   - updates a node
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_node.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_node.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )
    '''
    Operations on a node (server)

    POST    - reboots, then starts and stops a node
    '''
    'reboot a node'
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_reboot(
        self, method, url, body, headers
    ):
        return (
            httplib.ACCEPTED,
            '',
            {},
            httplib.responses[httplib.ACCEPTED]
        )
    'start a node'
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_stop(
        self, method, url, body, headers
    ):
        return (
            httplib.ACCEPTED,
            '',
            {},
            httplib.responses[httplib.ACCEPTED]
        )

    'stop a node'
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_start(
        self, method, url, body, headers
    ):
        return (
            httplib.ACCEPTED,
            '',
            {},
            httplib.responses[httplib.ACCEPTED]
        )

    """
    Operations on an image

    GET     - fetches an image
    DELETE  - deletes an image
    PATCH   - updates an image
    """
    def _cloudapi_v3_images_img_2(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_image.json')
            return (
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_image.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a volume

    GET     - fetches a volume
    DELETE  - destroys a volume
    PATCH   - updates a volume
    '''
    def _cloudapi_v3_datacenters_dc_1_volumes_vol_2(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_volume.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )
        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_volume.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a volume connected to a node (server)

    DELETE  -   destroys the link between a volume
                and a server but does delete the volume.
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_volumes_vol_2(
        self, method, url, body, headers
    ):
        return (
            httplib.ACCEPTED,
            '',
            {},
            httplib.responses[httplib.ACCEPTED]
        )

    '''
    Operations on a location

    GET     - fetches a location
    '''
    def _cloudapi_v3_locations_de_fkb(
        self, method, url, body, headers
    ):
        body = self.fixtures.load('ex_describe_location.json')
        return(
            httplib.OK,
            body,
            {},
            httplib.responses[httplib.OK]
        )

    '''
    Operations on volumes connected to nodes (servers)

    GET     - fetch volumes connected to a server
    POST    - attach a volume to a node (server)
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_volumes(
        self, method, url, body, headers
    ):
        if(method == 'GET'):
            body = self.fixtures.load('ex_list_attached_volumes.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('attach_volume.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on network interfaces connected to a server

    GET     - fetch network interfaces for a node (server)
    POST    - create a network interface for a node (server)
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_srv_1_nics(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_network_interfaces.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_network_interface.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on network interfaces

    GET     - fetch a network interface
    DELETE  - destroy a network interface
    PATCH   - update a network interface
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_s_3_nics_nic_2(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_network_interface.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_set_inet_access.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on firewall rules

    GET     - fetch a firewall rule
    DELETE  - destroy a firewall rule
    PATCH   - update a firewall rule
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_s_3_nics_nic_2_firewallrules_fw2(
        self,
        method,
        url,
        body,
        headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_firewall_rule.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_firewall_rule.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on firewall rules connected to a network interface

    GET     - fetch a list of firewall rules connected to a network interface
    POST    - create a firewall rule for a network interface
    '''
    def _cloudapi_v3_datacenters_dc_1_servers_s_3_nics_nic_2_firewallrules(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_firewall_rules.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_firewall_rule.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on lans

    GET     - fetch a list of lans
    POST    - create a lan
    '''
    def _cloudapi_v3_datacenters_dc_1_lans(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_lans.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_lan.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a single lan

    GET     - fetch a lan
    DELETE  - Destroy a lan
    PATCH   - update a lan
    '''
    def _cloudapi_v3_datacenters_dc_1_lans_10(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_lan.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_lan.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on snapshots

    GET     - fetch a list of snapshots
    '''
    def _cloudapi_v3__snapshots(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('list_snapshots.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

    '''
    Operations on volume snapshots

    POST    - create a volume snapshot
    '''
    def _cloudapi_v3_datacenters_dc_1_volumes_vol_2_create_snapshot(
        self, method, url, body, headers
    ):
        if method == 'POST':
            body = self.fixtures.load('create_volume_snapshot.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a single snapshot

    GET     - get information on a snapshot
    DELETE  - delete a snapshot
    PATCH   - update a snapshot
    '''
    def _cloudapi_v3_snapshots_sshot(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_snapshot.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_snapshot.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on load balancers

    GET     - list load balancers
    POST    - create a load balancer for this datacenter
    '''
    def _cloudapi_v3_datacenters_dc_1_loadbalancers(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_load_balancers.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_load_balancer.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a single load balancer

    GET     - get information on a load balancer
    DELETE  - delete a load balancer
    PATCH   - update a load balancer
    '''
    def _cloudapi_v3_datacenters_dc_2_loadbalancers_bal_1(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_load_balancer.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

        elif method == 'PATCH':
            body = self.fixtures.load('ex_update_load_balancer.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a load balancers nics

    GET     - get load balanced nics
    '''
    def _cloudapi_v3_datacenters_dc_2_loadbalancers_bal_1_balancednics(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_load_balanced_nics.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a load balanced nic

    DELETE  - remove the nic from a load balancer
    '''
    def _cloudapi_v3_datacenters_dc_2_loadbalancers_bal_1_balancednics_nic_2(
        self, method, url, body, headers
    ):
        if method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on IP blocks

    GET     - list IP blocks
    POST    - create an IP block
    '''
    def _cloudapi_v3_ipblocks(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_list_ip_blocks.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'POST':
            body = self.fixtures.load('ex_create_ip_block.json')
            return (
                httplib.ACCEPTED,
                body,
                {},
                httplib.responses[httplib.ACCEPTED]
            )

    '''
    Operations on a single IP block

    GET     - fetch an IP block
    DELETE  - delete an IP block
    '''
    def _cloudapi_v3_ipblocks_ipb_2(
        self, method, url, body, headers
    ):
        if method == 'GET':
            body = self.fixtures.load('ex_describe_ip_block.json')
            return(
                httplib.OK,
                body,
                {},
                httplib.responses[httplib.OK]
            )

        elif method == 'DELETE':
            return (
                httplib.ACCEPTED,
                '',
                {},
                httplib.responses[httplib.ACCEPTED]
            )

if __name__ == '__main__':
    sys.exit(unittest.main())
