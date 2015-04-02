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

import unittest
import sys

try:
    import Crypto
    Crypto
    crypto = True
except ImportError:
    crypto = False

from libcloud.common.types import InvalidCredsError

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import xmlrpclib
from libcloud.utils.py3 import next

from libcloud.compute.drivers.softlayer import SoftLayerNodeDriver as SoftLayer
from libcloud.compute.drivers.softlayer import SoftLayerException, \
    NODE_STATE_MAP
from libcloud.compute.base import AutoScaleAlarm, AutoScalePolicy, \
    AutoScaleGroup
from libcloud.compute.types import NodeState, KeyPairDoesNotExistError, \
    AutoScaleAdjustmentType, AutoScaleMetric, AutoScaleOperator

from libcloud.test import MockHttp               # pylint: disable-msg=E0611
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import SOFTLAYER_PARAMS

null_fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                   '00:00:00:00:00'
DELETE_GROUP_CALLS = 0


class SoftLayerTests(unittest.TestCase):

    def setUp(self):
        SoftLayer.connectionCls.conn_classes = (
            SoftLayerMockHttp, SoftLayerMockHttp)
        SoftLayerMockHttp.type = None
        SoftLayerMockHttp.test = self
        self.driver = SoftLayer(*SOFTLAYER_PARAMS)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        node = nodes[0]
        self.assertEqual(node.name, 'libcloud-testing1.example.com')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.extra['password'], 'L3TJVubf')

    def test_initializing_state(self):
        nodes = self.driver.list_nodes()
        node = nodes[1]
        self.assertEqual(node.state, NODE_STATE_MAP['INITIATING'])

    def test_list_locations(self):
        locations = self.driver.list_locations()
        dal = next(l for l in locations if l.id == 'dal05')
        self.assertEqual(dal.country, 'US')
        self.assertEqual(dal.id, 'dal05')
        self.assertEqual(dal.name, 'Dallas - Central U.S.')

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(image.id, 'CENTOS_6_64')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 13)

    def test_create_node(self):
        node = self.driver.create_node(name="libcloud-testing",
                                       location=self.driver.list_locations()[0],
                                       size=self.driver.list_sizes()[0],
                                       image=self.driver.list_images()[0])
        self.assertEqual(node.name, 'libcloud-testing.example.com')
        self.assertEqual(node.state, NODE_STATE_MAP['RUNNING'])

    def test_create_fail(self):
        SoftLayerMockHttp.type = "SOFTLAYEREXCEPTION"
        self.assertRaises(
            SoftLayerException,
            self.driver.create_node,
            name="SOFTLAYEREXCEPTION",
            location=self.driver.list_locations()[0],
            size=self.driver.list_sizes()[0],
            image=self.driver.list_images()[0])

    def test_create_creds_error(self):
        SoftLayerMockHttp.type = "INVALIDCREDSERROR"
        self.assertRaises(
            InvalidCredsError,
            self.driver.create_node,
            name="INVALIDCREDSERROR",
            location=self.driver.list_locations()[0],
            size=self.driver.list_sizes()[0],
            image=self.driver.list_images()[0])

    def test_create_node_no_location(self):
        self.driver.create_node(name="Test",
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[0])

    def test_create_node_no_image(self):
        self.driver.create_node(name="Test", size=self.driver.list_sizes()[0])

    def test_create_node_san(self):
        self.driver.create_node(name="Test", ex_local_disk=False)

    def test_create_node_domain_for_name(self):
        self.driver.create_node(name="libcloud.org")

    def test_create_node_ex_options(self):
        self.driver.create_node(name="Test",
                                location=self.driver.list_locations()[0],
                                size=self.driver.list_sizes()[0],
                                image=self.driver.list_images()[0],
                                ex_domain='libcloud.org',
                                ex_cpus=2,
                                ex_ram=2048,
                                ex_disk=100,
                                ex_key='test1',
                                ex_bandwidth=10,
                                ex_local_disk=False,
                                ex_datacenter='Dal05',
                                ex_os='UBUNTU_LATEST')

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        self.driver.reboot_node(node)

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.driver.destroy_node(node)

    def test_list_keypairs(self):
        keypairs = self.driver.list_key_pairs()
        self.assertEqual(len(keypairs), 2)
        self.assertEqual(keypairs[0].name, 'test1')
        self.assertEqual(keypairs[0].fingerprint, null_fingerprint)

    def test_get_key_pair(self):
        key_pair = self.driver.get_key_pair(name='test1')
        self.assertEqual(key_pair.name, 'test1')

    def test_get_key_pair_does_not_exist(self):
        self.assertRaises(KeyPairDoesNotExistError, self.driver.get_key_pair,
                          name='test-key-pair')

    def test_create_key_pair(self):
        if crypto:
            key_pair = self.driver.create_key_pair(name='my-key-pair')
            fingerprint = ('1f:51:ae:28:bf:89:e9:d8:1f:25:5d'
                           ':37:2d:7d:b8:ca:9f:f5:f1:6f')

            self.assertEqual(key_pair.name, 'my-key-pair')
            self.assertEqual(key_pair.fingerprint, fingerprint)
            self.assertTrue(key_pair.private_key is not None)
        else:
            self.assertRaises(NotImplementedError, self.driver.create_key_pair,
                              name='my-key-pair')

    def test_delete_key_pair(self):
        success = self.driver.delete_key_pair('test1')
        self.assertTrue(success)

    def test_create_auto_scale_group(self):

        group = self.driver.create_auto_scale_group(
            name="libcloud-testing", min_size=1, max_size=5, cooldown=300,
            image=self.driver.list_images()[0], termination_policies=2)

        self.assertEqual(group.name, 'libcloud-testing')
        self.assertEqual(group.cooldown, 300)
        self.assertEqual(group.min_size, 1)
        self.assertEqual(group.max_size, 5)
        self.assertEqual(group.termination_policies, [2])

    def test_create_auto_scale_group_size(self):

        group = self.driver.create_auto_scale_group(
            name="libcloud-testing", min_size=1, max_size=5, cooldown=300,
            image=self.driver.list_images()[0],
            size=self.driver.list_sizes()[0], termination_policies=2)

        self.assertEqual(group.name, 'libcloud-testing')
        self.assertEqual(group.cooldown, 300)
        self.assertEqual(group.min_size, 1)
        self.assertEqual(group.max_size, 5)
        self.assertEqual(group.termination_policies, [2])

    def test_list_auto_scale_groups(self):

        groups = self.driver.list_auto_scale_groups()
        self.assertEqual(len(groups), 3)

    def test_create_auto_scale_policy(self):

        group = AutoScaleGroup(145955, 'libcloud-testing', None, None, None, 0,
                               self.driver)

        policy = self.driver.create_auto_scale_policy(
            group=group, name='libcloud-testing-policy',
            adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
            scaling_adjustment=1)

        self.assertEqual(policy.name, 'libcloud-testing-policy')
        self.assertEqual(policy.adjustment_type,
                         AutoScaleAdjustmentType.CHANGE_IN_CAPACITY)
        self.assertEqual(policy.scaling_adjustment, 1)

    def test_list_auto_scale_policies(self):

        group = AutoScaleGroup(167555, 'libcloud-testing', None, None, None, 0,
                               self.driver)
        policies = self.driver.list_auto_scale_policies(group=group)
        self.assertEqual(len(policies), 1)

    def test_create_auto_scale_alarm(self):

        policy = AutoScalePolicy(45955, None, None, None,
                                 self.driver)

        alarm = self.driver.create_auto_scale_alarm(
            name='libcloud-testing-alarm', policy=policy,
            metric_name=AutoScaleMetric.CPU_UTIL,
            operator=AutoScaleOperator.GT, threshold=80, period=120)

        self.assertEqual(alarm.metric_name, AutoScaleMetric.CPU_UTIL)
        self.assertEqual(alarm.operator, AutoScaleOperator.GT)
        self.assertEqual(alarm.threshold, 80)
        self.assertEqual(alarm.period, 120)

    def test_list_auto_scale_alarms(self):

        policy = AutoScalePolicy(50055, None, None, None,
                                 self.driver)
        alarms = self.driver.list_auto_scale_alarms(policy)
        self.assertEqual(len(alarms), 1)

    def test_delete_alarm(self):

        alarm = AutoScaleAlarm(37903, None, None, None, None, None,
                               self.driver)
        self.driver.delete_auto_scale_alarm(alarm)

    def test_delete_policy(self):

        policy = AutoScalePolicy(45955, None, None, None, self.driver)
        self.driver.delete_auto_scale_policy(policy)

    def test_delete_group(self):

        group = AutoScaleGroup(145955, 'libcloud-testing', None, None, None, 0,
                               self.driver)
        SoftLayerMockHttp.type = 'DELETE'
        global DELETE_GROUP_CALLS
        DELETE_GROUP_CALLS = 0
        self.driver.delete_auto_scale_group(group)


class SoftLayerMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('softlayer')

    def _get_method_name(self, type, use_param, qs, path):
        return "_xmlrpc"

    def _xmlrpc(self, method, url, body, headers):
        params, meth_name = xmlrpclib.loads(body)
        url = url.replace("/", "_")
        meth_name = "%s_%s" % (url, meth_name)
        return getattr(self, meth_name)(method, url, body, headers)

    def _xmlrpc_v3_SoftLayer_Virtual_Guest_getCreateObjectOptions(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Virtual_Guest_getCreateObjectOptions.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Account_getVirtualGuests(
            self, method, url, body, headers):
        body = self.fixtures.load('v3_SoftLayer_Account_getVirtualGuests.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Location_Datacenter_getDatacenters(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3_SoftLayer_Location_Datacenter_getDatacenters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Virtual_Guest_createObject(
            self, method, url, body, headers):
        fixture = {
            None: 'v3__SoftLayer_Virtual_Guest_createObject.xml',
            'INVALIDCREDSERROR': 'SoftLayer_Account.xml',
            'SOFTLAYEREXCEPTION': 'fail.xml',
        }[self.type]
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Virtual_Guest_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'v3__SoftLayer_Virtual_Guest_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Virtual_Guest_rebootSoft(
            self, method, url, body, headers):
        body = self.fixtures.load('empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Virtual_Guest_deleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load('empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Account_getSshKeys(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Account_getSshKeys.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Security_Ssh_Key_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Security_Ssh_Key_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Security_Ssh_Key_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Security_Ssh_Key_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Security_Ssh_Key_deleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Security_Ssh_Key_deleteObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Location_Group_Regional_getAllObjects(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Location_Group_Regional_getAllObjects.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Group_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Group_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Group_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Group_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Group_getStatus(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Group_getStatus.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Group_getPolicies(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Group_getPolicies.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Group_forceDeleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Group_forceDeleteObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Account_getScaleGroups(
            self, method, url, body, headers):

        global DELETE_GROUP_CALLS
        if self.type == 'DELETE':
            if DELETE_GROUP_CALLS > 3:
                fixture = 'v3__SoftLayer_Account_getScaleGroups_emtpy.xml'
            else:
                DELETE_GROUP_CALLS = DELETE_GROUP_CALLS + 1
                fixture = 'v3__SoftLayer_Account_getScaleGroups.xml'
        else:
            fixture = 'v3__SoftLayer_Account_getScaleGroups.xml'

        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_getResourceUseTriggers(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_getResourceUseTriggers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_deleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_deleteObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_Trigger_ResourceUse_createObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_Trigger_ResourceUse_createObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_Trigger_ResourceUse_getObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_Trigger_ResourceUse_getObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3_SoftLayer_Scale_Policy_Trigger_ResourceUse_deleteObject(
            self, method, url, body, headers):
        body = self.fixtures.load('v3__SoftLayer_Scale_Policy_Trigger_ResourceUse_deleteObject.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
