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

from libcloud.container.base import ContainerCluster, ContainerImage, Container
from libcloud.container.drivers.ecs import ElasticContainerDriver
from libcloud.container.utils.docker import RegistryClient

from libcloud.utils.py3 import httplib
from libcloud.test.secrets import CONTAINER_PARAMS_ECS
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class ElasticContainerDriverTestCase(unittest.TestCase):

    def setUp(self):
        ElasticContainerDriver.connectionCls.conn_class = ECSMockHttp
        ECSMockHttp.type = None
        ECSMockHttp.use_param = 'a'
        ElasticContainerDriver.ecrConnectionClass.conn_class = ECSMockHttp

        self.driver = ElasticContainerDriver(*CONTAINER_PARAMS_ECS)

    def test_list_clusters(self):
        clusters = self.driver.list_clusters()
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].id, 'arn:aws:ecs:us-east-1:012345678910:cluster/default')
        self.assertEqual(clusters[0].name, 'default')

    def test_create_cluster(self):
        cluster = self.driver.create_cluster('my-cluster')
        self.assertEqual(cluster.name, 'my-cluster')

    def test_destroy_cluster(self):
        self.assertTrue(
            self.driver.destroy_cluster(
                ContainerCluster(
                    id='arn:aws:ecs:us-east-1:012345678910:cluster/jim',
                    name='jim',
                    driver=self.driver)))

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 1)

    def test_list_containers_for_cluster(self):
        cluster = self.driver.list_clusters()[0]
        containers = self.driver.list_containers(cluster=cluster)
        self.assertEqual(len(containers), 1)

    def test_deploy_container(self):
        container = self.driver.deploy_container(
            name='jim',
            image=ContainerImage(
                id=None,
                name='mysql',
                path='mysql',
                version=None,
                driver=self.driver
            )
        )
        self.assertEqual(container.id, 'arn:aws:ecs:ap-southeast-2:647433528374:container/e443d10f-dea3-481e-8a1e-966b9ad4e498')

    def test_get_container(self):
        container = self.driver.get_container(
            'arn:aws:ecs:us-east-1:012345678910:container/76c980a8-2454-4a9c-acc4-9eb103117273'
        )
        self.assertEqual(container.id, 'arn:aws:ecs:ap-southeast-2:647433528374:container/d56d4e2c-9804-42a7-9f2a-6029cb50d4a2')
        self.assertEqual(container.name, 'simple-app')
        self.assertEqual(container.image.name, 'simple-app')

    def test_start_container(self):
        container = self.driver.start_container(
            Container(
                id=None,
                name=None,
                image=None,
                state=None,
                ip_addresses=None,
                driver=self.driver,
                extra={
                    'taskDefinitionArn': ''
                }
            )
        )
        self.assertFalse(container is None)

    def test_stop_container(self):
        container = self.driver.stop_container(
            Container(
                id=None,
                name=None,
                image=None,
                state=None,
                ip_addresses=None,
                driver=self.driver,
                extra={
                    'taskArn': '12345',
                    'taskDefinitionArn': '123556'
                }
            )
        )
        self.assertFalse(container is None)

    def test_restart_container(self):
        container = self.driver.restart_container(
            Container(
                id=None,
                name=None,
                image=None,
                state=None,
                ip_addresses=None,
                driver=self.driver,
                extra={
                    'taskArn': '12345',
                    'taskDefinitionArn': '123556'
                }
            )
        )
        self.assertFalse(container is None)

    def test_list_images(self):
        images = self.driver.list_images('my-images')
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].name, '647433528374.dkr.ecr.region.amazonaws.com/my-images:latest')

    def test_ex_create_service(self):
        cluster = self.driver.list_clusters()[0]
        task_definition = self.driver.list_containers()[0].extra['taskDefinitionArn']
        service = self.driver.ex_create_service(cluster=cluster,
                                                name='jim',
                                                task_definition=task_definition)
        self.assertEqual(service['serviceName'], 'test')

    def test_ex_list_service_arns(self):
        arns = self.driver.ex_list_service_arns()
        self.assertEqual(len(arns), 2)

    def test_ex_describe_service(self):
        arn = self.driver.ex_list_service_arns()[0]
        service = self.driver.ex_describe_service(arn)
        self.assertEqual(service['serviceName'], 'test')

    def test_ex_destroy_service(self):
        arn = self.driver.ex_list_service_arns()[0]
        service = self.driver.ex_destroy_service(arn)
        self.assertEqual(service['status'], 'DRAINING')

    def test_ex_get_registry_client(self):
        client = self.driver.ex_get_registry_client('my-images')
        self.assertIsInstance(client, RegistryClient)


class ECSMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('ecs')
    fixture_map = {
        'DescribeClusters': 'describeclusters.json',
        'CreateCluster': 'createcluster.json',
        'DeleteCluster': 'deletecluster.json',
        'DescribeTasks': 'describetasks.json',
        'ListTasks': 'listtasks.json',
        'ListClusters': 'listclusters.json',
        'RegisterTaskDefinition': 'registertaskdefinition.json',
        'RunTask': 'runtask.json',
        'StopTask': 'stoptask.json',
        'ListImages': 'listimages.json',
        'DescribeRepositories': 'describerepositories.json',
        'CreateService': 'createservice.json',
        'ListServices': 'listservices.json',
        'DescribeServices': 'describeservices.json',
        'DeleteService': 'deleteservice.json',
        'GetAuthorizationToken': 'getauthorizationtoken.json'
    }

    def root(self, method, url, body, headers):
        target = headers['x-amz-target']

        # Workaround for host not being correctly set for the tests
        if '%s' in self.host:
            self.host = self.host % ('region')

        if target is not None:
            type = target.split('.')[-1]
            if type is None or self.fixture_map.get(type) is None:
                raise AssertionError('Unsupported request type %s' % (target))
            body = self.fixtures.load(self.fixture_map.get(type))
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
