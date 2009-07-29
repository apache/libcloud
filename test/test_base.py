# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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

from libcloud.providers import DRIVERS, get_driver, connect
from libcloud.types import ProviderCreds, InvalidCredsException, Provider
from libcloud.interface import INodeDriver
from zope.interface.verify import verifyObject
from zope.interface.exceptions import BrokenImplementation

class BaseTests(unittest.TestCase):
    
    def test_drivers_interface(self):
        failures = []
        for driver in DRIVERS:
            creds = ProviderCreds(driver, 'foo', 'bar')
            try:
                verifyObject(INodeDriver, get_driver(driver)(creds))
            except BrokenImplementation:
                failures.append(DRIVERS[driver][1])

        if failures:
            self.fail('the following drivers do not support the \
                       INodeDriver interface: %s' % (', '.join(failures)))

    def test_invalid_creds(self):
        failures = []
        for driver in DRIVERS:
            if driver == Provider.DUMMY:
                continue
            conn = connect(driver, 'bad', 'keys')
            try:
                conn.list_nodes()
            except InvalidCredsException:
                pass
            else:
                failures.append(DRIVERS[driver][1])

        if failures:
            self.fail('the following drivers did not throw an \
                       InvalidCredsException: %s' % (', '.join(failures)))
