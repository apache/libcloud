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
import tempfile
import logging

try:
    import paramiko  # NOQA
    have_paramiko = True
except ImportError:
    have_paramiko = False

from mock import patch

import libcloud
from libcloud import _init_once
from libcloud.utils.loggingconnection import LoggingConnection
from libcloud.base import DriverTypeNotFoundError
from libcloud.test import unittest


class TestUtils(unittest.TestCase):
    def tearDown(self):
        if 'LIBCLOUD_DEBUG' in os.environ:
            del os.environ['LIBCLOUD_DEBUG']

    def test_init_once_and_debug_mode(self):
        if have_paramiko:
            paramiko_logger = logging.getLogger('paramiko')
            paramiko_logger.setLevel(logging.INFO)

        # Debug mode is disabled
        _init_once()

        self.assertIsNone(LoggingConnection.log)

        if have_paramiko:
            paramiko_log_level = paramiko_logger.getEffectiveLevel()
            self.assertEqual(paramiko_log_level, logging.INFO)

        # Enable debug mode
        _, tmp_path = tempfile.mkstemp()
        os.environ['LIBCLOUD_DEBUG'] = tmp_path
        _init_once()

        self.assertTrue(LoggingConnection.log is not None)

        if have_paramiko:
            paramiko_log_level = paramiko_logger.getEffectiveLevel()
            self.assertEqual(paramiko_log_level, logging.DEBUG)

    def test_factory(self):
        driver = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.EC2)
        self.assertEqual(driver.__name__, 'EC2NodeDriver')

    def test_raises_error(self):
        with self.assertRaises(DriverTypeNotFoundError):
            libcloud.get_driver('potato', 'potato')

    @patch.object(libcloud.requests, '__version__', '2.6.0')
    @patch.object(libcloud.requests.packages.chardet, '__version__', '2.2.1')
    def test_init_once_detects_bad_yum_install_requests(self, *args):
        expected_msg = 'Known bad version of requests detected'
        with self.assertRaisesRegex(AssertionError, expected_msg):
            _init_once()

    @patch.object(libcloud.requests, '__version__', '2.6.0')
    @patch.object(libcloud.requests.packages.chardet, '__version__', '2.3.0')
    def test_init_once_correct_chardet_version(self, *args):
        _init_once()


if __name__ == '__main__':
    sys.exit(unittest.main())
