#!/usr/bin/env python
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

"""
Script which uploads pricing data file (pricing.json) to an S3 bucket.

Based on https://github.com/scalyr/scalyr-agent-2/blob/master/
scripts/circleci/upload-coverage-data-to-s3.py (ASF 2.0)
"""

import os
import sys

from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

BUCKET_NAME = os.environ.get("PRICING_DATA_BUCKET_NAME", "libcloud-pricing-data")

ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", None)
ACCESS_KEY_SECRET = os.environ.get("AWS_ACCESS_KEY_SECRET", None)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

if not ACCESS_KEY_ID:
    raise ValueError("AWS_ACCESS_KEY_ID env variable not set")

if not ACCESS_KEY_SECRET:
    raise ValueError("AWS_ACCESS_KEY_SECRET env variable not set")


def upload_file(file_path):
    if not os.path.isfile(file_path):
        raise ValueError("File %s doesn't exist" % (file_path))

    print("Uploading pricing data files to S3")

    cls = get_driver(Provider.S3)
    driver = cls(ACCESS_KEY_ID, ACCESS_KEY_SECRET, region=AWS_REGION)

    file_paths = [
        file_path,
        "%s.sha256" % (file_path),
        "%s.sha512" % (file_path),
    ]

    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        object_name = file_name

        container = driver.get_container(container_name=BUCKET_NAME)
        obj = container.upload_object(file_path=file_path, object_name=object_name)

        print("Object uploaded to: {}/{}".format(BUCKET_NAME, object_name))
        print(obj)


if __name__ == "__main__":
    file_path = os.path.abspath(sys.argv[1])
    upload_file(file_path)
