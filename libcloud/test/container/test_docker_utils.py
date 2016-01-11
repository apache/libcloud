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
from libcloud.container.utils.docker import HubClient
from libcloud.utils.py3 import httplib
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class DockerUtilitiesTestCase(unittest.TestCase):

    def setUp(self):
        HubClient.connectionCls.conn_classes = (
            DockerMockHttp, DockerMockHttp)
        DockerMockHttp.type = None
        DockerMockHttp.use_param = 'a'
        self.driver = HubClient()

    def test_list_tags(self):
        tags = self.driver.list_images('ubuntu', max_count=100)
        self.assertEqual(len(tags), 88)
        self.assertEqual(tags[0].name, 'registry.hub.docker.com/ubuntu:xenial')

    def test_get_repository(self):
        repo = self.driver.get_repository('ubuntu')
        self.assertEqual(repo['name'], 'ubuntu')

    def test_get_image(self):
        image = self.driver.get_image('ubuntu', 'latest')
        self.assertEqual(image.id, '2343')
        self.assertEqual(image.name, 'registry.hub.docker.com/ubuntu:latest')
        self.assertEqual(image.path, 'registry.hub.docker.com/ubuntu:latest')


class DockerMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('docker_utils')

    def _v2_repositories_library_ubuntu_tags_latest(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('v2_repositories_library_ubuntu_tags_latest.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_repositories_library_ubuntu_tags(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('v2_repositories_library_ubuntu_tags.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_repositories_library_ubuntu(
            self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('v2_repositories_library_ubuntu.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
