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

from zope.interface.verify import verifyObject

from libcloud.interface import IResponse, INode, INodeSize, INodeImage, INodeDriver
from libcloud.interface import IConnectionKey, IConnectionUserAndKey
from libcloud.base import Response, Node, NodeSize, NodeImage, NodeDriver
from libcloud.base import ConnectionKey, ConnectionUserAndKey

from test import MockResponse

class FakeDriver(object):
    type = 0

class BaseTests(unittest.TestCase):

    def test_base_node(self):
        node = Node(id=0, name=0, state=0, public_ip=0, private_ip=0,
            driver=FakeDriver())
        verifyObject(INode, node)

    def test_base_node_size(self):
        node_size = NodeSize(id=0, name=0, ram=0, disk=0, bandwidth=0, price=0,
            driver=FakeDriver())
        verifyObject(INodeSize, node_size)

    def test_base_node_image(self):
        node_image = NodeImage(id=0, name=0, driver=FakeDriver())
        verifyObject(INodeImage, node_image)

    def test_base_response(self):
        verifyObject(IResponse, Response(MockResponse(status=200,
                                                      body='foo')))

    def test_base_node_driver(self):
        node_driver = NodeDriver('foo')
        verifyObject(INodeDriver, node_driver)

    def test_base_connection_key(self):
        conn = ConnectionKey('foo')
        verifyObject(IConnectionKey, conn)

    def test_base_connection_userkey(self):
        conn = ConnectionUserAndKey('foo', 'bar')
        verifyObject(IConnectionUserAndKey, conn)

#    def test_drivers_interface(self):
#        failures = []
#        for driver in DRIVERS:
#            creds = ProviderCreds(driver, 'foo', 'bar')
#            try:
#                verifyObject(INodeDriver, get_driver(driver)(creds))
#            except BrokenImplementation:
#                failures.append(DRIVERS[driver][1])
#
#        if failures:
#            self.fail('the following drivers do not support the \
#                       INodeDriver interface: %s' % (', '.join(failures)))

#    def test_invalid_creds(self):
#        failures = []
#        for driver in DRIVERS:
#            if driver == Provider.DUMMY:
#                continue
#            conn = connect(driver, 'bad', 'keys')
#            try:
#                conn.list_nodes()
#            except InvalidCredsException:
#                pass
#            else:
#                failures.append(DRIVERS[driver][1])
#
#        if failures:
#            self.fail('the following drivers did not throw an \
#                       InvalidCredsException: %s' % (', '.join(failures)))

if __name__ == '__main__':
    sys.exit(unittest.main())
