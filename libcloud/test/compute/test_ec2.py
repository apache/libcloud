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

from __future__ import with_statement

import os
import sys
from datetime import datetime

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import parse_qsl

from libcloud.compute.drivers.ec2 import EC2NodeDriver
from libcloud.compute.drivers.ec2 import EC2USWestNodeDriver
from libcloud.compute.drivers.ec2 import EC2USWestOregonNodeDriver
from libcloud.compute.drivers.ec2 import EC2EUNodeDriver
from libcloud.compute.drivers.ec2 import EC2APSENodeDriver
from libcloud.compute.drivers.ec2 import EC2APNENodeDriver
from libcloud.compute.drivers.ec2 import EC2APSESydneyNodeDriver
from libcloud.compute.drivers.ec2 import EC2SAEastNodeDriver
from libcloud.compute.drivers.ec2 import NimbusNodeDriver, EucNodeDriver
from libcloud.compute.drivers.ec2 import IdempotentParamError
from libcloud.compute.drivers.ec2 import REGION_DETAILS
from libcloud.compute.drivers.ec2 import ExEC2AvailabilityZone
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import StorageVolume, VolumeSnapshot

from libcloud.test import MockHttpTestCase, LibcloudTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test import unittest
from libcloud.test.secrets import EC2_PARAMS


null_fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                   '00:00:00:00:00'


class BaseEC2Tests(LibcloudTestCase):

    def test_instantiate_driver_valid_regions(self):
        regions = REGION_DETAILS.keys()
        regions = [d for d in regions if d != 'nimbus']

        for region in regions:
            EC2NodeDriver(*EC2_PARAMS, **{'region': region})

    def test_instantiate_driver_invalid_regions(self):
        for region in ['invalid', 'nimbus']:
            try:
                EC2NodeDriver(*EC2_PARAMS, **{'region': region})
            except ValueError:
                pass
            else:
                self.fail('Invalid region, but exception was not thrown')


