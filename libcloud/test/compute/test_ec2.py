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

from collections import OrderedDict

import os
import sys
from datetime import datetime
from libcloud.utils.iso8601 import UTC

from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.ec2 import EC2NodeDriver
from libcloud.compute.drivers.ec2 import EC2PlacementGroup
from libcloud.compute.drivers.ec2 import NimbusNodeDriver, EucNodeDriver
from libcloud.compute.drivers.ec2 import OutscaleSASNodeDriver
from libcloud.compute.drivers.ec2 import IdempotentParamError
from libcloud.compute.drivers.ec2 import REGION_DETAILS, VALID_EC2_REGIONS
from libcloud.compute.drivers.ec2 import ExEC2AvailabilityZone
from libcloud.compute.drivers.ec2 import EC2NetworkSubnet
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import StorageVolume, VolumeSnapshot
from libcloud.compute.types import KeyPairDoesNotExistError, StorageVolumeState, \
    VolumeSnapshotState

from libcloud.test import MockHttp, LibcloudTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test import unittest
from libcloud.test.secrets import EC2_PARAMS


null_fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                   '00:00:00:00:00'


class BaseEC2Tests(LibcloudTestCase):

    def test_instantiate_driver_valid_regions(self):
        regions = REGION_DETAILS.keys()
        regions = [d for d in regions if d != 'nimbus' and d != 'cn-north-1']

        region_endpoints = [
            EC2NodeDriver(*EC2_PARAMS, **{'region': region}).connection.host for region in regions
        ]

        # Verify that each driver doesn't get the same API host endpoint
        self.assertEqual(len(region_endpoints),
                         len(set(region_endpoints)),
                         "Multiple Region Drivers were given the same API endpoint")

    def test_instantiate_driver_invalid_regions(self):
        for region in ['invalid', 'nimbus']:
            try:
                EC2NodeDriver(*EC2_PARAMS, **{'region': region})
            except ValueError:
                pass
            else:
                self.fail('Invalid region, but exception was not thrown')

    def test_list_sizes_valid_regions(self):
        unsupported_regions = list()

        for region in VALID_EC2_REGIONS:
            no_pricing = region in ['cn-north-1']
            driver = EC2NodeDriver(*EC2_PARAMS, **{'region': region})
            try:
                sizes = driver.list_sizes()
                if no_pricing:
                    self.assertTrue(all([s.price is None for s in sizes]))
            except Exception:
                unsupported_regions.append(region)

        if unsupported_regions:
            self.fail('Cannot list sizes from ec2 regions: %s' % unsupported_regions)


