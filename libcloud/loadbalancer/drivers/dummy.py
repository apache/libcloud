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

__all__ = [
    'DummyLBDriver'
]


from libcloud.utils.xml import findtext, findall
from libcloud.loadbalancer.types import State, LibcloudLBError
from libcloud.loadbalancer.base import Driver, LoadBalancer, Member


class DummyLBDriver(Driver):
    name = 'dummy'

    def __init__(self, access_id, secret):
        self.next_id = 0
        self.balancers = {}

    def list_protocols(self):
        return ['tcp', 'ssl', 'http', 'https']

    def list_balancers(self):
        return self.balancers.values()

    def create_balancer(self, name, port, protocol, algorithm, members):
        pending_balancer = LoadBalancer(
            id=str(self.next_id),
            name=name,
            state=State.PENDING,
            ip="192.168.1.2",
            port=port,
            driver=self
        )
        balancer = LoadBalancer(
            id=str(self.next_id),
            name=name,
            state=State.RUNNING,
            ip="192.168.1.2",
            port=port,
            driver=self
        )
        pending_balancer._members = []
        balancer._members = []
        self.balancers[str(self.next_id)] = balancer
        self.next_id += 1
        return pending_balancer

    def destroy_balancer(self, balancer):
        if not balancer.id in self.balancers.keys():
            raise LibcloudLBError("Balancer does not exist")
        del self.balancers[balancer.id]
        return True

    def get_balancer(self, balancer_id):
        if not balancer_id in self.balancers:
            raise LibcloudLBError("Balancer does not exist")
        return self.balancers[balancer_id]

    def balancer_attach_member(self, balancer, member):
        b = self.get_balancer(balancer.id)
        m = Member(member.id, member.ip, member.port, balancer=b)
        b._members.append(m)
        return m

    def balancer_detach_member(self, balancer, member):
        b = self.get_balancer(balancer.id)
        b._members = [m for m in balancer._members if m.id != member.id]
        return True

    def balancer_list_members(self, balancer):
        return list(balancer._members)
