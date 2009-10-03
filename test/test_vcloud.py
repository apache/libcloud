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
       VCloudNodeDriver.connectionCls.api_host = "test"
       VCloudNodeDriver.connectionCls.conn_classes = (None, VCloudMockHttp) 
       VCloudMockHttp.type = None
       self.driver = VCloudNodeDriver(HOSTINGCOM_USER, HOSTINGCOM_SECRET)
       self.driver.connection.hostingid = '111111'

    def test_list_images(self):
        VCloudMockHttp.type = 'images'
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id,'https://vcloud.safesecureweb.com/vAppTemplate/1')
        self.assertEqual(ret[-1].id,'https://vcloud.safesecureweb.com/vAppTemplate/4')


class VCloudMockHttp(MockHttp):


    def _api_v0_8_login(self, method, url, body, headers):
        body = """
        """
        headers = {'set-cookie': 'vcloud-token=testtoken'}
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

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
  </ResourceEntities>
</Vdc>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
