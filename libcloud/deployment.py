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

class Deployment(object):
  pass

class SSHDeployment(Deployment):
  def __init__(self, key):
    self.key = key
  
  def run(self, node, client):
    sftp = client.open_sftp()
    sftp.mkdir(".ssh")
    sftp.chdir(".ssh")
    ak = sftp.file("authorized_keys",  mode='w')
    ak.write(self.key)
    ak.close()
    sftp.close()
    return node