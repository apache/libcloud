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
import unittest

from libcloud.drivers.voxel import VoxelNodeDriver as Voxel
from libcloud.types import InvalidCredsException

import httplib

from test import MockHttp
from test.file_fixtures import FileFixtures

from secrets import VOXEL_KEY, VOXEL_SECRET

class VoxelTest(unittest.TestCase):

    def setUp(self):

        Voxel.connectionCls.conn_classes = (None, VoxelMockHttp)
        VoxelMockHttp.type = None
        self.driver = Voxel(VOXEL_KEY, VOXEL_SECRET)

    def test_auth_failed(self):
        VoxelMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_nodes()
        except Exception, e:
            self.assertTrue(isinstance(e, InvalidCredsException))
        else:
            self.fail('test should have thrown')

class VoxelMockHttp(MockHttp):

    fixtures = FileFixtures('voxel')

    def _UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load('unauthorized.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
