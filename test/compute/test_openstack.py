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
import string
import unittest
import httplib
import re
from urllib2 import urlparse
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeImage, Node
from libcloud.compute.drivers.openstack import OpenStackNodeDriver, OpenstackNodeSize
from libcloud.compute.types import NodeState
from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

class OpenStackTests(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        OpenStackNodeDriver.connectionCls.conn_classes = (OpenStackMockHttp, OpenStackMockHttp)
        OpenStackMockHttp.type = None
        self.driver = OpenStackNodeDriver(user_name='TestUser', api_key='TestKey',
                                          url='http://test.url.faked.auth:3333/v1.1/')
        self.driver.list_nodes() # to authorize

    def test_auth(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = OpenStackNodeDriver('TestUser', 'TestKey', 'http://test.url.faked.auth:3333/v1.1/')
            self.driver.list_nodes() # authorization if first request
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_auth_missing_key(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED_MISSING_KEY'
        try:
            self.driver = OpenStackNodeDriver('TestUser', 'TestKey', 'http://test.url.faked.auth:3333/v1.1/')
            self.driver.list_nodes() # authorization if first request
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

        #TODO http://docs.openstack.org/bexar/openstack-compute/developer/content/ch03s07.html

    def test_list_nodes(self):
        OpenStackMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        OpenStackMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 2)
        node = ret[0]
        self.assertEqual(u'67.23.10.132', node.public_ip[0])
        self.assertEqual(u'10.176.42.16', node.private_ip[0])
        self.assertEqual(node.extra.get('flavorRef'), 'https://servers.api.rackspacecloud.com/v1.1/32278/flavors/1')
        self.assertEqual(node.extra.get('imageRef'), 'https://servers.api.rackspacecloud.com/v1.1/32278/images/1234')
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        OpenStackMockHttp.type = 'METADATA'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 2)
        node = ret[0]
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        self.assertEqual(node.extra.get('metadata').get('Server Label'), 'Web Head 1')
        self.assertEqual(node.extra.get('metadata').get('Image Version'), '2.1')
        OpenStackMockHttp.type = None

    def get_flavor_by_id(self, list, id):
        for flavor in list:
            if str(flavor.id) == str(id):
                return flavor


    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 2)
        self.get_flavor_by_id(ret, 2)
        size = ret[0]
        self.assertEqual(size.name, '256 MB Server')

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertAlmostEqual(len(ret), 2, 1)

#         def __init__(self, id, name, driver, extra=None):
#        self.id = str(id)
#        self.name = name
#        self.driver = driver
#        if not extra:
#            self.extra = {}
#        else:
#            self.extra = extra
        first = ret[0]
        last = ret[-1]
        self.assertEqual(first.id, str(1))
        self.assertEqual(first.name, 'CentOS 5.2')
#        self.assertEqual(first.extra['serverRef'], None)
        self.assertEqual(last.id, str(5))
        self.assertEqual(last.name, 'CentOS 5.2')
        #TODO self.assertEqual(last.extra['serverRef'], None)

    def test_create_node(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver, extra={'links':[{'href':'http://servers.api.openstack.org/1234/flavors/1'}]})
        size = OpenstackNodeSize(1, '256 slice', None, None, None, None, driver=self.driver, links=[{'href':'http://servers.api.openstack.org/1234/flavors/1'}])
        node = self.driver.create_node(name='new-server-test', image=image, size=size, shared_ip_group='group1')
        self.assertEqual(node.id, str(1235))
        self.assertEqual(node.driver, self.driver)
        self.assertEquals(node.state, NodeState.PENDING)
        self.assertEqual(node.name, 'new-server-test')
        self.assertEqual(node.extra.get('created'),'2010-11-11T12:00:00Z')
        self.assertEqual(node.extra.get('hostId'),'e4d909c290d0fb1ca068ffaddf22cbd0')
        self.assertEqual(node.extra.get('imageRef'),'https://servers.api.openstack.org/v1.1/32278/images/1')
        self.assertEqual(node.extra.get('flavorRef'),'http://servers.api.openstack.org/v1.1/32278/flavors/1')
        self.assertEqual(node.extra.get('progress'),0)
        self.assertEqual(node.extra.get('affinityId'), 'fc88bcf8394db9c8d0564e08ca6a9724188a84d1')
        self.assertEqual(node.extra.get('adminPass'), 'GFf1j9aP')

    def test_create_node_with_metadata(self):
        OpenStackMockHttp.type = 'METADATA'
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver, extra={'links':[{'href':'http://servers.api.openstack.org/1234/flavors/1'}]})
        size = OpenstackNodeSize(1, '256 slice', None, None, None, None, driver=self.driver, links=[{'href':'http://servers.api.openstack.org/1234/flavors/1'}])
        metadata = {u'My Server Name': u'Apache1'}
        files = {'/file1': 'content1', '/file2': 'content2'}
        node = self.driver.create_node(name='new-server-test', image=image, size=size, metadata=metadata, files=files)
        self.assertEqual(node.name, 'new-server-test')
        self.assertEqual(node.extra.get('adminPass'), u'GFf1j9aP')
        self.assertEqual(node.extra.get('metadata'), metadata)

    def test_reboot_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_ex_limits(self):
        limits = self.driver.ex_limits()
        self.assertTrue("rate" in limits)
        self.assertTrue("absolute" in limits)

