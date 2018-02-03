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

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import xmlrpclib

from libcloud.compute.base import NodeLocation
from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.drivers.softlayer import SoftlayerLBDriver
from libcloud.loadbalancer.types import State

from libcloud.test import MockHttp
from libcloud.test.secrets import SOFTLAYER_PARAMS
from libcloud.test.file_fixtures import LoadBalancerFileFixtures


class SoftlayerLBTests(unittest.TestCase):
    def setUp(self):

        SoftlayerLBDriver.connectionCls.conn_class = SoftLayerMockHttp
        SoftLayerMockHttp.type = None

        self.driver = SoftlayerLBDriver(*SOFTLAYER_PARAMS)

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()

        self.assertEqual(len(protocols), 6)
        self.assertTrue('tcp' in protocols)
        self.assertTrue('http' in protocols)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEqual(len(balancers), 2)
        self.assertEqual(balancers[0].id, '76185')
        self.assertEqual(balancers[0].extra['datacenter'], 'dal05')
        self.assertEqual(balancers[0].extra['connection_limit'], 50)
        self.assertEqual(balancers[1].id, '76265')
        self.assertEqual(balancers[1].extra['datacenter'], 'par01')
        self.assertEqual(balancers[1].extra['connection_limit'], 50)

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='76185')

        self.assertEqual(balancer.id, '76185')
        self.assertEqual(balancer.state, State.UNKNOWN)
        self.assertEqual(balancer.extra['datacenter'], 'dal05')
        self.assertEqual(balancer.extra['protocol'], 'http')
        self.assertEqual(balancer.extra['algorithm'], Algorithm.ROUND_ROBIN)

    def test_balancer_list_members(self):
        balancer = self.driver.get_balancer(balancer_id='76185')
        members = balancer.list_members()

        self.assertEqual(len(members), 3)
        self.assertEqual(members[0].balancer, balancer)
        self.assertEqual(members[0].id, '226227')
        self.assertEqual(members[0].ip, '10.126.5.34')
        self.assertEqual(members[1].balancer, balancer)
        self.assertEqual(members[1].id, '226229')
        self.assertEqual(members[1].ip, '10.126.5.35')

    def test_balancer_attach_member(self):
        balancer = self.driver.get_balancer(balancer_id='76185')
        member = balancer.attach_member(Member(None, ip='10.126.5.34',
                                               port=8000))

        self.assertEqual(member.id, '226227')
        self.assertEqual(member.ip, '10.126.5.34')
        self.assertEqual(member.port, 8000)

    def test_balancer_detach_member(self):
        balancer = self.driver.get_balancer(balancer_id='76265')
        member = Member('226227', None, None)

        self.assertTrue(balancer.detach_member(member))

    def test_destroy_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='76185')

        self.assertTrue(self.driver.destroy_balancer(balancer))

    def test_ex_list_balancer_packages(self):
        packages = self.driver.ex_list_balancer_packages()
        self.assertEqual(len(packages), 9)

    def test_ex_place_balancer_order(self):
        packages = self.driver.ex_list_balancer_packages()
        lb_package = [p for p in packages if p.capacity == 50][0]

        self.assertTrue(self.driver.ex_place_balancer_order(
            lb_package, NodeLocation('dal05', None, None, None)))


class SoftLayerMockHttp(MockHttp):
    fixtures = LoadBalancerFileFixtures('softlayer')

    def _get_method_name(self, type, use_param, qs, path):
        return "_xmlrpc"

    def _xmlrpc(self, method, url, body, headers):
        params, meth_name = xmlrpclib.loads(body)
        url = url.replace("/", "_")
        meth_name = "%s_%s" % (url, meth_name)
        return getattr(self, meth_name)(method, url, body, headers)

    def _xmlrpc_v3_SoftLayer_Account_getAdcLoadBalancers(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Account_getAdcLoadBalancers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Billing_Item_cancelService(self, method, url,
                                                        body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Billing_Item_cancelService.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Location_Datacenter_getDatacenters(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Location_Datacenter_getDatacenters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Network_Application_Delivery_Controller_LoadBalancer_Service_deleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Network_Application_Delivery_Controller_'
            'LoadBalancer_Service_deleteObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Network_Application_Delivery_Controller_LoadBalancer_VirtualIpAddress_editObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Network_Application_Delivery_Controller_'
            'LoadBalancer_VirtualIpAddress_editObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Network_Application_Delivery_Controller_LoadBalancer_VirtualIpAddress_getBillingItem(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Network_Application_Delivery_Controller_'
            'LoadBalancer_VirtualIpAddress_getBillingItem.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Network_Application_Delivery_Controller_LoadBalancer_VirtualIpAddress_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Network_Application_Delivery_Controller_'
            'LoadBalancer_VirtualIpAddress_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Network_Subnet_IpAddress_getByIpAddress(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Network_Subnet_IpAddress_getByIpAddress.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Product_Order_placeOrder(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Product_Order_placeOrder.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Product_Package_getItems(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Product_Package_getItems.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
