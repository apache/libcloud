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

from libcloud.compute.drivers.libvirt_driver import LibvirtNodeDriver


from libcloud.test import unittest


class LibvirtNodeDriverTestCase( unittest.TestCase):
    

    def setUp(self):
        self.driver = LibvirtNodeDriver('')

    def _assert_arp_table(self, arp_table):
        self.assertIn('52:54:00:bc:f9:6c', arp_table)
        self.assertIn('52:54:00:04:89:51', arp_table)
        self.assertIn('52:54:00:c6:40:ec', arp_table)
        self.assertIn('52:54:00:77:1c:83', arp_table)
        self.assertEqual(arp_table['52:54:00:bc:f9:6c'], '1.2.10.80')
        self.assertEqual(arp_table['52:54:00:04:89:51'], '1.2.10.33')
        self.assertEqual(arp_table['52:54:00:c6:40:ec'], '1.2.10.97')
        self.assertEqual(arp_table['52:54:00:77:1c:83'], '1.2.10.40')

    def test_arp_map(self):
        arp_output_str = """? (1.2.10.80) at 52:54:00:bc:f9:6c [ether] on br0
? (1.2.10.33) at 52:54:00:04:89:51 [ether] on br0
? (1.2.10.97) at 52:54:00:c6:40:ec [ether] on br0
? (1.2.10.40) at 52:54:00:77:1c:83 [ether] on br0
"""
        arp_table = self.driver._parse_ip_table_arp(arp_output_str)
        self._assert_arp_table(arp_table)

    def test_ip_map(self):
        arp_output_str = """1.2.10.80 dev br0 lladdr 52:54:00:bc:f9:6c STALE
1.2.10.33 dev br0 lladdr 52:54:00:04:89:51 REACHABLE
1.2.10.97 dev br0 lladdr 52:54:00:c6:40:ec DELAY
1.2.10.40 dev br0 lladdr 52:54:00:77:1c:83 STALE
"""
        arp_table = self.driver._parse_ip_table_neigh(arp_output_str)
        self._assert_arp_table(arp_table)

if __name__ == '__main__':
    sys.exit(unittest.main())
