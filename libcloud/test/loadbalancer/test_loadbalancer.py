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

import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.loadbalancer.base import Member, Algorithm, LoadBalancer
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.drivers.dummy import DummyLBDriver
from libcloud.loadbalancer.types import State


class BaseLBTests(unittest.TestCase):

    def setUp(self):
            self.mock = self.driver = DummyLBDriver('', '')
            self.setUpMock()

    def setUpMock(self):
        self.mock_lb = self.mock.create_balancer(
            name="tests",
            protocol="http",
            port=80,
            algorithm=DEFAULT_ALGORITHM,
            members=[],
        )
        self.mock_lb.attach_member(Member(id='i-64bd081c', ip='1.1.1.1', port='80'))

    def test_list_supported_algorithms(self):
        algorithms = self.driver.list_supported_algorithms()

    def test_list_protocols(self):
        protocols = self.driver.list_protocols()
        self.assertTrue(len(protocols) > 0)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEquals(len(balancers), 1)

        self.assertTrue(isinstance(balancers[0], LoadBalancer))
        self.assertEquals(balancers[0].name, 'tests')
        self.assertEquals(balancers[0].state, State.RUNNING)

    def test_get_balancer(self):
        balancers = self.driver.list_balancers()
        balancer = self.driver.get_balancer(balancer_id=balancers[0].id)

        self.assertEquals(balancer.id, balancers[0].id)
        self.assertEquals(balancer.name, 'tests')
        self.assertEquals(balancer.state, State.RUNNING)

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]
        self.assertTrue(self.driver.destroy_balancer(balancer))

        for b in self.driver.list_balancers():
            if b.id == balancer.id:
                self.fail('Balancer was not destroyed')

    def test_create_balancer(self):
        members = [Member('srv-lv426', ip='1.1.1.1', port=80)]

        balancer = self.driver.create_balancer(name='lb2', port=80,
            protocol='http', algorithm=Algorithm.ROUND_ROBIN,
            members=members)

        self.assertTrue(isinstance(balancer, LoadBalancer))
        self.assertEquals(balancer.name, 'lb2')
        self.assertEquals(balancer.port, 80)
        self.assertTrue(balancer.state in (State.PENDING, State.RUNNING))

        for b in self.driver.list_balancers():
            if b.id == balancer.id:
                self.assertTrue(isinstance(b, LoadBalancer))
                self.assertEquals(b.name, 'lb2')
                self.assertEquals(b.port, 80)
                self.assertEquals(b.state, State.RUNNING)
                break
        else:
            self.fail("Balancer was not created")

    def test_balancer_list_members(self):
        balancer = self.driver.list_balancers()[0]
        members = balancer.list_members()

        self.assertEquals(len(members), 1)
        self.assertTrue(isinstance(members[0], Member))
        self.assertEquals(members[0].balancer, balancer)
        self.assertEquals('i-64bd081c', members[0].id)

    def test_balancer_attach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = balancer.attach_member(Member(id='i-64bd081d', ip='254.254.254.254',
                                               port=80))

        if member.id:
            self.assertEquals(member.id, 'i-64bd081d')
        else:
            self.assertEquals(member.ip, '254.254.254.254')
            self.assertEquals(member.port, 80)

        for m in balancer.list_members():
            if m.ip == '254.254.254.254' and m.port == 80:
                break
            if m.id == member.id:
                break
        else:
            self.fail('Member was not added')

    def test_balancer_detach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = Member('i-64bd081c', None, None)
        self.assertTrue(balancer.detach_member(member))

        for m in balancer.list_members():
            if m.id == 'i-64bd081c':
                self.fail('Member was not detached')


if __name__ == "__main__":
    sys.exit(unittest.main())
