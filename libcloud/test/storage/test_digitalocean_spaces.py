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

from libcloud.common.types import LibcloudError

from libcloud.storage.base import Container, Object
from libcloud.storage.drivers.digitalocean_spaces import (
    DigitalOceanSpacesStorageDriver,
    DOSpacesConnectionAWS4,
    DOSpacesConnectionAWS2)

from libcloud.test import LibcloudTestCase
from libcloud.test.secrets import STORAGE_S3_PARAMS


class DigitalOceanSpacesTests(LibcloudTestCase):
    driver_type = DigitalOceanSpacesStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = 'nyc3.digitaloceanspaces.com'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='2',
                                host=self.default_host)

    def setUp(self):
        self.driver = self.create_driver()
        self.container = Container('test-container', {}, self.driver)
        self.object = Object('test-object', 1, 'hash', {},
                             'meta_data', self.container, self.driver)

    def test_connection_class_type(self):
        res = self.driver.connectionCls is DOSpacesConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)

    def test_container_enable_cdn_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.container.enable_cdn()

    def test_container_get_cdn_url_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.container.get_cdn_url()

    def test_object_enable_cdn_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.object.enable_cdn()

    def test_object_get_cdn_url_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.object.get_cdn_url()

    def test_invalid_signature_version(self):
        with self.assertRaises(ValueError):
            self.driver_type(*self.driver_args,
                             signature_version='3',
                             host=self.default_host)

    def test_invalid_region(self):
        with self.assertRaises(LibcloudError):
            self.driver_type(*self.driver_args,
                             region='atlantis',
                             host=self.default_host)


class DigitalOceanSpacesTests_v4(DigitalOceanSpacesTests):
    driver_type = DigitalOceanSpacesStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = 'nyc3.digitaloceanspaces.com'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='4')

    def test_connection_class_type(self):
        res = self.driver.connectionCls is DOSpacesConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


class DigitalOceanSpacesDoubleInstanceTests(LibcloudTestCase):
    driver_type = DigitalOceanSpacesStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = 'nyc3.digitaloceanspaces.com'
    alt_host = 'ams3.digitaloceanspaces.com'

    def setUp(self):
        self.driver_v2 = self.driver_type(*self.driver_args,
                                          signature_version='2')
        self.driver_v4 = self.driver_type(*self.driver_args,
                                          signature_version='4',
                                          region='ams3')

    def test_connection_class_type(self):
        res = self.driver_v2.connectionCls is DOSpacesConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

        res = self.driver_v4.connectionCls is DOSpacesConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

        # Verify again that connection class hasn't been overriden when
        # instantiating a second driver class
        res = self.driver_v2.connectionCls is DOSpacesConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver_v2.connectionCls.host
        self.assertEqual(host, self.default_host)

        host = self.driver_v4.connectionCls.host
        self.assertEqual(host, self.alt_host)


if __name__ == '__main__':
    sys.exit(unittest.main())