class EC2Tests(LibcloudTestCase, TestCaseMixin):
    image_name = 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml'
    region = 'us-east-1'

    def setUp(self):
        EC2MockHttp.test = self
        EC2NodeDriver.connectionCls.conn_class = EC2MockHttp
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None

        self.driver = EC2NodeDriver(*EC2_PARAMS,
                                    **{'region': self.region})

    def test_instantiate_driver_with_token(self):
        token = 'temporary_credentials_token'
        driver = EC2NodeDriver(*EC2_PARAMS, **{'region': self.region, 'token': token})
        self.assertTrue(hasattr(driver, 'token'), 'Driver has no attribute token')
        self.assertEqual(token, driver.token, "Driver token does not match with provided token")

    def test_driver_with_token_signature_version(self):
        token = 'temporary_credentials_token'
        driver = EC2NodeDriver(*EC2_PARAMS, **{'region': self.region, 'token': token})
        kwargs = driver._ex_connection_class_kwargs()
        self.assertIn('signature_version', kwargs)
        self.assertEqual('4', kwargs['signature_version'], 'Signature version is not 4 with temporary credentials')

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

    def test_create_node_with_ex_assign_public_ip(self):
        # assertions are done in _create_ex_assign_public_ip_RunInstances
        EC2MockHttp.type = 'create_ex_assign_public_ip'
        image = NodeImage(id='ami-11111111',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        subnet = EC2NetworkSubnet('subnet-11111111', "test_subnet", "pending")
        self.driver.create_node(
            name='foo',
            image=image,
            size=size,
            ex_subnet=subnet,
            ex_security_group_ids=[
                'sg-11111111'
            ],
            ex_assign_public_ip=True,
        )

    def test_create_node_with_ex_terminate_on_shutdown(self):
        EC2MockHttp.type = 'create_ex_terminate_on_shutdown'
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        # The important part about the test is asserted inside
        # EC2MockHttp._create_ex_terminate_on_shutdown
        self.driver.create_node(name='foo', image=image, size=size, ex_terminate_on_shutdown=True)

    def test_create_node_with_metadata(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo',
                                       image=image,
                                       size=size,
                                       ex_metadata={'Bar': 'baz', 'Num': '42'})
        self.assertEqual(node.name, 'foo')
        self.assertEqual(node.extra['tags']['Name'], 'foo')
        self.assertEqual(node.extra['tags']['Bar'], 'baz')
        self.assertEqual(node.extra['tags']['Num'], '42')
        self.assertEqual(len(node.extra['tags']), 3)

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
        self.assertEqual(node.extra['client_token'], token)

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
        except IdempotentParamError as e:
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

        self.assertEqual(node.extra['launch_time'], '2013-12-02T11:58:11.000Z')
        self.assertEqual(node.created_at, datetime(2013, 12, 2, 11, 58, 11, tzinfo=UTC))

        self.assertTrue('instance_type' in node.extra)
        self.assertEqual(node.extra['availability'], 'us-east-1d')
        self.assertEqual(node.extra['key_name'], 'fauxkey')
        self.assertEqual(node.extra['monitoring'], 'disabled')
        self.assertEqual(node.extra['image_id'], 'ami-3215fe5a')
        self.assertEqual(len(node.extra['groups']), 2)
        self.assertEqual(len(node.extra['block_device_mapping']), 1)
        self.assertEqual(node.extra['block_device_mapping'][0]['device_name'], '/dev/sda1')
        self.assertEqual(node.extra['block_device_mapping'][0]['ebs']['volume_id'], 'vol-5e312311')
        self.assertTrue(node.extra['block_device_mapping'][0]['ebs']['delete'])
        self.assertEqual(node.extra['block_device_mapping'][0]['ebs']['status'], 'attached')
        self.assertEqual(node.extra['block_device_mapping'][0]['ebs']['attach_time'],
                         datetime(2013, 4, 9, 18, 1, 1, tzinfo=UTC))
        self.assertEqual(public_ips[0], '1.2.3.4')

        nodes = self.driver.list_nodes(ex_node_ids=['i-4382922a',
                                                    'i-8474834a'])
        ret_node1 = nodes[0]
        ret_node2 = nodes[1]

        self.assertEqual(ret_node1.id, 'i-4382922a')
        self.assertEqual(ret_node2.id, 'i-8474834a')
        self.assertEqual(ret_node2.name, 'Test Server 2')
        self.assertEqual(ret_node2.extra['subnet_id'], 'subnet-5fd9d412')
        self.assertEqual(ret_node2.extra['vpc_id'], 'vpc-61dcd30e')
        self.assertEqual(ret_node2.extra['tags']['Group'], 'VPC Test')

        self.assertEqual(ret_node1.extra['launch_time'], '2013-12-02T11:58:11.000Z')
        self.assertEqual(ret_node1.created_at, datetime(2013, 12, 2, 11, 58, 11, tzinfo=UTC))
        self.assertEqual(ret_node2.extra['launch_time'], '2013-12-02T15:58:29.000Z')
        self.assertEqual(ret_node2.created_at, datetime(2013, 12, 2, 15, 58, 29, tzinfo=UTC))

        self.assertIn('instance_type', ret_node1.extra)
        self.assertIn('instance_type', ret_node2.extra)

    def test_ex_list_reserved_nodes(self):
        node = self.driver.ex_list_reserved_nodes()[0]
        self.assertEqual(node.id, '93bbbca2-c500-49d0-9ede-9d8737400498')
        self.assertEqual(node.state, 'active')
        self.assertEqual(node.extra['instance_type'], 't1.micro')
        self.assertEqual(node.extra['availability'], 'us-east-1b')
        self.assertEqual(node.extra['start'], '2013-06-18T12:07:53.161Z')
        self.assertEqual(node.extra['end'], '2014-06-18T12:07:53.161Z')
        self.assertEqual(node.extra['duration'], 31536000)
        self.assertEqual(node.extra['usage_price'], 0.012)
        self.assertEqual(node.extra['fixed_price'], 23.0)
        self.assertEqual(node.extra['instance_count'], 1)
        self.assertEqual(node.extra['description'], 'Linux/UNIX')
        self.assertEqual(node.extra['instance_tenancy'], 'default')
        self.assertEqual(node.extra['currency_code'], 'USD')
        self.assertEqual(node.extra['offering_type'], 'Light Utilization')

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

    def test_ex_delete_security_group_by_id(self):
        group_id = 'sg-443d0a12'
        retValue = self.driver.ex_delete_security_group_by_id(group_id)
        self.assertTrue(retValue)

    def test_delete_security_group_by_name(self):
        group_name = 'WebServers'
        retValue = self.driver.ex_delete_security_group_by_name(group_name)
        self.assertTrue(retValue)

    def test_ex_delete_security_group(self):
        name = 'WebServers'
        retValue = self.driver.ex_delete_security_group(name)
        self.assertTrue(retValue)

    def test_authorize_security_group(self):
        resp = self.driver.ex_authorize_security_group('TestGroup', '22', '22',
                                                       '0.0.0.0/0')
        self.assertTrue(resp)

    def test_authorize_security_group_ingress(self):
        ranges = ['1.1.1.1/32', '2.2.2.2/32']
        description = "automated authorised IP ingress test"
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, cidr_ips=ranges, description=description)
        self.assertTrue(resp)
        groups = [{'group_id': 'sg-949265ff'}]
        description = "automated authorised group ingress test"
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 23, group_pairs=groups, description=description)
        self.assertTrue(resp)

    def test_authorize_security_group_egress(self):
        ranges = ['1.1.1.1/32', '2.2.2.2/32']
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, cidr_ips=ranges)
        self.assertTrue(resp)
        groups = [{'group_id': 'sg-949265ff'}]
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, group_pairs=groups)
        self.assertTrue(resp)

    def test_revoke_security_group_ingress(self):
        ranges = ['1.1.1.1/32', '2.2.2.2/32']
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, cidr_ips=ranges)
        self.assertTrue(resp)
        groups = [{'group_id': 'sg-949265ff'}]
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, group_pairs=groups)
        self.assertTrue(resp)

    def test_revoke_security_group_egress(self):
        ranges = ['1.1.1.1/32', '2.2.2.2/32']
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, cidr_ips=ranges)
        self.assertTrue(resp)
        groups = [{'group_id': 'sg-949265ff'}]
        resp = self.driver.ex_authorize_security_group_ingress('sg-42916629', 22, 22, group_pairs=groups)
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
            ('ec2_us_west', 'us-west-2'),
            ('ec2_eu_west', 'eu-west-1'),
            ('ec2_ap_southeast', 'ap-southeast-1'),
            ('ec2_ap_northeast', 'ap-northeast-1'),
            ('ec2_ap_southeast_2', 'ap-southeast-2'),
            ('ec2_ap_south_1', 'ap-south-1')
        ]

        for api_name, region_name in names:
            self.driver.api_name = api_name
            self.driver.region_name = region_name
            sizes = self.driver.list_sizes()
            self.assertNotEqual(len(sizes), 0)
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
                                        ex_iamprofile=iamProfile['name'])
        node3 = self.driver.create_node(name='bar', image=image, size=size,
                                        ex_iamprofile=iamProfile['arn'])

        self.assertFalse(node1.extra['iam_profile'])
        self.assertEqual(node2.extra['iam_profile'], iamProfile['id'])
        self.assertEqual(node3.extra['iam_profile'], iamProfile['id'])

    def test_list_images(self):
        images = self.driver.list_images()

        self.assertEqual(len(images), 2)
        location = '123456788908/Test Image'
        self.assertEqual(images[0].id, 'ami-57ba933a')
        self.assertEqual(images[0].name, 'Test Image')
        self.assertEqual(images[0].extra['image_location'], location)
        self.assertEqual(images[0].extra['architecture'], 'x86_64')
        self.assertEqual(len(images[0].extra['block_device_mapping']), 2)
        ephemeral = images[0].extra['block_device_mapping'][1]['virtual_name']
        self.assertEqual(ephemeral, 'ephemeral0')
        billing_product1 = images[0].extra['billing_products'][0]
        self.assertEqual(billing_product1, 'ab-5dh78019')

        location = '123456788908/Test Image 2'
        self.assertEqual(images[1].id, 'ami-85b2a8ae')
        self.assertEqual(images[1].name, 'Test Image 2')
        self.assertEqual(images[1].extra['image_location'], location)
        self.assertEqual(images[1].extra['architecture'], 'x86_64')
        size = images[1].extra['block_device_mapping'][0]['ebs']['volume_size']
        billing_product2 = images[1].extra['billing_products'][0]
        self.assertEqual(billing_product2, 'as-6dr90319')
        self.assertEqual(size, 20)

    def test_list_images_with_image_ids(self):
        EC2MockHttp.type = 'ex_imageids'
        images = self.driver.list_images(ex_image_ids=['ami-57ba933a'])

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].name, 'Test Image')

    def test_list_images_with_executable_by(self):
        images = self.driver.list_images(ex_executableby='self')

        self.assertEqual(len(images), 2)

    def test_get_image(self):
        image = self.driver.get_image('ami-57ba933a')
        self.assertEqual(image.id, 'ami-57ba933a')
        self.assertEqual(image.name, 'Test Image')
        self.assertEqual(image.extra['architecture'], 'x86_64')
        self.assertEqual(len(image.extra['block_device_mapping']), 2)
        self.assertEqual(image.extra['billing_products'][0], 'ab-5dh78019')

    def test_copy_image(self):
        image = self.driver.list_images()[0]
        resp = self.driver.copy_image(image, 'us-east-1',
                                      name='Faux Image',
                                      description='Test Image Copy')
        self.assertEqual(resp.id, 'ami-4db38224')

    def test_create_image(self):
        node = self.driver.list_nodes()[0]

        mapping = [{'VirtualName': None,
                    'Ebs': {'VolumeSize': 10,
                            'VolumeType': 'standard',
                            'DeleteOnTermination': 'true'},
                    'DeviceName': '/dev/sda1'}]

        resp = self.driver.create_image(node,
                                        'New Image',
                                        description='New EBS Image',
                                        block_device_mapping=mapping)
        self.assertEqual(resp.id, 'ami-e9b38280')

    def test_create_image_no_mapping(self):
        node = self.driver.list_nodes()[0]

        resp = self.driver.create_image(node,
                                        'New Image',
                                        description='New EBS Image')
        self.assertEqual(resp.id, 'ami-e9b38280')

    def delete_image(self):
        images = self.driver.list_images()
        image = images[0]

        resp = self.driver.delete_image(image)
        self.assertTrue(resp)

    def ex_register_image(self):
        mapping = [{'DeviceName': '/dev/sda1',
                    'Ebs': {'SnapshotId': 'snap-5ade3e4e'}}]
        image = self.driver.ex_register_image(name='Test Image',
                                              root_device_name='/dev/sda1',
                                              description='My Image',
                                              architecture='x86_64',
                                              block_device_mapping=mapping,
                                              ena_support=True,
                                              billing_products=['ab-5dh78019'],
                                              sriov_net_support='simple')
        self.assertEqual(image.id, 'ami-57c2fb3e')

    def test_ex_import_snapshot(self):
        disk_container = [{'Description': 'Dummy import snapshot task',
                           'Format': 'raw',
                           'UserBucket': {'S3Bucket': 'dummy-bucket', 'S3Key': 'dummy-key'}}]

        snap = self.driver.ex_import_snapshot(disk_container=disk_container)
        self.assertEqual(snap.id, 'snap-0ea83e8a87e138f39')

    def test_wait_for_import_snapshot_completion(self):
        snap = self.driver._wait_for_import_snapshot_completion(
            import_task_id='import-snap-fhdysyq6')
        self.assertEqual(snap.id, 'snap-0ea83e8a87e138f39')

    def test_timeout_wait_for_import_snapshot_completion(self):
        import_task_id = 'import-snap-fhdysyq6'
        EC2MockHttp.type = 'timeout'
        with self.assertRaises(Exception) as context:
            self.driver._wait_for_import_snapshot_completion(
                import_task_id=import_task_id, timeout=0.01, interval=0.001)
        self.assertEqual('Timeout while waiting for import task Id %s'
                         % import_task_id, str(context.exception))

    def test_ex_describe_import_snapshot_tasks(self):
        snap = self.driver.ex_describe_import_snapshot_tasks(
            import_task_id='import-snap-fh7y6i6w<')

        self.assertEqual(snap.snapshotId, 'snap-0ea83e8a87e138f39')
        self.assertEqual(snap.status, 'completed')

    def test_ex_list_availability_zones(self):
        availability_zones = self.driver.ex_list_availability_zones()
        availability_zone = availability_zones[0]
        self.assertTrue(len(availability_zones) > 0)
        self.assertEqual(availability_zone.name, 'eu-west-1a')
        self.assertEqual(availability_zone.zone_state, 'available')
        self.assertEqual(availability_zone.region_name, 'eu-west-1')

    def test_list_keypairs(self):
        keypairs = self.driver.list_key_pairs()

        self.assertEqual(len(keypairs), 1)
        self.assertEqual(keypairs[0].name, 'gsg-keypair')
        self.assertEqual(keypairs[0].fingerprint, null_fingerprint)

        # Test old deprecated method
        keypairs = self.driver.ex_list_keypairs()

        self.assertEqual(len(keypairs), 1)
        self.assertEqual(keypairs[0]['keyName'], 'gsg-keypair')
        self.assertEqual(keypairs[0]['keyFingerprint'], null_fingerprint)

    def test_get_key_pair(self):
        EC2MockHttp.type = 'get_one'

        key_pair = self.driver.get_key_pair(name='gsg-keypair')
        self.assertEqual(key_pair.name, 'gsg-keypair')

    def test_get_key_pair_does_not_exist(self):
        EC2MockHttp.type = 'doesnt_exist'

        self.assertRaises(KeyPairDoesNotExistError, self.driver.get_key_pair,
                          name='test-key-pair')

    def test_create_key_pair(self):
        key_pair = self.driver.create_key_pair(name='test-keypair')

        fingerprint = ('1f:51:ae:28:bf:89:e9:d8:1f:25:5d'
                       ':37:2d:7d:b8:ca:9f:f5:f1:6f')

        self.assertEqual(key_pair.name, 'my-key-pair')
        self.assertEqual(key_pair.fingerprint, fingerprint)
        self.assertTrue(key_pair.private_key is not None)

        # Test old and deprecated method
        key_pair = self.driver.ex_create_keypair(name='test-keypair')
        self.assertEqual(key_pair['keyFingerprint'], fingerprint)
        self.assertTrue(key_pair['keyMaterial'] is not None)

    def test_ex_describe_all_keypairs(self):
        keys = self.driver.ex_describe_all_keypairs()
        self.assertEqual(keys, ['gsg-keypair'])

    def test_list_key_pairs(self):
        keypair1 = self.driver.list_key_pairs()[0]

        self.assertEqual(keypair1.name, 'gsg-keypair')
        self.assertEqual(keypair1.fingerprint, null_fingerprint)

        # Test backward compatibility
        keypair2 = self.driver.ex_describe_keypairs('gsg-keypair')

        self.assertEqual(keypair2['keyName'], 'gsg-keypair')
        self.assertEqual(keypair2['keyFingerprint'], null_fingerprint)

    def test_delete_key_pair(self):
        keypair = self.driver.list_key_pairs()[0]
        success = self.driver.delete_key_pair(keypair)

        self.assertTrue(success)

        # Test old and deprecated method
        resp = self.driver.ex_delete_keypair('gsg-keypair')
        self.assertTrue(resp)

    def test_ex_describe_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        tags = self.driver.ex_describe_tags(resource=node)

        self.assertEqual(len(tags), 3)
        self.assertTrue('tag' in tags)
        self.assertTrue('owner' in tags)
        self.assertTrue('stack' in tags)

    def test_import_key_pair_from_string(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'misc',
                            'test_rsa.pub')

        with open(path, 'r') as fp:
            key_material = fp.read()

        key = self.driver.import_key_pair_from_string(name='keypair',
                                                      key_material=key_material)
        self.assertEqual(key.name, 'keypair')
        self.assertEqual(key.fingerprint, null_fingerprint)

        # Test old and deprecated method
        key = self.driver.ex_import_keypair_from_string('keypair',
                                                        key_material)
        self.assertEqual(key['keyName'], 'keypair')
        self.assertEqual(key['keyFingerprint'], null_fingerprint)

    def test_import_key_pair_from_file(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'misc',
                            'test_rsa.pub')

        key = self.driver.import_key_pair_from_file('keypair', path)
        self.assertEqual(key.name, 'keypair')
        self.assertEqual(key.fingerprint, null_fingerprint)

        # Test old and deprecated method
        key = self.driver.ex_import_keypair('keypair', path)
        self.assertEqual(key['keyName'], 'keypair')
        self.assertEqual(key['keyFingerprint'], null_fingerprint)

    def test_ex_create_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_create_tags(node, {'sample': 'tag'})

    def test_ex_delete_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_delete_tags(node, {'sample': 'tag'})

    def test_ex_delete_tags2(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        self.driver.ex_create_tags(node, {'sample': 'another tag'})
        self.driver.ex_delete_tags(node, {'sample': None})

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
            only_associated=True)
        self.assertEqual('1.2.3.7', elastic_ips1[3].ip)
        self.assertEqual('vpc', elastic_ips1[3].domain)
        self.assertEqual('eipalloc-992a5cf8', elastic_ips1[3].extra['allocation_id'])

        self.assertEqual(len(elastic_ips2), 2)
        self.assertEqual('1.2.3.5', elastic_ips2[1].ip)
        self.assertEqual('vpc', elastic_ips2[1].domain)

    def test_ex_allocate_address(self):
        elastic_ip = self.driver.ex_allocate_address()
        self.assertEqual('192.0.2.1', elastic_ip.ip)
        self.assertEqual('standard', elastic_ip.domain)
        EC2MockHttp.type = 'vpc'
        elastic_ip = self.driver.ex_allocate_address(domain='vpc')
        self.assertEqual('192.0.2.2', elastic_ip.ip)
        self.assertEqual('vpc', elastic_ip.domain)
        self.assertEqual('eipalloc-666d7f04', elastic_ip.extra['allocation_id'])

    def test_ex_release_address(self):
        EC2MockHttp.type = 'all_addresses'
        elastic_ips = self.driver.ex_describe_all_addresses()
        EC2MockHttp.type = ''
        ret = self.driver.ex_release_address(elastic_ips[2])
        self.assertTrue(ret)
        ret = self.driver.ex_release_address(elastic_ips[0], domain='vpc')
        self.assertTrue(ret)
        self.assertRaises(AttributeError,
                          self.driver.ex_release_address,
                          elastic_ips[0],
                          domain='bogus')

    def test_ex_associate_address_with_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        EC2MockHttp.type = 'all_addresses'
        elastic_ips = self.driver.ex_describe_all_addresses()
        EC2MockHttp.type = ''
        ret1 = self.driver.ex_associate_address_with_node(
            node, elastic_ips[2])
        ret2 = self.driver.ex_associate_addresses(
            node, elastic_ips[2])
        self.assertEqual(None, ret1)
        self.assertEqual(None, ret2)
        EC2MockHttp.type = 'vpc'
        ret3 = self.driver.ex_associate_address_with_node(
            node, elastic_ips[3], domain='vpc')
        ret4 = self.driver.ex_associate_addresses(
            node, elastic_ips[3], domain='vpc')
        self.assertEqual('eipassoc-167a8073', ret3)
        self.assertEqual('eipassoc-167a8073', ret4)
        self.assertRaises(AttributeError,
                          self.driver.ex_associate_address_with_node,
                          node,
                          elastic_ips[1],
                          domain='bogus')

    def test_ex_disassociate_address(self):
        EC2MockHttp.type = 'all_addresses'
        elastic_ips = self.driver.ex_describe_all_addresses()
        EC2MockHttp.type = ''
        ret = self.driver.ex_disassociate_address(elastic_ips[2])
        self.assertTrue(ret)
        # Test a VPC disassociation
        ret = self.driver.ex_disassociate_address(elastic_ips[1],
                                                  domain='vpc')
        self.assertTrue(ret)
        self.assertRaises(AttributeError,
                          self.driver.ex_disassociate_address,
                          elastic_ips[1],
                          domain='bogus')

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

        self.assertEqual(len(volumes), 3)

        self.assertEqual('vol-10ae5e2b', volumes[0].id)
        self.assertEqual(1, volumes[0].size)
        self.assertEqual('available', volumes[0].extra['state'])
        self.assertEqual(StorageVolumeState.AVAILABLE, volumes[0].state)

        self.assertEqual('vol-v24bfh75', volumes[1].id)
        self.assertEqual(11, volumes[1].size)
        self.assertIsNone(volumes[1].extra['snapshot_id'])
        self.assertEqual('in-use', volumes[1].extra['state'])
        self.assertEqual(StorageVolumeState.INUSE, volumes[1].state)

        self.assertEqual('vol-b6c851ec', volumes[2].id)
        self.assertEqual(8, volumes[2].size)
        self.assertEqual('some-unknown-status', volumes[2].extra['state'])
        self.assertEqual('i-d334b4b3', volumes[2].extra['instance_id'])
        self.assertEqual('/dev/sda1', volumes[2].extra['device'])
        self.assertEqual('snap-30d37269', volumes[2].extra['snapshot_id'])
        self.assertEqual(StorageVolumeState.UNKNOWN, volumes[2].state)

        EC2MockHttp.type = 'filters_nodes'
        node = Node('i-d334b4b3', None, None, None, None, self.driver)
        self.driver.list_volumes(node=node)

        EC2MockHttp.type = 'filters_status'
        self.driver.list_volumes(ex_filters={'status': 'available'})

    def test_create_volume(self):
        location = self.driver.list_locations()[0]
        vol = self.driver.create_volume(10, 'vol', location)

        self.assertEqual(10, vol.size)
        self.assertEqual('vol', vol.name)
        self.assertEqual('creating', vol.extra['state'])
        self.assertTrue(isinstance(vol.extra['create_time'], datetime))
        self.assertEqual(False, vol.extra['encrypted'])

    def test_create_encrypted_volume(self):
        location = self.driver.list_locations()[0]
        vol = self.driver.create_volume(
            10, 'vol', location,
            ex_encrypted=True,
            ex_kms_key_id='1234')

        self.assertEqual(10, vol.size)
        self.assertEqual('vol', vol.name)
        self.assertEqual('creating', vol.extra['state'])
        self.assertTrue(isinstance(vol.extra['create_time'], datetime))
        self.assertEqual(True, vol.extra['encrypted'])

    def test_destroy_volume(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            state=StorageVolumeState.AVAILABLE,
                            size=10, driver=self.driver)

        retValue = self.driver.destroy_volume(vol)
        self.assertTrue(retValue)

    def test_attach(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            size=10, state=StorageVolumeState.AVAILABLE,
                            driver=self.driver)

        node = Node('i-4382922a', None, None, None, None, self.driver)
        retValue = self.driver.attach_volume(node, vol, '/dev/sdh')

        self.assertTrue(retValue)

    def test_detach(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            state=StorageVolumeState.INUSE,
                            size=10, driver=self.driver)

        retValue = self.driver.detach_volume(vol)
        self.assertTrue(retValue)

    def test_create_volume_snapshot(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            state=StorageVolumeState.AVAILABLE,
                            size=10, driver=self.driver)
        snap = self.driver.create_volume_snapshot(
            vol, 'Test snapshot')
        self.assertEqual('snap-a7cb2hd9', snap.id)
        self.assertEqual(vol.size, snap.size)
        self.assertEqual('Test snapshot', snap.extra['name'])
        self.assertEqual(vol.id, snap.extra['volume_id'])
        self.assertEqual('pending', snap.extra['state'])
        self.assertEqual(VolumeSnapshotState.CREATING, snap.state)
        # 2013-08-15T16:22:30.000Z
        self.assertEqual(datetime(2013, 8, 15, 16, 22, 30, tzinfo=UTC), snap.created)

    def test_create_volume_snapshot_with_tags(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            state=StorageVolumeState.AVAILABLE,
                            size=10, driver=self.driver)
        snap = self.driver.create_volume_snapshot(
            vol, 'Test snapshot', ex_metadata={'my_tag': 'test'})
        self.assertEqual('test', snap.extra['tags']['my_tag'])

    def test_list_snapshots(self):
        snaps = self.driver.list_snapshots()

        self.assertEqual(len(snaps), 3)

        self.assertEqual('snap-428abd35', snaps[0].id)
        self.assertEqual(VolumeSnapshotState.CREATING, snaps[0].state)
        self.assertEqual('vol-e020df80', snaps[0].extra['volume_id'])
        self.assertEqual(30, snaps[0].size)
        self.assertEqual('Daily Backup', snaps[0].extra['description'])

        self.assertEqual('snap-18349159', snaps[1].id)
        self.assertEqual('DB Backup 1', snaps[1].name)
        self.assertEqual(VolumeSnapshotState.AVAILABLE, snaps[1].state)
        self.assertEqual('vol-b5a2c1v9', snaps[1].extra['volume_id'])
        self.assertEqual(15, snaps[1].size)
        self.assertEqual('Weekly backup', snaps[1].extra['description'])
        self.assertEqual('DB Backup 1', snaps[1].extra['name'])

    def test_list_volume_snapshots(self):
        volume = self.driver.list_volumes()[0]
        assert volume.id == 'vol-10ae5e2b'

        snapshots = self.driver.list_volume_snapshots(volume)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].id, 'snap-18349160')

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

    def test_ex_modify_snapshot_attribute(self):
        snap = VolumeSnapshot(id='snap-1234567890abcdef0',
                              size=10, driver=self.driver)

        data = {'CreateVolumePermission.Add.1.Group': 'all'}
        resp = self.driver.ex_modify_snapshot_attribute(snap, data)
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

        # Test old and new arguments are mutually exclusive
        self.assertRaises(ValueError, self.driver.create_node,
                          name='foo', image=image, size=size,
                          ex_securitygroup=security_groups,
                          ex_security_groups=security_groups)

    def test_create_node_ex_security_group_ids(self):
        EC2MockHttp.type = 'ex_security_group_ids'

        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        subnet = EC2NetworkSubnet(12345, "test_subnet", "pending")
        security_groups = ['sg-1aa11a1a', 'sg-2bb22b2b']

        self.driver.create_node(name='foo', image=image, size=size,
                                ex_security_group_ids=security_groups,
                                ex_subnet=subnet)
        self.assertRaises(ValueError, self.driver.create_node,
                          name='foo', image=image, size=size,
                          ex_security_group_ids=security_groups)

    def test_ex_get_metadata_for_node(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='foo',
                                       image=image,
                                       size=size,
                                       ex_metadata={'Bar': 'baz', 'Num': '42'})

        metadata = self.driver.ex_get_metadata_for_node(node)
        self.assertEqual(metadata['Name'], 'foo')
        self.assertEqual(metadata['Bar'], 'baz')
        self.assertEqual(metadata['Num'], '42')
        self.assertEqual(len(metadata), 3)

    def test_ex_get_limits(self):
        limits = self.driver.ex_get_limits()

        expected = {'max-instances': 20, 'vpc-max-elastic-ips': 5,
                    'max-elastic-ips': 5}
        self.assertEqual(limits['resource'], expected)

    def test_ex_create_security_group(self):
        group = self.driver.ex_create_security_group("WebServers",
                                                     "Rules to protect web nodes",
                                                     "vpc-143cab4")

        self.assertEqual(group["group_id"], "sg-52e2f530")

    def test_ex_create_placement_groups(self):
        resp = self.driver.ex_create_placement_group("NewPG")
        self.assertTrue(resp)

    def test_ex_delete_placement_groups(self):
        pgs = self.driver.ex_list_placement_groups()
        pg = pgs[0]

        resp = self.driver.ex_delete_placement_group(pg.name)
        self.assertTrue(resp)

    def test_ex_list_placement_groups(self):
        pgs = self.driver.ex_list_placement_groups()
        self.assertEqual(len(pgs), 2)
        self.assertIsInstance(pgs[0], EC2PlacementGroup)

    def test_ex_list_networks(self):
        vpcs = self.driver.ex_list_networks()

        self.assertEqual(len(vpcs), 2)

        self.assertEqual('vpc-532335e1', vpcs[0].id)
        self.assertEqual('vpc-532335e1', vpcs[0].name)
        self.assertEqual('192.168.51.0/24', vpcs[0].cidr_block)
        self.assertEqual('available', vpcs[0].extra['state'])
        self.assertEqual('dopt-7eded312', vpcs[0].extra['dhcp_options_id'])

        self.assertEqual('vpc-62ded30e', vpcs[1].id)
        self.assertEqual('Test VPC', vpcs[1].name)
        self.assertEqual('192.168.52.0/24', vpcs[1].cidr_block)
        self.assertEqual('available', vpcs[1].extra['state'])
        self.assertEqual('dopt-7eded312', vpcs[1].extra['dhcp_options_id'])

    def test_ex_list_networks_network_ids(self):
        EC2MockHttp.type = 'network_ids'
        network_ids = ['vpc-532335e1']

        # We assert in the mock http method
        self.driver.ex_list_networks(network_ids=network_ids)

    def test_ex_list_networks_filters(self):
        EC2MockHttp.type = 'filters'

        filters = OrderedDict([
            ('dhcp-options-id', 'dopt-7eded312'),  # matches two networks
            ('cidr', '192.168.51.0/24')  # matches two networks
        ])

        # We assert in the mock http method
        self.driver.ex_list_networks(filters=filters)

    def test_ex_create_network(self):
        vpc = self.driver.ex_create_network('192.168.55.0/24',
                                            name='Test VPC',
                                            instance_tenancy='default')

        self.assertEqual('vpc-ad3527cf', vpc.id)
        self.assertEqual('192.168.55.0/24', vpc.cidr_block)
        self.assertEqual('pending', vpc.extra['state'])

    def test_ex_delete_network(self):
        vpcs = self.driver.ex_list_networks()
        vpc = vpcs[0]

        resp = self.driver.ex_delete_network(vpc)
        self.assertTrue(resp)

    def test_ex_list_subnets(self):
        subnets = self.driver.ex_list_subnets()

        self.assertEqual(len(subnets), 2)

        self.assertEqual('subnet-ce0e7ce5', subnets[0].id)
        self.assertEqual('available', subnets[0].state)
        self.assertEqual(123, subnets[0].extra['available_ips'])

        self.assertEqual('subnet-ce0e7ce6', subnets[1].id)
        self.assertEqual('available', subnets[1].state)
        self.assertEqual(59, subnets[1].extra['available_ips'])

    def test_ex_create_subnet(self):
        subnet = self.driver.ex_create_subnet('vpc-532135d1',
                                              '192.168.51.128/26',
                                              'us-east-1b',
                                              name='Test Subnet')

        self.assertEqual('subnet-ce0e7ce6', subnet.id)
        self.assertEqual('pending', subnet.state)
        self.assertEqual('vpc-532135d1', subnet.extra['vpc_id'])

    def test_ex_modify_subnet_attribute(self):
        subnet = self.driver.ex_list_subnets()[0]
        resp = self.driver.ex_modify_subnet_attribute(subnet,
                                                      'auto_public_ip',
                                                      True)
        self.assertTrue(resp)
        resp = self.driver.ex_modify_subnet_attribute(subnet,
                                                      'auto_ipv6',
                                                      False)
        self.assertTrue(resp)

        expected_msg = 'Unsupported attribute: invalid'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                self.driver.ex_modify_subnet_attribute,
                                subnet,
                                'invalid',
                                True)

    def test_ex_delete_subnet(self):
        subnet = self.driver.ex_list_subnets()[0]
        resp = self.driver.ex_delete_subnet(subnet=subnet)
        self.assertTrue(resp)

    def test_ex_get_console_output(self):
        node = self.driver.list_nodes()[0]
        resp = self.driver.ex_get_console_output(node)
        self.assertEqual('Test String', resp['output'])

    def test_ex_list_network_interfaces(self):
        interfaces = self.driver.ex_list_network_interfaces()

        self.assertEqual(len(interfaces), 2)

        self.assertEqual('eni-18e6c05e', interfaces[0].id)
        self.assertEqual('in-use', interfaces[0].state)
        self.assertEqual('0e:6e:df:72:78:af',
                         interfaces[0].extra['mac_address'])

        self.assertEqual('eni-83e3c5c5', interfaces[1].id)
        self.assertEqual('in-use', interfaces[1].state)
        self.assertEqual('0e:93:0b:e9:e9:c4',
                         interfaces[1].extra['mac_address'])

    def test_ex_create_network_interface(self):
        subnet = self.driver.ex_list_subnets()[0]
        interface = self.driver.ex_create_network_interface(
            subnet,
            name='Test Interface',
            description='My Test')

        self.assertEqual('eni-2b36086d', interface.id)
        self.assertEqual('pending', interface.state)
        self.assertEqual('0e:bd:49:3e:11:74', interface.extra['mac_address'])

    def test_ex_delete_network_interface(self):
        interface = self.driver.ex_list_network_interfaces()[0]
        resp = self.driver.ex_delete_network_interface(interface)
        self.assertTrue(resp)

    def test_ex_attach_network_interface_to_node(self):
        node = self.driver.list_nodes()[0]
        interface = self.driver.ex_list_network_interfaces()[0]
        resp = self.driver.ex_attach_network_interface_to_node(interface,
                                                               node, 1)
        self.assertTrue(resp)

    def test_ex_detach_network_interface(self):
        resp = self.driver.ex_detach_network_interface('eni-attach-2b588b47')
        self.assertTrue(resp)

    def test_ex_list_internet_gateways(self):
        gateways = self.driver.ex_list_internet_gateways()

        self.assertEqual(len(gateways), 2)

        self.assertEqual('igw-84dd3ae1', gateways[0].id)
        self.assertEqual('igw-7fdae215', gateways[1].id)
        self.assertEqual('available', gateways[1].state)
        self.assertEqual('vpc-62cad41e', gateways[1].vpc_id)

    def test_ex_create_internet_gateway(self):
        gateway = self.driver.ex_create_internet_gateway()

        self.assertEqual('igw-13ac2b36', gateway.id)

    def test_ex_delete_internet_gateway(self):
        gateway = self.driver.ex_list_internet_gateways()[0]
        resp = self.driver.ex_delete_internet_gateway(gateway)
        self.assertTrue(resp)

    def test_ex_attach_internet_gateway(self):
        gateway = self.driver.ex_list_internet_gateways()[0]
        network = self.driver.ex_list_networks()[0]
        resp = self.driver.ex_attach_internet_gateway(gateway, network)
        self.assertTrue(resp)

    def test_ex_detach_internet_gateway(self):
        gateway = self.driver.ex_list_internet_gateways()[0]
        network = self.driver.ex_list_networks()[0]
        resp = self.driver.ex_detach_internet_gateway(gateway, network)
        self.assertTrue(resp)

    def test_ex_modify_volume(self):
        volume = self.driver.list_volumes()[0]
        assert volume.id == 'vol-10ae5e2b'

        params = {'VolumeType': 'io1',
                  'Size': 2,
                  'Iops': 1000}
        volume_modification = self.driver.ex_modify_volume(volume, params)

        self.assertIsNone(volume_modification.end_time)
        self.assertEqual('modifying', volume_modification.modification_state)
        self.assertEqual(300, volume_modification.original_iops)
        self.assertEqual(1, volume_modification.original_size)
        self.assertEqual('gp2', volume_modification.original_volume_type)
        self.assertEqual(0, volume_modification.progress)
        self.assertIsNone(volume_modification.status_message)
        self.assertEqual(1000, volume_modification.target_iops)
        self.assertEqual(2, volume_modification.target_size)
        self.assertEqual('io1', volume_modification.target_volume_type)
        self.assertEqual('vol-10ae5e2b', volume_modification.volume_id)

    def test_ex_describe_volumes_modifications(self):
        modifications = self.driver.ex_describe_volumes_modifications()

        self.assertEqual(len(modifications), 2)

        self.assertIsNone(modifications[0].end_time)
        self.assertEqual('optimizing', modifications[0].modification_state)
        self.assertEqual(100, modifications[0].original_iops)
        self.assertEqual(10, modifications[0].original_size)
        self.assertEqual('gp2', modifications[0].original_volume_type)
        self.assertEqual(3, modifications[0].progress)
        self.assertIsNone(modifications[0].status_message)
        self.assertEqual(10000, modifications[0].target_iops)
        self.assertEqual(2000, modifications[0].target_size)
        self.assertEqual('io1', modifications[0].target_volume_type)
        self.assertEqual('vol-06397e7a0eEXAMPLE', modifications[0].volume_id)

        self.assertEqual('completed', modifications[1].modification_state)
        self.assertEqual(100, modifications[1].original_iops)
        self.assertEqual(8, modifications[1].original_size)
        self.assertEqual('gp2', modifications[1].original_volume_type)
        self.assertEqual(100, modifications[1].progress)
        self.assertIsNone(modifications[1].status_message)
        self.assertEqual(10000, modifications[1].target_iops)
        self.assertEqual(200, modifications[1].target_size)
        self.assertEqual('io1', modifications[1].target_volume_type)
        self.assertEqual('vol-bEXAMPLE', modifications[1].volume_id)

    def test_params_is_not_simple_type_exception_is_thrown(self):
        params = {
            'not': {'not': ['simple']}
        }

        expected_msg = 'dictionary contains an attribute "not" which value'
        self.assertRaisesRegexp(ValueError, expected_msg,
                               self.driver.connection.request, '/', params=params)

        params = {
            'invalid': [1, 2, 3]
        }

        expected_msg = 'dictionary contains an attribute "invalid" which value'
        self.assertRaisesRegexp(ValueError, expected_msg,
                               self.driver.connection.request, '/', params=params)


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


