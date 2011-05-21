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

import unittest
import sys
import random
import string
import httplib
import xmlrpclib

from libcloud.compute.drivers.gandi import GandiNodeDriver as Gandi
from libcloud.compute.types import NodeState

from xml.etree import ElementTree as ET
from test import MockHttp
from test.file_fixtures import ComputeFileFixtures
from test.secrets import GANDI_USER

class MockGandiTransport(xmlrpclib.Transport):

    def request(self, host, handler, request_body, verbose=0):
        self.verbose = 0
        method = ET.XML(request_body).find('methodName').text
        mock = GandiMockHttp(host, 80)
        mock.request('POST', "%s/%s" % (handler, method))
        resp = mock.getresponse()

        if sys.version[0] == '2' and sys.version[2] == '7':
            response = self.parse_response(resp)
        else:
            response = self.parse_response(resp.body)
        return response

class GandiTests(unittest.TestCase):

    node_name = 'test2'
    def setUp(self):
        Gandi.connectionCls.proxyCls.transportCls = [MockGandiTransport, MockGandiTransport]
        self.driver = Gandi(GANDI_USER)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(len(nodes)>0)

    def test_list_locations(self):
        loc = filter(lambda x: 'france' in x.country.lower(), self.driver.list_locations())[0]
        self.assertEqual(loc.country, 'France')

    def test_list_images(self):
        loc = filter(lambda x: 'france' in x.country.lower(), self.driver.list_locations())[0]
        images = self.driver.list_images(loc)
        self.assertTrue(len(images)>2)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes)>=1)

    def test_destroy_node_running(self):
        nodes = self.driver.list_nodes()
        test_node = filter(lambda x: x.state == NodeState.RUNNING, nodes)[0]
        self.assertTrue(self.driver.destroy_node(test_node))

    def test_destroy_node_halted(self):
        nodes = self.driver.list_nodes()
        test_node = filter(lambda x: x.state == NodeState.TERMINATED, nodes)[0]
        self.assertTrue(self.driver.destroy_node(test_node))

    def test_reboot_node(self):
        nodes = self.driver.list_nodes()
        test_node = filter(lambda x: x.state == NodeState.RUNNING, nodes)[0]
        self.assertTrue(self.driver.reboot_node(test_node))

    def test_create_node(self):
        login = 'libcloud'
        passwd = ''.join(random.choice(string.letters + string.digits) for i in xrange(10))
        # Get france datacenter
        loc = filter(lambda x: 'france' in x.country.lower(), self.driver.list_locations())[0]
        # Get a debian image
        images = self.driver.list_images(loc)
        images = [x for x in images if x.name.lower().startswith('debian')]
        img = filter(lambda x: '5' in x.name, images)[0]
        # Get a configuration size
        size = self.driver.list_sizes()[0]
        node = self.driver.create_node(name=self.node_name,login=login,password=passwd,image=img,location=loc,size=size)
        self.assertEqual(node.name, self.node_name)

class GandiMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('gandi')

    def _xmlrpc_2_0__datacenter_list(self, method, url, body, headers):
        body = self.fixtures.load('datacenter_list.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__image_list(self, method, url, body, headers):
        body = self.fixtures.load('image_list_dc0.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_list(self, method, url, body, headers):
        body = self.fixtures.load('vm_list.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__account_info(self, method, url, body, headers):
        body = self.fixtures.load('account_info.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_info(self, method, url, body, headers):
        body = self.fixtures.load('vm_info.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_delete(self, method, url, body, headers):
        body = self.fixtures.load('vm_delete.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__operation_info(self, method, url, body, headers):
        body = self.fixtures.load('operation_info.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_create_from(self, method, url, body, headers):
        body = self.fixtures.load('vm_create_from.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_reboot(self, method, url, body, headers):
        body = self.fixtures.load('vm_reboot.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_2_0__vm_stop(self, method, url, body, headers):
        body = self.fixtures.load('vm_stop.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
