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
from libcloud.compute.base import NodeState
from libcloud.compute.types import Provider


from libcloud.test import unittest


class virConnect:
    """
    A stub/Mock implementation of the libvirt.virConnect class returned by
    the libvirt.openX calles
    """
    def __stub(self, *args, **kwargs):
        return 0

    def __yes(self, *args, **kwargs):
        return True

    def __ary(self, *args, **kwargs):
        return []

    def __init__(self):
        stub = self.__stub
        yes = self.__yes
        ary = self.__ary
        fnt = [
            '_dispatchCloseCallback',
            '_dispatchDomainEventAgentLifecycleCallback',
            '_dispatchDomainEventBalloonChangeCallback',
            '_dispatchDomainEventBlockJobCallback',
            '_dispatchDomainEventCallbacks',
            '_dispatchDomainEventDeviceAddedCallback',
            '_dispatchDomainEventDeviceRemovalFailedCallback',
            '_dispatchDomainEventDeviceRemovedCallback',
            '_dispatchDomainEventDiskChangeCallback',
            '_dispatchDomainEventGenericCallback',
            '_dispatchDomainEventGraphicsCallback',
            '_dispatchDomainEventIOErrorCallback',
            '_dispatchDomainEventIOErrorReasonCallback',
            '_dispatchDomainEventJobCompletedCallback',
            '_dispatchDomainEventLifecycleCallback',
            '_dispatchDomainEventMigrationIterationCallback',
            '_dispatchDomainEventPMSuspendCallback',
            '_dispatchDomainEventPMSuspendDiskCallback',
            '_dispatchDomainEventPMWakeupCallback',
            '_dispatchDomainEventRTCChangeCallback',
            '_dispatchDomainEventTrayChangeCallback',
            '_dispatchDomainEventTunableCallback',
            '_dispatchDomainEventWatchdogCallback',
            '_dispatchNetworkEventLifecycleCallback',
            '_o', 'allocPages', 'baselineCPU', 'c_pointer', 'changeBegin',
            'changeCommit', 'changeRollback', 'close', 'compareCPU',
            'createLinux', 'createXML', 'createXMLWithFiles', 'defineXML',
            'defineXMLFlags', 'domainEventDeregister',
            'domainEventDeregisterAny', 'domainEventRegister',
            'domainEventRegisterAny', 'domainListGetStats',
            'domainXMLFromNative', 'domainXMLToNative',
            'findStoragePoolSources', 'getAllDomainStats', 'getCPUMap',
            'getCPUModelNames', 'getCPUStats', 'getCapabilities',
            'getCellsFreeMemory', 'getDomainCapabilities', 'getFreeMemory',
            'getFreePages', 'getHostname', 'getInfo', 'getLibVersion',
            'getMaxVcpus', 'getMemoryParameters', 'getMemoryStats',
            'getSecurityModel', 'getSysinfo', 'getType', 'getURI',
            'getVersion', 'interfaceDefineXML', 'interfaceLookupByMACString',
            'interfaceLookupByName', 'isAlive', 'isEncrypted', 'isSecure',
            'listAllDevices', 'listAllDomains', 'listAllInterfaces',
            'listAllNWFilters', 'listAllNetworks', 'listAllSecrets',
            'listAllStoragePools', 'listDefinedDomains',
            'listDefinedInterfaces', 'listDefinedNetworks',
            'listDefinedStoragePools', 'listDevices', 'listDomainsID',
            'listInterfaces', 'listNWFilters', 'listNetworks', 'listSecrets',
            'listStoragePools', 'lookupByID', 'lookupByName', 'lookupByUUID',
            'lookupByUUIDString', 'networkCreateXML', 'networkDefineXML',
            'networkEventDeregisterAny', 'networkEventRegisterAny',
            'networkLookupByName', 'networkLookupByUUID',
            'networkLookupByUUIDString', 'newStream', 'nodeDeviceCreateXML',
            'nodeDeviceLookupByName', 'nodeDeviceLookupSCSIHostByWWN',
            'numOfDefinedDomains', 'numOfDefinedInterfaces',
            'numOfDefinedNetworks', 'numOfDefinedStoragePools', 'numOfDevices',
            'numOfDomains', 'numOfInterfaces', 'numOfNWFilters',
            'numOfNetworks', 'numOfSecrets', 'numOfStoragePools',
            'nwfilterDefineXML', 'nwfilterLookupByName',
            'nwfilterLookupByUUID', 'nwfilterLookupByUUIDString',
            'registerCloseCallback', 'restore', 'restoreFlags',
            'saveImageDefineXML', 'saveImageGetXMLDesc', 'secretDefineXML',
            'secretLookupByUUID', 'secretLookupByUUIDString',
            'secretLookupByUsage', 'setKeepAlive', 'setMemoryParameters',
            'storagePoolCreateXML', 'storagePoolDefineXML',
            'storagePoolLookupByName', 'storagePoolLookupByUUID',
            'storagePoolLookupByUUIDString', 'storageVolLookupByKey',
            'storageVolLookupByPath', 'suspendForDuration',
            'unregisterCloseCallback', 'virConnGetLastError',
            'virConnResetLastError'
        ]
        for f in fnt:
            if f.startswith('is'):
                self.__dict__[f] = yes
            elif f.startswith('list'):
                self.__dict__[f] = ary
            else:
                self.__dict__[f] = stub


