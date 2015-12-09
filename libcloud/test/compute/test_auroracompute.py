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

from libcloud.compute.drivers.auroracompute import AuroraComputeNodeDriver
from libcloud.compute.drivers.auroracompute import AuroraComputeRegion
from libcloud.test.compute.test_cloudstack import CloudStackCommonTestCase
from libcloud.test import unittest


class AuroraComputeNodeDriverTestCase(CloudStackCommonTestCase,
                                      unittest.TestCase):
    driver_klass = AuroraComputeNodeDriver

    def test_api_host(self):
        driver = self.driver_klass('invalid', 'invalid')
        self.assertEqual(driver.host, 'api.auroracompute.eu')

    def test_without_region(self):
        driver = self.driver_klass('invalid', 'invalid')
        self.assertEqual(driver.path, '/ams')

    def test_with_ams_region(self):
        driver = self.driver_klass('invalid', 'invalid',
                                   region=AuroraComputeRegion.AMS)
        self.assertEqual(driver.path, '/ams')

    def test_with_miami_region(self):
        driver = self.driver_klass('invalid', 'invalid',
                                   region=AuroraComputeRegion.MIA)
        self.assertEqual(driver.path, '/mia')

    def test_with_tokyo_region(self):
        driver = self.driver_klass('invalid', 'invalid',
                                   region=AuroraComputeRegion.TYO)
        self.assertEqual(driver.path, '/tyo')


if __name__ == '__main__':
    sys.exit(unittest.main())
