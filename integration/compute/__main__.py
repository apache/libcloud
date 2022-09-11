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

from integration.compute.api.data import NODES, REPORT_DATA
from integration.compute.driver.test import TestNodeDriver


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.instance = TestNodeDriver(
            "apache", "libcloud", secure=False, host="localhost", port=9898
        )

    def test_nodes(self):
        """
        Test that you can list nodes and that the responding objects
        match basic values, list (ip), and dict (extra).
        """
        nodes = self.instance.list_nodes()
        for node in NODES:
            match = [n for n in nodes if n.id == node["id"]]
            self.assertTrue(len(match) == 1)
            match = match[0]
            self.assertEqual(match.id, node["id"])
            self.assertEqual(match.name, node["name"])
            self.assertEqual(match.private_ips, node["private_ips"])
            self.assertEqual(match.public_ips, node["public_ips"])
            self.assertEqual(match.extra, node["extra"])

    def test_ex_report_data(self):
        """
        Test that a raw request can correctly return the data
        """
        data = self.instance.ex_report_data()
        self.assertEqual(data, REPORT_DATA)


if __name__ == "__main__":
    import libcloud

    with open("/tmp/testing.log", "w") as f:
        libcloud.enable_debug(f)
        sys.exit(unittest.main())