class EC2Tests(LibcloudTestCase, TestCaseMixin):
    image_name = 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml'
    region = 'us-east-1'

    def setUp(self):
        EC2MockHttp.test = self
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None

        self.driver = EC2NodeDriver(*EC2_PARAMS,
                                    **{'region': self.region})

    def test_create_node(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.name, 'foo')
        self.assertEqual(node.extra['tags']['Name'], 'foo')
        self.assertEqual(len(node.extra['tags']), 1)

    def test_create_node_with_ex_mincount(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size,
                                       ex_mincount=1, ex_maxcount=10)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.name, 'foo')
        self.assertEqual(node.extra['tags']['Name'], 'foo')
        self.assertEqual(len(node.extra['tags']), 1)

    def test_create_node_idempotent(self):
        EC2MockHttp.type = 'idempotent'
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        token = 'testclienttoken'
        node = self.driver.create_node(name='foo', image=image, size=size,
                                       ex_clienttoken=token)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.extra['clienttoken'], token)

        # from: http://docs.amazonwebservices.com/AWSEC2/latest/DeveloperGuide/index.html?Run_Instance_Idempotency.html
        #    If you repeat the request with the same client token, but change
        #    another request parameter, Amazon EC2 returns an
        #    IdempotentParameterMismatch error.
        # In our case, changing the parameter doesn't actually matter since we
        # are forcing the error response fixture.
        EC2MockHttp.type = 'idempotent_mismatch'

        idem_error = None
        # different count
        try:
            self.driver.create_node(name='foo', image=image, size=size,
                                    ex_mincount='2', ex_maxcount='2',
                                    ex_clienttoken=token)
        except IdempotentParamError:
            e = sys.exc_info()[1]
            idem_error = e
        self.assertTrue(idem_error is not None)

    def test_create_node_no_availability_zone(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        location = NodeLocation(0, 'Amazon US N. Virginia', 'US', self.driver)
        self.assertEqual(node.id, 'i-2ba64342')
        node = self.driver.create_node(name='foo', image=image, size=size,
                                       location=location)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.name, 'foo')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        public_ips = sorted(node.public_ips)
        self.assertEqual(node.id, 'i-4382922a')
        self.assertEqual(node.name, node.id)
        self.assertEqual(len(node.public_ips), 2)
        self.assertEqual(node.extra['launchdatetime'],
                         '2009-08-07T05:47:04.000Z')
        self.assertTrue('instancetype' in node.extra)

        self.assertEqual(public_ips[0], '1.2.3.4')
        self.assertEqual(public_ips[1], '1.2.3.5')

        nodes = self.driver.list_nodes(ex_node_ids=['i-4382922a',
                                                    'i-8474834a'])
        ret_node1 = nodes[0]
        ret_node2 = nodes[1]

        self.assertEqual(ret_node1.id, 'i-4382922a')
        self.assertEqual(ret_node2.id, 'i-8474834a')

        self.assertEqual(ret_node1.extra['launchdatetime'],
                         '2009-08-07T05:47:04.000Z')
        self.assertTrue('instancetype' in ret_node1.extra)

        self.assertEqual(ret_node2.extra['launchdatetime'],
                         '2009-08-07T05:47:04.000Z')
        self.assertTrue('instancetype' in ret_node2.extra)

    def test_list_nodes_with_name_tag(self):
        EC2MockHttp.type = 'WITH_TAGS'
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, 'i-8474834a')
        self.assertEqual(node.name, 'foobar1')

    def test_list_location(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) > 0)
        self.assertEqual(locations[0].name, 'eu-west-1a')
        self.assertTrue(locations[0].availability_zone is not None)
        self.assertTrue(isinstance(locations[0].availability_zone,
                                   ExEC2AvailabilityZone))

    def test_list_security_groups(self):
        groups = self.driver.ex_list_security_groups()
        self.assertEqual(groups, ['WebServers', 'RangedPortsBySource'])

    def test_authorize_security_group(self):
        resp = self.driver.ex_authorize_security_group('TestGroup', '22', '22',
                                                       '0.0.0.0/0')
        self.assertTrue(resp)

    def test_reboot_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_ex_start_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.ex_start_node(node)
        self.assertTrue(ret)

    def test_ex_stop_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.ex_stop_node(node)
        self.assertTrue(ret)

    def test_ex_create_node_with_ex_blockdevicemappings(self):
        EC2MockHttp.type = 'create_ex_blockdevicemappings'

        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        mappings = [
            {'DeviceName': '/dev/sda1', 'Ebs.VolumeSize': 10},
            {'DeviceName': '/dev/sdb', 'VirtualName': 'ephemeral0'},
            {'DeviceName': '/dev/sdc', 'VirtualName': 'ephemeral1'}
        ]
        node = self.driver.create_node(name='foo', image=image, size=size,
                                       ex_blockdevicemappings=mappings)
        self.assertEqual(node.id, 'i-2ba64342')

    def test_ex_create_node_with_ex_blockdevicemappings_attribute_error(self):
        EC2MockHttp.type = 'create_ex_blockdevicemappings'

        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        mappings = 'this should be a list'
        self.assertRaises(AttributeError, self.driver.create_node, name='foo',
                          image=image, size=size,
                          ex_blockdevicemappings=mappings)

        mappings = ['this should be a dict']
        self.assertRaises(AttributeError, self.driver.create_node, name='foo',
                          image=image, size=size,
                          ex_blockdevicemappings=mappings)

    def test_destroy_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        region_old = self.driver.region_name

        names = [
            ('ec2_us_east', 'us-east-1'),
            ('ec2_us_west', 'us-west-1'),
            ('ec2_eu_west', 'eu-west-1'),
            ('ec2_ap_southeast', 'ap-southeast-1'),
            ('ec2_ap_northeast', 'ap-northeast-1'),
            ('ec2_ap_southeast_2', 'ap-southeast-2')
        ]

        for api_name, region_name in names:
            self.driver.api_name = api_name
            self.driver.region_name = region_name
            sizes = self.driver.list_sizes()

            ids = [s.id for s in sizes]
            self.assertTrue('t1.micro' in ids)
            self.assertTrue('m1.small' in ids)
            self.assertTrue('m1.large' in ids)
            self.assertTrue('m1.xlarge' in ids)
            self.assertTrue('c1.medium' in ids)
            self.assertTrue('c1.xlarge' in ids)
            self.assertTrue('m2.xlarge' in ids)
            self.assertTrue('m2.2xlarge' in ids)
            self.assertTrue('m2.4xlarge' in ids)

            if region_name == 'us-east-1':
                self.assertEqual(len(sizes), 17)
                self.assertTrue('cg1.4xlarge' in ids)
                self.assertTrue('cc1.4xlarge' in ids)
                self.assertTrue('cc2.8xlarge' in ids)
                self.assertTrue('cr1.8xlarge' in ids)
            elif region_name in ['eu-west-1', 'ap-southeast-1',
                                 'ap-southeast-2']:
                self.assertEqual(len(sizes), 13)
            else:
                self.assertEqual(len(sizes), 12)

        self.driver.region_name = region_old

    def test_ex_create_node_with_ex_iam_profile(self):
        iamProfile = {
            'id': 'AIDGPMS9RO4H3FEXAMPLE',
            'name': 'Foo',
            'arn': 'arn:aws:iam:...'
        }

        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        EC2MockHttp.type = None
        node1 = self.driver.create_node(name='foo', image=image, size=size)
        EC2MockHttp.type = 'ex_iam_profile'
        node2 = self.driver.create_node(name='bar', image=image, size=size,
                                        ex_iam_profile=iamProfile['name'])
        node3 = self.driver.create_node(name='bar', image=image, size=size,
                                        ex_iam_profile=iamProfile['arn'])

        self.assertFalse(node1.extra['iam_profile'])
        self.assertEqual(node2.extra['iam_profile'], iamProfile['id'])
        self.assertEqual(node3.extra['iam_profile'], iamProfile['id'])

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]

        name = 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml'
        self.assertEqual(len(images), 1)
        self.assertEqual(image.name, name)
        self.assertEqual(image.id, 'ami-be3adfd7')

    def test_list_images_with_image_ids(self):
        images = self.driver.list_images(ex_image_ids=['ami-be3adfd7'])

        name = 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml'
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].name, name)

    def ex_destroy_image(self):
        images = self.driver.list_images()
        image = images[0]

        resp = self.driver.ex_destroy_image(image)
        self.assertTrue(resp)

    def test_ex_list_availability_zones(self):
        availability_zones = self.driver.ex_list_availability_zones()
        availability_zone = availability_zones[0]
        self.assertTrue(len(availability_zones) > 0)
        self.assertEqual(availability_zone.name, 'eu-west-1a')
        self.assertEqual(availability_zone.zone_state, 'available')
        self.assertEqual(availability_zone.region_name, 'eu-west-1')

    def test_ex_list_keypairs(self):
        keypairs = self.driver.ex_list_keypairs()

        self.assertEqual(len(keypairs), 1)
        self.assertEqual(keypairs[0]['keyName'], 'gsg-keypair')
        self.assertEqual(keypairs[0]['keyFingerprint'], null_fingerprint)

    def test_ex_describe_all_keypairs(self):
        keys = self.driver.ex_describe_all_keypairs()
        self.assertEqual(keys, ['gsg-keypair'])

    def test_ex_describe_keypairs(self):
        keypair1 = self.driver.ex_describe_keypair('gsg-keypair')

        # Test backward compatibility
        keypair2 = self.driver.ex_describe_keypairs('gsg-keypair')

        self.assertEqual(keypair1['keyName'], 'gsg-keypair')
        self.assertEqual(keypair1['keyFingerprint'], null_fingerprint)
        self.assertEqual(keypair2['keyName'], 'gsg-keypair')
        self.assertEqual(keypair2['keyFingerprint'], null_fingerprint)

    def ex_delete_keypair(self):
        resp = self.driver.ex_delete_keypair('testkey')
        self.assertTrue(resp)

    def test_ex_describe_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        tags = self.driver.ex_describe_tags(resource=node)

        self.assertEqual(len(tags), 3)
        self.assertTrue('tag' in tags)
        self.assertTrue('owner' in tags)
        self.assertTrue('stack' in tags)

    def test_ex_import_keypair_from_string(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'misc',
                            'dummy_rsa.pub')

        with open(path, 'r') as fh:
            key = self.driver.ex_import_keypair_from_string(
                'keypair', fh.read())

        self.assertEqual(key['keyName'], 'keypair')
        self.assertEqual(key['keyFingerprint'], null_fingerprint)

    def test_ex_import_keypair(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'misc',
                            'dummy_rsa.pub')
        key = self.driver.ex_import_keypair('keypair', path)
        self.assertEqual(key['keyName'], 'keypair')
        self.assertEqual(key['keyFingerprint'], null_fingerprint)

    def test_ex_create_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_create_tags(node, {'sample': 'tag'})

    def test_ex_delete_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_delete_tags(node, {'sample': 'tag'})

    def test_ex_describe_addresses_for_node(self):
        node1 = Node('i-4382922a', None, None, None, None, self.driver)
        ip_addresses1 = self.driver.ex_describe_addresses_for_node(node1)
        node2 = Node('i-4382922b', None, None, None, None, self.driver)
        ip_addresses2 = sorted(
            self.driver.ex_describe_addresses_for_node(node2))
        node3 = Node('i-4382922g', None, None, None, None, self.driver)
        ip_addresses3 = sorted(
            self.driver.ex_describe_addresses_for_node(node3))

        self.assertEqual(len(ip_addresses1), 1)
        self.assertEqual(ip_addresses1[0], '1.2.3.4')

        self.assertEqual(len(ip_addresses2), 2)
        self.assertEqual(ip_addresses2[0], '1.2.3.5')
        self.assertEqual(ip_addresses2[1], '1.2.3.6')

        self.assertEqual(len(ip_addresses3), 0)

    def test_ex_describe_addresses(self):
        node1 = Node('i-4382922a', None, None, None, None, self.driver)
        node2 = Node('i-4382922g', None, None, None, None, self.driver)
        nodes_elastic_ips1 = self.driver.ex_describe_addresses([node1])
        nodes_elastic_ips2 = self.driver.ex_describe_addresses([node2])

        self.assertEqual(len(nodes_elastic_ips1), 1)
        self.assertTrue(node1.id in nodes_elastic_ips1)
        self.assertEqual(nodes_elastic_ips1[node1.id], ['1.2.3.4'])

        self.assertEqual(len(nodes_elastic_ips2), 1)
        self.assertTrue(node2.id in nodes_elastic_ips2)
        self.assertEqual(nodes_elastic_ips2[node2.id], [])

    def test_ex_describe_all_addresses(self):
        EC2MockHttp.type = 'all_addresses'
        elastic_ips1 = self.driver.ex_describe_all_addresses()
        elastic_ips2 = self.driver.ex_describe_all_addresses(
            only_allocated=True)

        self.assertEqual(len(elastic_ips1), 3)
        self.assertTrue('1.2.3.5' in elastic_ips1)

        self.assertEqual(len(elastic_ips2), 2)
        self.assertTrue('1.2.3.5' not in elastic_ips2)

    def test_ex_allocate_address(self):
        ret = self.driver.ex_allocate_address()
        self.assertTrue(ret)

    def test_ex_release_address(self):
        ret = self.driver.ex_release_address('1.2.3.4')
        self.assertTrue(ret)

    def test_ex_associate_address_with_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)

        ret1 = self.driver.ex_associate_address_with_node(node, '1.2.3.4')
        ret2 = self.driver.ex_associate_addresses(node, '1.2.3.4')
        self.assertTrue(ret1)
        self.assertTrue(ret2)

    def test_ex_disassociate_address(self):
        ret = self.driver.ex_disassociate_address('1.2.3.4')
        self.assertTrue(ret)

    def test_ex_change_node_size_same_size(self):
        size = NodeSize('m1.small', 'Small Instance',
                        None, None, None, None, driver=self.driver)
        node = Node('i-4382922a', None, None, None, None, self.driver,
                    extra={'instancetype': 'm1.small'})

        try:
            self.driver.ex_change_node_size(node=node, new_size=size)
        except ValueError:
            pass
        else:
            self.fail('Same size was passed, but an exception was not thrown')

    def test_ex_change_node_size(self):
        size = NodeSize('m1.large', 'Small Instance',
                        None, None, None, None, driver=self.driver)
        node = Node('i-4382922a', None, None, None, None, self.driver,
                    extra={'instancetype': 'm1.small'})

        result = self.driver.ex_change_node_size(node=node, new_size=size)
        self.assertTrue(result)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()

        self.assertEqual(len(volumes), 2)

        self.assertEqual('vol-10ae5e2b', volumes[0].id)
        self.assertEqual(1, volumes[0].size)
        self.assertEqual('available', volumes[0].extra['state'])

        self.assertEqual('vol-v24bfh75', volumes[1].id)
        self.assertEqual(11, volumes[1].size)
        self.assertEqual('available', volumes[1].extra['state'])

    def test_create_volume(self):
        location = self.driver.list_locations()[0]
        vol = self.driver.create_volume(10, 'vol', location)

        self.assertEqual(10, vol.size)
        self.assertEqual('vol', vol.name)
        self.assertEqual('creating', vol.extra['state'])
        self.assertTrue(isinstance(vol.extra['create-time'], datetime))

    def test_destroy_volume(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            size=10, driver=self.driver)

        retValue = self.driver.destroy_volume(vol)
        self.assertTrue(retValue)

    def test_attach(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            size=10, driver=self.driver)

        node = Node('i-4382922a', None, None, None, None, self.driver)
        retValue = self.driver.attach_volume(node, vol, '/dev/sdh')

        self.assertTrue(retValue)

    def test_detach(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            size=10, driver=self.driver)

        retValue = self.driver.detach_volume(vol)
        self.assertTrue(retValue)

    def test_create_volume_snapshot(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            size=10, driver=self.driver)
        snap = self.driver.create_volume_snapshot(vol, 'Test description')

        self.assertEqual('snap-a7cb2hd9', snap.id)
        self.assertEqual(vol.size, snap.size)
        self.assertEqual('Test description', snap.extra['description'])
        self.assertEqual(vol.id, snap.extra['volume_id'])
        self.assertEqual('pending', snap.extra['state'])

    def test_list_snapshots(self):
        snaps = self.driver.list_snapshots()

        self.assertEqual(len(snaps), 2)

        self.assertEqual('snap-428abd35', snaps[0].id)
        self.assertEqual('vol-e020df80', snaps[0].extra['volume_id'])
        self.assertEqual(30, snaps[0].size)
        self.assertEqual('Daily Backup', snaps[0].extra['description'])

        self.assertEqual('snap-18349159', snaps[1].id)
        self.assertEqual('vol-b5a2c1v9', snaps[1].extra['volume_id'])
        self.assertEqual(15, snaps[1].size)
        self.assertEqual('Weekly backup', snaps[1].extra['description'])

    def test_destroy_snapshot(self):
        snap = VolumeSnapshot(id='snap-428abd35', size=10, driver=self.driver)
        resp = snap.destroy()
        self.assertTrue(resp)

    def test_ex_modify_image_attribute(self):
        images = self.driver.list_images()
        image = images[0]

        data = {'LaunchPermission.Add.1.Group': 'all'}
        resp = self.driver.ex_modify_image_attribute(image, data)
        self.assertTrue(resp)

    def test_create_node_ex_security_groups(self):
        EC2MockHttp.type = 'ex_security_groups'

        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        security_groups = ['group1', 'group2']

        # Old, deprecated argument name
        self.driver.create_node(name='foo', image=image, size=size,
                                ex_securitygroup=security_groups)

        # New argument name
        self.driver.create_node(name='foo', image=image, size=size,
                                ex_security_groups=security_groups)

        # Test old and new arguments are mutally exclusive
        self.assertRaises(ValueError, self.driver.create_node,
                          name='foo', image=image, size=size,
                          ex_securitygroup=security_groups,
                          ex_security_groups=security_groups)


