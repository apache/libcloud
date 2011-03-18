# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more§
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
import warnings
import os.path

# In Python > 2.7 DeprecationWarnings are disabled by default
warnings.simplefilter('default')

import libcloud.utils
from libcloud.compute.types import Provider
from libcloud.compute.providers import DRIVERS

WARNINGS_BUFFER = []

def show_warning(msg, cat, fname, lno, line=None):
    WARNINGS_BUFFER.append((msg, cat, fname, lno))

original_func = warnings.showwarning

class TestUtils(unittest.TestCase):
    def setUp(self):
        global WARNINGS_BUFFER
        WARNINGS_BUFFER = []

    def tearDown(self):
        global WARNINGS_BUFFER
        WARNINGS_BUFFER = []
        warnings.showwarning = original_func

    def test_guess_file_mime_type(self):
        file_path = os.path.abspath(__file__)
        mimetype, encoding = libcloud.utils.guess_file_mime_type(file_path=file_path)

        self.assertTrue(mimetype.find('python') != -1)

    def test_get_driver(self):
        driver = libcloud.utils.get_driver(drivers=DRIVERS,
                                           provider=Provider.DUMMY)
        self.assertTrue(driver is not None)

        try:
            driver = libcloud.utils.get_driver(drivers=DRIVERS,
                                               provider='fooba')
        except AttributeError:
            pass
        else:
            self.fail('Invalid provider, but an exception was not thrown')

    def test_deprecated_warning(self):
        warnings.showwarning = show_warning

        libcloud.utils.SHOW_DEPRECATION_WARNING = False
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.deprecated_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 0)

        libcloud.utils.SHOW_DEPRECATION_WARNING = True
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.deprecated_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 1)

    def test_in_development_warning(self):
        warnings.showwarning = show_warning

        libcloud.utils.SHOW_IN_DEVELOPMENT_WARNING = False
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.in_development_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 0)

        libcloud.utils.SHOW_IN_DEVELOPMENT_WARNING = True
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.in_development_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 1)

if __name__ == '__main__':
    sys.exit(unittest.main())
