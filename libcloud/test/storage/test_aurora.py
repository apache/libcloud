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
from libcloud.storage.drivers.auroraobjects import AuroraObjectsStorageDriver
from libcloud.test.storage.test_s3 import S3MockHttp, S3Tests


class AuroraObjectsTests(S3Tests, unittest.TestCase):
    driver_type = AuroraObjectsStorageDriver

    def setUp(self):
        super(AuroraObjectsTests, self).setUp()

        AuroraObjectsStorageDriver.connectionCls.conn_class = S3MockHttp
        S3MockHttp.type = None
        self.driver = self.create_driver()

    def test_get_object_cdn_url(self):
        self.mock_response_klass.type = 'get_object'
        obj = self.driver.get_object(container_name='test2',
                                     object_name='test')

        with self.assertRaises(LibcloudError):
            self.driver.get_object_cdn_url(obj)



if __name__ == '__main__':
    sys.exit(unittest.main())
