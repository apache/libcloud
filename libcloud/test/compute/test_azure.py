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

import os
import sys

import libcloud.security
from libcloud.common.types import LibcloudError
from libcloud.compute.base import NodeAuthPassword, NodeImage, NodeSize
from libcloud.compute.drivers.azure import AZURE_SERVICE_MANAGEMENT_HOST

from libcloud.test import unittest
from libcloud.test import LibcloudTestCase
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.utils.py3 import httplib
from libcloud.compute.base import Node, NodeState
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


class AzureNodeDriverTests(LibcloudTestCase):
    #  required otherwise we get client side SSL verification
    libcloud.security.VERIFY_SSL_CERT = False

    SUBSCRIPTION_ID = '3761b98b-673d-526c-8d55-fee918758e6e'
    KEY_FILE = os.path.join(os.path.dirname(__file__), 'fixtures/azure/libcloud.pem')  # empty file is fine

    def setUp(self):
        Azure = get_driver(Provider.AZURE)
        Azure.connectionCls.conn_classes = (None, AzureMockHttp)
        self.driver = Azure(self.SUBSCRIPTION_ID, self.KEY_FILE)

    def test_locations_returned_successfully(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 7)

        location_names_result = list(a.name for a in locations)
        location_names_expected = [
            'East Asia',
            'Southeast Asia',
            'North Europe',
            'West Europe',
            'East US',
            'North Central US',
            'West US'
        ]

        self.assertListEqual(location_names_result, location_names_expected)

        matched_location = next(
            location for location in locations
            if location.name == 'Southeast Asia'
        )
        services_result = matched_location.available_services
        services_expected = [
            'Compute',
            'Storage',
            'PersistentVMRole',
            'HighMemory'
        ]
        self.assertListEqual(services_result, services_expected)

        vm_role_sizes_result = matched_location.virtual_machine_role_sizes

        vm_role_sizes_expected = [
            'A5',
            'A6',
            'A7',
            'Basic_A0',
            'Basic_A1',
            'Basic_A2',
            'Basic_A3',
            'Basic_A4',
            'ExtraLarge',
            'ExtraSmall',
            'Large',
            'Medium',
            'Small'
        ]
        self.assertListEqual(vm_role_sizes_result, vm_role_sizes_expected)

    def test_images_returned_successfully(self):
        images = self.driver.list_images()
        # There should be 215 standard OSImages and one VMImage returned
        self.assertEqual(len(images), 216)

    def test_images_returned_successfully_filter_by_location(self):
        images = self.driver.list_images(location="West US")
        self.assertEqual(len(images), 207)

    def test_list_nodes_returned_successfully(self):
        vmimages = self.driver.list_nodes(
            ex_cloud_service_name="dcoddkinztest01"
        )
        self.assertEqual(len(vmimages), 2)

        img0 = vmimages[0]
        self.assertEqual(img0.id, "dc03")
        self.assertEqual(img0.name, "dc03")
        self.assertListEqual(img0.public_ips, ["191.235.135.62"])
        self.assertListEqual(img0.private_ips, ["100.92.66.69"])
        self.assertEqual(img0.size, None)
        self.assertEqual(img0.state, NodeState.RUNNING)
        self.assertTrue(isinstance(img0.extra, dict))
        extra = img0.extra
        self.assertEqual(extra["instance_size"], 'Small')
        self.assertEqual(extra["power_state"], 'Started')
        self.assertEqual(extra["ssh_port"], '22')

    def test_list_nodes_returned_no_deployments(self):
        nodes = self.driver.list_nodes(
            ex_cloud_service_name="dcoddkinztest03"
        )
        self.assertEqual(nodes, [])

    def test_list_nodes_returned_no_cloud_service(self):
        with self.assertRaises(LibcloudError):
            self.driver.list_nodes(ex_cloud_service_name="dcoddkinztest04")

    def test_restart_node_success(self):

        node = Node(
            id="dc03",
            name="dc03",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )
        result = self.driver.reboot_node(
            node=node,
            ex_cloud_service_name="dcoddkinztest01",
            ex_deployment_slot="Production"
        )

        self.assertTrue(result)

    #  simulating attempting to reboot a node that is already rebooting
    def test_restart_node_fail_no_deployment(self):

        node = Node(
            id="dc03",
            name="dc03",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        with self.assertRaises(LibcloudError):
            self.driver.reboot_node(
                node=node,
                ex_cloud_service_name="dcoddkinztest02",
                ex_deployment_slot="Production"
            )

    def test_restart_node_fail_no_cloud_service(self):

        node = Node(
            id="dc03",
            name="dc03",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        with self.assertRaises(LibcloudError):
            self.driver.reboot_node(
                node=node,
                ex_cloud_service_name="dcoddkinztest03",
                ex_deployment_slot="Production"
            )

    def test_restart_node_fail_node_not_found(self):

        node = Node(
            id="dc13",
            name="dc13",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        result = self.driver.reboot_node(
            node=node,
            ex_cloud_service_name="dcoddkinztest01",
            ex_deployment_slot="Production"
        )
        self.assertFalse(result)

    def test_destroy_node_success_single_node_in_cloud_service(self):

        node = Node(
            id="oddkinz1",
            name="oddkinz1",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        result = self.driver.destroy_node(
            node=node,
            ex_cloud_service_name="oddkinz1",
            ex_deployment_slot="Production"
        )
        self.assertTrue(result)

    def test_destroy_node_success_multiple_nodes_in_cloud_service(self):

        node = Node(
            id="oddkinz1",
            name="oddkinz1",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        result = self.driver.destroy_node(
            node=node,
            ex_cloud_service_name="oddkinz2",
            ex_deployment_slot="Production"
        )
        self.assertTrue(result)

    def test_destroy_node_fail_node_does_not_exist(self):

        node = Node(
            id="oddkinz2",
            name="oddkinz2",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        with self.assertRaises(LibcloudError):
            self.driver.destroy_node(
                node=node,
                ex_cloud_service_name="oddkinz2",
                ex_deployment_slot="Production"
            )

    def test_destroy_node_success_cloud_service_not_found(self):

        node = Node(
            id="cloudredis",
            name="cloudredis",
            state=NodeState.RUNNING,
            public_ips=[],
            private_ips=[],
            driver=self.driver
        )

        with self.assertRaises(LibcloudError):
            self.driver.destroy_node(
                node=node,
                ex_cloud_service_name="oddkinz5",
                ex_deployment_slot="Production"
            )

    def test_ex_create_cloud_service(self):
        result = self.driver.ex_create_cloud_service(name="testdc123", location="North Europe")
        self.assertTrue(result)

    def test_ex_create_cloud_service_service_exists(self):
        with self.assertRaises(LibcloudError):
            self.driver.ex_create_cloud_service(
                name="testdc1234",
                location="North Europe"
            )

    def test_ex_destroy_cloud_service(self):
        result = self.driver.ex_destroy_cloud_service(name="testdc123")
        self.assertTrue(result)

    def test_ex_destroy_cloud_service_service_does_not_exist(self):
        with self.assertRaises(LibcloudError):
            self.driver.ex_destroy_cloud_service(name="testdc1234")

    def test_ex_create_storage_service(self):
        result = self.driver.ex_create_storage_service(name="testdss123", location="East US")
        self.assertTrue(result)

    def test_ex_create_storage_service_service_exists(self):
        with self.assertRaises(LibcloudError):
            self.driver.ex_create_storage_service(
                name="dss123",
                location="East US"
            )

    def test_ex_destroy_storage_service(self):
        result = self.driver.ex_destroy_storage_service(name="testdss123")
        self.assertTrue(result)

    def test_ex_destroy_storage_service_service_does_not_exist(self):
        with self.assertRaises(LibcloudError):
            self.driver.ex_destroy_storage_service(name="dss123")

    def test_create_node_and_deployment_one_node(self):
        kwargs = {
            "ex_storage_service_name": "mtlytics",
            "ex_deployment_name": "dcoddkinztest02",
            "ex_deployment_slot": "Production",
            "ex_admin_user_id": "azurecoder"
        }

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"] = auth
        kwargs["name"] = "dcoddkinztest03"

        kwargs["size"] = NodeSize(
            id="ExtraSmall",
            name="ExtraSmall",
            ram=1024,
            disk="30gb",
            bandwidth=0,
            price=0,
            driver=self.driver
        )
        kwargs["image"] = NodeImage(
            id="5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415",
            name="FakeImage",
            driver=self.driver,
            extra={
                'vm_image': False
            }
        )

        result = self.driver.create_node(
            ex_cloud_service_name="testdcabc",
            **kwargs
        )
        self.assertIsNotNone(result)

    def test_create_node_and_deployment_second_node(self):
        kwargs = {
            "ex_storage_service_name": "mtlytics",
            "ex_deployment_name": "dcoddkinztest02",
            "ex_deployment_slot": "Production",
            "ex_admin_user_id": "azurecoder"
        }

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"] = auth

        kwargs["size"] = NodeSize(
            id="ExtraSmall",
            name="ExtraSmall",
            ram=1024,
            disk="30gb",
            bandwidth=0,
            price=0,
            driver=self.driver
        )
        kwargs["image"] = NodeImage(
            id="5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415",
            name="FakeImage",
            driver=self.driver,
            extra={
                'vm_image': False
            }
        )
        kwargs["name"] = "dcoddkinztest03"

        result = self.driver.create_node(
            ex_cloud_service_name="testdcabc2",
            **kwargs
        )
        self.assertIsNotNone(result)

    def test_create_node_and_deployment_second_node_307_response(self):
        kwargs = {
            "ex_storage_service_name": "mtlytics",
            "ex_deployment_name": "dcoddkinztest04",
            "ex_deployment_slot": "Production",
            "ex_admin_user_id": "azurecoder"
        }

        auth = NodeAuthPassword("Pa55w0rd", False)
        kwargs["auth"] = auth

        kwargs["size"] = NodeSize(
            id="ExtraSmall",
            name="ExtraSmall",
            ram=1024,
            disk="30gb",
            bandwidth=0,
            price=0,
            driver=self.driver
        )
        kwargs["image"] = NodeImage(
            id="5112500ae3b842c8b9c604889f8753c3__OpenLogic-CentOS-65-20140415",
            name="FakeImage",
            driver=self.driver,
            extra={
                'vm_image': False
            }
        )
        kwargs["name"] = "dcoddkinztest04"

        with self.assertRaises(LibcloudError):
            self.driver.create_node(
                ex_cloud_service_name="testdcabc3",
                **kwargs
            )


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
        headers["x-ms-request-id"] = "acc33f6756cda6fd96826394fce4c9f3"
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

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_vmimages(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_vmimages.xml')

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

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_storageservices(self, method, url, body, headers):
        # request url is the same irrespective of serviceName, only way to differentiate
        if "<ServiceName>testdss123</ServiceName>" in body:
            return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])
        elif "<ServiceName>dss123</ServiceName>" in body:
            return (httplib.CONFLICT, body, headers, httplib.responses[httplib.CONFLICT])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_storageservices_testdss123(self, method, url, body, headers):
        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_storageservices_dss123(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_storageservices_dss123.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdc1234(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdc1234.xml')

        return (httplib.NOT_FOUND, body, headers, httplib.responses[httplib.NOT_FOUND])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc_deployments(self, method, url, body, headers):
        headers["x-ms-request-id"] = "acc33f6756cda6fd96826394fce4c9f3"
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

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc_deployments_dcoddkinztest02_roles(self, method, url, body, headers):
        headers["x-ms-request-id"] = "acc33f6756cda6fd96826394fce4c9f3"
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deployments_dcoddkinztest02_roles(self, method, url, body, headers):
        headers["x-ms-request-id"] = "acc33f6756cda6fd96826394fce4c9f3"
        return (httplib.ACCEPTED, body, headers, httplib.responses[httplib.ACCEPTED])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc3(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc_deploymentslots_Production(self, method, url, body, headers):
        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2_deploymentslots_Production.xml')

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
        redirect_host = "ussouth.management.core.windows.net"

        if not getattr(AzureMockHttp, "in_redirect", False):
            setattr(AzureMockHttp, "in_redirect", True)
            headers["Location"] = url.replace(AZURE_SERVICE_MANAGEMENT_HOST, redirect_host)
            return (httplib.TEMPORARY_REDIRECT, None, headers, httplib.responses[httplib.TEMPORARY_REDIRECT])
        else:
            delattr(AzureMockHttp, "in_redirect")
            if redirect_host not in url:
                if AZURE_SERVICE_MANAGEMENT_HOST in url:
                    return (httplib.TEMPORARY_REDIRECT, None, headers, httplib.responses[httplib.TEMPORARY_REDIRECT])
                else:
                    return (httplib.REQUEST_TIMEOUT, None, None, httplib.responses[httplib.REQUEST_TIMEOUT])

            if method == "GET":
                body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_services_hostedservices_testdcabc2.xml')

            return (httplib.OK, body, headers, httplib.responses[httplib.OK])

    def _3761b98b_673d_526c_8d55_fee918758e6e_operations_acc33f6756cda6fd96826394fce4c9f3(self, method, url, body, headers):

        if method == "GET":
            body = self.fixtures.load('_3761b98b_673d_526c_8d55_fee918758e6e_operations_acc33f6756cda6fd96826394fce4c9f3.xml')

        return (httplib.OK, body, headers, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
