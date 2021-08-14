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
"""
Tests for Amazon Elastic Kubernetes Driver
"""

import sys
import unittest

from unittest.mock import MagicMock

from libcloud.container.drivers.eks import ElasticKubernetesDriver

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ContainerFileFixtures

from libcloud.test.secrets import CONTAINER_PARAMS_EKS

from libcloud.utils.py3 import httplib


class ElasticKubernetesDriverTestCase(unittest.TestCase):
    """
    Amazon Elastic Kubernetes Driver Test Class.
    """

    def setUp(self):
        ElasticKubernetesDriver.connectionCls.conn_class = EKSMockHttp
        EKSMockHttp.type = None
        EKSMockHttp.use_param = 'a'
        ElasticKubernetesDriver.containerDriverCls = MagicMock()
        self.driver = ElasticKubernetesDriver(*CONTAINER_PARAMS_EKS)

    def test_list_clusters(self):
        clusters = self.driver.list_clusters()
        self.assertEqual(clusters[0].name, 'default')
        self.assertEqual(clusters[0].id,
                         'arn:aws:eks:us-east-2:532769602413:cluster/default')

    def test_get_cluster(self):
        cluster = self.driver.get_cluster('default')
        self.assertEqual(cluster.name, 'default')
        self.assertEqual(cluster.id,
                         'arn:aws:eks:us-east-2:532769602413:cluster/default')

    def test_create_cluster(self):
        cluster = self.driver.create_cluster(
            name='default',
            role_arn='arn:aws:iam::532769602413:role/AmazonEKSClusterRole',
            vpc_id='vpc-e6782c8e',
            subnet_ids=[
                'subnet-0f4c23bae0d4f6b77',
                'subnet-044e2bb5e0c457418',
                'subnet-0d300601beef852af'
            ],
            security_group_ids=['sg-030fd1d39c9195c33'])
        self.assertEqual(cluster.name, 'default')
        self.assertEqual(cluster.id,
                         'arn:aws:eks:us-east-2:532769602413:cluster/default')


class EKSMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('eks')

    def _clusters(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('clusters.json')
        elif method == 'POST':
            body = self.fixtures.load('clusters_default.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _clusters_default(self, method, url, body, headers):
        body = self.fixtures.load('clusters_default.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
