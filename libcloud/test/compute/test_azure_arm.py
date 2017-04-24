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
# limitations under the License.import libcloud

from libcloud.test import LibcloudTestCase
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.utils.py3 import httplib
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


class AzureNodeDriverTests(LibcloudTestCase):
    TENANT_ID = '77777777-7777-7777-7777-777777777777'
    SUBSCRIPTION_ID = '99999999-9999-9999-9999-999999999999'
    APPLICATION_ID = '55555555-5555-5555-5555-555555555555'
    APPLICATION_PASS = 'p4ssw0rd'

    def setUp(self):
        Azure = get_driver(Provider.AZURE_ARM)
        Azure.connectionCls.conn_class = AzureMockHttp
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS)

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual([l.name for l in locations],
                         ['East US', 'East US 2', 'West US', 'Central US', 'North Central US', 'South Central US',
                          'North Europe', 'West Europe', 'East Asia', 'Southeast Asia', 'Japan East',
                          'Japan West', 'Australia East', 'Australia Southeast', 'Brazil South', 'South India',
                          'Central India', 'Canada Central', 'Canada East', 'West US 2', 'West Central US',
                          'UK South', 'UK West', 'Korea Central', 'Korea South'])

    def test_sizes_returned_successfully(self):
        sizes = self.driver.list_sizes(location=self.driver.list_locations()[0])
        self.assertEqual([l.name for l in sizes],
                         ['Standard_G1', 'Standard_G2', 'Standard_G3', 'Standard_G4', 'Standard_G5',
                          'Standard_GS1', 'Standard_GS2', 'Standard_GS3', 'Standard_GS4', 'Standard_GS5',
                          'Standard_L4s', 'Standard_L8s', 'Standard_L16s', 'Standard_L32s', 'Standard_A0',
                          'Standard_A1', 'Standard_A2', 'Standard_A3', 'Standard_A5', 'Standard_A4',
                          'Standard_A6', 'Standard_A7', 'Basic_A0', 'Basic_A1', 'Basic_A2', 'Basic_A3',
                          'Basic_A4', 'Standard_D1_v2', 'Standard_D2_v2', 'Standard_D3_v2', 'Standard_D4_v2',
                          'Standard_D5_v2', 'Standard_D11_v2', 'Standard_D12_v2', 'Standard_D13_v2',
                          'Standard_D14_v2', 'Standard_D15_v2', 'Standard_D2_v2_Promo', 'Standard_D3_v2_Promo',
                          'Standard_D4_v2_Promo', 'Standard_D5_v2_Promo', 'Standard_D11_v2_Promo',
                          'Standard_D12_v2_Promo', 'Standard_D13_v2_Promo', 'Standard_D14_v2_Promo', 'Standard_F1',
                          'Standard_F2', 'Standard_F4', 'Standard_F8', 'Standard_F16', 'Standard_A1_v2',
                          'Standard_A2m_v2', 'Standard_A2_v2', 'Standard_A4m_v2', 'Standard_A4_v2',
                          'Standard_A8m_v2', 'Standard_A8_v2', 'Standard_D1', 'Standard_D2', 'Standard_D3',
                          'Standard_D4', 'Standard_D11', 'Standard_D12', 'Standard_D13', 'Standard_D14',
                          'Standard_DS1_v2', 'Standard_DS2_v2', 'Standard_DS3_v2', 'Standard_DS4_v2',
                          'Standard_DS5_v2', 'Standard_DS11_v2', 'Standard_DS12_v2', 'Standard_DS13_v2',
                          'Standard_DS14_v2', 'Standard_DS15_v2', 'Standard_DS2_v2_Promo', 'Standard_DS3_v2_Promo',
                          'Standard_DS4_v2_Promo', 'Standard_DS5_v2_Promo', 'Standard_DS11_v2_Promo',
                          'Standard_DS12_v2_Promo', 'Standard_DS13_v2_Promo', 'Standard_DS14_v2_Promo',
                          'Standard_F1s', 'Standard_F2s', 'Standard_F4s', 'Standard_F8s', 'Standard_F16s',
                          'Standard_DS1', 'Standard_DS2', 'Standard_DS3', 'Standard_DS4', 'Standard_DS11',
                          'Standard_DS12', 'Standard_DS13', 'Standard_DS14'])

    def test_ex_get_ratecard(self):
        ratecard = self.driver.ex_get_ratecard('0026P')
        self.assertEqual(set(ratecard.keys()),
                         set(['Currency',
                              'Locale',
                              'IsTaxIncluded',
                              'OfferTerms',
                              'Meters']))


class AzureMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('azure_arm')

    def __getattr__(self, n):
        def m(method, url, body, headers):
            return (httplib.OK,
                    self.fixtures.load('%s.json' % n),
                    headers,
                    httplib.responses[httplib.OK])

        return m
