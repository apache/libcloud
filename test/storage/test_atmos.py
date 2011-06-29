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

import base64
import httplib
import os.path
import sys
import unittest

from xml.etree import ElementTree

from libcloud.storage.drivers.atmos import AtmosDriver

from test import StorageMockHttp, MockRawResponse
from test.file_fixtures import StorageFileFixtures

class AtmosTests(unittest.TestCase):
    def setUp(self):
        AtmosDriver.connectionCls.conn_classes = (None, AtmosMockHttp)
        AtmosDriver.connectionCls.rawResponseCls = AtmosMockRawResponse
        AtmosDriver.path = ''
        AtmosMockHttp.type = None
        AtmosMockRawResponse.type = None
        self.driver = AtmosDriver('dummy', base64.b64encode('dummy'))
        self._remove_test_file()

    def tearDown(self):
        self._remove_test_file()

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

    def test_list_containers(self):
        AtmosMockHttp.type = 'EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

        AtmosMockHttp.type = None
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 6)

class AtmosMockHttp(StorageMockHttp):
    fixtures = StorageFileFixtures('atmos')

    def _rest_namespace_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('empty_directory_listing.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_namespace(self, method, url, body, headers):
        body = self.fixtures.load('list_containers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

class AtmosMockRawResponse(MockRawResponse):
    pass

if __name__ == '__main__':
    sys.exit(unittest.main())
