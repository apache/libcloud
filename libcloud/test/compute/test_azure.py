import libcloud

__author__ = 'david'

import sys

import httplib
import unittest
import urlparse
import libcloud.security
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

class AzureNodeDriverTests(unittest.TestCase) :

    libcloud.security.VERIFY_SSL_CERT = False

    SUBSCRIPTION_ID = '5191b16a-673d-426c-8c55-fdd912858e4e'
    KEY_FILE = 'C:\\Users\\david\\Desktop\\libcloud.pem'

    def setUp(self):
        Azure = get_driver(Provider.AZURE)
        Azure.connectionCls.conn_classes = (None, AzureMockHttp)
        self.driver = Azure(self.SUBSCRIPTION_ID, self.KEY_FILE, pem_key_file = self.KEY_FILE )

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 7)

        locationNamesResult = list(a.name for a in locations)
        locationNamesExpected = ['East Asia','Southeast Asia','North Europe','West Europe','East US','North Central US','West US']

        self.assertListEqual(locationNamesResult, locationNamesExpected)

        matchedLocation = next(location for location in locations if location.name == 'Southeast Asia')
        servicesResult = matchedLocation.services
        servicesExpected = ['Compute','Storage','PersistentVMRole','HighMemory']
        self.assertListEqual(servicesResult, servicesExpected)

        vmRoleSizesResult = matchedLocation.vmRoleSizes

        vmRoleSizesExpected = ['A5','A6','A7','Basic_A0','Basic_A1','Basic_A2','Basic_A3','Basic_A4','ExtraLarge','ExtraSmall','Large','Medium','Small']
        self.assertListEqual(vmRoleSizesResult, vmRoleSizesExpected)

    def test_images_returned_successfully(self):
        images = self.driver.list_images()
        self.assertEquals(len(images), 212 )

    def test_images_returned_successfully_filter_by_location(self):
        images = self.driver.list_images("West US")
        self.assertEquals(len(images), 206 )

    def test_vmimages_returned_successfully(self):
        vmimages = self.driver.list_nodes(cloudServiceName="oddkinz")
        self.assertEqual(len(vmimages), 5)

        img0 = vmimages[0]
        self.assertEquals(img0.id,"c3Rvcm0x")
        self.assertEquals(img0.image,"Linux")
        self.assertEquals(img0.location,"North Europe")
        self.assertEquals(img0.name,"cloudredis")
        self.assertListEqual(img0.public_ips,["100.86.90.81"])
        self.assertEquals(img0.serviceName,"oddkinz")
        self.assertEquals(img0.size,"Medium")
        self.assertEquals(img0.state,"ReadyRole")
        self.assertEquals(img0.deploymentName,"storm1")
        self.assertTrue(isinstance(img0.extra,dict))

    def test_list_nodes_cloud_service_not_found(self):
        with self.assertRaises(ValueError):
            self.driver.list_nodes(cloudServiceName="424324")

    def test_vmimages_restart_node_success(self):
        node = dict()
        node["name"]="cloudredis"
        node["serviceName"]="oddkinz"
        node["deploymentName"]="storm1"

        result = self.driver.reboot_node(node)

        self.assertTrue(result)

    #simulating attempting to reboot a node that ifas already rebooting
    def test_vmimages_restart_node_fail(self):
        node = dict()
        node["name"]="cloudredis"
        node["serviceName"]="oddkinz"
        node["deploymentName"]="oddkinz1"

        result = self.driver.reboot_node(node)

        self.assertFalse(result)

    def test_destroy_node_success_single_node_in_cloud_service(self):

        node = type('Node', (object,), dict(id="oddkinz1"))

        result = self.driver.destroy_node(node, ex_cloud_service_name="oddkinz1", ex_deployment_slot="Production")
        self.assertTrue(result)

    def test_destroy_node_success_multiple_nodes_in_cloud_service(self):

        node = type('Node', (object,), dict(id="oddkinz1"))

        result = self.driver.destroy_node(node, ex_cloud_service_name="oddkinz2", ex_deployment_slot="Production")
        self.assertTrue(result)

    def test_destroy_node_fail_node_does_not_exist(self):

        node = type('Node', (object,), dict(id="oddkinz2"))

        result = self.driver.destroy_node(node, ex_cloud_service_name="oddkinz2", ex_deployment_slot="Production")
        self.assertFalse(result)

    def test_destroy_node_success_cloud_service_not_found(self):

        node = dict()
        node["name"]="cloudredis"

        result = self.driver.destroy_node(node, ex_cloud_service_name="oddkinz2", ex_deployment_slot="Production" )

        print result

class AzureMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('azure')

    def _5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz1_deploymentslots_Production(self, method, url, body, headers):
         if method == "GET":
                body = self.fixtures.load('_5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz1_deploymentslots_Production.xml')

         return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz1_deployments_dc01(self, method, url, body, headers):
         return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz2_deploymentslots_Production(self, method, url, body, headers):
         if method == "GET":
                body = self.fixtures.load('_5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz2_deploymentslots_Production.xml')

         return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz2_deployments_dc03_roles_oddkinz1(self, method, url, body, headers):
         return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _5191b16a_673d_426c_8c55_fdd912858e4e_services_hostedservices_oddkinz2_deployments_dc03_roles_oddkinz2(self, method, url, body, headers):
         return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

if __name__ == '__main__':
    sys.exit(unittest.main())
