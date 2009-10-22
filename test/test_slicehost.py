# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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

from libcloud.providers import Slicehost
from libcloud.types import Provider, NodeState
from libcloud.base import Node, NodeImage, NodeSize

import httplib

from test import MockHttp, multipleresponse, TestCaseMixin
from secrets import SLICEHOST_KEY
from xml.etree import ElementTree as ET

class SlicehostTest(unittest.TestCase, TestCaseMixin):

    def setUp(self):

        Slicehost.connectionCls.conn_classes = (None, SlicehostMockHttp)
        SlicehostMockHttp.type = None
        self.driver = Slicehost('foo')
        #self.driver = Slicehost(SLICEHOST_KEY)

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual(node.public_ip, '174.143.212.229')
        self.assertEqual(node.private_ip, '10.176.164.199')
        self.assertEqual(node.state, NodeState.PENDING)

        SlicehostMockHttp.type = 'UNAUTHORIZED'
        try:
            ret = self.driver.list_nodes()
        except Exception, e:
            self.assertEqual(e.message, 'HTTP Basic: Access denied.')
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
        self.assertEqual(image.id, 2)

    def test_reboot_node(self):
        node = Node(id=1, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)

        ret = node.reboot()
        self.assertTrue(ret is True)

        ret = self.driver.reboot_node(node)
        self.assertTrue(ret is True)

        SlicehostMockHttp.type = 'FORBIDDEN'
        try:
            ret = self.driver.reboot_node(node)
        except Exception, e:
            self.assertEqual(e.message, 'Permission denied')
        else:
            self.fail('test should have thrown')

    def test_destroy_node(self):
        node = Node(id=1, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)

        ret = node.destroy()
        self.assertTrue(ret is True)

        ret = self.driver.destroy_node(node)
        self.assertTrue(ret is True)

    def test_create_node(self):
        image = NodeImage(id=11, name='ubuntu 8.10', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node('slicetest', image, size)
        self.assertEqual(node.name, 'slicetest')

class SlicehostMockHttp(MockHttp):

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
                or not headers.has_key('Content-Type')  \
                or headers['Content-Type'] != 'application/xml':
              err_body = """<?xml version="1.0" encoding="UTF-8"?>
<errors>
  <error>Slice parameters are not properly nested</error>
</errors>"""
              return (httplib.UNPROCESSABLE_ENTITY, err_body, {}, '')

            body = """<slice>
  <name>slicetest</name>
  <image-id type="integer">11</image-id>
  <addresses type="array">
    <address>10.176.168.15</address>
    <address>67.23.20.114</address>
  </addresses>
  <root-password>fooadfa1231</root-password>
  <progress type="integer">0</progress>
  <id type="integer">71907</id>
  <bw-out type="float">0.0</bw-out>
  <bw-in type="float">0.0</bw-in>
  <flavor-id type="integer">1</flavor-id>
  <status>build</status>
  <ip-address>10.176.168.15</ip-address>
</slice>"""
            return (httplib.CREATED, body, {}, '')
        else:
            body = """<slices type="array">
  <slice>
    <name>libcloud-foo</name>
    <image-id type="integer">10</image-id>
    <addresses type="array">
      <address>174.143.212.229</address>
      <address>10.176.164.199</address>
    </addresses>
    <progress type="integer">0</progress>
    <id type="integer">1</id>
    <bw-out type="float">0.0</bw-out>
    <bw-in type="float">0.0</bw-in>
    <flavor-id type="integer">1</flavor-id>
    <status>build</status>
    <ip-address>174.143.212.229</ip-address>
  </slice>
</slices>"""
        
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_xml_UNAUTHORIZED(self, method, url, body, headers):
        err_body = 'HTTP Basic: Access denied.'
        return (httplib.UNAUTHORIZED, err_body, {}, 
                 httplib.responses[httplib.UNAUTHORIZED])

    def _flavors_xml(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8"?>
<flavors type="array">
  <flavor>
    <id type="integer">1</id>
    <name>256 slice</name>
    <price type="integer">2000</price>
    <ram type="integer">256</ram>
  </flavor>
  <flavor>
    <id type="integer">2</id>
    <name>512 slice</name>
    <price type="integer">3800</price>
    <ram type="integer">512</ram>
  </flavor>
  <flavor>
    <id type="integer">3</id>
    <name>1GB slice</name>
    <price type="integer">7000</price>
    <ram type="integer">1024</ram>
  </flavor>
  <flavor>
    <id type="integer">4</id>
    <name>2GB slice</name>
    <price type="integer">13000</price>
    <ram type="integer">2048</ram>
  </flavor>
  <flavor>
    <id type="integer">5</id>
    <name>4GB slice</name>
    <price type="integer">25000</price>
    <ram type="integer">4096</ram>
  </flavor>
  <flavor>
    <id type="integer">6</id>
    <name>8GB slice</name>
    <price type="integer">45000</price>
    <ram type="integer">8192</ram>
  </flavor>
  <flavor>
    <id type="integer">7</id>
    <name>15.5GB slice</name>
    <price type="integer">80000</price>
    <ram type="integer">15872</ram>
  </flavor>
</flavors>
"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _images_xml(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8"?>
<images type="array">
  <image>
    <name>CentOS 5.2</name>
    <id type="integer">2</id>
  </image>
  <image>
    <name>Gentoo 2008.0</name>
    <id type="integer">3</id>
  </image>
  <image>
    <name>Debian 5.0 (lenny)</name>
    <id type="integer">4</id>
  </image>
  <image>
    <name>Fedora 10 (Cambridge)</name>
    <id type="integer">5</id>
  </image>
  <image>
    <name>CentOS 5.3</name>
    <id type="integer">7</id>
  </image>
  <image>
    <name>Ubuntu 9.04 (jaunty)</name>
    <id type="integer">8</id>
  </image>
  <image>
    <name>Arch 2009.02</name>
    <id type="integer">9</id>
  </image>
  <image>
    <name>Ubuntu 8.04.2 LTS (hardy)</name>
    <id type="integer">10</id>
  </image>
  <image>
    <name>Ubuntu 8.10 (intrepid)</name>
    <id type="integer">11</id>
  </image>
  <image>
    <name>Red Hat EL 5.3</name>
    <id type="integer">12</id>
  </image>
  <image>
    <name>Fedora 11 (Leonidas)</name>
    <id type="integer">13</id>
  </image>
</images>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _slices_1_reboot_xml(self, method, url, body, headers):
        body = """<slice>
  <name>libcloud-test</name>
  <image-id type="integer">10</image-id>
  <addresses type="array">
    <address>174.143.212.229</address>
    <address>10.176.164.199</address>
  </addresses>
  <progress type="integer">100</progress>
  <id type="integer">70507</id>
  <bw-out type="float">0.0</bw-out>
  <bw-in type="float">0.0</bw-in>
  <flavor-id type="integer">1</flavor-id>
  <status>reboot</status>
  <ip-address>174.143.212.229</ip-address>
</slice>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


    def _slices_1_reboot_xml_FORBIDDEN(self, method, url, body, headers):
        err_body = """<errors>
  <error>Permission denied</error>
</errors>"""
        return (httplib.FORBIDDEN, err_body, {}, 
                 httplib.responses[httplib.FORBIDDEN])

    def _slices_1_destroy_xml(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
