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

from libcloud.storage.drivers.rgw import S3RGWStorageDriver
from libcloud.storage.drivers.rgw import S3RGWOutscaleStorageDriver
from libcloud.storage.drivers.rgw import S3RGWConnectionAWS4
from libcloud.storage.drivers.rgw import S3RGWConnectionAWS2

from libcloud.test.secrets import STORAGE_S3_PARAMS


class S3RGWTests(unittest.TestCase):
    driver_type = S3RGWStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = 'localhost'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='2',
                                host=self.default_host)

    def setUp(self):
        self.driver = self.create_driver()

    def test_connection_class_type(self):
        res = self.driver.connectionCls is S3RGWConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


class S3RGWOutscaleTests(S3RGWTests):
    driver_type = S3RGWOutscaleStorageDriver
    default_host = 'osu.eu-west-2.outscale.com'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='4')

    def test_connection_class_type(self):
        res = self.driver.connectionCls is S3RGWConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


class S3RGWOutscaleDoubleInstanceTests(S3RGWTests):
    driver_type = S3RGWOutscaleStorageDriver
    default_host = 'osu.eu-west-2.outscale.com'

    def setUp(self):
        self.driver_v2 = self.driver_type(*self.driver_args,
                                          signature_version='2')
        self.driver_v4 = self.driver_type(*self.driver_args,
                                          signature_version='4')

    def test_connection_class_type(self):
        res = self.driver_v2.connectionCls is S3RGWConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

        res = self.driver_v4.connectionCls is S3RGWConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

        # Verify again that connection class hasn't been overriden when
        # instantiating a second driver class
        res = self.driver_v2.connectionCls is S3RGWConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver_v2.connectionCls.host
        self.assertEqual(host, self.default_host)

        host = self.driver_v4.connectionCls.host
        self.assertEqual(host, self.default_host)


if __name__ == '__main__':
    sys.exit(unittest.main())
