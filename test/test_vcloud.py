# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
import unittest
import exceptions

from libcloud.drivers.vcloud import VCloudNodeDriver
from libcloud.base import Node, NodeImage, NodeSize
from libcloud.types import NodeState

from test import MockHttp

import httplib

from secrets import HOSTINGCOM_USER, HOSTINGCOM_SECRET


class VCloudTests(unittest.TestCase):

    def setUp(self):
       VCloudNodeDriver.connectionCls.host = "test"
       VCloudNodeDriver.connectionCls.conn_classes = (None, VCloudMockHttp) 
       VCloudMockHttp.type = None
       self.driver = VCloudNodeDriver('test@111111', HOSTINGCOM_SECRET)

    def test_list_images(self):
        VCloudMockHttp.type = 'images'
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id,'https://vcloud.safesecureweb.com/vAppTemplate/1')
        self.assertEqual(ret[-1].id,'https://vcloud.safesecureweb.com/vAppTemplate/4')

    def test_list_nodes(self):
        VCloudMockHttp.type = 'list'
        ret = self.driver.list_nodes()
        self.assertEqual(ret[0].id, '197833')
        self.assertEqual(ret[0].state, NodeState.RUNNING)


class VCloudMockHttp(MockHttp):


    def _api_v0_8_login_images(self, method, url, body, headers):
        body = """
        """
        headers = {'set-cookie': 'vcloud-token=testtoken'}
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_login_list(self, method, url, body, headers):
        body = """
        """
        headers = {'set-cookie': 'vcloud-token=testtoken'}
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _vdc_111111_list(self, method, uri, body, headers):
        return self._vdc_111111_images(method, uri, body, headers)

    def _vApp_197833_list(self, method, uri, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8"?>
<VApp href="https://vcloud.safesecureweb.com/vapp/197833"
    name="197833"
    status="4"
    xsi:schemaLocation="http://www.vmware.com/vcloud/v0.8/vapp.xsd"
    xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
    xmlns="http://www.vmware.com/vcloud/v0.8"
    xmlns:vmw="http://www.vmware.com/schema/ovf"
    xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"
    xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

  <NetworkSection>
    <ovf:Info>The list of logical networks</ovf:Info>
    <Network ovf:name="eth0" network="VLAN 2163" />
  </NetworkSection>

  <NetworkConfigSection href="https://vcloud.safesecureweb.com/api/v0.8/networkConfigSection/1">
    <NetworkConfig name="eth0">
      <Features>
        <vmw:FenceMode>bridged</vmw:FenceMode>
        <vmw:Dhcp>false</vmw:Dhcp>
      </Features>
      <vmw:NetworkAssociation href="https://vcloud.safesecureweb.com/api/v0.8/network" type="application/vnd.vmware.vcloud.network+xml" name="eth0"/>
    </NetworkConfig>
  </NetworkConfigSection>

  <NetworkConnectionSection>
    <NetworkConnection name="eth0">
      <IPAddress></IPAddress>
      <VMWareNetwork>VLAN 2163</VMWareNetwork>
    </NetworkConnection>
  </NetworkConnectionSection>

  <ovf:OperatingSystemSection ovf:id="" vmw:osType="">
    <!-- Configuration links. -->
    <ovf:Info>The kind of installed guest operating system</ovf:Info>
    <Description></Description>
  </ovf:OperatingSystemSection>

  <ovf:VirtualHardwareSection ovf:transport="iso">
    <!-- Configuration links -->
    <ovf:Info>Virtual hardware</ovf:Info>
    <System>
      <rasd:ElementName>Virtual Hardware Family</rasd:ElementName>
      <rasd:InstanceID>0</rasd:InstanceID>
      <rasd:VirtualSystemIdentifier>SimpleVM</rasd:VirtualSystemIdentifier>
      <rasd:VirtualSystemType>vmx-04</rasd:VirtualSystemType>
    </System>
    <Item>
      <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
      <rasd:Description>Number of Virtual CPUs</rasd:Description>
      <rasd:ElementName>1 virtual CPU(s)</rasd:ElementName>
      <rasd:InstanceID>1</rasd:InstanceID>
      <rasd:ResourceType>3</rasd:ResourceType>
      <rasd:VirtualQuantity>1</rasd:VirtualQuantity>
      <rasd:VirtualQuantityUnits>count</rasd:VirtualQuantityUnits>
    </Item>
    <Item>
      <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
      <rasd:Description>Memory Size</rasd:Description>
      <rasd:ElementName>512MB of memory</rasd:ElementName>
      <rasd:InstanceID>2</rasd:InstanceID>
      <rasd:ResourceType>4</rasd:ResourceType>
      <rasd:VirtualQuantity>512</rasd:VirtualQuantity>
      <rasd:VirtualQuantityUnits>byte * 2^20</rasd:VirtualQuantityUnits>
    </Item>
    <Item>
      <rasd:Address>0</rasd:Address>
      <rasd:Description>SCSI Controller</rasd:Description>
      <rasd:ElementName>SCSI Controller 0</rasd:ElementName>
      <rasd:InstanceID>3</rasd:InstanceID>
      <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
      <rasd:ResourceType>6</rasd:ResourceType>
    </Item>
    <Item>
      <rasd:AddressOnParent>7</rasd:AddressOnParent>
      <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
      <rasd:Connection connected="true">eth0</rasd:Connection>
      <rasd:Description>PCNet32 ethernet adapter on "VLAN 2163" network</rasd:Description>
      <rasd:ElementName>Network Adapter 1</rasd:ElementName>
      <rasd:InstanceID>8</rasd:InstanceID>
      <rasd:ResourceSubType>PCNet32</rasd:ResourceSubType>
      <rasd:ResourceType>10</rasd:ResourceType>
    </Item>
    <Item>
      <rasd:AddressOnParent>0</rasd:AddressOnParent>
      <rasd:ElementName>Hard Disk 1</rasd:ElementName>
      <rasd:HostResource capacity="20971520"/>
      <rasd:InstanceID>9</rasd:InstanceID>
      <rasd:Parent>3</rasd:Parent>
      <rasd:ResourceType>1</rasd:ResourceType>
    </Item>
  </ovf:VirtualHardwareSection>
</VApp>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _vdc_111111_images(self, method, url, body, headers):
    
        body = """<?xml version="1.0" encoding="UTF-8"?>
<Vdc
 href="https://vcloud.safesecureweb.com/vdc/196852"
 name="vDC Name"
 xsi:schemaLocation="http://www.vmware.com/vcloud/v0.8/vdc.xsd"
 xmlns="http://www.vmware.com/vcloud1/vl"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

  <Link rel="add"
    href="https://vcloud.safesecureweb.com/vdc/196852/vApps"
    type="application/vnd.vmware.vcloud.vApp+xml" />
  <Link rel="add"
    href="https://vcloud.safesecureweb.com/vdc/196852/vAppTemplates"
    type="application/vnd.vmware.vcloud.catalogItem+xml" />
  <Link rel="add"
    href="https://vcloud.safesecureweb.com/vdc/196852/media"
    type="application/vnd.vmware.vcloud.media+xml" />
  <Description>vDC Name</Description>
  <Type>Primary vDC for 196852</Type>
  <StorageCapacity>
    <Units>bytes * 10^9</Units> <!-- GB -->
    <Allocated>0</Allocated>
    <Used>0</Used>
  </StorageCapacity>
  <ComputeCapacity>
    <Cpu>
      <Units>hz * 10^6</Units> <!-- MHz -->
      <Allocated>0</Allocated>
      <Used>0</Used>
    </Cpu>
    <Memory>
      <Units>bytes * 10^9</Units> <!-- GB -->
      <Allocated>0</Allocated>
      <Used>0</Used>
    </Memory>
    <InstantiatedVmsQuota>
      <Limit>0</Limit>
      <Used>0</Used>
    </InstantiatedVmsQuota>
    <DeployedVmsQuota>
      <Limit>0</Limit>
      <Used>0</Used>
    </DeployedVmsQuota>
  </ComputeCapacity>
  <ResourceEntities>
    <ResourceEntity href="https://vcloud.safesecureweb.com/vAppTemplate/1"
        type="application/vnd.vmware.vcloud.vAppTemplate+xml"
        name="Plesk (Linux) 64-bit Template" />
    <ResourceEntity href="https://vcloud.safesecureweb.com/vAppTemplate/2"
        type="application/vnd.vmware.vcloud.vAppTemplate+xml"
        name="Windows 2008 Datacenter 64 Bit Template" />
    <ResourceEntity href="https://vcloud.safesecureweb.com/vAppTemplate/3"
        type="application/vnd.vmware.vcloud.vAppTemplate+xml"
        name="Cent OS 64 Bit Template" />
    <ResourceEntity href="https://vcloud.safesecureweb.com/vAppTemplate/4"
        type="application/vnd.vmware.vcloud.vAppTemplate+xml"
        name="cPanel (Linux) 64 Bit Template" />
    <ResourceEntity href="https://vcloud.safesecureweb.com/vApp/197833"
        type="application/vnd.vmware.vcloud.vApp+xml"
        name="197833"/>
  </ResourceEntities>
</Vdc>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
