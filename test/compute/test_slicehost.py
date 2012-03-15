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
from libcloud.utils.py3 import httplib

from xml.etree import ElementTree as ET

from libcloud.compute.drivers.slicehost import SlicehostNodeDriver as Slicehost
from libcloud.compute.types import NodeState, InvalidCredsError
from libcloud.compute.base import Node, NodeImage, NodeSize

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import SLICEHOST_PARAMS

class SlicehostTest(unittest.TestCase, TestCaseMixin):

    def setUp(self):

        Slicehost.connectionCls.conn_classes = (None, SlicehostMockHttp)
        SlicehostMockHttp.type = None
        self.driver = Slicehost(*SLICEHOST_PARAMS)

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertTrue('174.143.212.229' in node.public_ips)
        self.assertTrue('10.176.164.199' in node.private_ips)
        self.assertEqual(node.state, NodeState.PENDING)

        SlicehostMockHttp.type = 'UNAUTHORIZED'
        try:
            ret = self.driver.list_nodes()
        except InvalidCredsError:
            e = sys.exc_info()[1]
            self.assertEqual(e.value, 'HTTP Basic: Access denied.')
        else:
            self.fail('test should have thrown')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 7)
        size = ret[0]
        self.assertEqual(size.name, '256 slice')

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(len(ret), 11)
        image = ret[0]
        self.assertEqual(image.name, 'CentOS 5.2')
        self.assertEqual(image.id, '2')

    def test_reboot_node(self):
        node = Node(id=1, name=None, state=None, public_ips=None, private_ips=None,
                    driver=self.driver)

        ret = node.reboot()
        self.assertTrue(ret is True)

        ret = self.driver.reboot_node(node)
        self.assertTrue(ret is True)

        SlicehostMockHttp.type = 'FORBIDDEN'
        try:
            ret = self.driver.reboot_node(node)
        except Exception:
            e = sys.exc_info()[1]
            self.assertEqual(e.args[0], 'Permission denied')
        else:
            self.fail('test should have thrown')

    def test_destroy_node(self):
        node = Node(id=1, name=None, state=None, public_ips=None, private_ips=None,
                    driver=self.driver)

        ret = node.destroy()
        self.assertTrue(ret is True)

        ret = self.driver.destroy_node(node)
        self.assertTrue(ret is True)

    def test_create_node(self):
        image = NodeImage(id=11, name='ubuntu 8.10', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node(name='slicetest', image=image, size=size)
        self.assertEqual(node.name, 'slicetest')
        self.assertEqual(node.extra.get('password'), 'fooadfa1231')

class SlicehostMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('slicehost')

    def _slices_xml(self, method, url, body, headers):
        if method == 'POST':
            tree = ET.XML(body)
            name = tree.findtext('name')
            image_id = int(tree.findtext('image-id'))
            flavor_id = int(tree.findtext('flavor-id'))

            # TODO: would be awesome to get the slicehost api developers to fill in the
            # the correct validation logic
            if not (name and image_id and flavor_id) \
                or tree.tag != 'slice' \
                or not 'Content-Type' in headers  \
                or headers['Content-Type'] != 'application/xml':

                err_body = self.fixtures.load('slices_error.xml')
                return (httplib.UNPROCESSABLE_ENTITY, err_body, {}, '')

            body = self.fixtures.load('slices_post.xml')
            return (httplib.CREATED, body, {}, '')
        else:
            body = self.fixtures.load('slices_get.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_xml_UNAUTHORIZED(self, method, url, body, headers):
        err_body = 'HTTP Basic: Access denied.'
        return (httplib.UNAUTHORIZED, err_body, {},
                httplib.responses[httplib.UNAUTHORIZED])

    def _flavors_xml(self, method, url, body, headers):
        body = self.fixtures.load('flavors.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_xml(self, method, url, body, headers):
        body = self.fixtures.load('images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_1_reboot_xml(self, method, url, body, headers):
        body = self.fixtures.load('slices_1_reboot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_1_reboot_xml_FORBIDDEN(self, method, url, body, headers):
        body = self.fixtures.load('slices_1_reboot_forbidden.xml')
        return (httplib.FORBIDDEN, body, {}, httplib.responses[httplib.FORBIDDEN])

    def _slices_1_destroy_xml(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
