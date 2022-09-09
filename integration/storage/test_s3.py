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
import os
import sys
import unittest

from libcloud.storage import types
from integration.storage.base import Integration

try:
    import boto3
except ImportError:
    boto3 = None


class S3Test(Integration.TestBase):
    provider = "s3"

    @classmethod
    def setUpClass(cls):
        if boto3 is None:
            raise unittest.SkipTest("missing boto3 library")

        config = {
            key: os.getenv(key)
            for key in (
                "AWS_ACCESS_KEY_ID",
                "AWS_ACCESS_KEY_SECRET",
            )
        }

        for key, value in config.items():
            if not value:
                raise unittest.SkipTest("missing environment variable %s" % key)

        cls.account = config["AWS_ACCESS_KEY_ID"]
        cls.secret = config["AWS_ACCESS_KEY_SECRET"]

    @classmethod
    def tearDownClass(cls):
        client = boto3.Session(
            aws_access_key_id=cls.account,
            aws_secret_access_key=cls.secret,
        ).client("s3")

        buckets = (
            item["Name"]
            for item in client.list_buckets()["Buckets"]
            if item["Name"].startswith(cls.container_name_prefix)
        )

        for name in buckets:
            bucket = boto3.resource("s3").Bucket(name)
            bucket.objects.delete()
            client.delete_bucket(name)

    def assert_existing_container_cannot_be_recreated(self, container):
        pass

    def assert_file_is_missing(self, container, obj):
        with self.assertRaises(types.ObjectDoesNotExistError):
            self.driver.get_object(container.name, obj.name)


if __name__ == "__main__":
    sys.exit(unittest.main())
