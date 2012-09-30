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

from libcloud.compute.drivers.rackspace import RackspaceFirstGenNodeDriver
from libcloud.test.compute.test_openstack import OpenStack_1_0_Tests

from libcloud.test.secrets import RACKSPACE_PARAMS


class RackspaceusFirstGenUsTests(OpenStack_1_0_Tests):
    should_list_locations = True
    should_have_pricing = True

    driver_klass = RackspaceFirstGenNodeDriver
    driver_type = RackspaceFirstGenNodeDriver
    driver_args = RACKSPACE_PARAMS
    driver_kwargs = {'region': 'us'}

    def test_list_sizes_pricing(self):
        sizes = self.driver.list_sizes()

        for size in sizes:
            self.assertTrue(size.price > 0)


class RackspaceusFirstGenUkTests(OpenStack_1_0_Tests):
    should_list_locations = True
    should_have_pricing = True

    driver_klass = RackspaceFirstGenNodeDriver
    driver_type = RackspaceFirstGenNodeDriver
    driver_args = RACKSPACE_PARAMS
    driver_kwargs = {'region': 'uk'}

    def test_list_sizes_pricing(self):
        sizes = self.driver.list_sizes()

        for size in sizes:
            self.assertTrue(size.price > 0)


if __name__ == '__main__':
    sys.exit(unittest.main())
