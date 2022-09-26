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

NODES = [
    {
        "id": "1234a",
        "name": "test-1",
        "state": "RUNNING",
        "public_ips": ["4.4.4.4", "8.8.8.8"],
        "private_ips": ["10.0.0.1", "192.168.1.1"],
        "size": "test-size-1",
        "created_at": "2017-01-09T05:25:12+00:00",
        "image": "test-image-1",
        "extra": {"test-key": "test-value"},
    },
    {
        "id": "4567a",
        "name": "test-2",
        "state": "RUNNING",
        "public_ips": ["4.4.4.5", "8.8.8.8"],
        "private_ips": ["10.0.0.2", "192.168.1.1"],
        "size": "test-size-1",
        "created_at": "2017-01-09T05:25:12+00:00",
        "image": "test-image-1",
        "extra": {"test-key": "test-value"},
    },
]

REPORT_DATA = "Around the ragged rocks, the ragged rascal ran. \r\n"
