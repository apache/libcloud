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

"""
Provides generic deployment steps for machines post boot.
"""
import os

class Deployment(object):
    pass

class SSHKeyDeployment(Deployment):
    def __init__(self, key):
        self.key = key
  
    def run(self, node, client):
        client.put(".ssh/authorized_keys", contents=self.key)
        return node

class ScriptDeployment(Deployment):
    def __init__(self, script, name=None, delete=False):
        self.script = script
        self.stdout = None
        self.stderr = None
        self.delete = delete
        self.name = name
        if self.name is None:
            self.name = "/root/deployment_%s.sh" % (os.urandom(4).encode('hex'))

    def run(self, node, client):
        client.put(path=self.name, chmod=755, contents=self.script)
        self.stdout, self.stderr = client.run(self.name)
        if self.delete:
            client.delete(self.name)
        return node

class MultiStepDeployment(Deployment):
  def __init__(self, add = None):
    self.steps = []
    self.add(add)

  def add(self, add):
    if add is not None:
      add = add if isinstance(add, (list, tuple)) else [add]
      self.steps.extend(add)

  def run(self, node, client):
    for s in self.steps:
      node = s.run(node, client)
    return node
