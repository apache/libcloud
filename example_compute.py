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

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2 = get_driver(Provider.EC2_US_EAST)
Slicehost = get_driver(Provider.SLICEHOST)
Rackspace = get_driver(Provider.RACKSPACE)

drivers = [EC2('access key id', 'secret key'),
            Slicehost('api key'),
            Rackspace('username', 'api key')]

nodes = [driver.list_nodes() for driver in drivers]

print(nodes)
# [ <Node: provider=Amazon, status=RUNNING, name=bob, ip=1.2.3.4.5>,
# <Node: provider=Slicehost, status=REBOOT, name=korine, ip=6.7.8.9.10>, ... ]

# grab the node named "test"
node = [n for n in nodes if n.name == 'test'][0]

# reboot "test"
node.reboot()
