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
import httplib
import sys
import unittest
import urlparse

try:
    import json
except ImportError:
    import simplejson as json

from libcloud.types import LibcloudError, InvalidCredsError
from libcloud.drivers.gogrid import GoGridNodeDriver
from libcloud.base import Node, NodeImage, NodeSize, NodeLocation

from test import MockHttp, TestCaseMixin
from test.file_fixtures import FileFixtures


class GoGridTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        GoGridNodeDriver.connectionCls.conn_classes = (None, GoGridMockHttp)
        GoGridMockHttp.type = None
        self.driver = GoGridNodeDriver("foo", "bar")

    def test_create_node(self):
        image = NodeImage(1531, None, self.driver)
        size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)

        node = self.driver.create_node(name='test1', image=image, size=size)
        self.assertEqual(node.name, 'test1')
        self.assertTrue(node.id is not None)
        self.assertEqual(node.extra['password'], 'bebebe')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]

        self.assertEqual(node.id, '90967')
        self.assertEqual(node.extra['password'], 'bebebe')
        self.assertEqual(node.extra['isSandbox'], False)

    def test_reboot_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)

    def test_destroy_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(len(images), 4)
        self.assertEqual(image.name, 'CentOS 5.3 (32-bit) w/ None')
        self.assertEqual(image.id, '1531')

    def test_malformed_reply(self):
        GoGridMockHttp.type = 'FAIL'
        try:
            images = self.driver.list_images()
        except LibcloudError, e:
            self.assertTrue(isinstance(e, LibcloudError))
        else:
            self.fail("test should have thrown")

    def test_invalid_creds(self):
        GoGridMockHttp.type = 'FAIL'
        try:
            nodes = self.driver.list_nodes()
        except InvalidCredsError, e:
            self.assertTrue(e.driver is not None)
            self.assertEqual(e.driver.name, self.driver.name)
        else:
            self.fail("test should have thrown")

    def test_node_creation_without_free_public_ips(self):
        GoGridMockHttp.type = 'NOPUBIPS'
        try:
            image = NodeImage(1531, None, self.driver)
            size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)

            node = self.driver.create_node(name='test1', image=image, size=size)
        except LibcloudError, e:
            self.assertTrue(isinstance(e, LibcloudError))
            self.assertTrue(e.driver is not None)
            self.assertEqual(e.driver.name, self.driver.name)
        else:
            self.fail("test should have thrown")

    def test_list_locations(self):
        locations = self.driver.list_locations()
        location_names = [location.name for location in locations]

        self.assertEqual(len(locations), 2)
        for i in 0, 1:
            self.assertTrue(isinstance(locations[i], NodeLocation))
        self.assertTrue("US-West-1" in location_names)
        self.assertTrue("US-East-1" in location_names)

    def test_ex_save_image(self):
        node = self.driver.list_nodes()[0]
        image = self.driver.ex_save_image(node, "testimage")
        self.assertEqual(image.name, "testimage")

    def test_ex_edit_node(self):
        node = Node(90967, None, None, None, None, self.driver)
        size = NodeSize('512Mb', None, None, None, None, None, driver=self.driver)
        ret = self.driver.ex_edit_node(node=node, size=size)

        self.assertTrue(isinstance(ret, Node))

class GoGridMockHttp(MockHttp):

    fixtures = FileFixtures('gogrid')

    def _api_grid_image_list(self, method, url, body, headers):
        body = self.fixtures.load('image_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_image_list_FAIL(self, method, url, body, headers):
        body = "<h3>some non valid json here</h3>"
        return (httplib.SERVICE_UNAVAILABLE, body, {},
                httplib.responses[httplib.SERVICE_UNAVAILABLE])

    def _api_grid_server_list(self, method, url, body, headers):
        body = self.fixtures.load('server_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_grid_server_list_NOPUBIPS = _api_grid_server_list

    def _api_grid_server_list_FAIL(self, method, url, body, headers):
        return (httplib.FORBIDDEN, "123", {}, httplib.responses[httplib.FORBIDDEN])

    def _api_grid_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list_NOPUBIPS(self, method, url, body, headers):
        body = self.fixtures.load('ip_list_empty.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_power(self, method, url, body, headers):
        body = self.fixtures.load('server_power.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_add(self, method, url, body, headers):
        body = self.fixtures.load('server_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_grid_server_add_NOPUBIPS = _api_grid_server_add

    def _api_grid_server_delete(self, method, url, body, headers):
        body = self.fixtures.load('server_delete.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_server_edit(self, method, url, body, headers):
        body = self.fixtures.load('server_edit.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_support_password_list(self, method, url, body, headers):
        body = self.fixtures.load('password_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    _api_support_password_list_NOPUBIPS = _api_support_password_list

    def _api_grid_image_save(self, method, url, body, headers):
        body = self.fixtures.load('image_save.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_common_lookup_list(self, method, url, body, headers):
        _valid_lookups = ("ip.datacenter",)

        try:
            from urlparse import parse_qs
        except ImportError:
            from cgi import parse_qs

        lookup = parse_qs(urlparse.urlparse(url).query)["lookup"][0]
        if lookup in _valid_lookups:
            fixture_path = "lookup_list_%s.json" % \
                    (lookup.replace(".", "_"))
        else:
            raise NotImplementedError
        body = self.fixtures.load(fixture_path)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
