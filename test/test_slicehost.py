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
from libcloud.types import Provider, NodeState, Node

import httplib

from test import MockHttp

class SlicehostTests(unittest.TestCase):

    def setUp(self):
        Slicehost.connectionCls.conn_classes = (None, SlicehostMockHttp)
        self.driver = Slicehost('foo')

    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertEqual(node.ipaddress, '174.143.212.229')
        self.assertEqual(node.state, NodeState.PENDING)

    def test_reboot_node(self):
        node = Node(None, None, None, None, attrs={'id': 1})
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(None, None, None, None, attrs={'id': 1})
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret is True)


class SlicehostMockHttp(MockHttp):
    def _slices_xml(self, method, url, body, headers):
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

    def _slices_1_destroy_xml(self, method, url, body, headers):
        body = ''
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
