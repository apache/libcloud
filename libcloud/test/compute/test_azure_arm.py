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
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


class AzureNodeDriverTests(LibcloudTestCase):

    TENANT_ID = 'e3cf3c98-a978-465f-8254-9d541eeea73c'
    SUBSCRIPTION_ID = '35867a13-9915-428e-a146-97f3039bba98'
    APPLICATION_ID = '8038bf1e-2ccc-4103-8d0c-03cabdb6319c'
    APPLICATION_PASS = 'p4ssw0rd'

    def setUp(self):
        Azure = get_driver(Provider.AZURE_ARM)
        Azure.connectionCls.conn_class = AzureMockHttp
        self.driver = Azure(self.TENANT_ID, self.SUBSCRIPTION_ID,
                            self.APPLICATION_ID, self.APPLICATION_PASS,
                            region='eastus')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        assert len(nodes) == 1

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual([l.name for l in locations],
                         ["East US",
                          "East US 2",
                          "West US",
                          "Central US",
                          "North Central US",
                          "South Central US",
                          "North Europe",
                          "West Europe",
                          "East Asia",
                          "Southeast Asia",
                          "Japan East",
                          "Japan West",
                          'Australia East',
                          'Australia Southeast',
                          'Brazil South',
                          'South India',
                          'Central India',
                          'Canada Central',
                          'Canada East',
                          'West US 2',
                          'West Central US',
                          'UK South',
                          'UK West',
                          'Korea Central',
                          'Korea South'])

    def test_sizes_returned_successfully(self):
        sizes = self.driver.list_sizes(location=self.driver.list_locations()[0])
        size_names = [size.name for size in sizes]
        self.assertTrue('Standard_DS1_v2'in size_names)

    def test_ex_get_ratecard(self):
        ratecard = self.driver.ex_get_ratecard('0026P')
        self.assertEqual(set(ratecard.keys()),
                         set(['Currency',
                              'Locale',
                              'IsTaxIncluded',
                              'OfferTerms',
                              'Meters']))

    def test_start_node(self):
        node = self.driver.list_nodes()[0]
        assert self.driver.ex_start_node(node) is not None

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        assert node.reboot()

    def test_ex_list_publishers(self):
        publishers = self.driver.ex_list_publishers()
        _, names = zip(*publishers)
        assert "cloudbees" in names

    def test_offers(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0][0])
        _, names = zip(*offers)
        assert "voipnow" in names

    def test_offers_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        _, names = zip(*offers)
        assert "voipnow" in names

    def test_list_skus(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0][0])
        _, names = zip(*skus)
        assert "vnp360-single" in names

    def test_list_skus_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        _, names = zip(*skus)
        assert "vnp360-single" in names

    def test_list_image_versions(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        image_versions = self.driver.ex_list_image_versions(skus[0][0])
        _, names = zip(*image_versions)
        assert "3.6.0" in names

    def test_list_image_versions_as_tuple(self):
        publishers = self.driver.ex_list_publishers()
        offers = self.driver.ex_list_offers(publishers[0])
        skus = self.driver.ex_list_skus(offers[0])
        image_versions = self.driver.ex_list_image_versions(skus[0])
        _, names = zip(*image_versions)
        assert "3.6.0" in names

    def test_list_resource_groups(self):
        resource_groups = self.driver.ex_list_resource_groups()
        test_group = resource_groups[2]
        assert test_group.id == '/subscriptions/35867a13-9915-428e-a146-97f3039bba98/resourceGroups/salt-dev-master'
        assert test_group.name == 'salt-dev-master'

    def test_ex_list_network_security_groups(self):
        resource_groups = self.driver.ex_list_resource_groups()
        net_groups = self.driver.ex_list_network_security_groups(resource_groups[2].name)
        assert len(net_groups) == 0

    def test_ex_list_network_security_groups_obj(self):
        """
        Test that you can send an AzureResourceGroup instance instead of the name
        """
        resource_groups = self.driver.ex_list_resource_groups()
        net_groups = self.driver.ex_list_network_security_groups(resource_groups[2])
        assert len(net_groups) == 0


class AzureMockHttp(MockHttp):
    driver = get_driver(Provider.AZURE_ARM)
    fixtures = ('compute', 'azure_arm')
    mode = 'static'
    base_url = ('https://login.microsoftonline.com/',
                'https://management.azure.com/')
