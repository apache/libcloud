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

from libcloud.compute.ssh import ParamikoSSHClient
from libcloud.compute.ssh import have_paramiko

from mock import patch, Mock

if not have_paramiko:
    ParamikoSSHClient = None


class ParamikoSSHClientTests(unittest.TestCase):
    @patch('paramiko.SSHClient', Mock)
    def setUp(self):
        """
        Creates the object patching the actual connection.
        """
        conn_params = {'hostname': 'dummy.host.org',
                       'port': 8822,
                       'username': 'ubuntu',
                       'key': '~/.ssh/ubuntu_ssh',
                       'timeout': '600'}
        self.ssh_cli = ParamikoSSHClient(**conn_params)

    @patch('paramiko.SSHClient', Mock)
    def test_create_with_password(self):
        """
        Initialize object with password.

        Just to have better coverage, initialize the object
        with the 'password' value instead of the 'key'.
        """
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'password': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'password': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    def test_create_without_credentials(self):
        """
        Initialize object with no credentials.

        Just to have better coverage, initialize the object
        without 'password' neither 'key'.
        """
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'hostname': 'dummy.host.org',
                         'allow_agent': True,
                         'look_for_keys': True,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    def test_basic_usage_absolute_path(self):
        """
        Basic execution.
        """
        mock = self.ssh_cli
        # script to execute
        sd = "/root/random_script.sh"

        # Connect behavior
        mock.connect()
        mock_cli = mock.client  # The actual mocked object: SSHClient
        expected_conn = {'username': 'ubuntu',
                         'key_filename': '~/.ssh/ubuntu_ssh',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'timeout': '600',
                         'port': 8822}
        mock_cli.connect.assert_called_once_with(**expected_conn)

        mock.put(sd)
        # Make assertions over 'put' method
        mock_cli.open_sftp().chdir.assert_called_with('root')
        mock_cli.open_sftp().file.assert_called_once_with('random_script.sh',
                                                          mode='w')

        mock.run(sd)
        # Make assertions over 'run' method
        mock_cli.get_transport().open_session().exec_command \
                .assert_called_once_with(sd)

        mock.close()

    def test_run_script_with_relative_path(self):
        """
        Execute script with relative path.
        """
        mock = self.ssh_cli

        # Define behaviour then ask for 'current directory'
        mock.client.open_sftp().getcwd.return_value = '/home/ubuntu/'

        # Script without full path
        sd = 'random_script.sh'

        # Without assertions because they are the same than the previous
        # 'test_basic_usage' method
        mock.connect()

        mock_cli = mock.client  # The actual mocked object: SSHClient

        mock.put(sd, chmod=600)
        # Make assertions over 'put' method
        mock_cli.open_sftp().file.assert_called_once_with('random_script.sh',
                                                          mode='w')
        mock_cli.open_sftp().file().chmod.assert_called_once_with(600)

        mock.run(sd)
        # Make assertions over the 'run' method
        mock_cli.open_sftp().chdir.assert_called_with(".")
        mock_cli.open_sftp().getcwd.assert_called_once()
        full_sd = '/home/ubuntu/random_script.sh'
        mock_cli.get_transport().open_session().exec_command \
                .assert_called_once_with(full_sd)

        mock.close()

    def test_delete_script(self):
        """
        Provide a basic test with 'delete' action.
        """
        mock = self.ssh_cli
        # script to execute
        sd = '/root/random_script.sh'

        mock.connect()

        mock.delete(sd)
        # Make assertions over the 'delete' method
        mock.client.open_sftp().unlink.assert_called_with(sd)

        mock.close()

if not ParamikoSSHClient:
    class ParamikoSSHClientTests(unittest.TestCase):
        pass


if __name__ == '__main__':
    sys.exit(unittest.main())
