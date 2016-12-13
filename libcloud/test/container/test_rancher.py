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

from libcloud.test import unittest

from libcloud.container.base import ContainerImage
from libcloud.container.drivers.rancher import RancherContainerDriver

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_RANCHER
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


# --------------------------------------------------------------------------- #
# Mock Classes

class RancherMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('rancher')

    def _v1_environments(self, method, url, body, headers):
        if method == 'GET':
            return (httplib.OK, self.fixtures.load('ex_list_stacks.json'), {},
                    httplib.responses[httplib.OK])
        else:
            return (httplib.OK, self.fixtures.load('ex_deploy_stack.json'), {},
                    httplib.responses[httplib.OK])

    def _v1_environments_1e9(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('ex_deploy_stack.json'), {},
                httplib.responses[httplib.OK])

    def _v1_environments_1e10(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('ex_destroy_stack.json'), {},
                httplib.responses[httplib.OK])

    def _v1_environments_1e1(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('ex_activate_stack.json'), {},
                httplib.responses[httplib.OK])

    def _v1_services(self, method, url, body, headers):
        if '?healthState=healthy' in url:
            return (httplib.OK, self.fixtures.load('ex_search_services.json'),
                    {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            return (httplib.OK, self.fixtures.load('ex_list_services.json'),
                    {}, httplib.responses[httplib.OK])
        else:
            return (httplib.OK, self.fixtures.load('ex_deploy_service.json'),
                    {}, httplib.responses[httplib.OK])

    def _v1_services_1s13(self, method, url, body, headers):
        if method == 'GET':
            return (httplib.OK, self.fixtures.load('ex_deploy_service.json'),
                    {}, httplib.responses[httplib.OK])
        elif method == 'DELETE':
            return (httplib.OK, self.fixtures.load('ex_destroy_service.json'),
                    {}, httplib.responses[httplib.OK])

    def _v1_services_1s6(self, method, url, body, headers):
        return (httplib.OK, self.fixtures.load('ex_activate_service.json'), {},
                httplib.responses[httplib.OK])

    def _v1_containers(self, method, url, body, headers):
        if '?state=running' in url:
            return (httplib.OK,
                    self.fixtures.load('ex_search_containers.json'), {},
                    httplib.responses[httplib.OK])
        elif method == 'POST':
            return (httplib.OK, self.fixtures.load('deploy_container.json'),
                    {}, httplib.responses[httplib.OK])
        return (httplib.OK, self.fixtures.load('list_containers.json'), {},
                httplib.responses[httplib.OK])

    def _v1_containers_1i31(self, method, url, body, headers):
        if method == 'GET':
            return (httplib.OK, self.fixtures.load('deploy_container.json'),
                    {}, httplib.responses[httplib.OK])
        elif method == 'DELETE' or '?action=stop' in url:
            return (httplib.OK, self.fixtures.load('stop_container.json'), {},
                    httplib.responses[httplib.OK])
        elif '?action=start' in url:
            return (httplib.OK, self.fixtures.load('start_container.json'), {},
                    httplib.responses[httplib.OK])
        else:
            return (httplib.OK, self.fixtures.load('deploy_container.json'),
                    {}, httplib.responses[httplib.OK])


RancherContainerDriver.connectionCls.conn_classes = (
    RancherMockHttp, RancherMockHttp
)
RancherMockHttp.type = None
RancherMockHttp.use_param = 'a'


# --------------------------------------------------------------------------- #
# Test Cases


class RancherContainerDriverInitTestCase(unittest.TestCase):
    """
    Tests for testing the different permutations of the driver initialization
    string.
    """

    def test_full_url_string(self):
        """
        Test a 'full' URL string, which contains a scheme, port, and base path.
        """
        path = "http://myhostname:1234/base"
        driver = RancherContainerDriver(*CONTAINER_PARAMS_RANCHER, host=path)

        self.assertEqual(driver.secure, False)
        self.assertEqual(driver.connection.host, "myhostname")
        self.assertEqual(driver.connection.port, 1234)
        self.assertEqual(driver.baseuri, "/base")

    def test_url_string_no_port(self):
        """
        Test a partial URL string, which contains a scheme, and base path.
        """
        path = "http://myhostname/base"
        driver = RancherContainerDriver(*CONTAINER_PARAMS_RANCHER, host=path,
                                        port=1234)

        self.assertEqual(driver.secure, False)
        self.assertEqual(driver.connection.host, "myhostname")
        self.assertEqual(driver.connection.port, 1234)
        self.assertEqual(driver.baseuri, "/base")

    def test_url_string_no_scheme(self):
        """
        Test a partial URL string, which contains a port, and base path.
        """
        path = "myhostname:1234/base"
        driver = RancherContainerDriver(*CONTAINER_PARAMS_RANCHER, host=path)

        self.assertEqual(driver.secure, True)
        self.assertEqual(driver.connection.host, "myhostname")
        self.assertEqual(driver.connection.port, 1234)
        self.assertEqual(driver.baseuri, "/base")

    def test_url_string_no_base_path(self):
        """
        Test a partial URL string, which contains a scheme, and a port.
        """
        path = "http://myhostname:1234"
        driver = RancherContainerDriver(*CONTAINER_PARAMS_RANCHER, host=path)

        self.assertEqual(driver.secure, False)
        self.assertEqual(driver.connection.host, "myhostname")
        self.assertEqual(driver.connection.port, 1234)
        self.assertEqual(driver.baseuri, "/v%s" % driver.version)


class RancherContainerDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.driver = RancherContainerDriver(*CONTAINER_PARAMS_RANCHER)

    # Stacks
    def test_ex_list_stacks(self):
        stacks = self.driver.ex_list_stacks()
        self.assertEqual(len(stacks), 6)
        self.assertEqual(stacks[0]['id'], "1e1")

    def test_ex_deploy_stack(self):
        stack = self.driver.ex_deploy_stack(name="newstack",
                                            environment={
                                                "root_password": "password"
                                            })
        self.assertEqual(stack['id'], "1e9")
        self.assertEqual(stack['environment']['root_password'], "password")

    def test_ex_get_stack(self):
        # also uses ex_deploy_stack.json
        stack = self.driver.ex_get_stack("1e9")
        self.assertEqual(stack['id'], "1e9")
        self.assertEqual(stack['environment']['root_password'], "password")

    def test_ex_search_stacks(self):
        stacks = self.driver.ex_search_stacks({"healthState": "healthy"})
        self.assertEqual(len(stacks), 6)
        self.assertEqual(stacks[0]['healthState'], "healthy")

    def test_ex_destroy_stack(self):
        response = self.driver.ex_destroy_stack("1e10")
        self.assertEqual(response, True)

    def test_ex_activate_stack(self):
        response = self.driver.ex_activate_stack("1e1")
        self.assertEqual(response, True)

    def test_ex_deactivate_stack(self):
        # also uses ex_activate_stack.json
        response = self.driver.ex_activate_stack("1e1")
        self.assertEqual(response, True)

    def test_ex_list_services(self):
        services = self.driver.ex_list_services()
        self.assertEqual(len(services), 4)
        self.assertEqual(services[0]['id'], "1s1")

    def test_ex_deploy_service(self):
        image = ContainerImage(
            id="hastebin",
            name="hastebin",
            path="rlister/hastebin",
            version="latest",
            driver=None
        )
        service = self.driver.ex_deploy_service(name="newservice",
                                                environment_id="1e1",
                                                image=image,
                                                environment={
                                                    "root_password": "password"
                                                })
        self.assertEqual(service['id'], "1s13")
        self.assertEqual(service['environmentId'], "1e6")
        self.assertEqual(service['launchConfig']['environment']
                         ['root_password'], "password")
        self.assertEqual(service['launchConfig']['imageUuid'],
                         "docker:rlister/hastebin:latest")

    def test_ex_get_service(self):
        # also uses ex_deploy_service.json
        service = self.driver.ex_get_service("1s13")
        self.assertEqual(service['id'], "1s13")
        self.assertEqual(service['environmentId'], "1e6")
        self.assertEqual(service['launchConfig']['environment']
                         ['root_password'], "password")

    def test_ex_search_services(self):
        services = self.driver.ex_search_services({"healthState": "healthy"})
        self.assertEqual(len(services), 2)
        self.assertEqual(services[0]['healthState'], "healthy")

    def test_ex_destroy_service(self):
        # Not sure how to do these with returns in mockhttp
        response = self.driver.ex_destroy_service("1s13")
        self.assertEqual(response, True)

    def test_ex_activate_service(self):
        response = self.driver.ex_activate_service("1s6")
        self.assertEqual(response, True)

    def test_ex_deactivate_service(self):
        # also uses ex_activate_service.json
        response = self.driver.ex_activate_service("1s6")
        self.assertEqual(response, True)

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)
        self.assertEqual(containers[0].id, "1i1")

    def test_deploy_container(self):
        container = self.driver.deploy_container(
            name='newcontainer',
            image=ContainerImage(
                id="hastebin",
                name="hastebin",
                path="rlister/hastebin",
                version="latest",
                driver=None
            ),
            environment={"STORAGE_TYPE": "file"},
            networkMode="managed"
        )
        self.assertEqual(container.id, '1i31')
        self.assertEqual(container.name, 'newcontainer')
        self.assertEqual(container.extra['environment'],
                         {'STORAGE_TYPE': 'file'})

    def test_get_container(self):
        # also uses ex_deploy_container.json
        container = self.driver.get_container("1i31")
        self.assertEqual(container.id, '1i31')
        self.assertEqual(container.name, 'newcontainer')
        self.assertEqual(container.extra['environment'],
                         {'STORAGE_TYPE': 'file'})

    def test_start_container(self):
        container = self.driver.get_container("1i31")
        started = container.start()
        self.assertEqual(started.id, "1i31")
        self.assertEqual(started.name, "newcontainer")
        self.assertEqual(started.state, "pending")
        self.assertEqual(started.extra['state'], "starting")

    def test_stop_container(self):
        container = self.driver.get_container("1i31")
        stopped = container.stop()
        self.assertEqual(stopped.id, "1i31")
        self.assertEqual(stopped.name, "newcontainer")
        self.assertEqual(stopped.state, "pending")
        self.assertEqual(stopped.extra['state'], "stopping")

    def test_ex_search_containers(self):
        containers = self.driver.ex_search_containers({"state": "running"})
        self.assertEqual(len(containers), 1)

    def test_destroy_container(self):
        container = self.driver.get_container("1i31")
        destroyed = container.destroy()
        self.assertEqual(destroyed.id, "1i31")
        self.assertEqual(destroyed.name, "newcontainer")
        self.assertEqual(destroyed.state, "pending")
        self.assertEqual(destroyed.extra['state'], "stopping")


if __name__ == '__main__':
    sys.exit(unittest.main())
