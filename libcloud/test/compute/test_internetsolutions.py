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

from libcloud.compute.drivers.internetsolutions import InternetSolutionsNodeDriver
from libcloud.test.compute.test_dimensiondata_v2_3 import DimensionDataMockHttp, DimensionData_v2_3_Tests


class InternetSolutionsNodeDriverTests(DimensionData_v2_3_Tests, unittest.TestCase):

    def setUp(self):
        InternetSolutionsNodeDriver.connectionCls.conn_class = DimensionDataMockHttp
        InternetSolutionsNodeDriver.connectionCls.active_api_version = '2.3'
        DimensionDataMockHttp.type = None
        self.driver = InternetSolutionsNodeDriver('user', 'password')