class LibvirtNodeDriverTestCase(LibvirtNodeDriver, unittest.TestCase):
    type = Provider.LIBVIRT
    name = 'Libvirt'
    website = 'http://libvirt.org/'

    NODE_STATE_MAP = {
        0: NodeState.TERMINATED,  # no state
        1: NodeState.RUNNING,  # domain is running
        2: NodeState.PENDING,  # domain is blocked on resource
        3: NodeState.TERMINATED,  # domain is paused by user
        4: NodeState.TERMINATED,  # domain is being shut down
        5: NodeState.TERMINATED,  # domain is shut off
        6: NodeState.UNKNOWN,  # domain is crashed
        7: NodeState.UNKNOWN,  # domain is suspended by guest power management
    }

    def __init__(self, argv=None):
        unittest.TestCase.__init__(self, argv)
        self._uri = 'qemu:///system'
        self.connection = virConnect()

    def _assert_arp_table(self, arp_table):
        self.assertIn('52:54:00:bc:f9:6c', arp_table)
        self.assertIn('52:54:00:04:89:51', arp_table)
        self.assertIn('52:54:00:c6:40:ec', arp_table)
        self.assertIn('52:54:00:77:1c:83', arp_table)
        self.assertIn('1.2.10.80', arp_table['52:54:00:bc:f9:6c'])
        self.assertIn('1.2.10.33', arp_table['52:54:00:04:89:51'])
        self.assertIn('1.2.10.97', arp_table['52:54:00:c6:40:ec'])
        self.assertIn('1.2.10.40', arp_table['52:54:00:77:1c:83'])

    def test_arp_map(self):
        arp_output_str = """? (1.2.10.80) at 52:54:00:bc:f9:6c [ether] on br0
? (1.2.10.33) at 52:54:00:04:89:51 [ether] on br0
? (1.2.10.97) at 52:54:00:c6:40:ec [ether] on br0
? (1.2.10.40) at 52:54:00:77:1c:83 [ether] on br0
"""
        arp_table = self._parse_ip_table_arp(arp_output_str)
        self._assert_arp_table(arp_table)

    def test_ip_map(self):
        arp_output_str = """1.2.10.80 dev br0 lladdr 52:54:00:bc:f9:6c STALE
1.2.10.33 dev br0 lladdr 52:54:00:04:89:51 REACHABLE
1.2.10.97 dev br0 lladdr 52:54:00:c6:40:ec DELAY
1.2.10.40 dev br0 lladdr 52:54:00:77:1c:83 STALE
"""
        arp_table = self._parse_ip_table_neigh(arp_output_str)
        self._assert_arp_table(arp_table)

    def test_bad_map(self):
        arp_output_str = """1.2.10.80 dev br0  52:54:00:bc:f9:6c STALE
1.2.10.33 dev br0 lladdr 52:54:00:04:89:51 REACHABLE
1.2.10.97 dev br0 lladdr
1.2.10.40 dev br0 lladdr 52:54:00:77:1c:83 STALE
"""
        arp_table = self._parse_ip_table_neigh(arp_output_str)
        # we should at least get the correctly formatted lines
        self.assertEqual(len(arp_table), 2)
        arp_output_str = """? (1.2.10.80) at 52:54:00:bc:f9:6c [ether] on br0
? (1.2.10.33) at 52:54:00:04:89:51 [ether] on br0
? (1.2.10.97) at 52:54:00:c6:40:ec [ether] on br0
? (1.2.10.40) at 52:54:00:77:1c:83 [ether] on br0
"""
        arp_table = self._parse_ip_table_neigh(arp_output_str)
        # nothing should match if the wrong output is sent
        self.assertEqual(len(arp_table), 0)

    def test_list_nodes(self):
        nodes = self.list_nodes()
        self.assertEqual(type([]), type(nodes))
        self.assertEqual(len(nodes), 0)

if __name__ == '__main__':
    sys.exit(unittest.main())
