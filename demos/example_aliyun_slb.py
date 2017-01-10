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

from libcloud.compute.types import Provider as NodeProvider
from libcloud.compute.providers import get_driver as get_node_driver
from libcloud.loadbalancer.providers import get_driver
from libcloud.loadbalancer.base import Algorithm, Member
from libcloud.loadbalancer.types import Provider

SLBDriver = get_driver(Provider.ALIYUN_SLB)
ECSDriver = get_node_driver(NodeProvider.ALIYUN_ECS)

region = 'cn-hangzhou'

your_access_key_id = ''
your_access_key_secret = ''
slb = SLBDriver(your_access_key_id, your_access_key_secret, region=region)
ecs = ECSDriver(your_access_key_id, your_access_key_secret, region=region)

protos = slb.list_protocols()
print('Found %d protocols: %s' % (len(protos), protos))

balancers = slb.list_balancers()
print('Found %d load balancers' % len(balancers))
print(balancers)

if len(balancers) > 0:
    b1 = balancers[0]
    print('Delete %s' % b1)
    slb.destroy_balancer(b1)
else:
    extra = {'AddressType': 'internet',
             'Bandwidth': 1,
             'StickySession': 'off',
             'HealthCheck': 'off'}
    nodes = ecs.list_nodes()
    print('Found %d nodes' % len(nodes))
    members = [Member(node.id, node.public_ips[0], 80,
                      extra={'Weight': 50 * (i + 1)})
               for i, node in enumerate(nodes)]
    new_b = slb.create_balancer('test-balancer', 80, 'http',
                                Algorithm.WEIGHTED_ROUND_ROBIN, members,
                                **extra)
    print('Created balancer %s' % new_b)
