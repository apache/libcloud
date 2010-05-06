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

from libcloud.drivers.ec2 import EC2NodeDriver, EC2APSENodeDriver
from libcloud.base import Node, NodeImage, NodeSize

from test import MockHttp, TestCaseMixin
from test.file_fixtures import FileFixtures

import httplib

from secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        self.driver = EC2NodeDriver(EC2_ACCESS_ID, EC2_SECRET)

    def test_create_node(self):
        image = NodeImage(id='ami-be3adfd7',
                          name='ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml',
                          driver=self.driver)
        size = NodeSize('m1.small', 'Small Instance', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='foo', image=image, size=size)
        self.assertEqual(node.id, 'i-2ba64342')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, 'i-4382922a')

    def test_reboot_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 8)

        ids = [s.id for s in sizes]
        self.assertTrue('m1.small' in ids)
        self.assertTrue('m1.large' in ids)
        self.assertTrue('m1.xlarge' in ids)
        self.assertTrue('c1.medium' in ids)
        self.assertTrue('c1.xlarge' in ids)
        self.assertTrue('m2.xlarge' in ids)
        self.assertTrue('m2.2xlarge' in ids)
        self.assertTrue('m2.4xlarge' in ids)

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 1)
        self.assertEqual(image.name, 'ec2-public-images/fedora-8-i386-base-v1.04.manifest.xml')
        self.assertEqual(image.id, 'ami-be3adfd7')

class EC2MockHttp(MockHttp):

    fixtures = FileFixtures('ec2')

    def _DescribeInstances(self, method, url, body, headers):
        body = self.fixtures.load('describe_instances.xml')
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

    def _TerminateInstances(self, method, url, body, headers):
        body = self.fixtures.load('terminate_instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

class EC2APSETests(EC2Tests):
    def setUp(self):
        EC2APSENodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        self.driver = EC2APSENodeDriver(EC2_ACCESS_ID, EC2_SECRET)

if __name__ == '__main__':
    sys.exit(unittest.main())