class EC2USWest1Tests(EC2Tests):
    region = 'us-west-1'


class EC2USWest2Tests(EC2Tests):
    region = 'us-west-2'


class EC2EUWestTests(EC2Tests):
    region = 'eu-west-1'


class EC2APSE1Tests(EC2Tests):
    region = 'ap-southeast-1'


class EC2APNETests(EC2Tests):
    region = 'ap-northeast-1'


class EC2APSE2Tests(EC2Tests):
    region = 'ap-southeast-2'


class EC2SAEastTests(EC2Tests):
    region = 'sa-east-1'


# Tests for the old, deprecated way of instantiating a driver.
class EC2OldStyleModelTests(EC2Tests):
    driver_klass = EC2USWestNodeDriver

    def setUp(self):
        EC2MockHttp.test = self
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None

        self.driver = self.driver_klass(*EC2_PARAMS)


class EC2USWest1OldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2USWestNodeDriver


class EC2USWest2OldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2USWestOregonNodeDriver


class EC2EUWestOldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2EUNodeDriver


class EC2APSE1OldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2APSENodeDriver


class EC2APNEOldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2APNENodeDriver


class EC2APSE2OldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2APSESydneyNodeDriver


class EC2SAEastOldStyleModelTests(EC2OldStyleModelTests):
    driver_klass = EC2SAEastNodeDriver


