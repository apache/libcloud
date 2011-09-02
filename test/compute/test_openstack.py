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
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

from test.secrets import RACKSPACE_USER, RACKSPACE_KEY
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
        self.assertEqual(len(sizes), 8, 'Wrong sizes count')

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
        self.assertEqual(len(sizes), 8, 'Wrong sizes count')

        for size in sizes:
            self.assertTrue(isinstance(size.price, float),
                            'Wrong size price type')
            self.assertEqual(size.price, pricing[size.id],
                             'Size price should be zero by default')


class OpenStackMockHttp(MockHttp):
    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
        # only used by destroy node()
        return (httplib.ACCEPTED,
                "202 Accepted\n\nThe request is accepted for processing.\n\n   ",
                {'date': 'Thu, 09 Jun 2011 10:51:53 GMT', 'content-length': '58',
                 'content-type': 'text/html; charset=UTF-8'},
                httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_flavors_detail(self, method, url, body, headers):
        body = """<flavors xmlns="http://docs.rackspacecloud.com/servers/api/v1.0">
                    <flavor disk="40" id="3" name="m1.medium" ram="4096"/>
                    <flavor disk="20" id="2" name="m1.small" ram="2048"/>
                    <flavor disk="80" id="4" name="m1.large" ram="8192"/>
                    <flavor disk="0" id="6" name="s1" ram="256"/>
                    <flavor disk="0" id="7" name="s1.swap" ram="256"/>
                    <flavor disk="0" id="1" name="m1.tiny" ram="512"/>
                    <flavor disk="10" id="8" name="s1.tiny" ram="512"/>
                    <flavor disk="160" id="5" name="m1.xlarge" ram="16384"/>
                </flavors>
                """
        return (httplib.OK, body,
                {'date': 'Tue, 14 Jun 2011 09:43:55 GMT', 'content-length': '529', 'content-type': 'application/xml'},
                httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
