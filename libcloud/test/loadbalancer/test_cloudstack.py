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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qsl
from libcloud.utils.py3 import assertRaisesRegex

from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.cloudstack import CloudStackLBDriver

from libcloud.test import unittest
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import LoadBalancerFileFixtures


class CloudStackLBTests(unittest.TestCase):
    def setUp(self):
        CloudStackLBDriver.connectionCls.conn_class = CloudStackMockHttp

        CloudStackLBDriver.path = '/test/path'
        CloudStackLBDriver.type = -1
        CloudStackLBDriver.name = 'CloudStack'
        self.driver = CloudStackLBDriver('apikey', 'secret')
        CloudStackMockHttp.fixture_tag = 'default'
        self.driver.connection.poll_interval = 0.0

    def test_user_must_provide_host_and_path(self):
        CloudStackLBDriver.path = None
        CloudStackLBDriver.type = Provider.CLOUDSTACK

        expected_msg = 'When instantiating CloudStack driver directly ' + \
                       'you also need to provide host and path argument'
        cls = get_driver(Provider.CLOUDSTACK)

        assertRaisesRegex(self, Exception, expected_msg, cls,
                          'key', 'secret')

        try:
            cls('key', 'secret', True, 'localhost', '/path')
        except Exception:
            self.fail('host and path provided but driver raised an exception')

    def test_list_supported_algorithms(self):
        algorithms = self.driver.list_supported_algorithms()

        self.assertTrue(Algorithm.ROUND_ROBIN in algorithms)
        self.assertTrue(Algorithm.LEAST_CONNECTIONS in algorithms)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()
        for balancer in balancers:
            self.assertTrue(isinstance(balancer, LoadBalancer))

    def test_create_balancer(self):
        members = [Member(1, '1.1.1.1', 80), Member(2, '1.1.1.2', 80)]
        balancer = self.driver.create_balancer(
            name='test', algorithm=Algorithm.ROUND_ROBIN,
            members=members)
        self.assertTrue(isinstance(balancer, LoadBalancer))

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]
        self.driver.destroy_balancer(balancer)

    def test_balancer_attach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = Member(id=1234, ip='1.1.1.1', port=80)
        balancer.attach_member(member)

    def test_balancer_detach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = balancer.list_members()[0]
        balancer.detach_member(member)

    def test_balancer_list_members(self):
        balancer = self.driver.list_balancers()[0]
        members = balancer.list_members()
        for member in members:
            self.assertTrue(isinstance(member, Member))
            self.assertEqual(member.balancer, balancer)


class CloudStackMockHttp(MockHttp, unittest.TestCase):
    fixtures = LoadBalancerFileFixtures('cloudstack')
    fixture_tag = 'default'

    def _load_fixture(self, fixture):
        body = self.fixtures.load(fixture)
        return body, json.loads(body)

    def _test_path(self, method, url, body, headers):
        url = urlparse.urlparse(url)
        query = dict(parse_qsl(url.query))

        self.assertTrue('apiKey' in query)
        self.assertTrue('command' in query)
        self.assertTrue('response' in query)
        self.assertTrue('signature' in query)

        self.assertTrue(query['response'] == 'json')

        del query['apiKey']
        del query['response']
        del query['signature']
        command = query.pop('command')

        if hasattr(self, '_cmd_' + command):
            return getattr(self, '_cmd_' + command)(**query)
        else:
            fixture = command + '_' + self.fixture_tag + '.json'
            body, obj = self._load_fixture(fixture)
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _cmd_queryAsyncJobResult(self, jobid):
        fixture = 'queryAsyncJobResult' + '_' + str(jobid) + '.json'
        body, obj = self._load_fixture(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == "__main__":
    sys.exit(unittest.main())
