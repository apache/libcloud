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
import unittest
from libcloud.utils.py3 import httplib
import sys

from libcloud.compute.types import InvalidCredsError
from libcloud.compute.drivers.ibm_sbc import IBMNodeDriver as IBM
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import IBM_PARAMS

class IBMTests(unittest.TestCase, TestCaseMixin):
    """
    Tests the IBM Developer Cloud driver.
    """

    def setUp(self):
        IBM.connectionCls.conn_classes = (None, IBMMockHttp)
        IBMMockHttp.type = None
        self.driver = IBM(*IBM_PARAMS)

    def test_auth(self):
        IBMMockHttp.type = 'UNAUTHORIZED'

        try:
            self.driver.list_nodes()
        except InvalidCredsError:
            e = sys.exc_info()[1]
            self.assertTrue(isinstance(e, InvalidCredsError))
            self.assertEquals(e.value, '401: Unauthorized')
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEquals(len(ret), 3)
        self.assertEquals(ret[0].id, '26557')
        self.assertEquals(ret[0].name, 'Insight Instance')
        self.assertEquals(ret[0].public_ips, ['129.33.196.128'])
        self.assertEquals(ret[0].private_ips, [])  # Private IPs not supported
        self.assertEquals(ret[1].public_ips, [])   # Node is non-active (no IP)
        self.assertEquals(ret[1].private_ips, [])
        self.assertEquals(ret[1].id, '28193')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEquals(len(ret), 9) # 9 instance configurations supported
        self.assertEquals(ret[0].id, 'BRZ32.1/2048/60*175')
        self.assertEquals(ret[1].id, 'BRZ64.2/4096/60*500*350')
        self.assertEquals(ret[2].id, 'COP32.1/2048/60')
        self.assertEquals(ret[0].name, 'Bronze 32 bit')
        self.assertEquals(ret[0].disk, None)

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(len(ret), 21)
        self.assertEqual(ret[10].name, "Rational Asset Manager 7.2.0.1")
        self.assertEqual(ret[9].id, '10002573')

    def test_list_locations(self):
        ret = self.driver.list_locations()
        self.assertEquals(len(ret), 1)
        self.assertEquals(ret[0].id, '1')
        self.assertEquals(ret[0].name, 'US North East: Poughkeepsie, NY')
        self.assertEquals(ret[0].country, 'US')

    def test_create_node(self):
        # Test creation of node
        IBMMockHttp.type = 'CREATE'
        image = NodeImage(id=11, name='Rational Insight', driver=self.driver)
        size = NodeSize('LARGE', 'LARGE', None, None, None, None, self.driver)
        location = NodeLocation('1', 'POK', 'US', driver=self.driver)
        ret = self.driver.create_node(name='RationalInsight4',
                                      image=image,
                                      size=size,
                                      location=location,
                                      publicKey='MyPublicKey',
                                      configurationData={
                                           'insight_admin_password': 'myPassword1',
                                           'db2_admin_password': 'myPassword2',
                                           'report_user_password': 'myPassword3'})
        self.assertTrue(isinstance(ret, Node))
        self.assertEquals(ret.name, 'RationalInsight4')

        # Test creation attempt with invalid location
        IBMMockHttp.type = 'CREATE_INVALID'
        location = NodeLocation('3', 'DOESNOTEXIST', 'US', driver=self.driver)
        try:
            ret = self.driver.create_node(name='RationalInsight5',
                                          image=image,
                                          size=size,
                                          location=location,
                                          publicKey='MyPublicKey',
                                          configurationData={
                                               'insight_admin_password': 'myPassword1',
                                               'db2_admin_password': 'myPassword2',
                                               'report_user_password': 'myPassword3'})
        except Exception:
            e = sys.exc_info()[1]
            self.assertEquals(e.args[0], 'Error 412: No DataCenter with id: 3')
        else:
            self.fail('test should have thrown')

    def test_destroy_node(self):
        # Delete existant node
        nodes = self.driver.list_nodes()            # retrieves 3 nodes
        self.assertEquals(len(nodes), 3)
        IBMMockHttp.type = 'DELETE'
        toDelete = nodes[1]
        ret = self.driver.destroy_node(toDelete)
        self.assertTrue(ret)

        # Delete non-existant node
        IBMMockHttp.type = 'DELETED'
        nodes = self.driver.list_nodes()            # retrieves 2 nodes
        self.assertEquals(len(nodes), 2)
        try:
            self.driver.destroy_node(toDelete)      # delete non-existent node
        except Exception:
            e = sys.exc_info()[1]
            self.assertEquals(e.args[0], 'Error 404: Invalid Instance ID 28193')
        else:
            self.fail('test should have thrown')

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        IBMMockHttp.type = 'REBOOT'

        # Reboot active node
        self.assertEquals(len(nodes), 3)
        ret = self.driver.reboot_node(nodes[0])
        self.assertTrue(ret)

        # Reboot inactive node
        try:
            ret = self.driver.reboot_node(nodes[1])
        except Exception:
            e = sys.exc_info()[1]
            self.assertEquals(e.args[0], 'Error 412: Instance must be in the Active state')
        else:
            self.fail('test should have thrown')

class IBMMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('ibm_sbc')

    def _computecloud_enterprise_api_rest_20100331_instances(self, method, url, body, headers):
        body = self.fixtures.load('instances.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_DELETED(self, method, url, body, headers):
        body = self.fixtures.load('instances_deleted.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, body, {}, httplib.responses[httplib.UNAUTHORIZED])

    def _computecloud_enterprise_api_rest_20100331_offerings_image(self, method, url, body, headers):
        body = self.fixtures.load('images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_locations(self, method, url, body, headers):
        body = self.fixtures.load('locations.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_26557_REBOOT(self, method, url, body, headers):
        body = self.fixtures.load('reboot_active.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_28193_REBOOT(self, method, url, body, headers):
        return (412, 'Error 412: Instance must be in the Active state', {}, 'Precondition Failed')

    def _computecloud_enterprise_api_rest_20100331_instances_28193_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('delete.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_28193_DELETED(self, method, url, body, headers):
        return (404, 'Error 404: Invalid Instance ID 28193', {}, 'Precondition Failed')

    def _computecloud_enterprise_api_rest_20100331_instances_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _computecloud_enterprise_api_rest_20100331_instances_CREATE_INVALID(self, method, url, body, headers):
        return (412, 'Error 412: No DataCenter with id: 3', {}, 'Precondition Failed')

    # This is only to accomodate the response tests built into test\__init__.py
    def _computecloud_enterprise_api_rest_20100331_instances_26557(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('delete.xml')
        else:
            body = self.fixtures.load('reboot_active.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
