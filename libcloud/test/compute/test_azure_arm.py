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
        Azure.connectionCls.conn_classes = (None, AzureMockHttp)
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS)

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual([l.name for l in locations],
                         ["East US",
                          "East US 2",
                          "West US",
                          "Central US",
                          "South Central US",
                          "North Europe",
                          "West Europe",
                          "East Asia",
                          "Southeast Asia",
                          "Japan East",
                          "Japan West"])

    def test_sizes_returned_successfully(self):
        sizes = self.driver.list_sizes(location=self.driver.list_locations()[0])
        self.assertEqual([l.name for l in sizes],
                         ["Standard_A0",
                          "Standard_A1",
                          "Standard_A2"])

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
                    self.fixtures.load(n + ".json"),
                    headers,
                    httplib.responses[httplib.OK])
        return m
