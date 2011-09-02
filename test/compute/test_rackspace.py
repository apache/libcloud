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
import httplib

from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.compute.drivers.rackspace import RackspaceNodeDriver as Rackspace
from libcloud.compute.drivers.rackspace import OpenStackResponse
from libcloud.compute.drivers.rackspace import OpenStackNodeDriver as OpenStack
from libcloud.compute.base import Node, NodeImage, NodeSize
from libcloud.pricing import set_pricing

from test import MockHttp, MockResponse, MockHttpTestCase
from test.compute.test_openstack import OpenStackMockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import RACKSPACE_USER, RACKSPACE_KEY
from test.secrets import NOVA_USERNAME, NOVA_API_KEY, NOVA_HOST, NOVA_PORT
from test.secrets import NOVA_SECURE


class RackspaceTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        Rackspace.connectionCls.conn_classes = (None, RackspaceMockHttp)
        RackspaceMockHttp.type = None
        self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)

    def test_auth(self):
        RackspaceMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_auth_missing_key(self):
        RackspaceMockHttp.type = 'UNAUTHORIZED_MISSING_KEY'
        try:
            self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)
        except MalformedResponseError, e:
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_auth_server_error(self):
        RackspaceMockHttp.type = 'INTERNAL_SERVER_ERROR'
        try:
            self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)
        except MalformedResponseError, e:
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        RackspaceMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        RackspaceMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual('67.23.21.33', node.public_ip[0])
        self.assertEqual('10.176.168.218', node.private_ip[0])
        self.assertEqual(node.extra.get('flavorId'), '1')
        self.assertEqual(node.extra.get('imageId'), '11')
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        RackspaceMockHttp.type = 'METADATA'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        self.assertEqual(node.extra.get('metadata').get('somekey'),
                         'somevalue')
        RackspaceMockHttp.type = None

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 7)
        size = ret[0]
        self.assertEqual(size.name, '256 slice')
        self.assertTrue(isinstance(size.price, float))

    def test_list_images(self):
        ret = self.driver.list_images()
        expected = {10: {'serverId': None,
                         'status': 'ACTIVE',
                         'created': '2009-07-20T09:14:37-05:00',
                         'updated': '2009-07-20T09:14:37-05:00',
                         'progress': None},
                    11: {'serverId': '91221',
                         'status': 'ACTIVE',
                         'created': '2009-11-29T20:22:09-06:00',
                         'updated': '2009-11-29T20:24:08-06:00',
                         'progress': '100'}}
        for ret_idx, extra in expected.items():
            for key, value in extra.items():
                self.assertEqual(ret[ret_idx].extra[key], value)

    def test_create_node(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)',
                          driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='racktest', image=image, size=size)
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')

    def test_create_node_ex_shared_ip_group(self):
        RackspaceMockHttp.type = 'EX_SHARED_IP_GROUP'
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)',
                          driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='racktest', image=image, size=size,
                                       ex_shared_ip_group_id='12345')
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')

    def test_create_node_with_metadata(self):
        RackspaceMockHttp.type = 'METADATA'
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)',
                          driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        metadata = {'a': 'b', 'c': 'd'}
        files = {'/file1': 'content1', '/file2': 'content2'}
        node = self.driver.create_node(name='racktest', image=image, size=size,
                                       metadata=metadata, files=files)
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')
        self.assertEqual(node.extra.get('metadata'), metadata)

    def test_reboot_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_ex_limits(self):
        limits = self.driver.ex_limits()
        self.assertTrue("rate" in limits)
        self.assertTrue("absolute" in limits)

    def test_ex_save_image(self):
        node = Node(id=444222, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        image = self.driver.ex_save_image(node, "imgtest")
        self.assertEqual(image.name, "imgtest")
        self.assertEqual(image.id, "12345")

    def test_ex_list_ip_addresses(self):
        ret = self.driver.ex_list_ip_addresses(node_id=72258)
        self.assertEquals(2, len(ret.public_addresses))
        self.assertTrue('67.23.10.131' in ret.public_addresses)
        self.assertTrue('67.23.10.132' in ret.public_addresses)
        self.assertEquals(1, len(ret.private_addresses))
        self.assertTrue('10.176.42.16' in ret.private_addresses)

    def test_ex_list_ip_groups(self):
        ret = self.driver.ex_list_ip_groups()
        self.assertEquals(2, len(ret))
        self.assertEquals('1234', ret[0].id)
        self.assertEquals('Shared IP Group 1', ret[0].name)
        self.assertEquals('5678', ret[1].id)
        self.assertEquals('Shared IP Group 2', ret[1].name)
        self.assertTrue(ret[0].servers is None)

    def test_ex_list_ip_groups_detail(self):
        ret = self.driver.ex_list_ip_groups(details=True)

        self.assertEquals(2, len(ret))

        self.assertEquals('1234', ret[0].id)
        self.assertEquals('Shared IP Group 1', ret[0].name)
        self.assertEquals(2, len(ret[0].servers))
        self.assertEquals('422', ret[0].servers[0])
        self.assertEquals('3445', ret[0].servers[1])

        self.assertEquals('5678', ret[1].id)
        self.assertEquals('Shared IP Group 2', ret[1].name)
        self.assertEquals(3, len(ret[1].servers))
        self.assertEquals('23203', ret[1].servers[0])
        self.assertEquals('2456', ret[1].servers[1])
        self.assertEquals('9891', ret[1].servers[2])

    def test_ex_create_ip_group(self):
        ret = self.driver.ex_create_ip_group('Shared IP Group 1', '5467')
        self.assertEquals('1234', ret.id)
        self.assertEquals('Shared IP Group 1', ret.name)
        self.assertEquals(1, len(ret.servers))
        self.assertEquals('422', ret.servers[0])

    def test_ex_delete_ip_group(self):
        ret = self.driver.ex_delete_ip_group('5467')
        self.assertEquals(True, ret)

    def test_ex_share_ip(self):
        ret = self.driver.ex_share_ip('1234', '3445', '67.23.21.133')
        self.assertEquals(True, ret)

    def test_ex_unshare_ip(self):
        ret = self.driver.ex_unshare_ip('3445', '67.23.21.133')
        self.assertEquals(True, ret)

    def test_ex_resize(self):
        node = Node(id=444222, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        self.assertTrue(self.driver.ex_resize(node=node, size=size))

    def test_ex_confirm_resize(self):
        node = Node(id=444222, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        self.assertTrue(self.driver.ex_confirm_resize(node=node))

    def test_ex_revert_resize(self):
        node = Node(id=444222, name=None, state=None, public_ip=None,
                    private_ip=None, driver=self.driver)
        self.assertTrue(self.driver.ex_revert_resize(node=node))


class RackspaceMockHttp(OpenStackMockHttp):

    def _v1_0_slug_flavors_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_flavors_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
