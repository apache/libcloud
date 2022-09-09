# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import unittest

from libcloud.storage import types
from integration.storage.base import Integration


class MinioTest(Integration.ContainerTestBase):
    provider = "minio"

    account = "minioaccount"
    secret = "miniopassword"

    image = "minio/minio"
    port = 9000
    environment = {"MINIO_ROOT_USER": account, "MINIO_ROOT_PASSWORD": secret}
    command = ["server", "/data"]
    # Output seemed to have changed recently, see
    # https://github.com/apache/libcloud/runs/7481114211?check_suite_focus=true
    # ready_message = b'Console endpoint is listening on a dynamic port'
    ready_message = b"1 Online"

    def test_cdn_url(self):
        self.skipTest("Not implemented in driver")

    def assert_file_is_missing(self, container, obj):
        with self.assertRaises(types.ObjectDoesNotExistError):
            self.driver.get_object(container.name, obj.name)


if __name__ == "__main__":
    sys.exit(unittest.main())
