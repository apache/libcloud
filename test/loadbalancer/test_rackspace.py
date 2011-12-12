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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib

from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.drivers.rackspace import RackspaceLBDriver
from libcloud.loadbalancer.drivers.rackspace import RackspaceUKLBDriver
from libcloud.loadbalancer.drivers.rackspace import RackspaceAccessRuleType

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

    def test_list_supported_algorithms(self):
        algorithms = self.driver.list_supported_algorithms()

        self.assertTrue(Algorithm.RANDOM in algorithms)
        self.assertTrue(Algorithm.ROUND_ROBIN in algorithms)
        self.assertTrue(Algorithm.LEAST_CONNECTIONS in algorithms)
        self.assertTrue(Algorithm.WEIGHTED_ROUND_ROBIN in algorithms)
        self.assertTrue(Algorithm.WEIGHTED_LEAST_CONNECTIONS in algorithms)

    def test_ex_list_algorithms(self):
        algorithms = self.driver.ex_list_algorithm_names()

        self.assertTrue("RANDOM" in algorithms)
        self.assertTrue("ROUND_ROBIN" in algorithms)
        self.assertTrue("LEAST_CONNECTIONS" in algorithms)
        self.assertTrue("WEIGHTED_ROUND_ROBIN" in algorithms)
        self.assertTrue("WEIGHTED_LEAST_CONNECTIONS" in algorithms)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEquals(len(balancers), 2)
        self.assertEquals(balancers[0].name, "test0")
        self.assertEquals(balancers[0].id, "8155")
        self.assertEquals(balancers[0].port, 80)
        self.assertEquals(balancers[0].ip, "1.1.1.25")
        self.assertEquals(balancers[1].name, "test1")
        self.assertEquals(balancers[1].id, "8156")

    def test_list_balancers_ex_member_address(self):
        RackspaceLBMockHttp.type = 'EX_MEMBER_ADDRESS'
        balancers = self.driver.list_balancers(ex_member_address='127.0.0.1')

        self.assertEquals(len(balancers), 3)
        self.assertEquals(balancers[0].name, "First Loadbalancer")
        self.assertEquals(balancers[0].id, "1")
        self.assertEquals(balancers[1].name, "Second Loadbalancer")
        self.assertEquals(balancers[1].id, "2")
        self.assertEquals(balancers[2].name, "Third Loadbalancer")
        self.assertEquals(balancers[2].id, "8")

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

    def test_get_balancer_extra_public_vips(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        self.assertEquals(balancer.extra["publicVips"], ['50.56.49.149'])

    def test_get_balancer_extra_private_vips(self):
        balancer = self.driver.get_balancer(balancer_id='18941')

        self.assertEquals(balancer.extra["privateVips"], ['10.183.252.175'])

    def test_get_balancer_extra_private_vips_empty(self):
        balancer = self.driver.get_balancer(balancer_id='18945')

        self.assertEquals(balancer.extra['privateVips'], [])

    def test_get_balancer_extra_public_source_ipv4(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        self.assertEquals(balancer.extra["ipv4PublicSource"], '184.106.100.25')

    def test_get_balancer_extra_public_source_ipv6(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        self.assertEquals(balancer.extra["ipv6PublicSource"],
                          '2001:4801:7901::6/64')

    def test_get_balancer_extra_private_source_ipv4(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        self.assertEquals(balancer.extra["ipv4PrivateSource"], '10.183.252.25')

    def test_get_balancer_algorithm(self):
        balancer = self.driver.get_balancer(balancer_id='8290')
        self.assertEquals(balancer.extra["algorithm"], Algorithm.RANDOM)

    def test_get_balancer_weighted_round_robin_algorithm(self):
        balancer = self.driver.get_balancer(balancer_id='94692')
        self.assertEquals(balancer.extra["algorithm"],
                           Algorithm.WEIGHTED_ROUND_ROBIN)

    def test_get_balancer_weighted_least_connections_algorithm(self):
        balancer = self.driver.get_balancer(balancer_id='94693')
        self.assertEquals(balancer.extra["algorithm"],
                           Algorithm.WEIGHTED_LEAST_CONNECTIONS)

    def test_get_balancer_unknown_algorithm(self):
        balancer = self.driver.get_balancer(balancer_id='94694')
        self.assertFalse('algorithm' in balancer.extra)

    def test_get_balancer_connect_health_monitor(self):
        balancer = self.driver.get_balancer(balancer_id='94695')
        balancer_health_monitor = balancer.extra["healthMonitor"]

        self.assertEquals(balancer_health_monitor.type, "CONNECT")
        self.assertEquals(balancer_health_monitor.delay, 10)
        self.assertEquals(balancer_health_monitor.timeout, 5)
        self.assertEquals(balancer_health_monitor.attempts_before_deactivation,
                          2)

    def test_get_balancer_http_health_monitor(self):
        balancer = self.driver.get_balancer(balancer_id='94696')
        balancer_health_monitor = balancer.extra["healthMonitor"]

        self.assertEquals(balancer_health_monitor.type, "HTTP")
        self.assertEquals(balancer_health_monitor.delay, 10)
        self.assertEquals(balancer_health_monitor.timeout, 5)
        self.assertEquals(balancer_health_monitor.attempts_before_deactivation,
                          2)
        self.assertEquals(balancer_health_monitor.path, "/")
        self.assertEquals(balancer_health_monitor.status_regex,
                           "^[234][0-9][0-9]$")
        self.assertEquals(balancer_health_monitor.body_regex,
                           "Hello World!")

    def test_get_balancer_https_health_monitor(self):
        balancer = self.driver.get_balancer(balancer_id='94697')
        balancer_health_monitor = balancer.extra["healthMonitor"]

        self.assertEquals(balancer_health_monitor.type, "HTTPS")
        self.assertEquals(balancer_health_monitor.delay, 15)
        self.assertEquals(balancer_health_monitor.timeout, 12)
        self.assertEquals(balancer_health_monitor.attempts_before_deactivation,
                          5)
        self.assertEquals(balancer_health_monitor.path, "/test")
        self.assertEquals(balancer_health_monitor.status_regex,
                           "^[234][0-9][0-9]$")
        self.assertEquals(balancer_health_monitor.body_regex, "abcdef")

    def test_get_balancer_connection_throttle(self):
        balancer = self.driver.get_balancer(balancer_id='94695')
        balancer_connection_throttle = balancer.extra["connectionThrottle"]

        self.assertEquals(balancer_connection_throttle.min_connections, 50)
        self.assertEquals(balancer_connection_throttle.max_connections, 200)
        self.assertEquals(balancer_connection_throttle.max_connection_rate, 50)
        self.assertEquals(balancer_connection_throttle.rate_interval_seconds,
                           10)

    def test_get_session_persistence(self):
        balancer = self.driver.get_balancer(balancer_id='94695')
        self.assertEquals(balancer.extra["sessionPersistenceType"],
                           "HTTP_COOKIE")

    def test_get_connection_logging(self):
        balancer = self.driver.get_balancer(balancer_id='94695')
        self.assertEquals(balancer.extra["connectionLoggingEnabled"], True)

    def test_get_error_page(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        error_page = self.driver.ex_get_balancer_error_page(balancer)
        self.assertTrue("The service is temporarily unavailable" in error_page)

    def test_get_access_list(self):
        balancer = self.driver.get_balancer(balancer_id='18940')
        deny_rule, allow_rule = self.driver.ex_balancer_access_list(balancer)

        self.assertEquals(deny_rule.id, 2883)
        self.assertEquals(deny_rule.rule_type, RackspaceAccessRuleType.DENY)
        self.assertEquals(deny_rule.address, "0.0.0.0/0")

        self.assertEquals(allow_rule.id, 2884)
        self.assertEquals(allow_rule.address, "2001:4801:7901::6/64")
        self.assertEquals(allow_rule.rule_type, RackspaceAccessRuleType.ALLOW)

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

    def _v1_0_slug_loadbalancers_algorithms(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('v1_slug_loadbalancers_algorithms.json')
            return (httplib.ACCEPTED, body, {},
                    httplib.responses[httplib.ACCEPTED])

        raise NotImplementedError

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

    def _v1_0_slug_loadbalancers_EX_MEMBER_ADDRESS(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_loadbalancers_nodeaddress.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

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

    def _v1_0_slug_loadbalancers_18940(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_18940_ex_public_ips.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_18945(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_18945_ex_public_ips.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_18940_errorpage(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_18940_errorpage.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_18940_accesslist(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_18940_accesslist.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_18941(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_18941_ex_private_ips.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94692(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94692_weighted_round_robin.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94693(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94693_weighted_least_connections.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94694(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94694_unknown_algorithm.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94695(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94695_full_details.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94696(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94696_http_health_monitor.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_0_slug_loadbalancers_94697(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load("v1_slug_loadbalancers_94697_https_health_monitor.json")
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        raise NotImplementedError

    def _v1_1_auth(self, method, url, body, headers):
        headers = { 'content-type': 'application/json; charset=UTF-8' }
        body = self.auth_fixtures.load('_v1_1__auth.json')
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

if __name__ == "__main__":
    sys.exit(unittest.main())
