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

from libcloud.compute.drivers.rackspace import OpenStackResponse
from libcloud.compute.drivers.rackspace import OpenStackNodeDriver as OpenStack
from libcloud.compute.base import Node
from libcloud.pricing import set_pricing

from test import MockResponse, MockHttpTestCase
from test.file_fixtures import ComputeFileFixtures

from test.secrets import NOVA_USERNAME, NOVA_API_KEY, NOVA_HOST, NOVA_PORT
from test.secrets import NOVA_SECURE


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


class OpenStackTests(unittest.TestCase):
    def setUp(self):
        OpenStack.connectionCls.conn_classes = (OpenStackMockHttp, None)
        OpenStackMockHttp.type = None
        self.driver = OpenStack(NOVA_USERNAME, NOVA_API_KEY, NOVA_SECURE,
                                NOVA_HOST, NOVA_PORT)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True, 'Unsuccessful node destroying')

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
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_metadata.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_images(self, method, url, body, headers):
        if method != "POST":
            raise NotImplemented
        # this is currently used for creation of new image with
        # POST request, don't handle GET to avoid possible confusion
        body = self.fixtures.load('v1_slug_images_post.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_images_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_images_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_EX_SHARED_IP_GROUP(self, method, url, body, headers):
        # test_create_node_ex_shared_ip_group
        # Verify that the body contains sharedIpGroupId XML element
        self.assertTrue(body.find('sharedIpGroupId="12345"') != -1)
        body = self.fixtures.load('v1_slug_servers.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_METADATA(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_metadata.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or body[:8] != "<reboot ":
            raise NotImplemented
        # only used by reboot() right now, but we will need to parse body someday !!!!
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_limits(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_limits.xml')
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
        # only used by destroy node()
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_ips(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_ips.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_5467(self, method, url, body, headers):
        if method != 'DELETE':
            raise NotImplemented
        return (httplib.NO_CONTENT, "", {}, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_shared_ip_groups(self, method, url, body, headers):

        fixture = 'v1_slug_shared_ip_group.xml' if method == 'POST' else 'v1_slug_shared_ip_groups.xml'
        body = self.fixtures.load(fixture)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_shared_ip_groups_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_shared_ip_groups_detail.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

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
        return (httplib.OK, body,
                {'date': 'Tue, 14 Jun 2011 09:43:55 GMT', 'content-length': '529', 'content-type': 'application/xml'},
                httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
