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
import types

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import method_type
from libcloud.utils.py3 import u

from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.drivers.openstack import (
    OpenStack_1_0_NodeDriver, OpenStack_1_0_Response,
    OpenStack_1_1_NodeDriver
)
from libcloud.compute.base import Node, NodeImage, NodeSize
from libcloud.pricing import set_pricing, clear_pricing_data

from test import MockResponse, MockHttpTestCase, XML_HEADERS
from test.file_fixtures import ComputeFileFixtures, OpenStackFixtures
from test.compute import TestCaseMixin

from test.secrets import OPENSTACK_PARAMS


class OpenStack_1_0_ResponseTestCase(unittest.TestCase):
    XML = """<?xml version="1.0" encoding="UTF-8"?><root/>"""

    def test_simple_xml_content_type_handling(self):
        http_response = MockResponse(200, OpenStack_1_0_ResponseTestCase.XML, headers={'content-type': 'application/xml'})
        body = OpenStack_1_0_Response(http_response, None).parse_body()

        self.assertTrue(hasattr(body, 'tag'), "Body should be parsed as XML")

    def test_extended_xml_content_type_handling(self):
        http_response = MockResponse(200,
                                     OpenStack_1_0_ResponseTestCase.XML,
                                     headers={'content-type': 'application/xml; charset=UTF-8'})
        body = OpenStack_1_0_Response(http_response, None).parse_body()

        self.assertTrue(hasattr(body, 'tag'), "Body should be parsed as XML")

    def test_non_xml_content_type_handling(self):
        RESPONSE_BODY = "Accepted"

        http_response = MockResponse(202, RESPONSE_BODY, headers={'content-type': 'text/html'})
        body = OpenStack_1_0_Response(http_response, None).parse_body()

        self.assertEqual(body, RESPONSE_BODY, "Non-XML body should be returned as is")


