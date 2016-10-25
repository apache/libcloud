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

from mock import Mock

from libcloud.common.base import BaseDriver

from libcloud.test import unittest


class BaseDriverTestCase(unittest.TestCase):
    def test_timeout_argument_propagation_and_preservation(self):
        class DummyDriver1(BaseDriver):
            pass

        # 1. No timeout provided
        DummyDriver1.connectionCls = Mock()
        DummyDriver1(key='foo')
        call_kwargs = DummyDriver1.connectionCls.call_args[1]
        self.assertEqual(call_kwargs['timeout'], None)
        self.assertEqual(call_kwargs['retry_delay'], None)

        # 2. Timeout provided as constructor argument
        class DummyDriver1(BaseDriver):
            pass

        DummyDriver1.connectionCls = Mock()
        DummyDriver1(key='foo', timeout=12)
        call_kwargs = DummyDriver1.connectionCls.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 12)
        self.assertEqual(call_kwargs['retry_delay'], None)

        # 3. timeout provided via "_ex_connection_class_kwargs" method
        class DummyDriver2(BaseDriver):
            def _ex_connection_class_kwargs(self):
                result = {}
                result['timeout'] = 13
                return result

        DummyDriver2.connectionCls = Mock()
        DummyDriver2(key='foo')
        call_kwargs = DummyDriver2.connectionCls.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 13)
        self.assertEqual(call_kwargs['retry_delay'], None)

        # 4. Value provided via "_ex_connection_class_kwargs" and constructor,
        # constructor should win
        DummyDriver2.connectionCls = Mock()
        DummyDriver2(key='foo', timeout=14, retry_delay=10)
        call_kwargs = DummyDriver2.connectionCls.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 14)
        self.assertEqual(call_kwargs['retry_delay'], 10)


if __name__ == '__main__':
    sys.exit(unittest.main())
