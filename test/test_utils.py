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

import libcloud.utils.files

from libcloud.utils.misc import get_driver

from libcloud.utils.py3 import PY3
from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import b
from libcloud.compute.types import Provider
from libcloud.compute.providers import DRIVERS

WARNINGS_BUFFER = []

if PY3:
    from io import FileIO as file


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
        mimetype, encoding = libcloud.utils.files.guess_file_mime_type(
                file_path=file_path)

        self.assertTrue(mimetype.find('python') != -1)

    def test_get_driver(self):
        driver = get_driver(drivers=DRIVERS, provider=Provider.DUMMY)
        self.assertTrue(driver is not None)

        try:
            driver = get_driver(drivers=DRIVERS, provider='fooba')
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

    def test_read_in_chunks_iterator(self):
        def iterator():
            for x in range(0, 1000):
                yield 'aa'

        for result in libcloud.utils.files.read_in_chunks(iterator(),
                                                          chunk_size=10,
                                                          fill_size=False):
            self.assertEqual(result, b('aa'))

        for result in libcloud.utils.files.read_in_chunks(iterator(), chunk_size=10,
                                                          fill_size=True):
            self.assertEqual(result, b('aaaaaaaaaa'))

    def test_read_in_chunks_filelike(self):
            class FakeFile(file):
                def __init__(self):
                    self.remaining = 500

                def read(self, size):
                    self.remaining -= 1
                    if self.remaining == 0:
                        return ''
                    return 'b' * (size + 1)

            for index, result in enumerate(libcloud.utils.files.read_in_chunks(
                                           FakeFile(), chunk_size=10,
                                           fill_size=False)):
                self.assertEqual(result, b('b' * 11))

            self.assertEqual(index, 498)

            for index, result in enumerate(libcloud.utils.files.read_in_chunks(
                                           FakeFile(), chunk_size=10,
                                           fill_size=True)):
                if index != 548:
                    self.assertEqual(result, b('b' * 10))
                else:
                    self.assertEqual(result, b('b' * 9))

            self.assertEqual(index, 548)

    def test_exhaust_iterator(self):
        def iterator_func():
            for x in range(0, 1000):
                yield 'aa'

        data = b('aa' * 1000)
        iterator = libcloud.utils.files.read_in_chunks(iterator=iterator_func())
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, data)

        result = libcloud.utils.files.exhaust_iterator(iterator=iterator_func())
        self.assertEqual(result, data)

        data = '12345678990'
        iterator = StringIO(data)
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, b(data))

    def test_exhaust_iterator_empty_iterator(self):
        data = ''
        iterator = StringIO(data)
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, b(data))


if __name__ == '__main__':
    sys.exit(unittest.main())
