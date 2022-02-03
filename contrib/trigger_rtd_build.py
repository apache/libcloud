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

import requests

# Old deprecated API
url = "https://readthedocs.org/build/8284/"
r = requests.post(url)
print(r.text)

# New API (which doesn't apear to be working)
token = os.environ["RTD_TOKEN"]

url = "https://readthedocs.org/api/v2/webhook/libcloud/87656/"
r = requests.post(url, data={"token": token, "branches": "trunk"})
print(r.text)
