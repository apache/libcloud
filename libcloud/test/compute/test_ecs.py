# -*- coding: utf-8 -*-
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
from __future__ import unicode_literals

import sys
import unittest

from libcloud.common.types import LibcloudError
from libcloud.compute.base import Node, NodeAuthPassword, NodeImage, \
    NodeLocation, NodeSize, StorageVolume, VolumeSnapshot
from libcloud.compute.drivers.ecs import ECSDriver
from libcloud.compute.types import NodeState, StorageVolumeState
from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import ECS_PARAMS
from libcloud.utils.py3 import httplib


class ECSDriverTestCase(LibcloudTestCase):
    region = 'cn-qingdao'
    zone = 'cn-qingdao-b'
    image_id = 'ubuntu1404_64_20G_aliaegis_20150325.vhd'

    def setUp(self):
        ECSMockHttp.test = self
        ECSDriver.connectionCls.conn_class = ECSMockHttp
        ECSMockHttp.use_param = 'Action'
        ECSMockHttp.type = None

        self.driver = ECSDriver(*ECS_PARAMS, region=self.region)
        self.fake_size = NodeSize('ecs.t1.small', 'ecs t1 small',
                                  None, None, None, None,
                                  self.driver)
        self.fake_image = NodeImage(self.image_id, name='ubuntu 14.04 64bit',
                                    driver=self.driver)
        self.fake_node = Node(id='fake-node1', name='fake-node',
                              state=NodeState.RUNNING,
                              public_ips=None,
                              private_ips=None,
                              driver=self.driver)
        self.fake_volume = StorageVolume(id='fake-volume1', name='fake-volume',
                                         size=self.fake_size,
                                         driver=self.driver)
        self.fake_snapshot = VolumeSnapshot(id='fake-snapshot1',
                                            driver=self.driver)
        self.fake_location = NodeLocation(id=self.region, name=self.region,
                                          country=None, driver=self.driver)
        self.fake_instance_id = 'fake_instance_id'
        self.fake_security_group_id = 'fake_security_group_id'

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertIsNotNone(nodes)
        self.assertEqual(1, len(nodes))
        node = nodes[0]
        self.assertEqual('iZ28n7dkvovZ', node.name)
        self.assertEqual('i-28n7dkvov', node.id)
        self.assertEqual(NodeState.PENDING, node.state)
        self.assertEqual(1, len(node.public_ips))
        self.assertEqual('114.215.124.73', node.public_ips[0])
        self.assertEqual(1, len(node.private_ips))
        self.assertEqual('10.163.197.74', node.private_ips[0])
        expected_extra = {
            'image_id': 'ubuntu1404_64_20G_aliaegis_20150325.vhd',
            'description': '',
            'instance_type_family': 'ecs.t1',
            'zone_id': 'cn-qingdao-b',
            'internet_charge_type': 'PayByTraffic',
            'serial_number': 'ca0122d9-374d-4fce-9fc0-71f7c3eaf1c3',
            'io_optimized': 'false',
            'device_available': 'true',
            'instance_network_type': 'classic',
            'hostname': 'iZ28n7dkvovZ',
            'instance_type': 'ecs.t1.small',
            'creation_time': '2015-12-27T07:35Z',
            'instance_charge_type': 'PostPaid',
            'expired_time': '2999-09-08T16:00Z'
        }
        self._validate_extras(expected_extra, node.extra)
        vpc = {
            'vpc_id': '',
            'vswitch_id': '',
            'private_ip_address': None,
            'nat_ip_address': ''
        }
        self._validate_extras(vpc, node.extra['vpc_attributes'])
        eip_address = {
            'allocation_id': '',
            'ip_address': '',
            'internet_charge_type': '',
            'bandwidth': None
        }
        self._validate_extras(eip_address, node.extra['eip_address'])
        self.assertIsNone(node.extra['operation_locks']['lock_reason'])

    def test_list_nodes_with_ex_node_ids(self):
        ECSMockHttp.type = 'list_nodes_ex_node_ids'
        nodes = self.driver.list_nodes(ex_node_ids=['i-28n7dkvov',
                                                    'not-existed-id'])
        self.assertIsNotNone(nodes)

    def test_list_nodes_with_ex_filters(self):
        ECSMockHttp.type = 'list_nodes_ex_filters'
        nodes = self.driver.list_nodes(ex_filters={'ZoneId': self.zone})
        self.assertIsNotNone(nodes)

    def _validate_extras(self, expected, actual):
        self.assertIsNotNone(actual)
        for key, value in iter(expected.items()):
            self.assertTrue(key in actual)
            self.assertEqual(value, actual[key], ('extra %(key)s not equal, '
                                                  'expected: "%(expected)s", '
                                                  'actual: "%(actual)s"' %
                                                  {'key': key,
                                                   'expected': value,
                                                   'actual': actual[key]}))

    def test_create_node(self):
        ECSMockHttp.type = 'create_node'
        name = 'test_create_node'
        node = self.driver.create_node(name=name, image=self.fake_image,
                                       size=self.fake_size,
                                       ex_security_group_id='sg-28ou0f3xa',
                                       ex_description='description',
                                       ex_internet_charge_type='PayByTraffic',
                                       ex_internet_max_bandwidth_out=1,
                                       ex_internet_max_bandwidth_in=200,
                                       ex_hostname='hostname',
                                       auth=NodeAuthPassword('password'),
                                       ex_io_optimized=True,
                                       ex_system_disk={'category': 'cloud',
                                                       'disk_name': 'root',
                                                       'description': 'sys'},
                                       ex_vswitch_id='vswitch-id1',
                                       ex_private_ip_address='1.1.1.2',
                                       ex_client_token='client_token')
        self.assertIsNotNone(node)

    def test_create_node_with_data_disk(self):
        ECSMockHttp.type = 'create_node_with_data'
        self.name = 'test_create_node'
        self.data_disk = {
            'size': 5,
            'category': self.driver.disk_categories.CLOUD,
            'disk_name': 'data1',
            'description': 'description',
            'device': '/dev/xvdb',
            'delete_with_instance': True}
        node = self.driver.create_node(name=self.name, image=self.fake_image,
                                       size=self.fake_size,
                                       ex_security_group_id='sg-28ou0f3xa',
                                       ex_data_disks=self.data_disk)
        self.assertIsNotNone(node)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(2, len(sizes))
        size = sizes[0]
        self.assertEqual('ecs.t1.xsmall', size.id)
        self.assertEqual('ecs.t1.xsmall', size.name)
        self.assertEqual(0.5, size.ram)
        self.assertEqual(1, size.extra['cpu_core_count'])
        self.assertEqual('ecs.t1', size.extra['instance_type_family'])
        size = sizes[1]
        self.assertEqual('ecs.s2.small', size.id)
        self.assertEqual('ecs.s2.small', size.name)
        self.assertEqual(1.0, size.ram)
        self.assertEqual(2, size.extra['cpu_core_count'])
        self.assertEqual('ecs.s2', size.extra['instance_type_family'])

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(9, len(locations))
        location = locations[0]
        self.assertEqual('ap-southeast-1', location.id)
        self.assertIsNone(location.country)

    def test_create_node_without_sg_id_exception(self):
        name = 'test_create_node_without_sg_id_exception'
        self.assertRaises(AttributeError, self.driver.create_node,
                          name=name, image=self.fake_image,
                          size=self.fake_size)

    def test_creat_node_paybytraffic_exception(self):
        name = 'test_create_node_paybytraffic_exception'
        self.assertRaises(AttributeError, self.driver.create_node,
                          name=name, image=self.fake_image,
                          size=self.fake_size,
                          ex_security_group_id='sg-id1',
                          ex_internet_charge_type='PayByTraffic')

    def test_create_node_ex_system_disk_exception(self):
        name = 'test_creat_node_ex_system_disk_exception'
        self.assertRaises(AttributeError, self.driver.create_node,
                          name=name, image=self.fake_image,
                          size=self.fake_size,
                          ex_security_group_id='sg-id1',
                          ex_system_disk=None)

    def test_create_node_ex_private_ip_address_exception(self):
        name = 'test_create_node_ex_private_ip_address_exception'
        self.assertRaises(AttributeError, self.driver.create_node,
                          name=name, image=self.fake_image,
                          size=self.fake_size,
                          ex_security_group_id='sg-id1',
                          ex_private_ip_address='1.1.1.2')

    def test_reboot_node(self):
        ECSMockHttp.type = 'reboot_node'
        result = self.driver.reboot_node(self.fake_node)
        self.assertTrue(result)

    def test_reboot_node_with_ex_force_stop(self):
        ECSMockHttp.type = 'reboot_node_force_stop'
        result = self.driver.reboot_node(self.fake_node, ex_force_stop=True)
        self.assertTrue(result)

    def test_destroy_node(self):
        ECSMockHttp.type = 'destroy_node'
        result = self.driver.destroy_node(self.fake_node)
        self.assertTrue(result)

    def test_ex_start_node(self):
        ECSMockHttp.type = 'start_node'
        result = self.driver.ex_start_node(self.fake_node)
        self.assertTrue(result)

    def test_ex_stop_node(self):
        ECSMockHttp.type = 'stop_node'
        result = self.driver.ex_stop_node(self.fake_node)
        self.assertTrue(result)

    def test_stop_node_with_ex_force_stop(self):
        ECSMockHttp.type = 'stop_node_force_stop'
        result = self.driver.ex_stop_node(self.fake_node, ex_force_stop=True)
        self.assertTrue(result)

    def test_create_public_ip(self):
        ECSMockHttp.type = 'create_public_ip'
        result = self.driver.create_public_ip(self.fake_instance_id)
        self.assertTrue(result)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(2, len(volumes))
        volume = volumes[0]
        self.assertEqual('d-28m5zbua0', volume.id)
        self.assertEqual('', volume.name)
        self.assertEqual(5, volume.size)
        self.assertEqual(StorageVolumeState.AVAILABLE, volume.state)
        expected_extras = {
            'region_id': 'cn-qingdao',
            'zone_id': 'cn-qingdao-b',
            'description': '',
            'type': 'data',
            'category': 'cloud',
            'image_id': '',
            'source_snapshot_id': '',
            'product_code': '',
            'portable': True,
            'instance_id': '',
            'device': '',
            'delete_with_instance': False,
            'enable_auto_snapshot': False,
            'creation_time': '2014-07-23T02:44:07Z',
            'attached_time': '2014-07-23T07:47:35Z',
            'detached_time': '2014-07-23T08:28:48Z',
            'disk_charge_type': 'PostPaid',
            'operation_locks': {'lock_reason': None}
        }
        self._validate_extras(expected_extras, volume.extra)
        volume = volumes[1]
        self.assertEqual('d-28zfrmo13', volume.id)
        self.assertEqual('ubuntu1404sys', volume.name)
        self.assertEqual(5, volume.size)
        self.assertEqual(StorageVolumeState.INUSE, volume.state)
        expected_extras = {
            'region_id': 'cn-qingdao',
            'zone_id': 'cn-qingdao-b',
            'description': 'Description',
            'type': 'system',
            'category': 'cloud',
            'image_id': 'ubuntu1404_64_20G_aliaegis_20150325.vhd',
            'source_snapshot_id': '',
            'product_code': '',
            'portable': False,
            'instance_id': 'i-28whl2nj2',
            'device': '/dev/xvda',
            'delete_with_instance': True,
            'enable_auto_snapshot': True,
            'creation_time': '2014-07-23T02:44:06Z',
            'attached_time': '2016-01-04T15:02:17Z',
            'detached_time': '',
            'disk_charge_type': 'PostPaid',
            'operation_locks': {'lock_reason': None}
        }
        self._validate_extras(expected_extras, volume.extra)

    def test_list_volumes_with_ex_volume_ids(self):
        ECSMockHttp.type = 'list_volumes_ex_volume_ids'
        volumes = self.driver.list_volumes(ex_volume_ids=['i-28n7dkvov',
                                                          'not-existed-id'])
        self.assertIsNotNone(volumes)

    def test_list_volumes_with_ex_filters(self):
        ECSMockHttp.type = 'list_volumes_ex_filters'
        ex_filters = {'InstanceId': self.fake_node.id}
        volumes = self.driver.list_volumes(ex_filters=ex_filters)
        self.assertIsNotNone(volumes)

    def test_list_volume_snapshots(self):
        snapshots = self.driver.list_volume_snapshots(self.fake_volume)
        self.assertEqual(1, len(snapshots))

    def test_list_volume_snapshots_with_ex_snapshot_ids(self):
        ECSMockHttp.type = 'list_volume_snapshots_ex_snapshot_ids'
        ex_snapshot_ids = ['fake-snapshot1']
        self.driver.list_volume_snapshots(self.fake_volume,
                                          ex_snapshot_ids=ex_snapshot_ids)

    def test_list_volume_snapshots_with_ex_filters(self):
        ECSMockHttp.type = 'list_volume_snapshots_ex_filters'
        ex_filters = {'InstanceId': self.fake_node.id}
        self.driver.list_volume_snapshots(self.fake_volume,
                                          ex_filters=ex_filters)

    def test_create_volume(self):
        ECSMockHttp.type = 'create_volume'
        self.volume_size = 1
        self.volume_name = 'fake-volume-name'
        self.description = 'fake-description'
        self.disk_category = 'system'
        self.client_token = 'client_token'
        volume = self.driver.create_volume(self.volume_size, self.volume_name,
                                           snapshot=self.fake_snapshot,
                                           ex_zone_id=self.zone,
                                           ex_description=self.description,
                                           ex_disk_category=self.disk_category,
                                           ex_client_token=self.client_token)
        self.assertIsNotNone(volume)

    def test_create_volume_without_ex_zone_id_exception(self):
        self.assertRaises(AttributeError,
                          self.driver.create_volume,
                          1, 'fake-volume-name')

    def test_create_volume_snapshot(self):
        ECSMockHttp.type = 'create_volume_snapshot'
        self.snapshot_name = 'fake-snapshot1'
        self.description = 'fake-description'
        self.client_token = 'client-token'
        snapshot = self.driver.create_volume_snapshot(
            self.fake_volume, name=self.snapshot_name,
            ex_description=self.description,
            ex_client_token=self.client_token)
        self.assertIsNotNone(snapshot)

    def test_attach_volume(self):
        self.device = '/dev/sdb'
        self.delete_with_instance = True
        attached = self.driver.attach_volume(
            self.fake_node, self.fake_volume, device=self.device,
            ex_delete_with_instance=self.delete_with_instance)
        self.assertTrue(attached)

    def test_detach_volume(self):
        self.instance_id = 'fake-node1'
        result = self.driver.detach_volume(self.fake_volume,
                                           ex_instance_id=self.instance_id)
        self.assertTrue(result)

    def test_detach_volume_query_instance_id(self):
        ECSMockHttp.type = 'detach_volume'
        result = self.driver.detach_volume(self.fake_volume)
        self.assertTrue(result)

    def test_detach_volume_query_instance_id_exception(self):
        self.assertRaises(AttributeError, self.driver.detach_volume,
                          self.fake_volume)

    def test_destroy_volume(self):
        ECSMockHttp.type = 'destroy_volume'
        result = self.driver.destroy_volume(self.fake_volume)
        self.assertTrue(result)

    def test_destroy_volume_query_volumes_exception(self):
        self.assertRaises(LibcloudError, self.driver.destroy_volume,
                          self.fake_volume)

    def test_destroy_volume_state_exception(self):
        ECSMockHttp.type = 'destroy_volume_state'
        self.assertRaises(LibcloudError, self.driver.destroy_volume,
                          self.fake_volume)

    def test_destroy_volume_snapshot(self):
        result = self.driver.destroy_volume_snapshot(self.fake_snapshot)
        self.assertTrue(result)

    def test_destroy_volume_snapshot_exception(self):
        self.assertRaises(AttributeError, self.driver.destroy_volume_snapshot,
                          self.fake_volume)

    def test_list_images(self):
        images = self.driver.list_images(self.fake_location)
        self.assertEqual(1, len(images))
        image = images[0]
        self.assertEqual('freebsd1001_64_20G_aliaegis_20150527.vhd', image.id)
        self.assertEqual('freebsd1001_64_20G_aliaegis_20150527.vhd',
                         image.name)
        expected_extra = {
            'image_version': '1.0.0',
            'os_type': 'linux',
            'platform': 'Freebsd',
            'architecture': 'x86_64',
            'description': 'freebsd1001_64_20G_aliaegis_20150527.vhd',
            'size': 20,
            'image_owner_alias': 'system',
            'os_name': 'FreeBSD  10.1 64位',
            'product_code': '',
            'is_subscribed': False,
            'progress': '100%',
            'creation_time': '2015-06-19T07:25:42Z',
            'usage': 'instance',
            'is_copied': False
        }
        self._validate_extras(expected_extra, image.extra)
        expected_dev_mappings = {
            'snapshot_id': '',
            'size': 20,
            'device': '/dev/xvda',
            'format': '',
            'import_oss_bucket': '',
            'import_oss_object': ''
        }
        self._validate_extras(expected_dev_mappings,
                              image.extra['disk_device_mappings'])

    def test_list_images_with_ex_image_ids(self):
        ECSMockHttp.type = 'list_images_ex_image_ids'
        self.driver.list_images(location=self.fake_location,
                                ex_image_ids=[self.fake_image.id,
                                              'not-existed'])

    def test_list_images_with_ex_image_ids_type_exception(self):
        self.assertRaises(AttributeError, self.driver.list_images,
                          location=self.fake_location,
                          ex_image_ids={'image_ids': 'id1,id2'})

    def test_list_images_with_ex_filters(self):
        ECSMockHttp.type = 'list_images_ex_filters'
        ex_filters = {'Status': 'Available'}
        self.driver.list_images(location=self.fake_location,
                                ex_filters=ex_filters)

    def test_list_images_multiple_pages(self):
        ECSMockHttp.type = 'list_images_pages'
        images = self.driver.list_images()
        self.assertEqual(2, len(images))

    def test_create_image(self):
        self.image_name = 'fake-image1'
        self.description = 'description'
        self.image_version = '1.0.0'
        self.client_token = 'client_token'
        image = self.driver.create_image(None, self.image_name,
                                         self.description,
                                         ex_snapshot_id=self.fake_snapshot.id,
                                         ex_image_version=self.image_version,
                                         ex_client_token=self.client_token)
        self.assertIsNotNone(image)

    def test_creaet_image_exception(self):
        self.assertRaises(AttributeError, self.driver.create_image,
                          None, None)

    def test_delete_image(self):
        result = self.driver.delete_image(self.fake_image)
        self.assertTrue(result)

    def test_get_image(self):
        ECSMockHttp.type = 'get_image'
        image = self.driver.get_image(self.fake_image.id)
        self.assertIsNotNone(image)

    def test_get_image_not_found_exception(self):
        ECSMockHttp.type = 'get_image_not_found'
        self.assertRaises(LibcloudError, self.driver.get_image,
                          self.fake_image.id)

    def test_copy_image(self):
        self.image_name = 'copied-image1'
        self.description = 'description'
        self.dest_region = 'cn-hangzhou'
        self.client_token = 'client-token'
        image = self.driver.copy_image(
            self.region, self.fake_image,
            self.image_name,
            description=self.description,
            ex_destination_region_id=self.dest_region,
            ex_client_token=self.client_token)
        self.assertIsNotNone(image)

    def test_copy_image_in_the_same_region(self):
        ECSMockHttp.type = 'copy_image_same_region'
        image = self.driver.copy_image(self.region, self.fake_image, None)
        self.assertIsNotNone(image)

    def test_ex_create_security_group(self):
        self.sg_description = 'description'
        self.client_token = 'client-token'
        sg_id = self.driver.ex_create_security_group(
            description=self.sg_description, client_token=self.client_token)
        self.assertEqual('sg-F876FF7BA', sg_id)

    def test_ex_list_security_groups(self):
        sgs = self.driver.ex_list_security_groups()
        self.assertEqual(1, len(sgs))
        sg = sgs[0]
        self.assertEqual('sg-28ou0f3xa', sg.id)
        self.assertEqual('sg-28ou0f3xa', sg.name)
        self.assertEqual('System created security group.', sg.description)
        self.assertEqual('', sg.vpc_id)
        self.assertEqual('2015-06-26T08:35:30Z', sg.creation_time)

    def test_ex_join_security_group(self):
        result = self.driver.ex_join_security_group(
            self.fake_node, group_id=self.fake_security_group_id)
        self.assertTrue(result)

    def test_ex_leave_security_group(self):
        result = self.driver.ex_leave_security_group(
            self.fake_node, group_id=self.fake_security_group_id)
        self.assertTrue(result)

    def test_ex_delete_security_group_by_id(self):
        result = self.driver.ex_delete_security_group_by_id(
            group_id=self.fake_security_group_id)
        self.assertTrue(result)

    def test_ex_modify_security_group_by_id(self):
        self.sg_name = 'name'
        self.sg_description = 'description'
        result = self.driver.ex_modify_security_group_by_id(
            group_id=self.fake_security_group_id,
            name=self.sg_name,
            description=self.sg_description)
        self.assertTrue(result)

    def test_ex_list_security_groups_with_ex_filters(self):
        ECSMockHttp.type = 'list_sgs_filters'
        self.vpc_id = 'vpc1'
        ex_filters = {'VpcId': self.vpc_id}
        sgs = self.driver.ex_list_security_groups(ex_filters=ex_filters)
        self.assertEqual(1, len(sgs))

    def test_ex_list_security_group_attributes(self):
        self.sga_nictype = 'internet'
        sgas = self.driver.ex_list_security_group_attributes(
            group_id=self.fake_security_group_id, nic_type=self.sga_nictype)
        self.assertEqual(1, len(sgas))
        sga = sgas[0]
        self.assertEqual('ALL', sga.ip_protocol)
        self.assertEqual('-1/-1', sga.port_range)
        self.assertEqual('Accept', sga.policy)
        self.assertEqual('internet', sga.nic_type)

    def test_ex_list_zones(self):
        zones = self.driver.ex_list_zones()
        self.assertEqual(1, len(zones))
        zone = zones[0]
        self.assertEqual('cn-qingdao-b', zone.id)
        self.assertEqual(self.driver, zone.driver)
        self.assertEqual('青岛可用区B', zone.name)
        self.assertIsNotNone(zone.available_resource_types)
        self.assertEqual('IoOptimized', zone.available_resource_types[0])
        self.assertIsNotNone(zone.available_instance_types)
        self.assertEqual('ecs.m2.medium', zone.available_instance_types[0])
        self.assertIsNotNone(zone.available_disk_categories)
        self.assertEqual('cloud_ssd', zone.available_disk_categories[0])


class ECSMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('ecs')

    def _DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _list_nodes_ex_node_ids_DescribeInstances(self, method, url, body,
                                                  headers):
        params = {'InstanceIds': '["i-28n7dkvov", "not-existed-id"]'}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeInstances(method, url, body, headers)

    def _list_nodes_ex_filters_DescribeInstances(self, method, url, body,
                                                 headers):
        params = {'ZoneId': self.test.zone}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeInstances(method, url, body, headers)

    def _DescribeInstanceTypes(self, method, url, body, headers):
        resp_body = self.fixtures.load('describe_instance_types.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DescribeRegions(self, method, url, body, headers):
        resp_body = self.fixtures.load('describe_regions.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_CreateInstance(self, method, url, body, headers):
        params = {'SecurityGroupId': 'sg-28ou0f3xa',
                  'Description': 'description',
                  'InternetChargeType': 'PayByTraffic',
                  'InternetMaxBandwidthOut': '1',
                  'InternetMaxBandwidthIn': '200',
                  'HostName': 'hostname',
                  'Password': 'password',
                  'IoOptimized': 'optimized',
                  'SystemDisk.Category': 'cloud',
                  'SystemDisk.DiskName': 'root',
                  'SystemDisk.Description': 'sys',
                  'VSwitchId': 'vswitch-id1',
                  'PrivateIpAddress': '1.1.1.2',
                  'ClientToken': 'client_token'}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('create_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_StartInstance(self, method, url, body, headers):
        resp_body = self.fixtures.load('start_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_with_data_CreateInstance(self, method, url, body,
                                              headers):
        params = {'SecurityGroupId': 'sg-28ou0f3xa',
                  'DataDisk.1.Size': '5',
                  'DataDisk.1.Category': 'cloud',
                  'DataDisk.1.DiskName': 'data1',
                  'DataDisk.1.Description': 'description',
                  'DataDisk.1.Device': '/dev/xvdb',
                  'DataDisk.1.DeleteWithInstance': 'true'}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_with_data_DescribeInstances(self, method, url, body,
                                                 headers):
        resp_body = self.fixtures.load('create_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_node_with_data_StartInstance(self, method, url, body,
                                             headers):
        resp_body = self.fixtures.load('start_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _reboot_node_RebootInstance(self, method, url, body, headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id,
                                                'ForceStop': 'false'})
        resp_body = self.fixtures.load('reboot_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _reboot_node_DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('reboot_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _reboot_node_force_stop_RebootInstance(self, method, url, body,
                                               headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id,
                                                'ForceStop': 'true'})
        resp_body = self.fixtures.load('reboot_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _reboot_node_force_stop_DescribeInstances(self, method, url, body,
                                                  headers):
        resp_body = self.fixtures.load('reboot_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _destroy_node_DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('destroy_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _destroy_node_DeleteInstance(self, method, url, body, headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id})
        resp_body = self.fixtures.load('delete_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _start_node_StartInstance(self, method, url, body, headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id})
        resp_body = self.fixtures.load('start_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _start_node_DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('reboot_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _stop_node_StopInstance(self, method, url, body, headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id,
                                                'ForceStop': 'false'})
        resp_body = self.fixtures.load('stop_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _stop_node_DescribeInstances(self, method, url, body, headers):
        resp_body = self.fixtures.load('stop_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _stop_node_force_stop_StopInstance(self, method, url, body, headers):
        node_id = self.test.fake_node.id
        self.assertUrlContainsQueryParams(url, {'InstanceId': node_id,
                                                'ForceStop': 'true'})
        resp_body = self.fixtures.load('stop_instance.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _stop_node_force_stop_DescribeInstances(self, method, url, body,
                                                headers):
        resp_body = self.fixtures.load('stop_node_describe_instances.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DescribeDisks(self, method, url, body, headers):
        resp_body = self.fixtures.load('describe_disks.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _list_volumes_ex_volume_ids_DescribeDisks(self, method, url, body,
                                                  headers):
        region = self.test.region
        params = {'DiskIds': '["i-28n7dkvov", "not-existed-id"]',
                  'RegionId': region}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeInstances(method, url, body, headers)

    def _list_volumes_ex_filters_DescribeDisks(self, method, url, body,
                                               headers):
        params = {'InstanceId': self.test.fake_node.id}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeDisks(method, url, body, headers)

    def _DescribeSnapshots(self, method, url, body, headers):
        region = self.test.region
        volume_id = self.test.fake_volume.id
        params = {'RegionId': region,
                  'DiskId': volume_id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('describe_snapshots.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _list_volume_snapshots_ex_snapshot_ids_DescribeSnapshots(
            self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'SnapshotIds': '["fake-snapshot1"]'}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeSnapshots(method, url, body, headers)

    def _list_volume_snapshots_ex_filters_DescribeSnapshots(self, method, url, body,
                                                            headers):
        params = {'InstanceId': self.test.fake_node.id}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeSnapshots(method, url, body, headers)

    def _create_volume_CreateDisk(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'DiskName': self.test.volume_name,
                  'Size': str(self.test.volume_size),
                  'ZoneId': self.test.zone,
                  'SnapshotId': self.test.fake_snapshot.id,
                  'Description': self.test.description,
                  'DiskCategory': self.test.disk_category,
                  'ClientToken': self.test.client_token}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_disk.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_volume_DescribeDisks(self, method, url, body, headers):
        resp_body = self.fixtures.load('create_volume_describe_disks.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_volume_snapshot_CreateSnapshot(self, method, url, body,
                                               headers):
        params = {'DiskId': self.test.fake_volume.id,
                  'SnapshotName': self.test.snapshot_name,
                  'Description': self.test.description,
                  'ClientToken': self.test.client_token}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_snapshot.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_volume_snapshot_DescribeSnapshots(self, method, url, body,
                                                  headers):
        resp_body = self.fixtures.load('describe_snapshots.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _AttachDisk(self, method, url, body, headers):
        delete_with_instance = str(self.test.delete_with_instance).lower()
        params = {'InstanceId': self.test.fake_node.id,
                  'DiskId': self.test.fake_volume.id,
                  'Device': self.test.device,
                  'DeleteWithInstance': delete_with_instance}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('attach_disk.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DetachDisk(self, method, url, body, headers):
        params = {'DiskId': self.test.fake_volume.id,
                  'InstanceId': self.test.instance_id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('detach_disk.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _detach_volume_DescribeDisks(self, method, url, body, headers):
        params = {'DiskIds': '["' + self.test.fake_volume.id + '"]'}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('detach_volume_describe_disks.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _detach_volume_DetachDisk(self, method, url, body, headers):
        params = {'DiskId': self.test.fake_volume.id,
                  'InstanceId': 'i-28whl2nj2'}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('detach_disk.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _destroy_volume_DescribeDisks(self, method, url, body, headers):
        params = {'DiskIds': '["' + self.test.fake_volume.id + '"]'}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('destroy_volume_describe_disks.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _destroy_volume_DeleteDisk(self, method, url, body, headers):
        params = {'DiskId': self.test.fake_volume.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('delete_disk.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _destroy_volume_state_DescribeDisks(self, method, url, body, headers):
        return self._detach_volume_DescribeDisks(method, url, body, headers)

    def _DeleteSnapshot(self, method, url, body, header):
        params = {'SnapshotId': self.test.fake_snapshot.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('delete_snapshot.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DescribeImages(self, method, url, body, headers):
        params = {'RegionId': self.test.fake_location.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _list_images_pages_DescribeImages(self, method, url, body, headers):
        if 'PageNumber=2' in url:
            resp_body = self.fixtures.load('pages_describe_images_page2.xml')
        else:
            resp_body = self.fixtures.load('pages_describe_images.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _list_images_ex_image_ids_DescribeImages(self, method, url, body,
                                                 headers):
        params = {'ImageId': self.test.fake_image.id + ',not-existed'}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeImages(method, url, body, headers)

    def _list_images_ex_filters_DescribeImages(self, method, url, body,
                                               headers):
        params = {'Status': 'Available'}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeImages(method, url, body, headers)

    def _CreateImage(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageName': self.test.image_name,
                  'Description': self.test.description,
                  'SnapshotId': self.test.fake_snapshot.id,
                  'ImageVersion': self.test.image_version,
                  'ClientToken': self.test.client_token}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_image.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DeleteImage(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageId': self.test.fake_image.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('delete_image.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _get_image_DescribeImages(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageId': self.test.fake_image.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _get_image_not_found_DescribeImages(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageId': self.test.fake_image.id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('get_image_describe_images.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _CopyImage(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageId': self.test.fake_image.id,
                  'DestinationRegionId': self.test.dest_region,
                  'DestinationImageName': self.test.image_name,
                  'DestinationDescription': self.test.description,
                  'ClientToken': self.test.client_token}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('copy_image.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _copy_image_same_region_CopyImage(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'ImageId': self.test.fake_image.id,
                  'DestinationRegionId': self.test.region}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('copy_image.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _copy_image_same_region_DescribeImages(self, method, url, body,
                                               headers):
        return self._DescribeImages(method, url, body, headers)

    def _DescribeSecurityGroups(self, method, url, body, headers):
        params = {'RegionId': self.test.region}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('describe_security_groups.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _JoinSecurityGroup(self, method, url, body, headers):
        params = {'InstanceId': self.test.fake_node.id,
                  'SecurityGroupId': self.test.fake_security_group_id}
        self.assertUrlContainsQueryParams(url, params)
        body = self.fixtures.load('join_security_group_by_id.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _LeaveSecurityGroup(self, method, url, body, headers):
        params = {'InstanceId': self.test.fake_node.id,
                  'SecurityGroupId': self.test.fake_security_group_id}
        self.assertUrlContainsQueryParams(url, params)
        body = self.fixtures.load('leave_security_group_by_id.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _list_sgs_filters_DescribeSecurityGroups(self, method, url, body,
                                                 headers):
        params = {'VpcId': self.test.vpc_id}
        self.assertUrlContainsQueryParams(url, params)
        return self._DescribeSecurityGroups(method, url, body, headers)

    def _CreateSecurityGroup(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'Description': self.test.sg_description,
                  'ClientToken': self.test.client_token}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('create_security_group.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DeleteSecurityGroup(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'SecurityGroupId': self.test.fake_security_group_id}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('delete_security_group_by_id.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _ModifySecurityGroupAttribute(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'SecurityGroupId': self.test.fake_security_group_id,
                  'SecurityGroupName': self.test.sg_name,
                  'Description': self.test.sg_description}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('modify_security_group_by_id.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DescribeSecurityGroupAttribute(self, method, url, body, headers):
        params = {'RegionId': self.test.region,
                  'SecurityGroupId': self.test.fake_security_group_id,
                  'NicType': self.test.sga_nictype}
        self.assertUrlContainsQueryParams(url, params)
        resp_body = self.fixtures.load('describe_security_group_attributes.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _DescribeZones(self, method, url, body, headers):
        resp_body = self.fixtures.load('describe_zones.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])

    def _create_public_ip_AllocatePublicIpAddress(self, method, url, body, headers):
        resp_body = self.fixtures.load('create_public_ip.xml')
        return (httplib.OK, resp_body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