# *** Commented because: saving image from node is not implemented in OpenStack yet
#TODO: uncomment after OpenStack is fixed and libcloud is updated accordingly

#    def test_ex_save_image(self):
#        node = Node(id=444222, name=None, state=None, public_ip=None, private_ip=None,
#                    driver=self.driver)
#        image = self.driver.ex_save_image(node, "imgtest")
#        self.assertEqual(image.name, "imgtest")
#        self.assertEqual(image.id, "12345")

# *** Commented because: listing IPs by node is not implemented in OpenStack yet
#TODO: uncomment after OpenStack is fixed and libcloud is updated accordingly

#    def test_ex_list_ip_addresses(self):
#        ret = self.driver.ex_list_ip_addresses(node_id=72258)
#        self.assertEquals(2, len(ret.public_addresses))
#        self.assertTrue('67.23.10.131' in ret.public_addresses)
#        self.assertTrue('67.23.10.132' in ret.public_addresses)
#        self.assertEquals(1, len(ret.private_addresses))
#        self.assertTrue('10.176.42.16' in ret.private_addresses)
#        #
#        #    def test_ex_list_ip_groups(self):
#        #        ret = self.driver.ex_list_ip_groups()
#        #        self.assertEquals(2, len(ret))
#        #        self.assertEquals('1234', ret[0].id)
#        #        self.assertEquals('Shared IP Group 1', ret[0].name)
#        #        self.assertEquals('5678', ret[1].id)
#        #        self.assertEquals('Shared IP Group 2', ret[1].name)
#        #        self.assertTrue(ret[0].servers is None)
#        #
#        #    def test_ex_list_ip_groups_detail(self):
#        #        ret = self.driver.ex_list_ip_groups(details=True)
#
#        self.assertEquals(2, len(ret))
#
#        self.assertEquals('1234', ret[0].id)
#        self.assertEquals('Shared IP Group 1', ret[0].name)
#        self.assertEquals(2, len(ret[0].servers))
#        self.assertEquals('422', ret[0].servers[0])
#        self.assertEquals('3445', ret[0].servers[1])
#
#        self.assertEquals('5678', ret[1].id)
#        self.assertEquals('Shared IP Group 2', ret[1].name)
#        self.assertEquals(3, len(ret[1].servers))
#        self.assertEquals('23203', ret[1].servers[0])
#        self.assertEquals('2456', ret[1].servers[1])
#        self.assertEquals('9891', ret[1].servers[2])


class OpenStackMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('openstack')

    def _v1_1_UNAUTHORIZED(self, method, url, body, headers):
        return  httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED]

    def _v1_1_UNAUTHORIZED_MISSING_KEY(self, method, url, body, headers):
        headers = {'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT]

    def _v1_1_servers_detail_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers, '_empty'))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_detail_METADATA(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or string.find(body, 'reboot') == -1:
            raise NotImplemented
            # only used by reboot() right now, but we will need to parse body someday !!!!
        return httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED]

    def _v1_1_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
            # only used by destroy node()
        return httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED]

    def _form_fixture_name(self, method, url, body, headers, suffix=''):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        action = re.sub('^/v[1-9]\.[0-9]', '', path)
        action = action.replace('/', '_')

        accept = headers.get('accept')
        ext = (not accept or re.search('/json$', accept)) and '.json' or '.xml'

        return 'v1.1_' + method.lower() + action + suffix + ext

    def _v1_1(self, method, url, body, headers):
        headers = {'x-server-management-url': 'http://test.url.faked:4444/v1.1',
                   'x-auth-token': 'faked-x-auth-token-for-test',
                   'x-cdn-management-url': '' #TODO verify normal auth response
        }
        return httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT]

    def _v1_1_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_flavors_detail(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_images_detail(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_1234_detail(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_1234(self, method, url, body, headers):
        # invoked on /servers/1234,  1234 is the first server id in get_servers_detail.json fixture
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_1234_action(self, method, url, body, headers):
        # invoked on /servers/1234/action, 1234 is the first server id in get_servers_detail.json fixture
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_servers_METADATA(self, method, url, body, headers):
        if method != "POST":
            raise NotImplemented
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _v1_1_limits(self, method, url, body, headers):
        body = self.fixtures.load(self._form_fixture_name(method, url, body, headers))
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

if __name__ == '__main__':
    import sys

    sys.exit(unittest.main())
