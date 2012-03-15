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

from xml.etree import ElementTree as ET

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import xmlrpclib
from libcloud.utils.py3 import next

from libcloud.compute.drivers.softlayer import SoftLayerNodeDriver as SoftLayer
from libcloud.compute.types import NodeState

from test import MockHttp               # pylint: disable-msg=E0611
from test.file_fixtures import ComputeFileFixtures # pylint: disable-msg=E0611
from test.secrets import SOFTLAYER_PARAMS

class MockSoftLayerTransport(xmlrpclib.Transport):

    def request(self, host, handler, request_body, verbose=0):
        self.verbose = 0
        method = ET.XML(request_body).find('methodName').text
        mock = SoftLayerMockHttp(host, 80)
        mock.request('POST', "%s/%s" % (handler, method))
        resp = mock.getresponse()

        if sys.version[0] == '2' and sys.version[2] == '7':
            response = self.parse_response(resp)
        else:
            response = self.parse_response(resp.body)
        return response

class SoftLayerTests(unittest.TestCase):

    def setUp(self):
        SoftLayer.connectionCls.proxyCls.transportCls = [
            MockSoftLayerTransport, MockSoftLayerTransport]
        self.driver = SoftLayer(*SOFTLAYER_PARAMS)

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.name, 'test1')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.extra['password'], 'TEST')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        seattle = next(l for l in locations if l.name == 'sea01')
        self.assertEqual(seattle.country, 'US')
        self.assertEqual(seattle.id, '18171')

    def test_list_images(self):
        images = self.driver.list_images()
        image = images[0]
        self.assertEqual(image.id, '1684')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 2)
        self.assertEqual(sizes[0].id, 'sl1')

class SoftLayerMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('softlayer')

    def _xmlrpc_v3__SoftLayer_Account_getVirtualGuests(
        self, method, url, body, headers):

        body = self.fixtures.load('v3_SoftLayer_Account_getVirtualGuests.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _xmlrpc_v3__SoftLayer_Location_Datacenter_getDatacenters(
        self, method, url, body, headers):

        body = self.fixtures.load(
            'v3_SoftLayer_Location_Datacenter_getDatacenters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
