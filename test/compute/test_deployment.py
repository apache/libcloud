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
from libcloud.compute.deployment import SSHKeyDeployment, ScriptDeployment
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState
from libcloud.compute.ssh import BaseSSHClient
from libcloud.compute.drivers.ec2 import EC2NodeDriver

class MockDeployment(Deployment):
    def run(self, node, client):
        return node

class MockClient(BaseSSHClient):
    def __init__(self, *args, **kwargs):
        self.stdout = ''
        self.stderr = ''
        self.exit_status = 0

    def put(self,  path, contents, chmod=755):
        return contents

    def run(self, name):
        return self.stdout, self.stderr, self.exit_status

    def delete(self, name):
        return True

class DeploymentTests(unittest.TestCase):

    def setUp(self):
        self.node = Node(id=1, name='test', state=NodeState.RUNNING,
                   public_ip=['1.2.3.4'], private_ip='1.2.3.5',
                   driver=EC2NodeDriver)

    def test_multi_step_deployment(self):
        msd = MultiStepDeployment()
        self.assertEqual(len(msd.steps), 0)

        msd.add(MockDeployment())
        self.assertEqual(len(msd.steps), 1)

        self.assertEqual(self.node, msd.run(node=self.node, client=None))

    def test_ssh_key_deployment(self):
        sshd = SSHKeyDeployment(key='1234')

        self.assertEqual(self.node, sshd.run(node=self.node,
                        client=MockClient(hostname='localhost')))

    def test_script_deployment(self):
        sd1 = ScriptDeployment(script='foobar', delete=True)
        sd2 = ScriptDeployment(script='foobar', delete=False)
        sd3 = ScriptDeployment(script='foobar', delete=False, name='foobarname')

        self.assertTrue(sd1.name.find('deployment') != '1')
        self.assertEqual(sd3.name, 'foobarname')

        self.assertEqual(self.node, sd1.run(node=self.node,
                        client=MockClient(hostname='localhost')))
        self.assertEqual(self.node, sd2.run(node=self.node,
                        client=MockClient(hostname='localhost')))

if __name__ == '__main__':
    sys.exit(unittest.main())
