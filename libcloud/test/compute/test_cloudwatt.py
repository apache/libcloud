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

import unittest

from libcloud.compute.drivers.cloudwatt import CloudwattNodeDriver
from libcloud.test.compute.test_openstack import OpenStack_1_1_Tests


class CloudwattNodeDriverTests(OpenStack_1_1_Tests, unittest.TestCase):
    driver_klass = CloudwattNodeDriver
    driver_type = CloudwattNodeDriver

    # These tests dont work because cloudwatt doesn't pass,
    # auth tokens- hide them from the base class
    def test_ex_force_auth_token_passed_to_connection(self):
        pass

    def test_auth_token_without_base_url_raises_exception(self):
        pass
