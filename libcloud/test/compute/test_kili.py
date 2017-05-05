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

from libcloud.compute.drivers.kili import KiliCloudNodeDriver, ENDPOINT_ARGS
from libcloud.test.compute.test_openstack import OpenStack_1_1_Tests


def _ex_connection_class_kwargs(self):
    kwargs = self.openstack_connection_kwargs()
    kwargs['get_endpoint_args'] = ENDPOINT_ARGS
    # Remove keystone from the URL path so that the openstack base tests work
    kwargs['ex_force_auth_url'] = 'https://api.kili.io/v2.0/tokens'
    kwargs['ex_tenant_name'] = self.tenant_name

    return kwargs

KiliCloudNodeDriver._ex_connection_class_kwargs = _ex_connection_class_kwargs


class KiliCloudNodeDriverTests(OpenStack_1_1_Tests, unittest.TestCase):
    driver_klass = KiliCloudNodeDriver
    driver_type = KiliCloudNodeDriver
