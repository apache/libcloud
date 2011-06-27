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
import httplib

from libcloud.compute.drivers.ec2 import EC2NodeDriver, EC2APSENodeDriver
from libcloud.compute.drivers.ec2 import NimbusNodeDriver
from libcloud.compute.drivers.ec2 import EC2APNENodeDriver, IdempotentParamError
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp, LibcloudTestCase
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(LibcloudTestCase, TestCaseMixin):

    def setUp(self):
        EC2MockHttp.test = self
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2NodeDriver(EC2_ACCESS_ID, EC2_SECRET)

    def test_create_node(self):
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        self.assertEqual(node.id, 'i-2ba64342')
        self.assertEqual(node.name, 'foo')
        self.assertEqual(node.extra['tags']['Name'], 'foo')
        self.assertEqual(len(node.extra['tags']), 1)

    def test_create_node_idempotent(self):
        EC2MockHttp.type = 'idempotent'
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
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
        try:
            self.driver.create_node(name='foo', image=image, size=size,
                    ex_mincount='2', ex_maxcount='2', # different count
                    ex_clienttoken=token)
        except IdempotentParamError, e:
            idem_error = e
        self.assertTrue(idem_error is not None)

    def test_create_node_no_availability_zone(self):
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
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
        public_ips = sorted(node.public_ip)
        self.assertEqual(node.id, 'i-4382922a')
        self.assertEqual(node.name, node.id)
        self.assertEqual(len(node.public_ip), 2)

        self.assertEqual(public_ips[0], '1.2.3.4')
        self.assertEqual(public_ips[1], '1.2.3.5')

    def test_list_nodes_with_name_tag(self):
        EC2MockHttp.type = 'WITH_TAGS'
        node = self.driver.list_nodes()[0]
        public_ips = sorted(node.public_ip)
        self.assertEqual(node.id, 'i-8474834a')
        self.assertEqual(node.name, 'foobar1')

    def test_list_location(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) > 0)
        self.assertTrue(locations[0].availability_zone != None)

    def test_reboot_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        region_old = self.driver.region_name

        names = [ ('ec2_us_east', 'us-east-1'),
                  ('ec2_us_west', 'us-west-1'),
                  ('ec2_eu_west', 'eu-west-1'),
                  ('ec2_ap_southeast', 'ap-southeast-1'),
                  ('ec2_ap_northeast', 'ap-northeast-1')
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
                self.assertEqual(len(sizes), 11)
                self.assertTrue('cg1.4xlarge' in ids)
                self.assertTrue('cc1.4xlarge' in ids)
            else:
                self.assertEqual(len(sizes), 9)

        self.driver.region_name = region_old

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 1)
        self.assertEqual(image.name, 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml')
        self.assertEqual(image.id, 'ami-be3adfd7')

    def test_ex_list_availability_zones(self):
        availability_zones = self.driver.ex_list_availability_zones()
        availability_zone = availability_zones[0]
        self.assertTrue(len(availability_zones) > 0)
        self.assertEqual(availability_zone.name, 'eu-west-1a')
        self.assertEqual(availability_zone.zone_state, 'available')
        self.assertEqual(availability_zone.region_name, 'eu-west-1')

    def test_ex_describe_tags(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        tags = self.driver.ex_describe_tags(node)

        self.assertEqual(len(tags), 3)
        self.assertTrue('tag' in tags)
        self.assertTrue('owner' in tags)
        self.assertTrue('stack' in tags)

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
        ip_addresses2 = sorted(self.driver.ex_describe_addresses_for_node(node2))
        node3 = Node('i-4382922g', None, None, None, None, self.driver)
        ip_addresses3 = sorted(self.driver.ex_describe_addresses_for_node(node3))

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

    def test_ex_change_node_size_same_size(self):
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
        node = Node('i-4382922a', None, None, None, None, self.driver,
                    extra={'instancetype': 'm1.small'})

        try:
            self.driver.ex_change_node_size(node=node, new_size=size)
        except ValueError:
            pass
        else:
            self.fail('Same size was passed, but an exception was not thrown')

    def test_ex_change_node_size(self):
        size = NodeSize('m1.large', 'Small Instance', None, None, None, None, driver=self.driver)
        node = Node('i-4382922a', None, None, None, None, self.driver,
                    extra={'instancetype': 'm1.small'})

        result = self.driver.ex_change_node_size(node=node, new_size=size)
        self.assertTrue(result)

class EC2MockHttp(MockHttp):

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

    def _DescribeImages(self, method, url, body, headers):
        body = self.fixtures.load('describe_images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_mismatch_RunInstances(self, method, url, body, headers):
        body = self.fixtures.load('run_instances_idem_mismatch.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.BAD_REQUEST])

    def _TerminateInstances(self, method, url, body, headers):
        body = self.fixtures.load('terminate_instances.xml')
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

    def _WITH_TAGS_DescribeAddresses(self, method, url, body, headers):
        body = self.fixtures.load('describe_addresses_multi.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _ModifyInstanceAttribute(self, method, url, body, headers):
        body = self.fixtures.load('modify_instance_attribute.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _idempotent_CreateTags(self, method, url, body, headers):
        body = self.fixtures.load('create_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

class EC2APSETests(EC2Tests):
    def setUp(self):
        EC2APSENodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2APSENodeDriver(EC2_ACCESS_ID, EC2_SECRET)

class EC2APNETests(EC2Tests):
    def setUp(self):
        EC2APNENodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = EC2APNENodeDriver(EC2_ACCESS_ID, EC2_SECRET)

class NimbusTests(EC2Tests):
    def setUp(self):
        NimbusNodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None
        self.driver = NimbusNodeDriver(EC2_ACCESS_ID, EC2_SECRET,
                host="some.nimbuscloud.com")

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
        public_ips = node.public_ip
        self.assertEqual(node.id, 'i-4382922a')
        self.assertEqual(len(node.public_ip), 1)
        self.assertEqual(public_ips[0], '1.2.3.5')
        self.assertEqual(node.extra['tags'], {})

        node = self.driver.list_nodes()[1]
        self.assertExecutedMethodCount(0)
        public_ips = node.public_ip
        self.assertEqual(node.id, 'i-8474834a')
        self.assertEqual(len(node.public_ip), 1)
        self.assertEqual(public_ips[0], '1.2.3.5')
        self.assertEqual(node.extra['tags'], {'user_key0': 'user_val0', 'user_key1': 'user_val1'})

    def test_ex_create_tags(self):
       # Nimbus doesn't support creating tags so this one should be a
       # passthrough
       node = self.driver.list_nodes()[0]
       self.driver.ex_create_tags(node=node, tags={'foo': 'bar'})
       self.assertExecutedMethodCount(0)

if __name__ == '__main__':
    sys.exit(unittest.main())
