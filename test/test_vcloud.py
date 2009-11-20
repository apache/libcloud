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

from libcloud.drivers.vcloud import TerremarkDriver
from libcloud.drivers.vcloud import VCloudNodeDriver
from libcloud.base import Node, NodeImage, NodeSize
from libcloud.types import NodeState

from test import MockHttp, TestCaseMixin

import httplib

from secrets import TERREMARK_USER, TERREMARK_SECRET

class TerremarkTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        VCloudNodeDriver.connectionCls.host = "test"
        VCloudNodeDriver.connectionCls.conn_classes = (None, TerremarkMockHttp) 
        TerremarkMockHttp.type = None
        self.driver = TerremarkDriver(TERREMARK_USER, TERREMARK_SECRET)

    def test_list_images(self):
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id,'https://services.vcloudexpress.terremark.com/api/v0.8/vAppTemplate/5')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(ret[0].ram, 512)
        
    def test_create_node(self):
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        node = self.driver.create_node(
            name='testerpart2', 
            image=image, 
            size=size,
            vdc='https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224',
            network='https://services.vcloudexpress.terremark.com/api/v0.8/network/725', 
            cpus=2,
        )
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.id, 'https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031')
        self.assertEqual(node.name, 'testerpart2')
        
    def test_list_nodes(self):
        ret = self.driver.list_nodes()
        node = ret[0]
        self.assertEqual(node.id, 'https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031')
        self.assertEqual(node.name, 'testerpart2')
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.public_ip, [])
        self.assertEqual(node.private_ip, ['10.112.78.69'])
        
    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node)
        self.assertTrue(ret)
        
    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)

        
class TerremarkMockHttp(MockHttp):

    def _api_v0_8_login(self, method, url, body, headers):
        headers['set-cookie'] = 'vcloud-token=testtoken'
        body = """<OrgList xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Org href="https://services.vcloudexpress.terremark.com/api/v0.8/org/240" type="application/vnd.vmware.vcloud.org+xml" name="a@example.com"/>
</OrgList>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_org_240(self, method, url, body, headers):
        body = """<Org href="https://services.vcloudexpress.terremark.com/api/v0.8/org/240" name="a@example.com" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224/catalog" type="application/vnd.vmware.vcloud.catalog+xml" name="Miami Environment 1 Catalog"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/tasksList/224" type="application/vnd.vmware.vcloud.tasksList+xml" name="Miami Environment 1 Tasks List"/>
</Org>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vdc_224(self, method, url, body, headers):
        body = """<Vdc href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224/catalog" type="application/vnd.vmware.vcloud.catalog+xml" name="Miami Environment 1"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224/publicIps" type="application/xml" name="Public IPs"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224/internetServices" type="application/xml" name="Internet Services"/>
  <Description/>
  <ResourceEntities>
    <ResourceEntity href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
  </ResourceEntities>
  <AvailableNetworks>
    <Network href="https://services.vcloudexpress.terremark.com/api/v0.8/network/725" type="application/vnd.vmware.vcloud.network+xml" name="10.112.78.64/26"/>
  </AvailableNetworks>
</Vdc>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_vdc_224_catalog(self, method, url, body, headers):
        body = """<Catalog href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224/catalog" type="application/vnd.vmware.vcloud.catalog+xml" name="Miami Environment 1" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <CatalogItems>
    <CatalogItem href="https://services.vcloudexpress.terremark.com/api/v0.8/catalogItem/5" type="application/vnd.vmware.vcloud.catalogItem+xml" name="CentOS 5.3 (32-bit)"/>
  </CatalogItems>
</Catalog>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _api_v0_8_catalogItem_5(self, method, url, body, headers):
        body = """<CatalogItem href="https://services.vcloudexpress.terremark.com/api/v0.8/catalogItem/5" type="application/vnd.vmware.vcloud.catalogItem+xml" name="CentOS 5.3 (32-bit)" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/catalogItem/5/options/compute" type="application/xml" name="Compute Options"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/catalogItem/5/options/customization" type="application/xml" name="Customization Options"/>
  <Entity href="https://services.vcloudexpress.terremark.com/api/v0.8/vAppTemplate/5" type="application/vnd.vmware.vcloud.vAppTemplate+xml" name="CentOS 5.3 (32-bit)"/>
  <Property key="LicensingCost">0</Property>
</CatalogItem>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])
      
    def _api_v0_8_vdc_224_action_instantiateVAppTemplate(self, method, url, body, headers):
        body = """<VApp href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2" status="0" size="10" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Link rel="up" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml"/>
