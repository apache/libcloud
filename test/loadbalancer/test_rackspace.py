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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.drivers.rackspace import RackspaceLBDriver
from libcloud.loadbalancer.drivers.rackspace import RackspaceUKLBDriver

from test import MockHttpTestCase
from test.file_fixtures import LoadBalancerFileFixtures, OpenStackFixtures

class RackspaceLBTests(unittest.TestCase):

    def setUp(self):
        RackspaceLBDriver.connectionCls.conn_classes = (None,
                RackspaceLBMockHttp)
        RackspaceLBMockHttp.type = None
        self.driver = RackspaceLBDriver('user', 'key')

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()

        self.assertEqual(len(protocols), 10)
        self.assertTrue('http' in protocols)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEquals(len(balancers), 2)
        self.assertEquals(balancers[0].name, "test0")
        self.assertEquals(balancers[0].id, "8155")
        self.assertEquals(balancers[1].name, "test1")
        self.assertEquals(balancers[1].id, "8156")

    def test_create_balancer(self):
        balancer = self.driver.create_balancer(name='test2',
                port=80,
                algorithm=Algorithm.ROUND_ROBIN,
                members=(Member(None, '10.1.0.10', 80),
                    Member(None, '10.1.0.11', 80))
                )

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '8290')

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]

        ret = self.driver.destroy_balancer(balancer)
        self.assertTrue(ret)

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='8290')

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '8290')

    def test_balancer_list_members(self):
        balancer = self.driver.get_balancer(balancer_id='8290')
        members = balancer.list_members()

        self.assertEquals(len(members), 2)
        self.assertEquals(set(['10.1.0.10:80', '10.1.0.11:80']),
                set(["%s:%s" % (member.ip, member.port) for member in members]))

    def test_balancer_attach_member(self):
        balancer = self.driver.get_balancer(balancer_id='8290')
        member = balancer.attach_member(Member(None, ip='10.1.0.12', port='80'))

        self.assertEquals(member.ip, '10.1.0.12')
        self.assertEquals(member.port, 80)

    def test_balancer_detach_member(self):
        balancer = self.driver.get_balancer(balancer_id='8290')
        member = balancer.list_members()[0]

        ret = balancer.detach_member(member)

        self.assertTrue(ret)


class RackspaceUKLBTests(RackspaceLBTests):

    def setUp(self):
        RackspaceLBDriver.connectionCls.conn_classes = (None,
                RackspaceLBMockHttp)
        RackspaceLBMockHttp.type = None
        self.driver = RackspaceUKLBDriver('user', 'key')


class RackspaceLBMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('rackspace')
    auth_fixtures = OpenStackFixtures()

    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_loadbalancers_protocols(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_loadbalancers_protocols.json')
        return (httplib.ACCEPTED, body, {},
                httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_loadbalancers(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('v1_slug_loadbalancers.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body_json = json.loads(body)
            self.assertEqual(body_json['loadBalancer']['protocol'], 'HTTP')
            self.assertEqual(body_json['loadBalancer']['algorithm'], 'ROUND_ROBIN')

            body = self.fixtures.load('v1_slug_loadbalancers_post.json')
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_8155(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_8290(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_loadbalancers_8290.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_loadbalancers_8290_nodes(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('v1_slug_loadbalancers_8290_nodes.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == "POST":
            body = self.fixtures.load('v1_slug_loadbalancers_8290_nodes_post.json')
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_8290_nodes_30944(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

        raise NotImplementedError

    def _v1_1__auth(self, method, url, body, headers):
        headers = { 'content-type': 'application/json; charset=UTF-8'}
        body = self.auth_fixtures.load('_v1_1__auth.json')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

if __name__ == "__main__":
    sys.exit(unittest.main())
