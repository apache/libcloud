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
from libcloud.loadbalancer.drivers.alb import ApplicationLBDriver
from libcloud.loadbalancer.types import State

from libcloud.test import MockHttpTestCase
from libcloud.test.secrets import LB_ALB_PARAMS
from libcloud.test.file_fixtures import LoadBalancerFileFixtures


class ApplicationLBTests(unittest.TestCase):
    def setUp(self):
        ApplicationLBMockHttp.test = self
        ApplicationLBDriver.connectionCls.conn_classes = (None, ApplicationLBMockHttp)
        ApplicationLBMockHttp.type = None
        ApplicationLBMockHttp.use_param = 'Action'
        self.driver = ApplicationLBDriver(*LB_ALB_PARAMS)

    def test_instantiate_driver_with_token(self):
        token = 'temporary_credentials_token'
        driver = ApplicationLBDriver(*LB_ALB_PARAMS, **{'token': token})
        self.assertTrue(hasattr(driver, 'token'), 'Driver has no attribute token')
        self.assertEquals(token, driver.token, "Driver token does not match with provided token")

    def test_driver_with_token_signature_version(self):
        token = 'temporary_credentials_token'
        driver = ApplicationLBDriver(*LB_ALB_PARAMS, **{'token': token})
        kwargs = driver._ex_connection_class_kwargs()
        self.assertTrue(('signature_version' in kwargs), 'Driver has no attribute signature_version')
        self.assertEquals('4', kwargs['signature_version'], 'Signature version is not 4 with temporary credentials')

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()
        self.assertEqual(len(protocols), 2)
        self.assertTrue('http' in protocols)
        self.assertTrue('https' in protocols)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()
        self.assertEqual(len(balancers), 1)
        self.assertEqual(
            balancers[0].id,
            'arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/Test-ALB/1111111111111111'
        )
        self.assertEqual(balancers[0].name, 'Test-ALB')

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        self.assertEqual(
            balancer.id,
            'arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/Test-ALB/1111111111111111'
        )
        self.assertEqual(balancer.name, 'Test-ALB')
        self.assertEqual(balancer.state, State.UNKNOWN)

    def test_balancer_list_members(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        members = balancer.list_members()
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].balancer, balancer)
        self.assertEqual('i-01111111111111111', members[0].id)

    def test_ex_balancer_list_listeners(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        self.assertTrue(('listeners' in balancer.extra), 'No listeners dict found in balancer.extra')
        listeners = self.driver.ex_balancer_list_listeners(balancer)
        self.assertEqual(len(listeners), 1)

    def test_ex_get_balancer_tags(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        self.assertTrue(('tags' in balancer.extra), 'No tags dict found in balancer.extra')
        tags = self.driver._ex_get_balancer_tags(balancer)
        self.assertEqual(tags['project'], 'lima')

    def test_ex_get_target_group_members(self):
        target_group_members = self.driver._ex_get_target_group_members(
            'arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/TEST-TARGET-GROUP1/1111111111111111'
        )
        self.assertEqual(len(target_group_members), 1)
        self.assertTrue(('id' in target_group_members[0]), 'Target group member is missing "id" field')
        self.assertTrue(('port' in target_group_members[0]), 'Target group member is missing "port" field')
        self.assertTrue(('health' in target_group_members[0]), 'Target group member is missing "health" field')

    def test_ex_get_balancer_target_groups(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        target_groups = self.driver._ex_get_balancer_target_groups(balancer)
        self.assertEqual(len(target_groups), 1)
        self.assertTrue(('id' in target_groups[0]), 'Target group is missing "id" field')
        self.assertTrue(('name' in target_groups[0]), 'Target group is missing "port" field')
        self.assertTrue(('members' in target_groups[0]), 'Target group is missing "members" field')

    def test_ex_get_balancer_listeners(self):
        balancer = self.driver.get_balancer(balancer_id='Test-ALB')
        listeners = self.driver._ex_get_balancer_listeners(balancer)
        self.assertEqual(len(listeners), 1)
        self.assertTrue(('id' in listeners[0]), 'Listener is missing "id" field')
        self.assertTrue(('port' in listeners[0]), 'Listener is missing "port" field')
        self.assertTrue(('protocol' in listeners[0]), 'Listener is missing "protocol" field')
        self.assertTrue(('rules' in listeners[0]), 'Listener is missing "rules" field')

    def test_ex_get_rules_for_listener(self):
        listener_rules = self.driver._ex_get_rules_for_listener(
            'arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/Test-ALB/1111111111111111/1111111111111111'
        )
        self.assertEqual(len(listener_rules), 1)
        self.assertTrue(('id' in listener_rules[0]), 'Rule is missing "id" field')
        self.assertTrue(('is_default' in listener_rules[0]), 'Rule is missing "port" field')
        self.assertTrue(('priority' in listener_rules[0]), 'Rule is missing "priority" field')
        self.assertTrue(('target_group' in listener_rules[0]), 'Rule is missing "target_group" field')
        self.assertTrue(('conditions' in listener_rules[0]), 'Rule is missing "conditions" field')


class ApplicationLBMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('alb')

    def _2015_12_01_DescribeLoadBalancers(self, method, url, body, headers):
        body = self.fixtures.load('describe_load_balancers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_DescribeListeners(self, method, url, body, headers):
        body = self.fixtures.load('describe_load_balancer_listeters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_DescribeRules(self, method, url, body, headers):
        body = self.fixtures.load('describe_load_balancer_rules.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_DescribeTargetGroups(self, method, url, body, headers):
        body = self.fixtures.load('describe_load_balancer_target_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_DescribeTargetHealth(self, method, url, body, headers):
        body = self.fixtures.load('describe_target_health.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_DescribeTags(self, method, url, body, headers):
        body = self.fixtures.load('describe_tags.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
