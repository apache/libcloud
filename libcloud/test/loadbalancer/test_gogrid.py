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

from libcloud.common.types import LibcloudError
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.gogrid import GoGridLBDriver
from libcloud.loadbalancer.drivers.dummy import DummyLBDriver
from libcloud.test.loadbalancer.mocks.gogrid import GoGridLBMockHttp

from .test_loadbalancer import BaseLBTests


class GoGridTests(BaseLBTests):

    def setUp(self):
        GoGridLBMockHttp.test = self
        GoGridLBDriver.connectionCls.conn_classes = (None,
                                                      GoGridLBMockHttp)

        self.driver = GoGridLBDriver('user', 'key')
        self.mock = DummyLBDriver('', '')

        self.setUpMock()

    """
    def test_create_balancer_UNEXPECTED_ERROR(self):
        # Try to create new balancer and attach members with an IP address which
        # does not belong to this account
        GoGridLBMockHttp.type = 'UNEXPECTED_ERROR'

        try:
            self.driver.create_balancer(name='test2',
                    port=80,
                    protocol='http',
                    algorithm=Algorithm.ROUND_ROBIN,
                    members=(Member(None, '10.1.0.10', 80),
                             Member(None, '10.1.0.11', 80))
                    )
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(str(e).find('tried to add a member with an IP address not assigned to your account') != -1)
        else:
            self.fail('Exception was not thrown')
    """


if __name__ == "__main__":
    sys.exit(unittest.main())
