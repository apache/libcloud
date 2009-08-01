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
from libcloud.types import Node, NodeState
from libcloud.interface import INodeDriver
from zope.interface import implements

import uuid

class DummyNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds

    def get_uuid(self, unique_field=None):
        return str(uuid.uuid4())
        
    def list_nodes(self):
        return [
            Node(uuid=self.get_uuid(),
                 name='dummy-1',
                 state=NodeState.RUNNING,
                 ipaddress='127.0.0.1',
                 creds=self.creds,
                 attrs={'foo': 'bar'}),
            Node(uuid=self.get_uuid(),
                 name='dummy-2',
                 state=NodeState.REBOOTING,
                 ipaddress='127.0.0.2',
                 creds=self.creds,
                 attrs={'foo': 'bar'})
        ]

    def reboot_node(self, node):
        node.state = NodeState.REBOOTING
        return node

    def destroy_node(self, node):
        pass

    def create_node(self, node):
        pass
