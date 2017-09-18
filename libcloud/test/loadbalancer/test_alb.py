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
from libcloud.loadbalancer.base import Member

from libcloud.test import MockHttp
from libcloud.test.secrets import LB_ALB_PARAMS
from libcloud.test.file_fixtures import LoadBalancerFileFixtures


class ApplicationLBTests(unittest.TestCase):
    # defaults from fixtures
    balancer_id = 'arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/Test-ALB/1111111111111111'
    target_group_id = 'arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/Test-ALB-tg/1111111111111111'
    listener_id = \
        'arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/Test-ALB/1111111111111111/1111111111111111'
    rule_id = 'arn:aws:elasticloadbalancing:us-east-1:111111111111:listener-rule/app/Test-Develop-App-LB/1111111111111111/' \
              '1111111111111111/1111111111111111'
    ssl_cert_id = 'arn:aws:iam::111111111111:server-certificate/test.certificate'

    def setUp(self):
        ApplicationLBMockHttp.test = self
        ApplicationLBDriver.connectionCls.conn_class = ApplicationLBMockHttp
        ApplicationLBMockHttp.type = None
        ApplicationLBMockHttp.use_param = 'Action'
        self.driver = ApplicationLBDriver(*LB_ALB_PARAMS)

    def test_instantiate_driver_with_token(self):
        token = 'temporary_credentials_token'
        driver = ApplicationLBDriver(*LB_ALB_PARAMS, **{'token': token})
        self.assertTrue(hasattr(driver, 'token'), 'Driver has no attribute token')
        self.assertEqual(token, driver.token, "Driver token does not match with provided token")

    def test_driver_with_token_signature_version(self):
        token = 'temporary_credentials_token'
        driver = ApplicationLBDriver(*LB_ALB_PARAMS, **{'token': token})
        kwargs = driver._ex_connection_class_kwargs()
        self.assertTrue(('signature_version' in kwargs), 'Driver has no attribute signature_version')
        self.assertEqual('4', kwargs['signature_version'], 'Signature version is not 4 with temporary credentials')

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()
        self.assertEqual(len(protocols), 2)
        self.assertTrue('http' in protocols)
        self.assertTrue('https' in protocols)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()
        self.assertEqual(len(balancers), 1)
        self.assertEqual(balancers[0].id, self.balancer_id)
        self.assertEqual(balancers[0].name, 'Test-ALB')

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id=self.balancer_id)
        self.assertEqual(balancer.id, self.balancer_id)
        self.assertEqual(balancer.extra['listeners'][0].balancer.id, self.balancer_id)
        self.assertEqual(balancer.name, 'Test-ALB')
        self.assertEqual(balancer.state, State.UNKNOWN)

    def test_create_balancer(self):
        balancer = self.driver.create_balancer(name='Test-ALB', port=443, protocol='HTTPS', algorithm=None,
                                               members=[Member(id='i-01111111111111111', ip=None, port=443)],
                                               ex_scheme="internet-facing", ex_security_groups=['sg-11111111'],
                                               ex_subnets=['subnet-11111111', 'subnet-22222222'], ex_tags={},
                                               ex_ssl_cert_arn=self.ssl_cert_id)
        self.assertEqual(balancer.id, self.balancer_id)
        self.assertEqual(balancer.name, 'Test-ALB')
        self.assertEqual(balancer.state, State.UNKNOWN)
        self.assertEqual(balancer.port, 443)

    def test_ex_create_balancer(self):
        balancer = self.driver.ex_create_balancer(name='Test-ALB', addr_type='ipv4', scheme='internet-facing',
                                                  security_groups=['sg-11111111'],
                                                  subnets=['subnet-11111111', 'subnet-22222222'])
        self.assertEqual(balancer.id, self.balancer_id)
        self.assertEqual(balancer.name, 'Test-ALB')
        self.assertEqual(balancer.state, State.UNKNOWN)

    def test_ex_create_target_group(self):
        target_group = self.driver.ex_create_target_group(name='Test-ALB-tg', port=443, proto="HTTPS", vpc='vpc-11111111',
                                                          health_check_interval=30, health_check_path="/",
                                                          health_check_port="traffic-port", health_check_proto="HTTP",
                                                          health_check_timeout=5, health_check_matcher="200",
                                                          healthy_threshold=5, unhealthy_threshold=2
                                                          )
        self.assertTrue(hasattr(target_group, 'id'), 'Target group is missing "id" field')
        self.assertTrue(hasattr(target_group, 'members'), 'Target group is missing "members" field')
        self.assertEqual(target_group.name, 'Test-ALB-tg')
        self.assertEqual(target_group.port, 443)
        self.assertEqual(target_group.protocol, 'HTTPS')
        self.assertEqual(target_group.vpc, 'vpc-11111111')
        self.assertEqual(target_group.health_check_timeout, 5)
        self.assertEqual(target_group.health_check_port, 'traffic-port')
        self.assertEqual(target_group.health_check_path, '/')
        self.assertEqual(target_group.health_check_matcher, "200")
        self.assertEqual(target_group.health_check_proto, 'HTTPS')
        self.assertEqual(target_group.health_check_interval, 30)
        self.assertEqual(target_group.healthy_threshold, 5)
        self.assertEqual(target_group.unhealthy_threshold, 2)

    def test_ex_register_targets(self):
        balancer = self.driver.get_balancer(self.balancer_id)
        target_group = self.driver.ex_get_target_group(self.target_group_id)
        members = [Member('i-01111111111111111', '10.0.0.0', 443)]
        targets_not_registered = self.driver.ex_register_targets(target_group=target_group,
                                                                 members=members)
        self.assertTrue(targets_not_registered, 'ex_register_targets is expected to return True on success')

    def test_ex_create_listener(self):
        balancer = self.driver.get_balancer(self.balancer_id)
        target_group = self.driver.ex_get_target_group(self.target_group_id)
        listener = self.driver.ex_create_listener(balancer=balancer, port=443, proto='HTTPS',
                                                  target_group=target_group, action="forward",
                                                  ssl_cert_arn=self.ssl_cert_id,
                                                  ssl_policy="ELBSecurityPolicy-2016-08")

        self.assertTrue(hasattr(listener, 'id'), 'Listener is missing "id" field')
        self.assertTrue(hasattr(listener, 'rules'), 'Listener is missing "rules" field')
        self.assertTrue(hasattr(listener, 'balancer'), 'Listener is missing "balancer" field')
        self.assertEqual(listener.balancer.id, balancer.id)
        self.assertEqual(listener.rules[0].target_group.id, target_group.id)
        self.assertEqual(listener.port, 443)
        self.assertEqual(listener.protocol, 'HTTPS')
        self.assertEqual(listener.action, 'forward')
        self.assertEqual(listener.ssl_certificate, self.ssl_cert_id)
        self.assertEqual(listener.ssl_policy, 'ELBSecurityPolicy-2016-08')

    def test_ex_create_rule(self):
        balancer = self.driver.get_balancer(self.balancer_id)
        listener = balancer.extra.get('listeners')[0]
        target_group = self.driver.ex_get_target_group(self.target_group_id)
        rule = self.driver.ex_create_listener_rule(listener=listener, priority=10, target_group=target_group,
                                                   action="forward", condition_field="path-pattern",
                                                   condition_value="/img/*")

        self.assertTrue(hasattr(rule, 'id'), 'Rule is missing "id" field')
        self.assertTrue(hasattr(rule, 'conditions'), 'Rule is missing "conditions" field')
        self.assertEqual(rule.is_default, False)
        self.assertEqual(rule.priority, '10')
        self.assertEqual(rule.target_group.id, self.target_group_id)
        self.assertTrue(('/img/*' in rule.conditions['path-pattern']), 'Rule is missing test condition')

    def test_ex_get_balancer_tags(self):
        balancer = self.driver.get_balancer(balancer_id=self.balancer_id)
        self.assertTrue(('tags' in balancer.extra), 'No tags dict found in balancer.extra')
        tags = self.driver._ex_get_balancer_tags(balancer)
        self.assertEqual(tags['project'], 'lima')

    def test_ex_get_target_group(self):
        target_group = self.driver.ex_get_target_group(self.target_group_id)
        target_group_fields = ('id', 'name', 'protocol', 'port', 'vpc', 'health_check_timeout',
                               'health_check_port', 'health_check_path', 'health_check_proto',
                               'health_check_matcher', 'health_check_interval', 'healthy_threshold',
                               'unhealthy_threshold', '_balancers', '_balancers_arns', '_members',
                               '_driver',)

        for field in target_group_fields:
            self.assertTrue((field in target_group.__dict__),
                            'Field [%s] is missing in ALBTargetGroup object' % field)

        self.assertEqual(target_group.id, self.target_group_id)

    def test_ex_get_listener(self):
        listener = self.driver.ex_get_listener(self.listener_id)
        listener_fields = ('id', 'protocol', 'port', 'action', 'ssl_policy', 'ssl_certificate',
                           '_balancer', '_balancer_arn', '_rules', '_driver',)

        for field in listener_fields:
            self.assertTrue((field in listener.__dict__),
                            'Field [%s] is missing in ALBListener object' % field)

        self.assertEqual(listener.id, self.listener_id)

    def test_ex_get_rule(self):
        rule = self.driver.ex_get_rule(self.rule_id)
        rule_fields = ('id', 'is_default', 'priority', 'conditions', '_listener', '_listener_arn',
                       '_target_group', '_target_group_arn', '_driver',)

        for field in rule_fields:
            self.assertTrue((field in rule.__dict__),
                            'Field [%s] is missing in ALBRule object' % field)

        self.assertEqual(rule.id, self.rule_id)


    def test_ex_get_target_group_members(self):
        target_group = self.driver.ex_get_target_group(self.target_group_id)
        target_group_members = self.driver._ex_get_target_group_members(target_group)
        self.assertEqual(len(target_group_members), 1)
        self.assertTrue(hasattr(target_group_members[0], 'id'), 'Target group member is missing "id" field')
        self.assertTrue(hasattr(target_group_members[0], 'port'), 'Target group member is missing "port" field')
        self.assertTrue(('health' in target_group_members[0].extra), 'Target group member is missing "health" field')

    def test_ex_get_balancer_listeners(self):
        balancer = self.driver.get_balancer(balancer_id=self.balancer_id)
        listeners = self.driver._ex_get_balancer_listeners(balancer)
        self.assertEqual(len(listeners), 1)
        self.assertTrue(hasattr(listeners[0], 'id'), 'Listener is missing "id" field')
        self.assertTrue(hasattr(listeners[0], 'port'), 'Listener is missing "port" field')
        self.assertTrue(hasattr(listeners[0], 'protocol'), 'Listener is missing "protocol" field')
        self.assertTrue(hasattr(listeners[0], 'rules'), 'Listener is missing "rules" field')

    def test_ex_get_rules_for_listener(self):
        listener = self.driver.ex_get_listener(self.listener_id)
        listener_rules = self.driver._ex_get_rules_for_listener(listener)
        self.assertEqual(len(listener_rules), 1)
        self.assertTrue(hasattr(listener_rules[0], 'id'), 'Rule is missing "id" field')
        self.assertTrue(hasattr(listener_rules[0], 'is_default'), 'Rule is missing "port" field')
        self.assertTrue(hasattr(listener_rules[0], 'priority'), 'Rule is missing "priority" field')
        self.assertTrue(hasattr(listener_rules[0], 'target_group'), 'Rule is missing "target_group" field')
        self.assertTrue(hasattr(listener_rules[0], 'conditions'), 'Rule is missing "conditions" field')