class EC2MockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('ec2')

    def _DescribeInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _WITH_TAGS_DescribeInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_instances_with_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAvailabilityZones(self, method, url, body, headers):
        body = self.fixtures.load('describe_availability_zones.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RebootInstances(self, method, url, body, headers):
        body = self.fixtures.load('reboot_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _StartInstances(self, method, url, body, headers):
        body = self.fixtures.load('start_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _StopInstances(self, method, url, body, headers):
        body = self.fixtures.load('stop_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeSecurityGroups(self, method, url, body, headers):
        body = self.fixtures.load('describe_security_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AuthorizeSecurityGroupIngress(self, method, url, body, headers):
        body = self.fixtures.load('authorize_security_group_ingress.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeImages(self, method, url, body, headers):
        body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ex_security_groups_RunInstances(self, method, url, body, headers):
        # Need to remove '/?'
        url = url[2:]
        params = dict(parse_qsl(url))

        self.assertEqual(params['SecurityGroup.1'], 'group1')
        self.assertEqual(params['SecurityGroup.1'], 'group1')

        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _create_ex_blockdevicemappings_RunInstances(self, method, url, body, headers):
        # Need to remove '/?'
        url = url[2:]
        parameters = dict(parse_qsl(url))
        self.assertEqual(parameters['BlockDeviceMapping.1.DeviceName'],
                         '/dev/sda1')
        self.assertEqual(parameters['BlockDeviceMapping.1.Ebs.VolumeSize'],
                         '10')
        self.assertEqual(parameters['BlockDeviceMapping.2.DeviceName'],
                         '/dev/sdb')
        self.assertEqual(parameters['BlockDeviceMapping.2.VirtualName'],
                         'ephemeral0')
        self.assertEqual(parameters['BlockDeviceMapping.3.DeviceName'],
                         '/dev/sdc')
        self.assertEqual(parameters['BlockDeviceMapping.3.VirtualName'],
                         'ephemeral1')

        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_mismatch_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem_mismatch.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _ex_iam_profile_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_iam_profile.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _TerminateInstances(self, method, url, body, headers):
        body = self.fixtures.load('terminate_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeKeyPairs(self, method, url, body, headers):
        body = self.fixtures.load('describe_key_pairs.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ImportKeyPair(self, method, url, body, headers):
        body = self.fixtures.load('import_key_pair.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeTags(self, method, url, body, headers):
        body = self.fixtures.load('describe_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateTags(self, method, url, body, headers):
        body = self.fixtures.load('create_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteTags(self, method, url, body, headers):
        body = self.fixtures.load('delete_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAddresses(self, method, url, body, headers):
        body = self.fixtures.load('describe_addresses_multi.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AllocateAddress(self, method, url, body, headers):
        body = self.fixtures.load('allocate_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AssociateAddress(self, method, url, body, headers):
        body = self.fixtures.load('associate_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DisassociateAddress(self, method, url, body, headers):
        body = self.fixtures.load('disassociate_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ReleaseAddress(self, method, url, body, headers):
        body = self.fixtures.load('release_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _all_addresses_DescribeAddresses(self, method, url, body, headers):
        body = self.fixtures.load('describe_addresses_all.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _WITH_TAGS_DescribeAddresses(self, method, url, body, headers):
        body = self.fixtures.load('describe_addresses_multi.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyInstanceAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_instance_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_CreateTags(self, method, url, body, headers):
        body = self.fixtures.load('create_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateVolume(self, method, url, body, headers):
        body = self.fixtures.load('create_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteVolume(self, method, url, body, headers):
        body = self.fixtures.load('delete_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AttachVolume(self, method, url, body, headers):
        body = self.fixtures.load('attach_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DetachVolume(self, method, url, body, headers):
        body = self.fixtures.load('detach_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeVolumes(self, method, url, body, headers):
        body = self.fixtures.load('describe_volumes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateSnapshot(self, method, url, body, headers):
        body = self.fixtures.load('create_snapshot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeSnapshots(self, method, url, body, headers):
        body = self.fixtures.load('describe_snapshots.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteSnapshot(self, method, url, body, headers):
        body = self.fixtures.load('delete_snapshot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeregisterImage(self, method, url, body, headers):
        body = self.fixtures.load('deregister_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteKeypair(self, method, url, body, headers):
        url = url[2:]
        params = dict(parse_qsl(url))
        self.assertEqual(params['KeyPair'], 'testkey')

        body = self.fixtures.load('delete_keypair.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyImageAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_image_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class EucMockHttp(EC2MockHttp):
    fixtures = ComputeFileFixtures('ec2')

    def _services_Eucalyptus_DescribeInstances(self, method, url, body,
                                               headers):
        return self._DescribeInstances(method, url, body, headers)

    def _services_Eucalyptus_DescribeImages(self, method, url, body,
                                            headers):
        return self._DescribeImages(method, url, body, headers)

    def _services_Eucalyptus_DescribeAddresses(self, method, url, body,
                                               headers):
        return self._DescribeAddresses(method, url, body, headers)

    def _services_Eucalyptus_RebootInstances(self, method, url, body,
                                             headers):
        return self._RebootInstances(method, url, body, headers)

    def _services_Eucalyptus_TerminateInstances(self, method, url, body,
                                                headers):
        return self._TerminateInstances(method, url, body, headers)

    def _services_Eucalyptus_RunInstances(self, method, url, body,
                                          headers):
        return self._RunInstances(method, url, body, headers)

    def _services_Eucalyptus_CreateTags(self, method, url, body,
                                        headers):
        return self._CreateTags(method, url, body, headers)


class NimbusTests(EC2Tests):

    def setUp(self):
        NimbusNodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = NimbusNodeDriver(key=EC2_PARAMS[0], secret=EC2_PARAMS[1],
                                       host='some.nimbuscloud.com')

    def test_ex_describe_addresses_for_node(self):
        # overridden from EC2Tests -- Nimbus doesn't support elastic IPs.
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ip_addresses = self.driver.ex_describe_addresses_for_node(node)
        self.assertEqual(len(ip_addresses), 0)

    def test_ex_describe_addresses(self):
        # overridden from EC2Tests -- Nimbus doesn't support elastic IPs.
        node = Node('i-4382922a', None, None, None, None, self.driver)
        nodes_elastic_ips = self.driver.ex_describe_addresses([node])

        self.assertEqual(len(nodes_elastic_ips), 1)
        self.assertEqual(len(nodes_elastic_ips[node.id]), 0)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()

        ids = [s.id for s in sizes]
        self.assertTrue('m1.small' in ids)
        self.assertTrue('m1.large' in ids)
        self.assertTrue('m1.xlarge' in ids)

    def test_list_nodes(self):
        # overridden from EC2Tests -- Nimbus doesn't support elastic IPs.
        node = self.driver.list_nodes()[0]
        self.assertExecutedMethodCount(0)
        public_ips = node.public_ips
        self.assertEqual(node.id, 'i-4382922a')
        self.assertEqual(len(node.public_ips), 1)
        self.assertEqual(public_ips[0], '1.2.3.5')
        self.assertEqual(node.extra['tags'], {})

        node = self.driver.list_nodes()[1]
        self.assertExecutedMethodCount(0)
        public_ips = node.public_ips
        self.assertEqual(node.id, 'i-8474834a')
        self.assertEqual(len(node.public_ips), 1)
        self.assertEqual(public_ips[0], '1.2.3.5')
        self.assertEqual(node.extra['tags'], {
                         'user_key0': 'user_val0', 'user_key1': 'user_val1'})

    def test_ex_create_tags(self):
        # Nimbus doesn't support creating tags so this one should be a
        # passthrough
        node = self.driver.list_nodes()[0]
        self.driver.ex_create_tags(resource=node, tags={'foo': 'bar'})
        self.assertExecutedMethodCount(0)


class EucTests(LibcloudTestCase, TestCaseMixin):

    def setUp(self):
        EucNodeDriver.connectionCls.conn_classes = (None, EucMockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EucNodeDriver(key=EC2_PARAMS[0], secret=EC2_PARAMS[1],
                                    host='some.eucalyptus.com')

    def test_list_locations_response(self):
        try:
            self.driver.list_locations()
        except Exception:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_list_location(self):
        pass


if __name__ == '__main__':
    sys.exit(unittest.main())