class OpenStack_1_0_Tests(unittest.TestCase, TestCaseMixin):
    should_list_locations = False

    driver_klass = OpenStack_1_0_NodeDriver
    driver_args = OPENSTACK_PARAMS
    driver_kwargs = {}

    @classmethod
    def create_driver(self):
        if self is not OpenStack_1_0_FactoryMethodTests:
            self.driver_type = self.driver_klass
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (OpenStackMockHttp, OpenStackMockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v1.1/"
        OpenStackMockHttp.type = None
        self.driver = self.create_driver()
        clear_pricing_data()

    def test_auth(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = self.create_driver()
        except InvalidCredsError:
            e = sys.exc_info()[1]
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('test should have thrown')

    def test_auth_missing_key(self):
        OpenStackMockHttp.type = 'UNAUTHORIZED_MISSING_KEY'
        try:
            self.driver = self.create_driver()
        except MalformedResponseError:
            e = sys.exc_info()[1]
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_auth_server_error(self):
        OpenStackMockHttp.type = 'INTERNAL_SERVER_ERROR'
        try:
            self.driver = self.create_driver()
        except MalformedResponseError:
            e = sys.exc_info()[1]
            self.assertEqual(True, isinstance(e, MalformedResponseError))
        else:
            self.fail('test should have thrown')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 1)

    def test_list_nodes(self):
        OpenStackMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        OpenStackMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual('67.23.21.33', node.public_ips[0])
        self.assertEqual('10.176.168.218', node.private_ips[0])
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
        for ret_idx, extra in list(expected.items()):
            for key, value in list(extra.items()):
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
        node = Node(id=72258, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

    def test_ex_limits(self):
        limits = self.driver.ex_limits()
        self.assertTrue("rate" in limits)
        self.assertTrue("absolute" in limits)

    def test_ex_save_image(self):
        node = Node(id=444222, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        image = self.driver.ex_save_image(node, "imgtest")
        self.assertEqual(image.name, "imgtest")
        self.assertEqual(image.id, "12345")

    def test_ex_delete_image(self):
        image = NodeImage(id=333111, name='Ubuntu 8.10 (intrepid)',
                          driver=self.driver)
        ret = self.driver.ex_delete_image(image)
        self.assertTrue(ret)

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
        node = Node(id=444222, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        self.assertTrue(self.driver.ex_resize(node=node, size=size))

    def test_ex_confirm_resize(self):
        node = Node(id=444222, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        self.assertTrue(self.driver.ex_confirm_resize(node=node))

    def test_ex_revert_resize(self):
        node = Node(id=444222, name=None, state=None, public_ips=None,
                    private_ips=None, driver=self.driver)
        self.assertTrue(self.driver.ex_revert_resize(node=node))

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 7, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')

            if self.driver.api_name == 'openstack':
                self.assertEqual(size.price, 0,
                                 'Size price should be zero by default')

    def test_list_sizes_with_specified_pricing(self):
        if self.driver.api_name != 'openstack':
            return

        pricing = dict((str(i), i) for i in range(1, 8))

        set_pricing(driver_type='compute', driver_name='openstack',
                    pricing=pricing)

        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 7, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(float(size.price), float(pricing[size.id]))


class OpenStack_1_0_FactoryMethodTests(OpenStack_1_0_Tests):
    should_list_locations = False

    driver_klass = OpenStack_1_0_NodeDriver
    driver_type = get_driver(Provider.OPENSTACK)
    driver_args = OPENSTACK_PARAMS + ('1.0',)

    def test_factory_method_invalid_version(self):
        try:
            self.driver_type(*(OPENSTACK_PARAMS + ('15.5',)))
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')


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

    def _v1_0_slug_images_333111(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplementedError()
        # this is currently used for deletion of an image
        # as such it should not accept GET/POST
        return(httplib.NO_CONTENT,"","",httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_images(self, method, url, body, headers):
        if method != "POST":
            raise NotImplementedError()
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
        body = u(body)
        self.assertTrue(body.find('sharedIpGroupId="12345"') != -1)
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_metadata.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or body[:8] != "<reboot ":
            raise NotImplementedError()
        # only used by reboot() right now, but we will need to parse body someday !!!!
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_limits(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_limits.xml')
        return (httplib.ACCEPTED, body, XML_HEADERS, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplementedError()
        # only used by destroy node()
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_ips(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_ips.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_5467(self, method, url, body, headers):
        if method != 'DELETE':
            raise NotImplementedError()
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
        body = u(body)
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

    def _v1_1_auth(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_auth_UNAUTHORIZED(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth_unauthorized.json')
        return  (httplib.UNAUTHORIZED, body, self.json_content_headers, httplib.responses[httplib.UNAUTHORIZED])

    def _v1_1_auth_UNAUTHORIZED_MISSING_KEY(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth_mssing_token.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_auth_INTERNAL_SERVER_ERROR(self, method, url, body, headers):
        return (httplib.INTERNAL_SERVER_ERROR, "<h1>500: Internal Server Error</h1>",  {'content-type': 'text/html'}, httplib.responses[httplib.INTERNAL_SERVER_ERROR])

class OpenStack_1_1_Tests(unittest.TestCase, TestCaseMixin):
    should_list_locations = False

    driver_klass = OpenStack_1_1_NodeDriver
    driver_type = OpenStack_1_1_NodeDriver
    driver_args = OPENSTACK_PARAMS
    driver_kwargs = {'ex_force_auth_version': '1.0'}

    @classmethod
    def create_driver(self):
        if self is not OpenStack_1_1_FactoryMethodTests:
            self.driver_type = self.driver_klass
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (OpenStack_1_1_MockHttp, OpenStack_1_1_MockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v1.0/"
        OpenStack_1_1_MockHttp.type = None
        self.driver = self.create_driver()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        node = nodes[0]

        self.assertEqual('12065', node.id)
        self.assertEqual('50.57.94.35', node.public_ips[0])
        self.assertEqual('2001:4801:7808:52:16:3eff:fe47:788a', node.public_ips[1])
        self.assertEqual('10.182.64.34', node.private_ips[0])
        self.assertEqual('fec0:4801:7808:52:16:3eff:fe60:187d', node.private_ips[1])

        self.assertEqual(node.extra.get('flavorId'), '2')
        self.assertEqual(node.extra.get('imageId'), '7')
        self.assertEqual(node.extra.get('metadata'), {})

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 8, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(size.price, 0,
                             'Size price should be zero by default')

    def test_list_sizes_with_specified_pricing(self):

        pricing = dict((str(i), i*5.0) for i in range(1, 9))

        set_pricing(driver_type='compute', driver_name='openstack', pricing=pricing)

        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 8, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(size.price, pricing[size.id],
                             'Size price should match')

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 13, 'Wrong images count')

        image = images[0]
        self.assertEqual(image.id, '13')
        self.assertEqual(image.name, 'Windows 2008 SP2 x86 (B24)')
        self.assertEqual(image.extra['updated'], '2011-08-06T18:14:02Z')
        self.assertEqual(image.extra['created'], '2011-08-06T18:13:11Z')
        self.assertEqual(image.extra['status'], 'ACTIVE')
        self.assertEqual(image.extra['metadata']['os_type'], 'windows')

    def test_create_node(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='racktest', image=image, size=size)
        self.assertEqual(node.id, '26f7fbee-8ce1-4c28-887a-bfe8e4bb10fe')
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra['password'], 'racktestvJq7d3')
        self.assertEqual(node.extra['metadata']['My Server Name'], 'Apache1')

    def test_destroy_node(self):
        self.assertTrue(self.node.destroy())

    def test_reboot_node(self):
        self.assertTrue(self.node.reboot())

    def test_ex_set_password(self):
        try:
            self.driver.ex_set_password(self.node, 'New1&53jPass')
        except Exception:
            e = sys.exc_info()[1]
            self.fail('An error was raised: ' + repr(e))

    def test_ex_rebuild(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver)
        try:
            self.driver.ex_rebuild(self.node, image=image)
        except Exception:
            e = sys.exc_info()[1]
            self.fail('An error was raised: ' + repr(e))

    def test_ex_resize(self):
        size = NodeSize(1, '256 slice', None, None, None, None,
                        driver=self.driver)
        try:
            self.driver.ex_resize(self.node, size)
        except Exception:
            e = sys.exc_info()[1]
            self.fail('An error was raised: ' + repr(e))

    def test_ex_confirm_resize(self):
        try:
            self.driver.ex_confirm_resize(self.node)
        except Exception:
            e = sys.exc_info()[1]
            self.fail('An error was raised: ' + repr(e))

    def test_ex_revert_resize(self):
        try:
            self.driver.ex_revert_resize(self.node)
        except Exception:
            e = sys.exc_info()[1]
            self.fail('An error was raised: ' + repr(e))

    def test_ex_save_image(self):
        image = self.driver.ex_save_image(self.node, 'new_image')
        self.assertEqual(image.name, 'new_image')
        self.assertEqual(image.id, '4949f9ee-2421-4c81-8b49-13119446008b')

    def test_ex_set_server_name(self):
        old_node = Node(
            id='12064', name=None, state=None,
            public_ips=None, private_ips=None, driver=self.driver,
        )
        new_node = self.driver.ex_set_server_name(old_node, 'Bob')
        self.assertEqual('Bob', new_node.name)

    def test_ex_set_metadata(self):
        old_node = Node(
            id='12063', name=None, state=None,
            public_ips=None, private_ips=None, driver=self.driver,
        )
        metadata = {'Image Version': '2.1', 'Server Label': 'Web Head 1'}
        returned_metadata = self.driver.ex_set_metadata(old_node, metadata)
        self.assertEqual(metadata, returned_metadata)

    def test_ex_get_metadata(self):
        node = Node(
            id='12063', name=None, state=None,
            public_ips=None, private_ips=None, driver=self.driver,
        )

        metadata = {'Image Version': '2.1', 'Server Label': 'Web Head 1'}
        returned_metadata = self.driver.ex_get_metadata(node)
        self.assertEqual(metadata, returned_metadata)

    def test_ex_update_node(self):
        old_node = Node(
            id='12064',
            name=None, state=None, public_ips=None, private_ips=None, driver=self.driver,
        )

        new_node = self.driver.ex_update_node(old_node, name='Bob')

        self.assertTrue(new_node)
        self.assertEqual('Bob', new_node.name)
        self.assertEqual('50.57.94.30', new_node.public_ips[0])

    def test_ex_get_node_details(self):
        node_id = '12064'
        node = self.driver.ex_get_node_details(node_id)
        self.assertEqual(node.id, '12064')
        self.assertEqual(node.name, 'lc-test')

    def test_ex_get_size(self):
        size_id = '7'
        size = self.driver.ex_get_size(size_id)
        self.assertEqual(size.id, size_id)
        self.assertEqual(size.name, '15.5GB slice')

    def test_ex_get_image(self):
        image_id = '13'
        image = self.driver.ex_get_image(image_id)
        self.assertEqual(image.id, image_id)
        self.assertEqual(image.name, 'Windows 2008 SP2 x86 (B24)')

    def test_ex_delete_image(self):
        image = NodeImage(id='26365521-8c62-11f9-2c33-283d153ecc3a', name='My Backup', driver=self.driver)
        result = self.driver.ex_delete_image(image)
        self.assertTrue(result)

    def test_extract_image_id_from_url(self):
        url = 'http://127.0.0.1/v1.1/68/images/1d4a8ea9-aae7-4242-a42d-5ff4702f2f14'
        url_two = 'http://127.0.0.1/v1.1/68/images/13'
        image_id = self.driver._extract_image_id_from_url(url)
        image_id_two = self.driver._extract_image_id_from_url(url_two)
        self.assertEqual(image_id, '1d4a8ea9-aae7-4242-a42d-5ff4702f2f14')
        self.assertEqual(image_id_two, '13')

class OpenStack_1_1_FactoryMethodTests(OpenStack_1_1_Tests):
    should_list_locations = False

    driver_klass = OpenStack_1_1_NodeDriver
    driver_type = get_driver(Provider.OPENSTACK)
    driver_args = OPENSTACK_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '1.0'}

class OpenStack_1_1_MockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('openstack_v1.1')
    auth_fixtures = OpenStackFixtures()
    json_content_headers = {'content-type': 'application/json; charset=UTF-8'}

    def _v2_0_tokens(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v2_0__auth.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_0(self, method, url, body, headers):
        headers = {
            'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
            'x-server-management-url': 'https://api.example.com/v1.1/slug',
        }
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_1_slug_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load('_servers_detail.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_flavors_detail(self, method, url, body, headers):
        body = self.fixtures.load('_flavors_detail.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_images_detail(self, method, url, body, headers):
        body = self.fixtures.load('_images_detail.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_servers(self, method, url, body, headers):
        if method == "POST":
            body = self.fixtures.load('_servers_create.json')
        elif method == "GET":
            body = self.fixtures.load('_servers.json')
        else:
            raise NotImplementedError()

        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_servers_26f7fbee_8ce1_4c28_887a_bfe8e4bb10fe(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_servers_26f7fbee_8ce1_4c28_887a_bfe8e4bb10fe.json')
        else:
            raise NotImplementedError()

        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_servers_12065_action(self, method, url, body, headers):
        if method != "POST":
            self.fail('HTTP method other than POST to action URL')

        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_1_slug_servers_12064_action(self, method, url, body, headers):
        if method != "POST":
            self.fail('HTTP method other than POST to action URL')
        if "createImage" in json.loads(body):
            return (httplib.ACCEPTED, "",
                    {"location": "http://127.0.0.1/v1.1/68/images/4949f9ee-2421-4c81-8b49-13119446008b"},
                    httplib.responses[httplib.ACCEPTED])

        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_1_slug_servers_12065(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])
        else:
            raise NotImplementedError()

    def _v1_1_slug_servers_12064(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_servers_12064.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        elif method == "PUT":
            body = self.fixtures.load('_servers_12064_updated_name_bob.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        elif method == "DELETE":
            return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])
        else:
            raise NotImplementedError()

    def _v1_1_slug_servers_12062(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_servers_12064.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_servers_12063_metadata(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_servers_12063_metadata_two_keys.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        elif method == "PUT":
            body = self.fixtures.load('_servers_12063_metadata_two_keys.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])

    def _v1_1_slug_flavors_7(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_flavors_7.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        else:
            raise NotImplementedError()

    def _v1_1_slug_images_13(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_images_13.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        else:
            raise NotImplementedError()

    def _v1_1_slug_images_26365521_8c62_11f9_2c33_283d153ecc3a(self, method, url, body, headers):
        if method == "DELETE":
            return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])
        else:
            raise NotImplementedError()

    def _v1_1_slug_images_4949f9ee_2421_4c81_8b49_13119446008b(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_images_4949f9ee_2421_4c81_8b49_13119446008b.json')
            return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])
        else:
            raise NotImplementedError()

class OpenStack_1_1_Auth_2_0_MockHttp(OpenStack_1_1_MockHttp):
    fixtures = ComputeFileFixtures('openstack_v1.1')
    auth_fixtures = OpenStackFixtures()
    json_content_headers = {'content-type': 'application/json; charset=UTF-8'}

    def __init__(self, *args, **kwargs):
        super(OpenStack_1_1_Auth_2_0_MockHttp, self).__init__(*args, **kwargs)

        # TODO Figure out why 1.1 tests are using some 1.0 endpoints
        methods1 = OpenStackMockHttp.__dict__
        methods2 = OpenStack_1_1_MockHttp.__dict__

        names1 = [m for m in methods1 if m.find('_v1_0') == 0]
        names2 = [m for m in methods2 if m.find('_v1_1') == 0]

        for name in names1:
            method = methods1[name]
            new_name = name.replace('_v1_0_slug_', '_v1_0_1337_')
            setattr(self, new_name, method_type(method, self,
                OpenStack_1_1_Auth_2_0_MockHttp))

        for name in names2:
            method = methods2[name]
            new_name = name.replace('_v1_1_slug_', '_v1_0_1337_')
            setattr(self, new_name, method_type(method, self,
                OpenStack_1_1_Auth_2_0_MockHttp))


class OpenStack_1_1_Auth_2_0_Tests(OpenStack_1_1_Tests):
    driver_args = OPENSTACK_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '2.0'}

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = \
                (OpenStack_1_1_Auth_2_0_MockHttp, OpenStack_1_1_Auth_2_0_MockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v2.0/"
        OpenStack_1_1_MockHttp.type = None
        self.driver = self.create_driver()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

        server_url = 'https://servers.api.rackspacecloud.com/v1.0/1337'
        auth_token = 'aaaaaaaaaaaa-bbb-cccccccccccccc'
        tenant_compute = '1337'
        tenant_object_store = 'MossoCloudFS_11111-111111111-1111111111-1111111'

        self.assertEqual(self.driver.connection.server_url, server_url)
        self.assertEqual(self.driver.connection.auth_token, auth_token)
        self.assertEqual(self.driver.connection.tenant_ids,
              {'compute': tenant_compute, 'object-store': tenant_object_store})



if __name__ == '__main__':
    sys.exit(unittest.main())
