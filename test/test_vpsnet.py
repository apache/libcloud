# Licensed to libcloud.org under one or more
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

from libcloud.drivers.vpsnet import VPSNetNodeDriver
from libcloud.base import Node, NodeImage, NodeSize
from libcloud.types import NodeState

from test import MockHttp

import httplib

from secrets import VPSNET_USER, VPSNET_KEY

class EC2Tests(unittest.TestCase):

    def setUp(self):
        VPSNetNodeDriver.connectionCls.conn_classes = (None, VPSNetMockHttp)
        self.driver = VPSNetNodeDriver(VPSNET_USER, VPSNET_KEY)

    def test_list_nodes(self):
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, '1384')
        self.assertEqual(node.state, NodeState.RUNNING)


class VPSNetMockHttp(MockHttp):
    def _virtual_machines_api10json_virtual_machines(self, method, url, body, headers):
        body = """     [{
              "virtual_machine": 
                {
                  "running": true, 
                  "updated_at": "2009-05-15T06:55:02-04:00", 
                  "power_action_pending": false, 
                  "system_template_id": 41, 
                  "id": 1384, 
                  "cloud_id": 3, 
                  "domain_name": "demodomain.com", 
                  "hostname": "web01", 
                  "consumer_id": 0, 
                  "backups_enabled": false, 
                  "password": "a8hjsjnbs91", 
                  "label": "Web Server 01", 
                  "slices_count": null, 
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              },
              {
                "virtual_machine": 
                  {
                    "running": true, 
                    "updated_at": "2009-05-15T06:55:02-04:00", 
                    "power_action_pending": false, 
                    "system_template_id": 41, 
                    "id": 1385, 
                    "cloud_id": 3, 
                    "domain_name": "demodomain.com", 
                    "hostname": "mysql01", 
                    "consumer_id": 0, 
                    "backups_enabled": false, 
                    "password": "dsi8h38hd2s", 
                    "label": "MySQL Server 01", 
                    "slices_count": null, 
                    "created_at": "2009-04-16T08:17:39-04:00"
                  }
                }]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
