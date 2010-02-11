# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
import unittest

from libcloud.drivers.voxel import VoxelNodeDriver as Voxel
from libcloud.types import Provider, NodeState, InvalidCredsException
from libcloud.base import Node, NodeImage, NodeSize

import httplib

from test import MockHttp, multipleresponse, TestCaseMixin
from secrets import VOXEL_KEY, VOXEL_SECRET
from xml.etree import ElementTree as ET

class VoxelTest(unittest.TestCase):

    def setUp(self):

        Voxel.connectionCls.conn_classes = (None, VoxelMockHttp)
        VoxelMockHttp.type = None
        self.driver = Voxel('foo', 'bar')

    def test_auth_failed(self):
        VoxelMockHttp.type = 'UNAUTHORIZED'
        try:
            ret = self.driver.list_nodes()
        except Exception, e:
            self.assertTrue(isinstance(e, InvalidCredsException))
        else:
            self.fail('test should have thrown')

class VoxelMockHttp(MockHttp):

    def _UNAUTHORIZED(self, method, url, body, headers):
        body = """<?xml version="1.0"?>
<rsp stat="fail"><err code="1" msg="Invalid login or password"/><method>voxel.devices.list</method><parameters><param name="timestamp">2010-02-10T23:39:25.808107+0000</param><param name="key">authshouldfail</param><param name="api_sig">ae069bb835e998622caaddaeff8c98e0</param></parameters><string_to_sign>YOUR_SECRETtimestamp2010-02-10T23:39:25.808107+0000methodvoxel.devices.listkeyauthshouldfail</string_to_sign></rsp>
"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
