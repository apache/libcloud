#!/usr/bin/env python
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


import os
import time

from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import Provider, State
from libcloud.loadbalancer.providers import get_driver


def main():
    Rackspace = get_driver(Provider.RACKSPACE_US)

    driver = Rackspace('username', 'api key')

    balancers = driver.list_balancers()

    print(balancers)

    # creating a balancer which balances traffic across two
    # nodes: 192.168.86.1:80 and 192.168.86.2:8080. Balancer
    # itself listens on port 80/tcp
    new_balancer_name = 'testlb' + os.urandom(4).encode('hex')
    new_balancer = driver.create_balancer(name=new_balancer_name,
            algorithm=Algorithm.ROUND_ROBIN,
            port=80,
            protocol='http',
            members=(Member(None, '192.168.86.1', 80),
                     Member(None, '192.168.86.2', 8080))
            )

    print(new_balancer)

    # wait for balancer to become ready
    # NOTE: in real life code add timeout to not end up in
    # endless loop when things go wrong on provider side
    while True:
        balancer = driver.get_balancer(balancer_id=new_balancer.id)

        if balancer.state == State.RUNNING:
            break

        print('sleeping for 30 seconds for balancers to become ready')
        time.sleep(30)

    # fetch list of members
    members = balancer.list_members()
    print(members)

    # remove first member
    balancer.detach_member(members[0])

    # remove the balancer
    driver.destroy_balancer(new_balancer)

if __name__ == "__main__":
    main()