</VApp>
"""
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])
      
    def _api_v0_8_vapp_14031_action_deploy(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/10496" type="application/vnd.vmware.vcloud.task+xml" status="queued" startTime="2009-11-13T23:58:22.893Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>
"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])
      
    def _api_v0_8_task_10496(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/10496" type="application/vnd.vmware.vcloud.task+xml" status="success" startTime="2009-11-13T23:58:22.893Z" endTime="2009-11-14T00:01:02.507Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>
"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])
      
    def _api_v0_8_vapp_14031_power_action_powerOn(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/10499" type="application/vnd.vmware.vcloud.task+xml" status="queued" startTime="2009-11-14T00:01:05.227Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>

"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])
      
    def _api_v0_8_vapp_14031(self, method, url, body, headers):
        if method == 'GET':
            body = """<VApp href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2" status="4" size="10485760" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Link rel="up" href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031/options/compute" type="application/xml" name="Compute Options"/>
  <Link rel="down" href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031/options/customization" type="application/xml" name="Customization Options"/>
  <Section xsi:type="q1:NetworkConnectionSectionType" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:q1="http://www.vmware.com/vcloud/v1">
    <q1:NetworkConnection Network="Internal">
      <q1:IpAddress>10.112.78.69</q1:IpAddress>
    </q1:NetworkConnection>
  </Section>
  <OperatingSystemSection d2p1:id="25" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:d2p1="http://schemas.dmtf.org/ovf/envelope/1">
    <Info>The kind of installed guest operating system</Info>
    <Description>Red Hat Enterprise Linux 5 (32-bit)</Description>
  </OperatingSystemSection>
  <Section xsi:type="q2:VirtualHardwareSection_Type" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:q2="http://www.vmware.com/vcloud/v1">
    <Info>Virtual Hardware</Info>
    <q2:System>
      <AutomaticRecoveryAction xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <AutomaticShutdownAction xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <AutomaticStartupAction xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <AutomaticStartupActionDelay xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <AutomaticStartupActionSequenceNumber xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <Caption xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <ConfigurationDataRoot xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <ConfigurationFile xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <ConfigurationID xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <CreationTime xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <Description xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <ElementName xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">Virtual Hardware Family</ElementName>
      <InstanceID xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">0</InstanceID>
      <LogDataRoot xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <RecoveryFile xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <SnapshotDataRoot xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <SuspendDataRoot xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <SwapFileDataRoot xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"/>
      <VirtualSystemIdentifier xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">testerpart2</VirtualSystemIdentifier>
      <VirtualSystemType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">vmx-07</VirtualSystemType>
    </q2:System>
    <q2:Item>
      <Address xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AddressOnParent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AllocationUnits xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">hertz * 10^6</AllocationUnits>
      <AutomaticAllocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticDeallocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Caption xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ConsumerVisibility xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Description xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">Number of Virtual CPUs</Description>
      <ElementName xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">2 virtual CPU(s)</ElementName>
      <InstanceID xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">1</InstanceID>
      <Limit xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <MappingBehavior xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <OtherResourceType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Parent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <PoolID xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Reservation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceSubType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">3</ResourceType>
      <VirtualQuantity xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">2</VirtualQuantity>
      <VirtualQuantityUnits xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">count</VirtualQuantityUnits>
      <Weight xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
    </q2:Item>
    <q2:Item>
      <Address xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AddressOnParent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AllocationUnits xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">byte * 2^20</AllocationUnits>
      <AutomaticAllocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticDeallocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Caption xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ConsumerVisibility xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Description xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">Memory Size</Description>
      <ElementName xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">512MB of memory</ElementName>
      <InstanceID xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">2</InstanceID>
      <Limit xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <MappingBehavior xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <OtherResourceType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Parent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <PoolID xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Reservation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceSubType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">4</ResourceType>
      <VirtualQuantity xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">512</VirtualQuantity>
      <VirtualQuantityUnits xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">byte * 2^20</VirtualQuantityUnits>
      <Weight xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
    </q2:Item>
    <q2:Item>
      <Address xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">0</Address>
      <AddressOnParent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AllocationUnits xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticAllocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticDeallocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Caption xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ConsumerVisibility xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Description xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">SCSI Controller</Description>
      <ElementName xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">SCSI Controller 0</ElementName>
      <InstanceID xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">3</InstanceID>
      <Limit xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <MappingBehavior xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <OtherResourceType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Parent xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <PoolID xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Reservation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceSubType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">lsilogic</ResourceSubType>
      <ResourceType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">6</ResourceType>
      <VirtualQuantity xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <VirtualQuantityUnits xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Weight xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
    </q2:Item>
    <q2:Item>
      <Address xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AddressOnParent xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">0</AddressOnParent>
      <AllocationUnits xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticAllocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <AutomaticDeallocation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Caption xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ConsumerVisibility xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Description xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ElementName xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">Hard Disk 1</ElementName>
      <HostResource xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">10485760</HostResource>
      <InstanceID xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">9</InstanceID>
      <Limit xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <MappingBehavior xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <OtherResourceType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Parent xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">3</Parent>
      <PoolID xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Reservation xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceSubType xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <ResourceType xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">17</ResourceType>
      <VirtualQuantity xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">10485760</VirtualQuantity>
      <VirtualQuantityUnits xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
      <Weight xsi:nil="true" xmlns="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"/>
    </q2:Item>
  </Section>
</VApp>
"""
        elif method == 'DELETE':
            body = ''
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031_power_action_reset(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/10555" type="application/vnd.vmware.vcloud.task+xml" status="queued" startTime="2009-11-14T00:54:50.417Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>
"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_vapp_14031_power_action_poweroff(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/11001" type="application/vnd.vmware.vcloud.task+xml" status="queued" startTime="2009-11-16T18:18:02.82Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>
"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _api_v0_8_task_11001(self, method, url, body, headers):
        body = """<Task href="https://services.vcloudexpress.terremark.com/api/v0.8/task/11001" type="application/vnd.vmware.vcloud.task+xml" status="success" startTime="2009-11-16T18:18:02.82Z" endTime="2009-11-16T18:18:17.567Z" xmlns="http://www.vmware.com/vcloud/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Owner href="https://services.vcloudexpress.terremark.com/api/v0.8/vdc/224" type="application/vnd.vmware.vcloud.vdc+xml" name="Miami Environment 1"/>
  <Result href="https://services.vcloudexpress.terremark.com/api/v0.8/vapp/14031" type="application/vnd.vmware.vcloud.vApp+xml" name="testerpart2"/>
</Task>
"""
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

      
