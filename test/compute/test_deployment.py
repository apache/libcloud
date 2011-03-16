# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more§
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

from libcloud.compute.deployment import MultiStepDeployment, Deployment
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState
from libcloud.compute.drivers.ec2 import EC2NodeDriver

class MockDeployment(Deployment):
    def run(self, node, client):
        return node

class DeploymentTests(unittest.TestCase):

    def test_multi_step_deployment(self):
        msd = MultiStepDeployment()
        self.assertEqual(len(msd.steps), 0)

        msd.add(MockDeployment())
        self.assertEqual(len(msd.steps), 1)

        node = Node(id=1, name='test', state=NodeState.RUNNING,
                   public_ip=['1.2.3.4'], private_ip='1.2.3.5',
                   driver=EC2NodeDriver)
        self.assertEqual(node, msd.run(node=node, client=None))

if __name__ == '__main__':
    sys.exit(unittest.main())
