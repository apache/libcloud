#!/usr/bin/env python3
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

import os
import sys

import requests

token = os.environ["RTD_TOKEN"]
branch = os.environ["BRANCH_NAME"]

print(f"Using branch: {branch}")

url = "https://readthedocs.org/api/v2/webhook/libcloud/87656/"
r = requests.post(url, data={"token": token, "branches": branch})
print(r.text)

if r.status_code != 200:
    print("Triggering RTD build failed")
    sys.exit(1)
