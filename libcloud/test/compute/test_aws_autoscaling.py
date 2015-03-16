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

from __future__ import with_statement

from libcloud.utils.py3 import httplib

from libcloud.compute.base import NodeImage, AutoScaleAlarm, AutoScalePolicy,\
    AutoScaleGroup, NodeSize
from libcloud.compute.types import AutoScaleAdjustmentType, AutoScaleOperator,\
    AutoScaleMetric

from libcloud.compute.drivers.ec2 import EC2NodeDriver
from libcloud.compute.drivers.aws_autoscaling import AutoScaleDriver
from libcloud.compute.drivers.aws_autoscaling import CloudWatchDriver

from libcloud.test import MockHttpTestCase, LibcloudTestCase
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.compute.test_ec2 import EC2MockHttp

from libcloud.test.secrets import EC2_PARAMS


class AutoScaleTests(LibcloudTestCase):
    region = 'eu-west-1'
    POLICY_ID = 'arn:aws:autoscaling:eu-west-1:786301965414:scalingPolicy:'\
        'e1c4a42b-4777-4fbb-bac4-41e2060bf775:autoScalingGroupName/libcloud-'\
        'testing:policyName/libcloud-testing-policy'

    ALARM_ID = 'arn:aws:cloudwatch:eu-west-1:786301965414:alarm:libcloud-'\
        'testing-alarm'

    def setUp(self):

        # EC2NodeDriver is needed for our auto scale tests
        EC2MockHttp.test = self
        EC2NodeDriver.connectionCls.conn_classes = (None, EC2MockHttp)
        EC2MockHttp.use_param = 'Action'
        EC2MockHttp.type = None

        AutoScaleDriver.connectionCls.conn_classes = (None, AutoScaleMockHttp)
        CloudWatchDriver.connectionCls.conn_classes = (None, AutoScaleMockHttp)

        AutoScaleMockHttp.test = self
        AutoScaleMockHttp.use_param = 'Action'
        AutoScaleMockHttp.type = None

        self.ec2_driver = EC2NodeDriver(*EC2_PARAMS,
                                        **{'region': self.region})

        self.as_driver = AutoScaleDriver(*EC2_PARAMS,
                                         **{'region': self.region})

        self.cw_driver = CloudWatchDriver(*EC2_PARAMS,
                                          **{'region': self.region})

    def test_create_auto_scale_group(self):

        image = NodeImage(id='ami-9a562df2', name='', driver=self.as_driver)
        location = self.ec2_driver.list_locations()[0]
        size = NodeSize('t2.micro', None, None, None, None, None, None)
        group = self.as_driver.\
            create_auto_scale_group(name='libcloud-testing',
                                    min_size=1, max_size=5, cooldown=300,
                                    image=image, location=location, size=size,
                                    termination_policies=[2])

        self.assertEqual(group.name, 'libcloud-testing')
        self.assertEqual(group.cooldown, 300)
        self.assertEqual(group.min_size, 1)
        self.assertEqual(group.max_size, 5)
        self.assertEqual(group.termination_policies, [2])

    def test_create_auto_scale_group_with_ex_instance_name(self):

        image = NodeImage(id='ami-9a562df2', name='', driver=self.as_driver)
        location = self.ec2_driver.list_locations()[0]
        group = self.as_driver.\
            create_auto_scale_group(name='libcloud-testing',
                                    min_size=1, max_size=5, cooldown=300,
                                    image=image, location=location,
                                    termination_policies=[2],
                                    ex_instance_name='test-node')

        self.assertEqual(group.name, 'libcloud-testing')
        self.assertEqual(group.cooldown, 300)
        self.assertEqual(group.min_size, 1)
        self.assertEqual(group.max_size, 5)
        self.assertEqual(group.termination_policies, [2])

    def test_list_auto_scale_groups(self):

        groups = self.as_driver.list_auto_scale_groups()
        self.assertEqual(len(groups), 1)

    def test_delete_group(self):

        group = AutoScaleGroup('123', 'libcloud-testing', None, None, None,
                               [0], self.as_driver)
        AutoScaleMockHttp.type = 'DELETE'
        self.as_driver.delete_auto_scale_group(group)

    def test_create_auto_scale_policy(self):

        group = AutoScaleGroup('123', 'libcloud-testing', None, None, None, [0],
                               self.as_driver)

        policy = self.as_driver.create_auto_scale_policy(
            group=group, name='libcloud-testing-policy',
            adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
            scaling_adjustment=1)

        self.assertEqual(policy.name, 'libcloud-testing-policy')
        self.assertEqual(policy.adjustment_type,
                         AutoScaleAdjustmentType.CHANGE_IN_CAPACITY)
        self.assertEqual(policy.scaling_adjustment, 1)

    def test_list_auto_scale_policies(self):

        group = AutoScaleGroup('123', 'libcloud-testing', None, None, None, [0],
                               self.as_driver)
        policies = self.as_driver.list_auto_scale_policies(group=group)
        self.assertEqual(len(policies), 1)

    def test_delete_policy(self):

        policy = AutoScalePolicy(self.POLICY_ID, None, None, None,
                                 self.as_driver)
        self.as_driver.delete_auto_scale_policy(policy)

    def test_create_auto_scale_alarm(self):

        policy = AutoScalePolicy(self.POLICY_ID, None, None, None,
                                 self.cw_driver)

        alarm = self.cw_driver.create_auto_scale_alarm(
            name='libcloud-testing-alarm', policy=policy,
            metric_name=AutoScaleMetric.CPU_UTIL,
            operator=AutoScaleOperator.GT, threshold=80, period=120)

        self.assertEqual(alarm.metric_name, AutoScaleMetric.CPU_UTIL)
        self.assertEqual(alarm.operator, AutoScaleOperator.GT)
        self.assertEqual(alarm.threshold, 80)
        self.assertEqual(alarm.period, 120)

    def test_list_auto_scale_alarms(self):

        policy = AutoScalePolicy(self.POLICY_ID, None, None, None,
                                 self.cw_driver)
        alarms = self.cw_driver.list_auto_scale_alarms(policy)
        self.assertEqual(len(alarms), 1)

    def test_delete_alarm(self):

        alarm = AutoScaleAlarm(None, 'libcloud-testing-alarm', None, None,
                               None, None, self.cw_driver)
        self.cw_driver.delete_auto_scale_alarm(alarm)


class AutoScaleMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('aws_autoscaling')

    def _CreateLaunchConfiguration(self, method, url, body, headers):
        body = self.fixtures.load('create_launchconfiguration.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _CreateAutoScalingGroup(self, method, url, body, headers):
        body = self.fixtures.load('create_scaling_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAutoScalingGroups(self, method, url, body, headers):
        body = self.fixtures.load('describe_scaling_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DELETE_DescribeAutoScalingGroups(self, method, url, body, headers):

        # simulate empty list (group had been deleted) after a few calls
        if len([meth for meth in self.test._executed_mock_methods
                if meth == '_DELETE_DescribeAutoScalingGroups']) > 3:
            body = self.fixtures.load('describe_scaling_groups_empty.xml')
        else:
            body = self.fixtures.load('describe_scaling_groups.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DELETE_DeleteAutoScalingGroup(self, method, url, body, headers):
        body = self.fixtures.load('delete_scaling_group.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DELETE_DeleteLaunchConfiguration(self, method, url, body, headers):
        body = self.fixtures.load('delete_launchconfiguration.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _PutScalingPolicy(self, method, url, body, headers):
        body = self.fixtures.load('put_scaling_policy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribePolicies(self, method, url, body, headers):
        body = self.fixtures.load('describe_policies.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeletePolicy(self, method, url, body, headers):
        body = self.fixtures.load('delete_policy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _PutMetricAlarm(self, method, url, body, headers):
        body = self.fixtures.load('put_metric_alarm.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DescribeAlarms(self, method, url, body, headers):
        body = self.fixtures.load('describe_alarms.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _DeleteAlarms(self, method, url, body, headers):
        body = self.fixtures.load('delete_alarms.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
