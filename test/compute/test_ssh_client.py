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

import libcloud.compute.ssh

from mock import Mock


class ParamikoSSHClientTests(unittest.TestCase):

    def test_either_key_or_password_must_be_provided(self):
        libcloud.compute.ssh.paramiko = Mock()
        client = libcloud.compute.ssh.ParamikoSSHClient(hostname='foo.bar.com')

        try:
            client.connect()
        except Exception:
            e = sys.exc_info()[1]
            self.assertTrue(str(e).find('must specify either password or')
                            != -1)
        else:
            self.fail('Exception was not thrown')


if __name__ == '__main__':
    sys.exit(unittest.main())