class EC2MockHttp(MockHttp):
    fixtures = ComputeFileFixtures('ec2')

    def _DescribeInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeReservedInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_reserved_instances.xml')
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

    def _DeleteSecurityGroup(self, method, url, body, headers):
        body = self.fixtures.load('delete_security_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AuthorizeSecurityGroupIngress(self, method, url, body, headers):
        body = self.fixtures.load('authorize_security_group_ingress.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeImages(self, method, url, body, headers):
        body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RegisterImages(self, method, url, body, headers):
        body = self.fixtures.load('register_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ImportSnapshot(self, method, url, body, headers):
        body = self.fixtures.load('import_snapshot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeImportSnapshotTasks(self, method, url, body, headers):
        body = self.fixtures.load('describe_import_snapshot_tasks.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _timeout_DescribeImportSnapshotTasks(self, method, url, body, headers):
        body = self.fixtures.load('describe_import_snapshot_tasks_active.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ex_imageids_DescribeImages(self, method, url, body, headers):
        body = self.fixtures.load('describe_images_ex_imageids.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _create_ex_assign_public_ip_RunInstances(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {
            'NetworkInterface.1.AssociatePublicIpAddress': "true",
            'NetworkInterface.1.DeleteOnTermination': "true",
            'NetworkInterface.1.DeviceIndex': "0",
            'NetworkInterface.1.SubnetId': "subnet-11111111",
            'NetworkInterface.1.SecurityGroupId.1': "sg-11111111",
        })
        body = self.fixtures.load('run_instances_with_subnet_and_security_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _create_ex_terminate_on_shutdown_RunInstances(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {
            'InstanceInitiatedShutdownBehavior': 'terminate'
        })

        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ex_security_groups_RunInstances(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {'SecurityGroup.1': 'group1'})
        self.assertUrlContainsQueryParams(url, {'SecurityGroup.2': 'group2'})

        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ex_security_group_ids_RunInstances(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {'SecurityGroupId.1': 'sg-1aa11a1a'})
        self.assertUrlContainsQueryParams(url, {'SecurityGroupId.2': 'sg-2bb22b2b'})

        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _create_ex_blockdevicemappings_RunInstances(self, method, url, body, headers):
        expected_params = {
            'BlockDeviceMapping.1.DeviceName': '/dev/sda1',
            'BlockDeviceMapping.1.Ebs.VolumeSize': '10',
            'BlockDeviceMapping.2.DeviceName': '/dev/sdb',
            'BlockDeviceMapping.2.VirtualName': 'ephemeral0',
            'BlockDeviceMapping.3.DeviceName': '/dev/sdc',
            'BlockDeviceMapping.3.VirtualName': 'ephemeral1'
        }
        self.assertUrlContainsQueryParams(url, expected_params)

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

    def _get_one_DescribeKeyPairs(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {'KeyName': 'gsg-keypair'})

        body = self.fixtures.load('describe_key_pairs.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _doesnt_exist_DescribeKeyPairs(self, method, url, body, headers):
        body = self.fixtures.load('describe_key_pairs_doesnt_exist.xml')
        return (httplib.BAD_REQUEST, body, {},
                httplib.responses[httplib.BAD_REQUEST])

    def _CreateKeyPair(self, method, url, body, headers):
        body = self.fixtures.load('create_key_pair.xml')
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

    def _vpc_AllocateAddress(self, method, url, body, headers):
        body = self.fixtures.load('allocate_vpc_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AssociateAddress(self, method, url, body, headers):
        body = self.fixtures.load('associate_address.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _vpc_AssociateAddress(self, method, url, body, headers):
        body = self.fixtures.load('associate_vpc_address.xml')
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

    def _ModifySnapshotAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_snapshot_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateVolume(self, method, url, body, headers):
        if 'KmsKeyId=' in url:
            assert 'Encrypted=1' in url, "If a KmsKeyId is specified, the " \
                                         "Encrypted flag must also be set."
        if 'Encrypted=1' in url:
            body = self.fixtures.load('create_encrypted_volume.xml')
        else:
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

    def _filters_nodes_DescribeVolumes(self, method, url, body, headers):
        expected_params = {
            'Filter.1.Name': 'attachment.instance-id',
            'Filter.1.Value.1': 'i-d334b4b3',
        }

        self.assertUrlContainsQueryParams(url, expected_params)

        body = self.fixtures.load('describe_volumes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _filters_status_DescribeVolumes(self, method, url, body, headers):
        expected_params = {
            'Filter.1.Name': 'status',
            'Filter.1.Value.1': 'available'
        }

        self.assertUrlContainsQueryParams(url, expected_params)

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

    def _CopyImage(self, method, url, body, headers):
        body = self.fixtures.load('copy_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateImage(self, method, url, body, headers):
        body = self.fixtures.load('create_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeregisterImage(self, method, url, body, headers):
        body = self.fixtures.load('deregister_image.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteKeyPair(self, method, url, body, headers):
        self.assertUrlContainsQueryParams(url, {'KeyName': 'gsg-keypair'})

        body = self.fixtures.load('delete_key_pair.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyImageAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_image_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAccountAttributes(self, method, url, body, headers):
        body = self.fixtures.load('describe_account_attributes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateSecurityGroup(self, method, url, body, headers):
        body = self.fixtures.load('create_security_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeVpcs(self, method, url, body, headers):
        body = self.fixtures.load('describe_vpcs.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _network_ids_DescribeVpcs(self, method, url, body, headers):
        expected_params = {
            'VpcId.1': 'vpc-532335e1'
        }
        self.assertUrlContainsQueryParams(url, expected_params)

        body = self.fixtures.load('describe_vpcs.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _filters_DescribeVpcs(self, method, url, body, headers):
        expected_params = {
            'Filter.1.Name': 'dhcp-options-id',
            'Filter.1.Value.1': 'dopt-7eded312',
            'Filter.2.Name': 'cidr',
            'Filter.2.Value.1': '192.168.51.0/24'
        }

        self.assertUrlContainsQueryParams(url, expected_params)

        body = self.fixtures.load('describe_vpcs.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateVpc(self, method, url, body, headers):
        body = self.fixtures.load('create_vpc.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteVpc(self, method, url, body, headers):
        body = self.fixtures.load('delete_vpc.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeSubnets(self, method, url, body, headers):
        body = self.fixtures.load('describe_subnets.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateSubnet(self, method, url, body, headers):
        body = self.fixtures.load('create_subnet.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifySubnetAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_subnet_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteSubnet(self, method, url, body, headers):
        body = self.fixtures.load('delete_subnet.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _GetConsoleOutput(self, method, url, body, headers):
        body = self.fixtures.load('get_console_output.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeNetworkInterfaces(self, method, url, body, headers):
        body = self.fixtures.load('describe_network_interfaces.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateNetworkInterface(self, method, url, body, headers):
        body = self.fixtures.load('create_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteNetworkInterface(self, method, url, body, headers):
        body = self.fixtures.load('delete_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AttachNetworkInterface(self, method, url, body, headers):
        body = self.fixtures.load('attach_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DetachNetworkInterface(self, method, url, body, headers):
        body = self.fixtures.load('detach_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeInternetGateways(self, method, url, body, headers):
        body = self.fixtures.load('describe_internet_gateways.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateInternetGateway(self, method, url, body, headers):
        body = self.fixtures.load('create_internet_gateway.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteInternetGateway(self, method, url, body, headers):
        body = self.fixtures.load('delete_internet_gateway.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _AttachInternetGateway(self, method, url, body, headers):
        body = self.fixtures.load('attach_internet_gateway.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DetachInternetGateway(self, method, url, body, headers):
        body = self.fixtures.load('detach_internet_gateway.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreatePlacementGroup(self, method, url, body, headers):
        body = self.fixtures.load('create_placement_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeletePlacementGroup(self, method, url, body, headers):
        body = self.fixtures.load('delete_placement_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribePlacementGroups(self, method, url, body, headers):
        body = self.fixtures.load('describe_placement_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyVolume(self, method, url, body, headers):
        body = self.fixtures.load('modify_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeVolumesModifications(self, method, url, body, headers):
        body = self.fixtures.load('describe_volumes_modifications.xml')
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

    def _services_Eucalyptus_DescribeInstanceTypes(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('describe_instance_types.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class NimbusTests(EC2Tests):

    def setUp(self):
        NimbusNodeDriver.connectionCls.conn_class = EC2MockHttp
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
        self.assertEqual(public_ips[0], '1.2.3.4')
        self.assertEqual(node.extra['tags'], {})

        node = self.driver.list_nodes()[1]
        self.assertExecutedMethodCount(0)
        public_ips = node.public_ips
        self.assertEqual(node.id, 'i-8474834a')
        self.assertEqual(len(node.public_ips), 1)
        self.assertEqual(public_ips[0], '1.2.3.5')
        self.assertEqual(node.extra['tags'],
                         {'Name': 'Test Server 2', 'Group': 'VPC Test'})

    def test_ex_create_tags(self):
        # Nimbus doesn't support creating tags so this one should be a
        # passthrough
        node = self.driver.list_nodes()[0]
        self.driver.ex_create_tags(resource=node, tags={'foo': 'bar'})
        self.assertExecutedMethodCount(0)

    def test_create_volume_snapshot_with_tags(self):
        vol = StorageVolume(id='vol-4282672b', name='test',
                            state=StorageVolumeState.AVAILABLE,
                            size=10, driver=self.driver)
        snap = self.driver.create_volume_snapshot(
            vol, 'Test snapshot', ex_metadata={'my_tag': 'test'})
        self.assertDictEqual({}, snap.extra['tags'])


class EucTests(LibcloudTestCase, TestCaseMixin):

    def setUp(self):
        EucNodeDriver.connectionCls.conn_class = EucMockHttp
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EucNodeDriver(key=EC2_PARAMS[0], secret=EC2_PARAMS[1],
                                    host='some.eucalyptus.com', api_version='3.4.1')

    def test_list_locations_response(self):
        try:
            self.driver.list_locations()
        except Exception:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_list_location(self):
        pass

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        ids = [s.id for s in sizes]
        self.assertEqual(len(ids), 18)
        self.assertTrue('t1.micro' in ids)
        self.assertTrue('m1.medium' in ids)
        self.assertTrue('m3.xlarge' in ids)


class OutscaleTests(EC2Tests):

    def setUp(self):
        OutscaleSASNodeDriver.connectionCls.conn_class = EC2MockHttp
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = OutscaleSASNodeDriver(key=EC2_PARAMS[0],
                                            secret=EC2_PARAMS[1],
                                            host='some.outscalecloud.com')

    def test_ex_create_network(self):
        # overridden from EC2Tests -- Outscale don't support instance_tenancy
        vpc = self.driver.ex_create_network('192.168.55.0/24',
                                            name='Test VPC')

        self.assertEqual('vpc-ad3527cf', vpc.id)
        self.assertEqual('192.168.55.0/24', vpc.cidr_block)
        self.assertEqual('pending', vpc.extra['state'])

    def test_ex_copy_image(self):
        # overridden from EC2Tests -- Outscale does not support copying images
        image = self.driver.list_images()[0]
        try:
            self.driver.ex_copy_image('us-east-1', image,
                                      name='Faux Image',
                                      description='Test Image Copy')
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_get_limits(self):
        # overridden from EC2Tests -- Outscale does not support getting limits
        try:
            self.driver.ex_get_limits()
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_create_network_interface(self):
        # overridden from EC2Tests -- Outscale don't allow creating interfaces
        subnet = self.driver.ex_list_subnets()[0]
        try:
            self.driver.ex_create_network_interface(
                subnet,
                name='Test Interface',
                description='My Test')
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_delete_network_interface(self):
        # overridden from EC2Tests -- Outscale don't allow deleting interfaces
        interface = self.driver.ex_list_network_interfaces()[0]
        try:
            self.driver.ex_delete_network_interface(interface)
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_attach_network_interface_to_node(self):
        # overridden from EC2Tests -- Outscale don't allow attaching interfaces
        node = self.driver.list_nodes()[0]
        interface = self.driver.ex_list_network_interfaces()[0]
        try:
            self.driver.ex_attach_network_interface_to_node(interface, node, 1)
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_detach_network_interface(self):
        # overridden from EC2Tests -- Outscale don't allow detaching interfaces
        try:
            self.driver.ex_detach_network_interface('eni-attach-2b588b47')
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()

        ids = [s.id for s in sizes]
        self.assertTrue('m1.small' in ids)
        self.assertTrue('m1.large' in ids)
        self.assertTrue('m1.xlarge' in ids)

    def test_ex_create_node_with_ex_iam_profile(self):
        image = NodeImage(id='ami-be3adfd7',
                          name=self.image_name,
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None,
                        driver=self.driver)

        self.assertRaises(NotImplementedError, self.driver.create_node,
                          name='foo',
                          image=image, size=size,
                          ex_iamprofile='foo')


class FCUMockHttp(EC2MockHttp):
    fixtures = ComputeFileFixtures('fcu')

    def _DescribeQuotas(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_quotas.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeProductTypes(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_product_types.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeInstanceTypes(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_instance_types.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _GetProductType(self, method, url, body, headers):
        body = self.fixtures.load('ex_get_product_type.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyInstanceKeypair(self, method, url, body, headers):
        body = self.fixtures.load('ex_modify_instance_keypair.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class OutscaleFCUTests(LibcloudTestCase):

    def setUp(self):
        OutscaleSASNodeDriver.connectionCls.conn_class = FCUMockHttp
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = OutscaleSASNodeDriver(key=EC2_PARAMS[0],
                                            secret=EC2_PARAMS[1],
                                            host='some.fcucloud.com')

    def test_ex_describe_quotas(self):
        is_truncated, quota = self.driver.ex_describe_quotas()
        self.assertTrue(is_truncated == 'true')
        self.assertTrue('global' in quota.keys())
        self.assertTrue('vpc-00000000' in quota.keys())

    def test_ex_describe_product_types(self):
        product_types = self.driver.ex_describe_product_types()
        pt = {}
        for e in product_types:
            pt[e['productTypeId']] = e['description']
        self.assertTrue('0001' in pt.keys())
        self.assertTrue('MapR' in pt.values())
        self.assertTrue(pt['0002'] == 'Windows')

    def test_ex_describe_instance_instance_types(self):
        instance_types = self.driver.ex_describe_instance_types()
        it = {}
        for e in instance_types:
            it[e['name']] = e['memory']
        self.assertTrue('og4.4xlarge' in it.keys())
        self.assertTrue('oc2.8xlarge' in it.keys())
        self.assertTrue('68718428160' in it.values())
        self.assertTrue(it['m3.large'] == '8050966528')

    def test_ex_get_product_type(self):
        product_type = self.driver.ex_get_product_type('ami-29ab9e54')
        self.assertTrue(product_type['productTypeId'] == '0002')
        self.assertTrue(product_type['description'] == 'Windows')

    def test_ex_modify_instance_keypair(self):
        r = self.driver.ex_modify_instance_keypair('i-57292bc5', 'key_name')
        self.assertTrue(r)


if __name__ == '__main__':
    sys.exit(unittest.main())
