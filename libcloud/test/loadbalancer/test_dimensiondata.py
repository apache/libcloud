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

from libcloud.common.types import InvalidCredsError
from libcloud.loadbalancer.base import LoadBalancer
from libcloud.loadbalancer.drivers.dimensiondata import DimensionDataLBDriver as DimensionData
from libcloud.loadbalancer.types import State
from libcloud.common.dimensiondata import DimensionDataAPIException

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import LoadBalancerFileFixtures

from libcloud.test.secrets import DIMENSIONDATA_PARAMS


class DimensionDataTests(unittest.TestCase):

    def setUp(self):
        DimensionData.connectionCls.conn_classes = (None, DimensionDataMockHttp)
        DimensionDataMockHttp.type = None
        self.driver = DimensionData(*DIMENSIONDATA_PARAMS)

    def test_invalid_creds(self):
        DimensionDataMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_balancers()
            self.assertTrue(
                False)  # Above command should have thrown an InvalidCredsException
        except InvalidCredsError:
            pass

    def test_list_balancers(self):
        bal = self.driver.list_balancers()
        self.assertEqual(bal[0].name, 'myProduction.Virtual.Listener')
        self.assertEqual(bal[0].id, '6115469d-a8bb-445b-bb23-d23b5283f2b9')
        self.assertEqual(bal[0].port, '8899')
        self.assertEqual(bal[0].ip, '165.180.12.22')
        self.assertEqual(bal[0].state, State.RUNNING)

    def test_balancer_list_members(self):
        extra={}
        extra['pool_id']='4d360b1f-bc2c-4ab7-9884-1f03ba2768f7'
        balancer = LoadBalancer(
            id='234',
            name='test',
            state=State.RUNNING,
            ip='1.2.3.4',
            port=1234,
            driver=self.driver,
            extra=extra
        )
        members = self.driver.balancer_list_members(balancer)
        self.assertEqual(2, len(members))
        self.assertEqual(members[0].ip, '10.0.3.13')
        self.assertEqual(members[0].id, '3dd806a2-c2c8-4c0c-9a4f-5219ea9266c0')
        self.assertEqual(members[0].port, 9889)

    def test_get_balancer(self):
        bal = self.driver.get_balancer('6115469d-a8bb-445b-bb23-d23b5283f2b9')
        self.assertEqual(bal.name, 'myProduction.Virtual.Listener')
        self.assertEqual(bal.id, '6115469d-a8bb-445b-bb23-d23b5283f2b9')
        self.assertEqual(bal.port, '8899')
        self.assertEqual(bal.ip, '165.180.12.22')
        self.assertEqual(bal.state, State.RUNNING)

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()
        self.assertNotEqual(0, len(protocols))
    
    def test_get_pools(self):
        pools = self.driver.ex_get_pools()
        self.assertNotEqual(0, len(pools))
        self.assertEqual(pools[0].name, 'myDevelopmentPool.1')
        self.assertEqual(pools[0].id, '4d360b1f-bc2c-4ab7-9884-1f03ba2768f7')
        
    def test_get_pool(self):
        pool = self.driver.ex_get_pool('4d360b1f-bc2c-4ab7-9884-1f03ba2768f7')
        self.assertEqual(pool.name, 'myDevelopmentPool.1')
        self.assertEqual(pool.id, '4d360b1f-bc2c-4ab7-9884-1f03ba2768f7')

    def test_get_pool_members(self):
        members = self.driver.ex_get_pool_members('4d360b1f-bc2c-4ab7-9884-1f03ba2768f7')
        self.assertEqual(2, len(members))
        self.assertEqual(members[0].id, '3dd806a2-c2c8-4c0c-9a4f-5219ea9266c0')
        self.assertEqual(members[0].name, '10.0.3.13')
        self.assertEqual(members[0].status, 'NORMAL')
        self.assertEqual(members[0].ip_address, '10.0.3.13')
        self.assertEqual(members[0].port, 9889)
    
    def test_get_pool_member(self):
        member = self.driver.ex_get_pool_member('3dd806a2-c2c8-4c0c-9a4f-5219ea9266c0')
        self.assertEqual(member.id, '3dd806a2-c2c8-4c0c-9a4f-5219ea9266c0')
        self.assertEqual(member.name, '10.0.3.13')
        self.assertEqual(member.status, 'NORMAL')
        self.assertEqual(member.ip_address, '10.0.3.13')
        self.assertEqual(member.port, 9889)

class DimensionDataMockHttp(MockHttp):

    fixtures = LoadBalancerFileFixtures('dimensiondata')

    def _oec_0_9_myaccount_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_virtualListener(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_virtualListener.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_virtualListener_6115469d_a8bb_445b_bb23_d23b5283f2b9(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_virtualListener_6115469d_a8bb_445b_bb23_d23b5283f2b9.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_pool(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_pool.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_pool_4d360b1f_bc2c_4ab7_9884_1f03ba2768f7(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_pool_4d360b1f_bc2c_4ab7_9884_1f03ba2768f7.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    
    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_poolMember(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_poolMember.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_poolMember_3dd806a2_c2c8_4c0c_9a4f_5219ea9266c0(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_0_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkDomainVip_poolMember_3dd806a2_c2c8_4c0c_9a4f_5219ea9266c0.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
