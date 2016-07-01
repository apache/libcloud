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

import os
import sys
import logging

try:
    import paramiko
    have_paramiko = True
except ImportError:
    have_paramiko = False

import libcloud
from libcloud import _init_once
from libcloud.base import DriverTypeNotFoundError
from libcloud.common.base import LoggingHTTPConnection
from libcloud.common.base import LoggingHTTPSConnection

from libcloud.test import unittest


class TestUtils(unittest.TestCase):
    def test_init_once_and_debug_mode(self):
        # Debug mode is disabled
        _init_once()

        self.assertEqual(LoggingHTTPConnection.log, None)
        self.assertEqual(LoggingHTTPSConnection.log, None)

        if have_paramiko:
            logger = paramiko.util.logging.getLogger()
            paramiko_log_level = logger.getEffectiveLevel()
            self.assertEqual(paramiko_log_level, logging.WARNING)

        # Enable debug mode
        os.environ['LIBCLOUD_DEBUG'] = '/dev/null'
        _init_once()

        self.assertTrue(LoggingHTTPConnection.log is not None)
        self.assertTrue(LoggingHTTPSConnection.log is not None)

        if have_paramiko:
            logger = paramiko.util.logging.getLogger()
            paramiko_log_level = logger.getEffectiveLevel()
            self.assertEqual(paramiko_log_level, logging.DEBUG)

    def test_factory(self):
        driver = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.EC2)
        self.assertEqual(driver.__name__, 'EC2NodeDriver')

    def test_raises_error(self):
        with self.assertRaises(DriverTypeNotFoundError):
            libcloud.get_driver('potato', 'potato')

if __name__ == '__main__':
    sys.exit(unittest.main())
