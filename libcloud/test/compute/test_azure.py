import libcloud
from libcloud.common.types import LibcloudError
from libcloud.compute.base import NodeAuthPassword

__author__ = 'david'

import sys

import httplib
import unittest
import libcloud.security

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

class AzureNodeDriverTests(unittest.TestCase) :

    #required otherwise we get client side SSL verification
    libcloud.security.VERIFY_SSL_CERT = False

    SUBSCRIPTION_ID = '3761b98b-673d-526c-8d55-fee918758e6e'
    KEY_FILE = 'fixtures/azure/libcloud.pem' #empty file is fine

    def setUp(self):
        Azure = get_driver(Provider.AZURE)
        Azure.connectionCls.conn_classes = (None, AzureMockHttp)
        self.driver = Azure(self.SUBSCRIPTION_ID, self.KEY_FILE )

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 7)

        locationNamesResult = list(a.name for a in locations)
        locationNamesExpected = ['East Asia','Southeast Asia','North Europe',
                                 'West Europe','East US','North Central US',
                                 'West US']

        self.assertListEqual(locationNamesResult, locationNamesExpected)

        matchedLocation = next(location for location in locations
                               if location.name == 'Southeast Asia')
        servicesResult = matchedLocation.available_services
        servicesExpected = ['Compute','Storage','PersistentVMRole','HighMemory']
        self.assertListEqual(servicesResult, servicesExpected)

        vmRoleSizesResult = matchedLocation.virtual_machine_role_sizes

        vmRoleSizesExpected = ['A5','A6','A7','Basic_A0','Basic_A1','Basic_A2',
                               'Basic_A3','Basic_A4','ExtraLarge','ExtraSmall',
                               'Large','Medium','Small']
        self.assertListEqual(vmRoleSizesResult, vmRoleSizesExpected)

    def test_images_returned_successfully(self):
        images = self.driver.list_images()
        self.assertEquals(len(images), 215 )

    def test_images_returned_successfully_filter_by_location(self):
        images = self.driver.list_images(location="West US")
        self.assertEquals(len(images), 207 )

    def test_list_nodes_returned_successfully(self):
        vmimages = self.driver.list_nodes(
            ex_cloud_service_name="dcoddkinztest01")
        self.assertEqual(len(vmimages), 2)

        img0 = vmimages[0]
        self.assertEquals(img0.id,"dc03")
        self.assertEquals(img0.name,u"dc03")
        self.assertListEqual(img0.public_ips,["191.235.135.62"])
        self.assertListEqual(img0.private_ips,["100.92.66.69"])
        self.assertEquals(img0.size,None)
        self.assertEquals(img0.state,0)
        self.assertTrue(isinstance(img0.extra,dict))
        extra = img0.extra
        self.assertEquals(extra["instance_size"], u'Small')
        self.assertEquals(extra["power_state"], u'Started')
        self.assertEquals(extra["ssh_port"], u'22')

    def test_list_nodes_returned_no_deployments(self):
        vmimages = self.driver.list_nodes(
            ex_cloud_service_name="dcoddkinztest03")
        self.assertIsNone(vmimages)

    def test_list_nodes_returned_no_cloud_service(self):
        with self.assertRaises(LibcloudError):
           self.driver.list_nodes(ex_cloud_service_name="dcoddkinztest04")

    def test_restart_node_success(self):

        node = type('Node', (object,), dict(id="dc03"))
        result = self.driver.reboot_node(
            node=node, ex_cloud_service_name="dcoddkinztest01",
            ex_deployment_slot="Production")

        self.assertTrue(result)

    #simulating attempting to reboot a node that ifas already rebooting
    def test_restart_node_fail_no_deployment(self):

        node = type('Node', (object,), dict(id="dc03"))

        with self.assertRaises(LibcloudError):
            self.driver.reboot_node(node=node,
                                    ex_cloud_service_name="dcoddkinztest02",
                                    ex_deployment_slot="Production")

    def test_restart_node_fail_no_cloud_service(self):

        node = type('Node', (object,), dict(id="dc03"))

        with self.assertRaises(LibcloudError):
            self.driver.reboot_node(node=node,
                                    ex_cloud_service_name="dcoddkinztest03",
                                    ex_deployment_slot="Production")

    def test_restart_node_fail_node_not_found(self):

        node = type('Node', (object,), dict(id="dc13"))


        result = self.driver.reboot_node(
            node=node, ex_cloud_service_name="dcoddkinztest01",
            ex_deployment_slot="Production")
        self.assertFalse(result)

    def test_destroy_node_success_single_node_in_cloud_service(self):

        node = type('Node', (object,), dict(id="oddkinz1"))

        result = self.driver.destroy_node(node=node,
                                          ex_cloud_service_name="oddkinz1",
                                          ex_deployment_slot="Production")
        self.assertTrue(result)

    def test_destroy_node_success_multiple_nodes_in_cloud_service(self):

        node = type('Node', (object,), dict(id="oddkinz1"))

        result = self.driver.destroy_node(node=node,
                                          ex_cloud_service_name="oddkinz2",
                                          ex_deployment_slot="Production")
        self.assertTrue(result)

    def test_destroy_node_fail_node_does_not_exist(self):

        node = type('Node', (object,), dict(id="oddkinz2"))

        with self.assertRaises(LibcloudError):
            self.driver.destroy_node(node=node,
                                     ex_cloud_service_name="oddkinz2",
                                     ex_deployment_slot="Production")

    def test_destroy_node_success_cloud_service_not_found(self):

        node = dict()
        node["name"]="cloudredis"

        with self.assertRaises(LibcloudError):
            self.driver.destroy_node(node=node,
                                     ex_cloud_service_name="oddkinz5",
                                     ex_deployment_slot="Production" )

    def test_create_cloud_service(self):
        result = self.driver.create_cloud_service("testdc123", "North Europe")
        self.assertTrue(result)

    def test_create_cloud_service_service_exists(self):

        with self.assertRaises(LibcloudError):
            self.driver.create_cloud_service(ex_cloud_service_name="testdc1234",
                                             location="North Europe")

    def test_destroy_cloud_service(self):

        result = self.driver.destroy_cloud_service(
            ex_cloud_service_name="testdc123")
        self.assertTrue(result)

    def test_destroy_cloud_service_service_does_not_exist(self):

        with self.assertRaises(LibcloudError):
            self.driver.destroy_cloud_service(
                ex_cloud_service_name="testdc1234")

    def test_create_node_and_deployment_one_node(self):
        kwargs = {}

        kwargs["ex_storage_service_name"]="mtlytics"
        kwargs["ex_deployment_name"]="dcoddkinztest02"
        kwargs["ex_deployment_slot"]="Production"
        kwargs["ex_admin_user_id"]="azurecoder"

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"]= auth

        kwargs["size"]= "ExtraSmall"
        kwargs["image"] = \
            "5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415"
        kwargs["name"] = "dcoddkinztest03"

        result = self.driver.create_node(
            ex_cloud_service_name="testdcabc", **kwargs)
        self.assertIsNotNone(result)

    def test_create_node_and_deployment_second_node(self):
        kwargs = {}

        kwargs["ex_storage_service_name"]="mtlytics"
        kwargs["ex_deployment_name"]="dcoddkinztest02"
        kwargs["ex_deployment_slot"]="Production"
        kwargs["ex_admin_user_id"]="azurecoder"

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"]= auth

        kwargs["size"]= "ExtraSmall"
        kwargs["image"] = \
            "5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415"
        kwargs["name"] = "dcoddkinztest03"

        node = type('Node', (object,), dict(id="dc14"))
        result = self.driver.create_node(
            ex_cloud_service_name="testdcabc2", **kwargs)
        self.assertIsNotNone(result)

    def test_create_node_and_deployment_second_node_307_response(self):
        kwargs = {}

        kwargs["ex_storage_service_name"]="mtlytics"
        kwargs["ex_deployment_name"]="dcoddkinztest04"
        kwargs["ex_deployment_slot"]="Production"
        kwargs["ex_admin_user_id"]="azurecoder"

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"]= auth

        kwargs["size"]= "ExtraSmall"
        kwargs["image"] = \
            "5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415"
        kwargs["name"] = "dcoddkinztest04"

        with self.assertRaises(LibcloudError):
            self.driver.create_node(ex_cloud_service_name="testdcabc3",
                                    **kwargs)

class AzureMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('azure')

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz1_deploymentslots_Production(self, method, url, body, headers):
         if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz1_deploymentslots_Production.xml')

         return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz1_deployments_dc01(self, method, url, body, headers):
         return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz2_deploymentslots_Production(self, method, url, body, headers):
         if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz2_deploymentslots_Production.xml')

         return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz2_deployments_dc03_roles_oddkinz1(self, method, url, body, headers):
         return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz2_deployments_dc03_roles_oddkinz2(self, method, url, body, headers):
         return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz5_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_oddkinz5_deploymentslots_Production.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01_deploymentslots_Production.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01_deployments_dc03_roleinstances_dc03(self, method, url, body, headers):
        headers["x-ms-request-id"]="acc33f6756cda6fd96826394fce4c9f3"
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest02_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest02_deploymentslots_Production.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest03_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest03_deploymentslots_Production.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01_deployments_dc03_roleinstances_dc13(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01_deployments_dc03_roleinstances_dc13.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest01.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest03(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest03.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest04(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_dcoddkinztest04.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_images(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_images.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_locations(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_locations.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices(self, method, url, body, headers):
        # request url is the same irrespective of serviceName, only way to differentiate
        if "<ServiceName>testdc123</ServiceName>" in body:
            return (httplib.CREATED, body, headers, httplib.responses[httplib.CREATED])
        elif "<ServiceName>testdc1234</ServiceName>" in body:
            return (httplib.CONFLICT, body, headers, httplib.responses[httplib.CONFLICT])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdc123(self, method, url, body, headers):
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdc1234(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdc1234.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc_deployments(self, method, url, body, headers):
        headers["x-ms-request-id"]="acc33f6756cda6fd96826394fce4c9f3"
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc_deployments.xml')

        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deploymentslots_Production(self, method, url, body, headers):

        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deploymentslots_Production.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deployments(self, method, url, body, headers):

        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deployments.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deployments_dcoddkinztest02_roles(self, method, url, body, headers):
        headers["x-ms-request-id"]="acc33f6756cda6fd96826394fce4c9f3"
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc3(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc3_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deploymentslots_Production.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc3_deployments(self, method, url, body, headers):
        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deployments.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc3_deployments_dcoddkinztest02_roles(self, method, url, body, headers):

        return (httplib.TEMPORARY_REDIRECT, None, headers, httplib.responses[httplib.TEMPORARY_REDIRECT])

    def _3761b98b_673d_526c_8d55_fee918758e6e_operations_acc33f6756cda6fd96826394fce4c9f3(self, method, url, body, headers):

        if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_operations_acc33f6756cda6fd96826394fce4c9f3.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])
if __name__ == '__main__':
    sys.exit(unittest.main())
