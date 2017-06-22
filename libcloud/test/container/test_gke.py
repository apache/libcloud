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

from libcloud.utils.py3 import httplib
from libcloud.container.drivers.gke import GKEContainerDriver, API_VERSION
from libcloud.common.google import (GoogleBaseAuthConnection)
from libcloud.test.common.test_google import GoogleAuthMockHttp, GoogleTestCase

from libcloud.test import MockHttp
from libcloud.test.container import TestCaseMixin
from libcloud.test.file_fixtures import ContainerFileFixtures

from libcloud.test.secrets import GKE_PARAMS, GKE_KEYWORD_PARAMS


class GKEContainerDriverTestCase(GoogleTestCase, TestCaseMixin):
    """
    Google Compute Engine Test Class.
    """
    # Mock out a few specific calls that interact with the user, system or
    # environment.
    datacenter = 'us-central1-a'

    def setUp(self):
        GKEMockHttp.test = self
        GKEContainerDriver.connectionCls.conn_class = GKEMockHttp
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        GKEMockHttp.type = None
        kwargs = GKE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        kwargs['datacenter'] = self.datacenter
        self.driver = GKEContainerDriver(*GKE_PARAMS, **kwargs)

    def test_list_images_response(self):
        config = self.driver.list_clusters(ex_zone="us-central1-a")
        assert "clusters" in config
        assert config["clusters"][0]["zone"] == "us-central1-a"

    def test_server_config(self):
        config = self.driver.get_server_config()
        assert "validImageTypes" in config


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
            'zones_us-central1-a_instance_serverconfig.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_clusters(self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_list.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
