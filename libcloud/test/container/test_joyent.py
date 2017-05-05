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

from libcloud.test import unittest

from libcloud.container.drivers.joyent import JoyentContainerDriver
from libcloud.test.secrets import CONTAINER_PARAMS_DOCKER


from libcloud.test.container.test_docker import DockerContainerDriverTestCase, DockerMockHttp


class JoyentContainerDriverTestCase(DockerContainerDriverTestCase, unittest.TestCase):

    def setUp(self):
        # Create a test driver for each version
        versions = ('linux_124', 'mac_124')
        self.drivers = []
        for version in versions:
            JoyentContainerDriver.connectionCls.conn_class = \
                DockerMockHttp
            DockerMockHttp.type = None
            DockerMockHttp.use_param = 'a'
            driver = JoyentContainerDriver(*CONTAINER_PARAMS_DOCKER)
            driver.version = version
            self.drivers.append(driver)