# Commented out to avoid confusion. In AWS ALB relation between load balancer
# and target group/members is indirect. So it's better to go through full chain
# to obtain required object(s).
# Chain is: balancer->listener->rule->target group->member
#
#    def test_balancer_list_members(self):
#         balancer = self.driver.get_balancer(balancer_id=self.balancer_id)
#         members = balancer.list_members()
#         self.assertEqual(len(members), 1)
#         self.assertEqual(members[0].balancer, balancer)
#         self.assertEqual('i-01111111111111111', members[0].id)
#
#    def test_ex_get_balancer_target_groups(self):
#         balancer = self.driver.get_balancer(balancer_id=self.balancer_id)
#         target_groups = self.driver._ex_get_balancer_target_groups(balancer)
#         self.assertEqual(len(target_groups), 1)
#         self.assertTrue(hasattr(target_groups[0], 'id'), 'Target group is missing "id" field')
#         self.assertTrue(hasattr(target_groups[0], 'name'), 'Target group is missing "port" field')
#         self.assertTrue(hasattr(target_groups[0], 'members'), 'Target group is missing "members" field')


class ApplicationLBMockHttp(MockHttp):
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

    def _2015_12_01_CreateLoadBalancer(self, method, url, body, headers):
        body = self.fixtures.load('create_balancer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_CreateTargetGroup(self, method, url, body, headers):
        body = self.fixtures.load('create_target_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_CreateListener(self, method, url, body, headers):
        body = self.fixtures.load('create_listener.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_CreateRule(self, method, url, body, headers):
        body = self.fixtures.load('create_rule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2015_12_01_RegisterTargets(self, method, url, body, headers):
        body = self.fixtures.load('register_targets.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
