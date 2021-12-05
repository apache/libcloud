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
from libcloud.storage.drivers.scaleway import ScalewayStorageDriver
from libcloud.storage.drivers.scaleway import ScalewayConnectionAWS4

from libcloud.test.secrets import STORAGE_S3_PARAMS


class ScalewayStorageDriverTestCase(unittest.TestCase):
    driver_type = ScalewayStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = "libcloud-storage-test.s3.fr-par.scw.cloud"

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args, host=self.default_host)

    def setUp(self):
        self.driver = self.create_driver()

    def test_connection_class_type(self):
        self.assertEqual(self.driver.connectionCls, ScalewayConnectionAWS4)

    def test_connection_class_default_host(self):
        self.assertEqual(self.driver.connectionCls.host, self.default_host)
        self.assertEqual(self.driver.connectionCls.port, 443)
        self.assertEqual(self.driver.connectionCls.secure, True)

    def test_empty_host_error(self):
        self.assertRaisesRegex(
            LibcloudError,
            "host argument is required",
            self.driver_type,
            *self.driver_args,
        )

if __name__ == "__main__":
    sys.exit(unittest.main())
