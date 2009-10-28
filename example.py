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
from libcloud.types import Provider
from libcloud.providers import get_driver

EC2 = get_driver(Provider.EC2)
Slicehost = get_driver(Provider.SLICEHOST)

ec2 = EC2('access key id', 'secret key')
slicehost = Slicehost('api key')
rackspace = Rackspace('username', 'api key')

all_nodes = []
for provider in [ ec2, slicehost, rackspace ]:
  all_nodes.extend(provider.list_nodes())

print all_nodes
"""
[ <Node: provider=Amazon, status=RUNNING, name=bob, ip=1.2.3.4.5>,
<Node: provider=Slicehost, status=REBOOT, name=korine, ip=6.7.8.9.10>, ... ]
"""

node = all_nodes[0]
print node.destroy()
# <Node: provider=Amazon, status=TERMINATED, name=bob, ip=1.2.3.4.5>,

print slicehost.create_node(based_on=node)
# <Node: provider=Slicehost, status=PENDING, name=bob, ip=None>,
