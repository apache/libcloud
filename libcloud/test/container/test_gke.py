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
Tests for Google Container Engine Driver
"""

import sys
import unittest

from unittest.mock import MagicMock

from libcloud.utils.py3 import httplib
from libcloud.container.drivers.gke import GKEContainerDriver, API_VERSION
from libcloud.common.google import (GoogleBaseAuthConnection)
from libcloud.test.common.test_google import GoogleAuthMockHttp, GoogleTestCase

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ContainerFileFixtures

from libcloud.test.secrets import GKE_PARAMS, GKE_KEYWORD_PARAMS


class GKEContainerDriverTestCase(GoogleTestCase):
    """
    Google Compute Engine Test Class.
    """

    def setUp(self):
        GKEMockHttp.test = self
        GKEContainerDriver.connectionCls.conn_class = GKEMockHttp
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        GKEMockHttp.type = None
        GKEContainerDriver.clusterDriverCls = MagicMock()
        kwargs = GKE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        self.driver = GKEContainerDriver(*GKE_PARAMS, **kwargs)

    def test_list_clusters(self):
        clusters = self.driver.list_clusters()
        self.assertEqual(
            clusters[0].id,
            'f7ff4c8cf47b48e9b13640d687fcef3d0a36cdb8ca2c4960b28e164eb52ae52b')
        self.assertEqual(clusters[0].name, 'cluster-1')
        self.assertEqual(clusters[0].location, 'us-central1-a')

    def test_create_cluster(self):
        cluster = self.driver.ex_create_cluster('us-central1-a', 'default')
        self.assertEqual(
            cluster.id,
            'e16b714412e546488a36281cce5acd6e595901c0624346c5904e986371f9d993')
        self.assertEqual(cluster.name, 'default')
        self.assertEqual(cluster.location, 'us-central1-a')

    def test_get_cluster(self):
        cluster = self.driver.ex_get_cluster('us-central1-a', 'default')
        self.assertEqual(
            cluster.id,
            'e16b714412e546488a36281cce5acd6e595901c0624346c5904e986371f9d993')
        self.assertEqual(cluster.name, 'default')
        self.assertEqual(cluster.location, 'us-central1-a')

    def test_destroy_cluster(self):
        cluster = self.driver.ex_destroy_cluster('us-central1-a', 'default')
        self.assertEqual(
            cluster.id,
            'e16b714412e546488a36281cce5acd6e595901c0624346c5904e986371f9d993')
        self.assertEqual(cluster.name, 'default')
        self.assertEqual(cluster.location, 'us-central1-a')

    def test_cluster_credentials(self):
        cluster = self.driver.ex_get_cluster('us-central1-a', 'default')
        self.driver.connection.oauth2_credential = MagicMock()
        self.driver.connection.oauth2_credential.access_token = '12345'
        credentials = self.driver.get_cluster_credentials(cluster)
        self.assertEqual(credentials['host'], '34.122.208.135')
        self.assertEqual(credentials['port'], '443')
        self.assertEqual(credentials['token'], '12345')

    def test_get_server_config(self):
        config = self.driver.get_server_config('us-central1-a')
        self.assertEqual(config['defaultClusterVersion'], '1.6.4')
        self.assertEqual(config['defaultImageType'], 'COS')


class GKEMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('gke')
    json_hdr = {'content-type': 'application/json; charset=UTF-8'}

    def _get_method_name(self, type, use_param, qs, path):
        api_path = '/%s' % API_VERSION
        project_path = '/projects/%s' % GKE_KEYWORD_PARAMS['project']
        path = path.replace(api_path, '')
        # This replace is separate, since there is a call with a different
        # project name
        path = path.replace(project_path, '')
        # The path to get project information is the base path, so use a fake
        # '/project' path instead
        if not path:
            path = '/project'
        method_name = super(GKEMockHttp, self)._get_method_name(
            type, use_param, qs, path)
        return method_name

    def _zones_us_central1_a_serverconfig(self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_serverconfig.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones___clusters(self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_-_clusters.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_clusters_default(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_clusters_default.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_clusters(self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_clusters_default.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
