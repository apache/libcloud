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

from libcloud.loadbalancer.drivers.dummy import DummyLBDriver
from libcloud.loadbalancer.drivers.brightbox import BrightboxLBDriver
from libcloud.test.loadbalancer.mocks.brightbox import BrightboxLBMockHttp
from libcloud.test.secrets import LB_BRIGHTBOX_PARAMS

from .test_loadbalancer import BaseLBTests

class BrightboxLBTests(BaseLBTests):

    def setUp(self):
        BrightboxLBMockHttp.test = self
        BrightboxLBMockHttp.type = None

        BrightboxLBDriver.connectionCls.conn_classes = (None,
                                                        BrightboxLBMockHttp)
        
        self.driver = BrightboxLBDriver(*LB_BRIGHTBOX_PARAMS)
        self.mock = DummyLBDriver('', '')
        self.setUpMock()


if __name__ == "__main__":
    sys.exit(unittest.main())
