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
Dummy Driver

@note: This driver is out of date
"""
from libcloud.interface import INodeDriver
from libcloud.base import ConnectionKey, NodeDriver, NodeSize, NodeLocation
from libcloud.base import NodeImage, Node
from libcloud.types import Provider,NodeState
from zope.interface import implements

import uuid

class DummyConnection(ConnectionKey):
    """
    Dummy connection class
    """

    def connect(self, host=None, port=None):
        pass

class DummyNodeDriver(NodeDriver):
    """
    Dummy node driver
    """

    name = "Dummy Node Provider"
    type = Provider.DUMMY

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds
        self.nl = [
            Node(id=1,
                 name='dummy-1',
                 state=NodeState.RUNNING,
                 public_ip=['127.0.0.1'],
                 private_ip=[],
                 driver=self,
                 extra={'foo': 'bar'}),
            Node(id=2,
                 name='dummy-2',
                 state=NodeState.RUNNING,
                 public_ip=['127.0.0.1'],
                 private_ip=[],
                 driver=self,
                 extra={'foo': 'bar'}),
        ]
        self.connection = DummyConnection(self.creds)

    def get_uuid(self, unique_field=None):
        return str(uuid.uuid4())

    def list_nodes(self):
        return self.nl

    def reboot_node(self, node):
        node.state = NodeState.REBOOTING
        return True

    def destroy_node(self, node):
        node.state = NodeState.TERMINATED
        self.nl.remove(node)
        return True

    def list_images(self, location=None):
        return [
            NodeImage(id=1, name="Ubuntu 9.10", driver=self),
            NodeImage(id=2, name="Ubuntu 9.04", driver=self),
            NodeImage(id=3, name="Slackware 4", driver=self),
        ]

    def list_sizes(self, location=None):
        return [
          NodeSize(id=1,
                   name="Small",
                   ram=128,
                   disk=4,
                   bandwidth=500,
                   price=4,
                   driver=self),
          NodeSize(id=2,
                   name="Medium",
                   ram=512,
                   disk=16,
                   bandwidth=1500,
                   price=8,
                   driver=self),
          NodeSize(id=3,
                   name="Big",
                   ram=4096,
                   disk=32,
                   bandwidth=2500,
                   price=32,
                   driver=self),
          NodeSize(id=4,
                   name="XXL Big",
                   ram=4096*2,
                   disk=32*4,
                   bandwidth=2500*3,
                   price=32*2,
                   driver=self),
        ]

    def list_locations(self):
        return [
          NodeLocation(id=1,
                       name="Paul's Room",
                       country='US',
                       driver=self),
          NodeLocation(id=1,
                       name="London Loft",
                       country='GB',
                       driver=self),
          NodeLocation(id=1,
                       name="Island Datacenter",
                       country='FJ',
                       driver=self),
        ]

    def create_node(self, **kwargs):
        l = len(self.nl) + 1
        n = Node(id=l,
                 name='dummy-%d' % l,
                 state=NodeState.RUNNING,
                 public_ip=['127.0.0.%d' % l],
                 private_ip=[],
                 driver=self,
                 extra={'foo': 'bar'})
        self.nl.append(n)
        return n
