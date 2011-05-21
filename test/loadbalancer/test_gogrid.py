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

import httplib
import sys
import unittest
from urlparse import urlparse, parse_qsl

from libcloud.common.types import LibcloudError
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.gogrid import GoGridLBDriver

from test import MockHttpTestCase
from test.file_fixtures import LoadBalancerFileFixtures

class GoGridTests(unittest.TestCase):

    def setUp(self):
        GoGridLBDriver.connectionCls.conn_classes = (None,
                GoGridLBMockHttp)
        GoGridLBMockHttp.type = None
        self.driver = GoGridLBDriver('user', 'key')

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()

        self.assertEqual(len(protocols), 1)
        self.assertEqual(protocols[0], 'http')

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEquals(len(balancers), 2)
        self.assertEquals(balancers[0].name, "foo")
        self.assertEquals(balancers[0].id, "23517")
        self.assertEquals(balancers[1].name, "bar")
        self.assertEquals(balancers[1].id, "23526")

    def test_create_balancer(self):
        balancer = self.driver.create_balancer(name='test2',
                port=80,
                protocol='http',
                algorithm=Algorithm.ROUND_ROBIN,
                members=(Member(None, '10.1.0.10', 80),
                    Member(None, '10.1.0.11', 80))
                )

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '123')

    def test_create_balancer_UNEXPECTED_ERROR(self):
        # Try to create new balancer and attach members with an IP address which
        # does not belong to this account
        GoGridLBMockHttp.type = 'UNEXPECTED_ERROR'

        try:
            self.driver.create_balancer(name='test2',
                    port=80,
                    protocol='http',
                    algorithm=Algorithm.ROUND_ROBIN,
                    members=(Member(None, '10.1.0.10', 80),
                             Member(None, '10.1.0.11', 80))
                    )
        except LibcloudError, e:
            self.assertTrue(str(e).find('tried to add a member with an IP address not assigned to your account') != -1)
        else:
            self.fail('Exception was not thrown')

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]

        ret = self.driver.destroy_balancer(balancer)
        self.assertTrue(ret)

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='23530')

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '23530')

    def test_balancer_list_members(self):
        balancer = self.driver.get_balancer(balancer_id='23530')
        members = balancer.list_members()

        expected_members = set([u'10.0.0.78:80', u'10.0.0.77:80',
            u'10.0.0.76:80'])

        self.assertEquals(len(members), 3)
        self.assertEquals(expected_members,
                set(["%s:%s" % (member.ip, member.port) for member in members]))

    def test_balancer_attach_member(self):
        balancer = LoadBalancer(23530, None, None, None, None, None)
        member = self.driver.balancer_attach_member(balancer,
                    Member(None, ip='10.0.0.75', port='80'))

        self.assertEquals(member.ip, '10.0.0.75')
        self.assertEquals(member.port, 80)

    def test_balancer_detach_member(self):
        balancer = LoadBalancer(23530, None, None, None, None, None)
        member = self.driver.balancer_list_members(balancer)[0]

        ret = self.driver.balancer_detach_member(balancer, member)

        self.assertTrue(ret)

class GoGridLBMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('gogrid')

    def _api_grid_loadbalancer_list(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_add(self, method, url, body, headers):
        qs = dict(parse_qsl(urlparse(url).query))
        self.assertEqual(qs['loadbalancer.type'], 'round robin')

        body = self.fixtures.load('loadbalancer_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list_UNEXPECTED_ERROR(self, method, url, body, headers):
        return self._api_grid_ip_list(method, url, body, headers)

    def _api_grid_loadbalancer_add_UNEXPECTED_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('unexpected_error.json')
        return (httplib.INTERNAL_SERVER_ERROR, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_delete(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_get(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_edit(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_edit.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
