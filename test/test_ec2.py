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

from libcloud.providers import connect
from libcloud.types import Provider, Node

from secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase):

    def setUp(self):
        self.conn = connect(Provider.EC2, EC2_ACCESS_ID, EC2_SECRET)

    def test_list_nodes(self):
        ret = self.conn.list_nodes()

# XXX: need to make this test based on a node that was created
#    def test_reboot_nodes(self):
#        node = Node(None, None, None, None, None, 
#                    attrs={'instanceId':'i-e1615d88'})
#        ret = self.conn.reboot_node(node)
