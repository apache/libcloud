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

import mock

from libcloud.compute.drivers.libvirt_driver import LibvirtNodeDriver
from libcloud.compute.drivers.libvirt_driver import have_libvirt
from libcloud.utils.py3 import PY3

from libcloud.test import unittest

__all__ = [
    'LibvirtNodeDriverTestCase'
]


@unittest.skipIf(not have_libvirt, 'libvirt not available, skipping tests')
@mock.patch('libcloud.compute.drivers.libvirt_driver.libvirt', autospec=True)
class LibvirtNodeDriverTestCase(unittest.TestCase):
    arp_output_str = """? (1.2.10.80) at 52:54:00:bc:f9:6c [ether] on br0
? (1.2.10.33) at 52:54:00:04:89:51 [ether] on br0
? (1.2.10.97) at 52:54:00:c6:40:ec [ether] on br0
? (1.2.10.40) at 52:54:00:77:1c:83 [ether] on br0"""
    ip_output_str = """1.2.10.80 dev br0 lladdr 52:54:00:bc:f9:6c STALE
1.2.10.33 dev br0 lladdr 52:54:00:04:89:51 REACHABLE
1.2.10.97 dev br0 lladdr 52:54:00:c6:40:ec DELAY
1.2.10.40 dev br0 lladdr 52:54:00:77:1c:83 STALE"""
    bad_output_str = """1.2.10.80 dev br0  52:54:00:bc:f9:6c STALE
1.2.10.33 dev br0 lladdr 52:54:00:04:89:51 REACHABLE
1.2.10.97 dev br0 lladdr
1.2.10.40 dev br0 lladdr 52:54:00:77:1c:83 STALE"""
    if PY3:
        from libcloud.utils.py3 import b
        arp_output_str = b(arp_output_str)
        ip_output_str = b(ip_output_str)
        bad_output_str = b(bad_output_str)

    def _assert_arp_table(self, arp_table):
        self.assertIn('52:54:00:bc:f9:6c', arp_table)
        self.assertIn('52:54:00:04:89:51', arp_table)
        self.assertIn('52:54:00:c6:40:ec', arp_table)
        self.assertIn('52:54:00:77:1c:83', arp_table)
        self.assertIn('1.2.10.80', arp_table['52:54:00:bc:f9:6c'])
        self.assertIn('1.2.10.33', arp_table['52:54:00:04:89:51'])
        self.assertIn('1.2.10.97', arp_table['52:54:00:c6:40:ec'])
        self.assertIn('1.2.10.40', arp_table['52:54:00:77:1c:83'])

    def test_arp_map(self, *args, **keywargs):
        driver = LibvirtNodeDriver('')
        arp_table = driver._parse_ip_table_arp(self.arp_output_str)
        self._assert_arp_table(arp_table)

    def test_ip_map(self, *args, **keywargs):
        driver = LibvirtNodeDriver('')
        arp_table = driver._parse_ip_table_neigh(self.ip_output_str)
        self._assert_arp_table(arp_table)

    def test_bad_map(self, *args, **keywargs):
        driver = LibvirtNodeDriver('')
        arp_table = driver._parse_ip_table_neigh(self.bad_output_str)
        # we should at least get the correctly formatted lines
        self.assertEqual(len(arp_table), 2)
        arp_table = driver._parse_ip_table_neigh(self.arp_output_str)
        # nothing should match if the wrong output is sent
        self.assertEqual(len(arp_table), 0)

    def test_list_nodes(self, *args, **keywargs):
        driver = LibvirtNodeDriver('')
        nodes = driver.list_nodes()
        self.assertEqual(type([]), type(nodes))
        self.assertEqual(len(nodes), 0)

if __name__ == '__main__':
    sys.exit(unittest.main())
