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
"""
Tests for Amazon Elastic Kubernetes Driver
"""

import sys
import unittest

from unittest.mock import MagicMock

from libcloud.container.drivers.eks import ElasticKubernetesDriver

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ContainerFileFixtures

from libcloud.test.secrets import CONTAINER_PARAMS_EKS


class ElasticKubernetesDriverTestCase(unittest.TestCase):
    """
    Amazon Elastic Kubernetes Driver Test Class.
    """

    def setUp(self):
        ElasticKubernetesDriver.connectionCls.conn_class = EKSMockHttp
        EKSMockHttp.type = None
        EKSMockHttp.use_param = 'a'
        ElasticKubernetesDriver.containerDriverCls = MagicMock()
        self.driver = ElasticKubernetesDriver(*CONTAINER_PARAMS_EKS)


class EKSMockHttp(MockHttp):
    fixtures = ContainerFileFixtures('eks')


if __name__ == '__main__':
    sys.exit(unittest.main())
