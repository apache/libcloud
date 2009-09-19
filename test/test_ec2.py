# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
import unittest

from libcloud.drivers.ec2 import EC2NodeDriver
from libcloud.base import Node

from test import MockHttp

import httplib

from secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase):

    def setUp(self):
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        self.driver = EC2NodeDriver(EC2_ACCESS_ID, EC2_SECRET)

    def test_list_nodes(self):
        EC2MockHttp.type = 'describe_instances'
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, 'i-4382922a')

    def test_reboot_node(self):
        EC2MockHttp.type = 'reboot_instances'
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        EC2MockHttp.type = 'terminate_instances'
        node = Node('i-4382922a', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 5)
        self.assertEqual(sizes[0].id, 'm1.small')

class EC2MockHttp(MockHttp):
    def _describe_instances(self, method, url, body, headers):
        body = """<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2009-04-04/">
    <requestId>56d0fffa-8819-4658-bdd7-548f143a86d2</requestId>
    <reservationSet>
        <item>
            <reservationId>r-07adf66e</reservationId>
            <ownerId>822272953071</ownerId>
            <groupSet>
                <item>
                    <groupId>default</groupId>
                </item>
            </groupSet>
            <instancesSet>
                <item>
                    <instanceId>i-4382922a</instanceId>
                    <imageId>ami-0d57b264</imageId>
                    <instanceState>
                        <code>0</code>
                        <name>pending</name>
                    </instanceState>
                    <privateDnsName/>
                    <dnsName/>
                    <reason/>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>m1.small</instanceType>
                    <launchTime>2009-08-07T05:47:04.000Z</launchTime>
                    <placement>
                        <availabilityZone>us-east-1a</availabilityZone>
                    </placement>
                    <monitoring>
                        <state>disabled</state>
                    </monitoring>
                </item>
            </instancesSet>
        </item>
    </reservationSet>
</DescribeInstancesResponse>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _reboot_instances(self, method, url, body, headers):
        body = """<RebootInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2009-04-04/">
    <requestId>76dabb7a-fb39-4ed1-b5e0-31a4a0fdf5c0</requestId>
    <return>true</return>
</RebootInstancesResponse>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _terminate_instances(self, method, url, body, headers):
        body = """<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2009-04-04/">
    <requestId>fa63083d-e0f7-4933-b31a-f266643bdee8</requestId>
    <instancesSet>
        <item>
            <instanceId>i-4382922a</instanceId>
            <shutdownState>
                <code>32</code>
                <name>shutting-down</name>
            </shutdownState>
            <previousState>
                <code>16</code>
                <name>running</name>
            </previousState>
        </item>
    </instancesSet>
</TerminateInstancesResponse>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
