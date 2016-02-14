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
import pickle

from libcloud.compute.drivers.rackspace import RackspaceNodeDriver
from libcloud.compute.drivers.digitalocean import DigitalOceanNodeDriver
from libcloud.test.compute.test_digitalocean_v2 import DigitalOceanMockHttp
from libcloud.test import unittest
from libcloud.test.secrets import DIGITALOCEAN_v2_PARAMS


class PickleDriverClassTestCase(unittest.TestCase):

    def setUp(self):
        DigitalOceanNodeDriver.connectionCls.conn_classes = \
            (None, DigitalOceanMockHttp)
        DigitalOceanMockHttp.type = None
        self.driver = DigitalOceanNodeDriver(*DIGITALOCEAN_v2_PARAMS)

    def test_pickle_and_unpickle_driver_instance(self):
        driver = RackspaceNodeDriver('testkey', 'testsecret', region='iad')

        self.assertEqual(driver.key, 'testkey')
        self.assertEqual(driver.secret, 'testsecret')
        self.assertTrue(driver.connection)
        self.assertEqual(driver.connection.user_id, 'testkey')
        self.assertEqual(driver.connection.key, 'testsecret')

        pickled = pickle.dumps(driver)
        unpickled = pickle.loads(pickled)

        self.assertEqual(unpickled.key, 'testkey')
        self.assertEqual(unpickled.secret, 'testsecret')
        self.assertTrue(unpickled.connection)
        self.assertEqual(unpickled.connection.user_id, 'testkey')
        self.assertEqual(unpickled.connection.key, 'testsecret')

    def test_pickle_and_unpickle_node_instance(self):
        node = self.driver.list_nodes()[0]

        self.assertEqual(node.name, 'example.com')
        self.assertEqual(node.public_ips, ['104.236.32.182'])
        self.assertEqual(node.extra['image']['id'], 6918990)
        self.assertEqual(node.extra['size_slug'], '512mb')
        self.assertEqual(node.driver.name, self.driver.name)

        pickled = pickle.dumps(node)
        unpickled = pickle.loads(pickled)

        self.assertEqual(unpickled.name, 'example.com')
        self.assertEqual(unpickled.public_ips, ['104.236.32.182'])
        self.assertEqual(unpickled.extra['image']['id'], 6918990)
        self.assertEqual(unpickled.extra['size_slug'], '512mb')
        self.assertEqual(unpickled.driver.name, self.driver.name)


if __name__ == '__main__':
    sys.exit(unittest.main())
