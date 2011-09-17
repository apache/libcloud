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
from libcloud.compute.drivers.rackspace import OpenStackNodeDriver, OpenStackResponse
from libcloud.compute.base import Node, NodeImage, NodeSize
from libcloud.pricing import set_pricing, clear_pricing_data

from test import MockResponse, MockHttpTestCase, XML_HEADERS
from test.file_fixtures import ComputeFileFixtures, OpenStackFixtures
from test.compute import TestCaseMixin

from test.secrets import OPENSTACK_PARAMS


class OpenStackResponseTestCase(unittest.TestCase):
    XML = """<?xml version="1.0" encoding="UTF-8"?><root/>"""

    def test_simple_xml_content_type_handling(self):
        http_response = MockResponse(200, OpenStackResponseTestCase.XML, headers={'content-type': 'application/xml'})
        body = OpenStackResponse(http_response).parse_body()

        self.assertTrue(hasattr(body, 'tag'), "Body should be parsed as XML")

    def test_extended_xml_content_type_handling(self):
        http_response = MockResponse(200,
                                     OpenStackResponseTestCase.XML,
                                     headers={'content-type': 'application/xml; charset=UTF-8'})
        body = OpenStackResponse(http_response).parse_body()

        self.assertTrue(hasattr(body, 'tag'), "Body should be parsed as XML")

    def test_non_xml_content_type_handling(self):
        RESPONSE_BODY = "Accepted"

        http_response = MockResponse(202, RESPONSE_BODY, headers={'content-type': 'text/html'})
        body = OpenStackResponse(http_response).parse_body()

        self.assertEqual(body, RESPONSE_BODY, "Non-XML body should be returned as is")


class OpenStackTests(unittest.TestCase, TestCaseMixin):
    should_list_locations = False

    driver_type = OpenStackNodeDriver
    driver_args = OPENSTACK_PARAMS

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args)

    def setUp(self):
        self.driver_type.connectionCls.conn_classes = (OpenStackMockHttp, OpenStackMockHttp)
        self.driver_type.connectionCls.auth_url = "https://auth.api.example.com/v1.1/"
        OpenStackMockHttp.type = None
        self.driver = self.create_driver()
        clear_pricing_data()

    def test_auth(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = self.create_driver()
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_auth_missing_key(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED_MISSING_KEY'
        try:
            self.driver = self.create_driver()
        except MalformedResponseError, e:
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_auth_server_error(self):
        OpenStackMockHttp.type = 'INTERNAL_SERVER_ERROR'
        try:
            self.driver = self.create_driver()
        except MalformedResponseError, e:
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        OpenStackMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        OpenStackMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual('67.23.21.33', node.public_ip[0])
        self.assertEqual('10.176.168.218', node.private_ip[0])
        self.assertEqual(node.extra.get('flavorId'), '1')
        self.assertEqual(node.extra.get('imageId'), '11')
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        OpenStackMockHttp.type = 'METADATA'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual(type(node.extra.get('metadata')), type(dict()))
        self.assertEqual(node.extra.get('metadata').get('somekey'),
                         'somevalue')
        OpenStackMockHttp.type = None

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
        OpenStackMockHttp.type = 'EX_SHARED_IP_GROUP'
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)',
                          driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        node = self.driver.create_node(name='racktest', image=image, size=size,
                                       ex_shared_ip_group_id='12345')
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')

    def test_create_node_with_metadata(self):
        OpenStackMockHttp.type = 'METADATA'
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

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 7, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(size.price, 0,
                             'Size price should be zero by default')

    def test_list_sizes_with_specified_pricing(self):
        pricing = dict((str(i), i) for i in range(1, 9))

        set_pricing(driver_type='compute', driver_name='openstack',
                    pricing=pricing)

        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 7, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(size.price, pricing[size.id],
                             'Size price should be zero by default')


class OpenStackMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('openstack')
    auth_fixtures = OpenStackFixtures()
    json_content_headers = {'content-type': 'application/json; charset=UTF-8'}

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_UNAUTHORIZED(self, method, url, body, headers):
        return  (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _v1_0_INTERNAL_SERVER_ERROR(self, method, url, body, headers):
        return (httplib.INTERNAL_SERVER_ERROR, "<h1>500: Internal Server Error</h1>", {}, httplib.responses[httplib.INTERNAL_SERVER_ERROR])

    def _v1_0_UNAUTHORIZED_MISSING_KEY(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_servers_detail_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_empty.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_metadata.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_images(self, method, url, body, headers):
        if method != "POST":
            raise NotImplemented
        # this is currently used for creation of new image with
        # POST request, don't handle GET to avoid possible confusion
        body = self.fixtures.load('v1_slug_images_post.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_images_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_images_detail.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_EX_SHARED_IP_GROUP(self, method, url, body, headers):
        # test_create_node_ex_shared_ip_group
        # Verify that the body contains sharedIpGroupId XML element
        self.assertTrue(body.find('sharedIpGroupId="12345"') != -1)
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_metadata.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or body[:8] != "<reboot ":
            raise NotImplemented
        # only used by reboot() right now, but we will need to parse body someday !!!!
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_limits(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_limits.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
        # only used by destroy node()
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_ips(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_ips.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_5467(self, method, url, body, headers):
        if method != 'DELETE':
            raise NotImplemented
        return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_shared_ip_groups(self, method, url, body, headers):

        fixture = 'v1_slug_shared_ip_group.xml' if method == 'POST' else 'v1_slug_shared_ip_groups.xml'
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_shared_ip_groups_detail.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_3445_ips_public_67_23_21_133(self, method, url, body, headers):
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_444222_action(self, method, url, body, headers):
        if body.find('resize') != -1:
            # test_ex_resize_server
            return (httplib.ACCEPTED, "", headers, httplib.responses[httplib.NO_CONTENT])
        elif body.find('confirmResize') != -1:
            # test_ex_confirm_resize
            return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])
        elif body.find('revertResize') != -1:
            # test_ex_revert_resize
            return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_flavors_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_flavors_detail.xml')
        headers = {'date': 'Tue, 14 Jun 2011 09:43:55 GMT', 'content-length': '529'}
        headers.update(XML_HEADERS)
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _v1_1__auth(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1__auth_UNAUTHORIZED(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth_unauthorized.json')
        return  (httplib.UNAUTHORIZED, body, self.json_content_headers, httplib.responses[httplib.UNAUTHORIZED])

    def _v1_1__auth_UNAUTHORIZED_MISSING_KEY(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth_mssing_token.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1__auth_INTERNAL_SERVER_ERROR(self, method, url, body, headers):
        return (httplib.INTERNAL_SERVER_ERROR, "<h1>500: Internal Server Error</h1>",  {'content-type': 'text/html'}, httplib.responses[httplib.INTERNAL_SERVER_ERROR])



if __name__ == '__main__':
    sys.exit(unittest.main())
