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

from __future__ import absolute_import
from __future__ import with_statement

import os
import sys
import tempfile

from libcloud import _init_once
from libcloud.test import LibcloudTestCase
from libcloud.test import unittest
from libcloud.compute.ssh import ParamikoSSHClient
from libcloud.compute.ssh import ShellOutSSHClient
from libcloud.compute.ssh import have_paramiko

from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import u
from libcloud.utils.py3 import assertRaisesRegex

from mock import patch, Mock, MagicMock, call

if not have_paramiko:
    ParamikoSSHClient = None  # NOQA
    paramiko_version = '0.0.0'
else:
    import paramiko
    paramiko_version = paramiko.__version__


@unittest.skipIf(not have_paramiko, 'Skipping because paramiko is not available')
class ParamikoSSHClientTests(LibcloudTestCase):

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
        _, self.tmp_file = tempfile.mkstemp()
        os.environ['LIBCLOUD_DEBUG'] = self.tmp_file
        _init_once()
        self.ssh_cli = ParamikoSSHClient(**conn_params)

    def tearDown(self):
        if 'LIBCLOUD_DEBUG' in os.environ:
            del os.environ['LIBCLOUD_DEBUG']

    @patch('paramiko.SSHClient', Mock)
    def test_create_with_password(self):
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
        self.assertLogMsg('Connecting to server')

    @patch('paramiko.SSHClient', Mock)
    def test_deprecated_key_argument(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)
        self.assertLogMsg('Connecting to server')

    def test_key_files_and_key_material_arguments_are_mutual_exclusive(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa',
                       'key_material': 'key'}

        expected_msg = ('key_files and key_material arguments are mutually '
                        'exclusive')
        assertRaisesRegex(self, ValueError, expected_msg,
                          ParamikoSSHClient, **conn_params)

    @patch('paramiko.SSHClient', Mock)
    def test_key_material_argument(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc', 'test_rsa.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        pkey = paramiko.RSAKey.from_private_key(StringIO(private_key))
        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'pkey': pkey,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)
        self.assertLogMsg('Connecting to server')

    @patch('paramiko.SSHClient', Mock)
    def test_key_material_argument_invalid_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': 'id_rsa'}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'Invalid or unsupported key type'
        assertRaisesRegex(self, paramiko.ssh_exception.SSHException,
                          expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    @unittest.skipIf(paramiko_version >= '2.7.0',
                     'New versions of paramiko support OPENSSH key format')
    def test_key_file_non_pem_format_error(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa_non_pem_format.key')

        # Supplied as key_material
        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'Invalid or unsupported key type'
        assertRaisesRegex(self, paramiko.ssh_exception.SSHException,
                          expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    def test_password_protected_key_no_password_provided_1(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa_2048b_pass_foobar.key')

        # Supplied as key_material
        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'private key file is encrypted'
        assertRaisesRegex(self, paramiko.ssh_exception.PasswordRequiredException,
                          expected_msg, mock.connect)

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': path}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'private key file is encrypted'
        assertRaisesRegex(self, paramiko.ssh_exception.PasswordRequiredException,
                          expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    def test_password_protected_key_no_password_provided_2(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa_2048b_pass_foobar.key')

        # Supplied as key_material
        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key,
                       'password': 'invalid'}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'OpenSSH private key file checkints do not match'
        assertRaisesRegex(self, paramiko.ssh_exception.SSHException,
                          expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    def test_password_protected_key_valid_password_provided(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa_2048b_pass_foobar.key')

        # Supplied as key_material
        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key,
                       'password': 'foobar'}

        mock = ParamikoSSHClient(**conn_params)
        self.assertTrue(mock.connect())

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': path,
                       'password': 'foobar'}

        mock = ParamikoSSHClient(**conn_params)
        self.assertTrue(mock.connect())

    @patch('paramiko.SSHClient', Mock)
    def test_ed25519_key_type(self):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_ed25519.key')

        # Supplied as key_material
        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key}

        mock = ParamikoSSHClient(**conn_params)
        self.assertTrue(mock.connect())

    def test_key_material_valid_pem_keys_invalid_header_auto_conversion(self):
        # Test a scenario where valid PEM keys with invalid headers which is
        # not recognized by paramiko are automatically converted in a format
        # which is recognized by paramiko
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        # 1. RSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa_non_paramiko_recognized_header.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.RSAKey))

        # 2. DSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_dsa_non_paramiko_recognized_header.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.DSSKey))

        # 3. ECDSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_ecdsa_non_paramiko_recognized_header.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.ECDSAKey))

    def test_key_material_valid_pem_keys(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        # 1. RSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_rsa.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.RSAKey))

        # 2. DSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_dsa.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.DSSKey))

        # 3. ECDSA key type with header which is not supported by paramiko
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures', 'misc',
                            'test_ecdsa.key')

        with open(path, 'r') as fp:
            private_key = fp.read()

        pkey = client._get_pkey_object(key=private_key)
        self.assertTrue(pkey)
        self.assertTrue(isinstance(pkey, paramiko.ECDSAKey))

    @patch('paramiko.SSHClient', Mock)
    def test_create_with_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)
        self.assertLogMsg('Connecting to server')

    @patch('paramiko.SSHClient', Mock)
    def test_create_with_password_and_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'password': 'ubuntu',
                       'key': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'password': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)
        self.assertLogMsg('Connecting to server')

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

    @patch.object(ParamikoSSHClient, '_consume_stdout',
                  MagicMock(return_value=StringIO('')))
    @patch.object(ParamikoSSHClient, '_consume_stderr',
                  MagicMock(return_value=StringIO('')))
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
        self.assertLogMsg('Executing command (cmd=/root/random_script.sh)')
        self.assertLogMsg('Command finished')

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
        self.assertLogMsg('Deleting file')

        mock.close()
        self.assertLogMsg('Closing server connection')

    def assertLogMsg(self, expected_msg):
        with open(self.tmp_file, 'r') as fp:
            content = fp.read()

        self.assertTrue(content.find(expected_msg) != -1)

    def test_consume_stdout(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1024

        chan = Mock()
        chan.recv_ready.side_effect = [True, True, False]
        chan.recv.side_effect = ['123', '456']

        stdout = client._consume_stdout(chan).getvalue()
        self.assertEqual(u('123456'), stdout)
        self.assertEqual(len(stdout), 6)

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1024

        chan = Mock()
        chan.recv_ready.side_effect = [True, True, False]
        chan.recv.side_effect = ['987', '6543210']

        stdout = client._consume_stdout(chan).getvalue()
        self.assertEqual(u('9876543210'), stdout)
        self.assertEqual(len(stdout), 10)

    def test_consume_stderr(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1024

        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, False]
        chan.recv_stderr.side_effect = ['123', '456']

        stderr = client._consume_stderr(chan).getvalue()
        self.assertEqual(u('123456'), stderr)
        self.assertEqual(len(stderr), 6)

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1024

        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, False]
        chan.recv_stderr.side_effect = ['987', '6543210']

        stderr = client._consume_stderr(chan).getvalue()
        self.assertEqual(u('9876543210'), stderr)
        self.assertEqual(len(stderr), 10)

    def test_consume_stdout_chunk_contains_part_of_multi_byte_utf8_character(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1

        chan = Mock()
        chan.recv_ready.side_effect = [True, True, True, True, False]
        chan.recv.side_effect = ['\xF0', '\x90', '\x8D', '\x88']

        stdout = client._consume_stdout(chan).getvalue()
        self.assertEqual('ð\x90\x8d\x88', stdout)
        self.assertEqual(len(stdout), 4)

    def test_consume_stderr_chunk_contains_part_of_multi_byte_utf8_character(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1

        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, True, True, False]
        chan.recv_stderr.side_effect = ['\xF0', '\x90', '\x8D', '\x88']

        stderr = client._consume_stderr(chan).getvalue()
        self.assertEqual('ð\x90\x8d\x88', stderr)
        self.assertEqual(len(stderr), 4)

    def test_consume_stdout_chunk_contains_non_utf8_character(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1

        chan = Mock()
        chan.recv_ready.side_effect = [True, True, True, False]
        chan.recv.side_effect = ['🤦'.encode('utf-32'), 'a', 'b']

        stdout = client._consume_stdout(chan).getvalue()
        self.assertEqual('\x00\x00&\x01\x00ab', stdout)
        self.assertEqual(len(stdout), 7)

    def test_consume_stderr_chunk_contains_non_utf8_character(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)
        client.CHUNK_SIZE = 1

        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, True, False]
        chan.recv_stderr.side_effect = ['🤦'.encode('utf-32'), 'a', 'b']

        stderr = client._consume_stderr(chan).getvalue()
        self.assertEqual('\x00\x00&\x01\x00ab', stderr)
        self.assertEqual(len(stderr), 7)

    def test_keep_alive_and_compression(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_transport = Mock()
        client.client.get_transport = Mock(return_value=mock_transport)

        transport = client._get_transport()
        self.assertEqual(transport.set_keepalive.call_count, 0)
        self.assertEqual(transport.use_compression.call_count, 0)

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'keep_alive': 15,
                       'use_compression': True}
        client = ParamikoSSHClient(**conn_params)

        mock_transport = Mock()
        client.client.get_transport = Mock(return_value=mock_transport)

        transport = client._get_transport()
        self.assertEqual(transport.set_keepalive.call_count, 1)
        self.assertEqual(transport.use_compression.call_count, 1)

    def test_put_absolute_path(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_client = Mock()
        mock_sftp_client = Mock()
        mock_transport = Mock()

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = '/mock/cwd'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        result = client.put(path='/test/remote/path.txt', contents='foo bar', chmod=455, mode='w')
        self.assertEqual(result, '/test/remote/path.txt')

        calls = [
            call('/'),
            call('test'),
            call('remote')
        ]
        mock_sftp_client.chdir.assert_has_calls(calls, any_order=False)

        calls = [
            call('path.txt', mode='w'),
            call().write('foo bar'),
            call().chmod(455),
            call().close()
        ]
        mock_sftp_client.file.assert_has_calls(calls, any_order=False)

    def test_put_absolute_path_windows(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_client = Mock()
        mock_sftp_client = Mock()
        mock_transport = Mock()

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = 'C:\\Administrator'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        result = client.put(path='C:\\users\\user1\\1.txt', contents='foo bar', chmod=455, mode='w')
        self.assertEqual(result, 'C:\\users\\user1\\1.txt')

        result = client.put(path='\\users\\user1\\1.txt', contents='foo bar', chmod=455, mode='w')
        self.assertEqual(result, '\\users\\user1\\1.txt')

        result = client.put(path='1.txt', contents='foo bar', chmod=455, mode='w')
        self.assertEqual(result, 'C:\\Administrator\\1.txt')

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = '/C:\\User1'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        result = client.put(path='1.txt', contents='foo bar', chmod=455, mode='w')
        self.assertEqual(result, 'C:\\User1\\1.txt')

    def test_put_relative_path(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_client = Mock()
        mock_sftp_client = Mock()
        mock_transport = Mock()

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = '/mock/cwd'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        result = client.put(path='path2.txt', contents='foo bar 2', chmod=466, mode='a')
        self.assertEqual(result, '/mock/cwd/path2.txt')

        calls = [
            call('.')
        ]
        mock_sftp_client.chdir.assert_has_calls(calls, any_order=False)

        calls = [
            call('path2.txt', mode='a'),
            call().write('foo bar 2'),
            call().chmod(466),
            call().close()
        ]
        mock_sftp_client.file.assert_has_calls(calls, any_order=False)

    def test_putfo_absolute_path(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_client = Mock()
        mock_sftp_client = Mock()
        mock_transport = Mock()

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = '/mock/cwd'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        mock_fo = StringIO('mock stream data 1')

        result = client.putfo(path='/test/remote/path.txt', fo=mock_fo, chmod=455)
        self.assertEqual(result, '/test/remote/path.txt')

        calls = [
            call('/'),
            call('test'),
            call('remote')
        ]
        mock_sftp_client.chdir.assert_has_calls(calls, any_order=False)

        mock_sftp_client.putfo.assert_called_once_with(mock_fo, "/test/remote/path.txt")

        calls = [
            call('path.txt'),
            call().chmod(455),
            call().close()
        ]
        mock_sftp_client.file.assert_has_calls(calls, any_order=False)

    def test_putfo_relative_path(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        mock_client = Mock()
        mock_sftp_client = Mock()
        mock_transport = Mock()

        mock_client.get_transport.return_value = mock_transport
        mock_sftp_client.getcwd.return_value = '/mock/cwd'
        client.client = mock_client
        client.sftp_client = mock_sftp_client

        mock_fo = StringIO('mock stream data 2')

        result = client.putfo(path='path2.txt', fo=mock_fo, chmod=466)
        self.assertEqual(result, '/mock/cwd/path2.txt')

        calls = [
            call('.')
        ]
        mock_sftp_client.chdir.assert_has_calls(calls, any_order=False)

        mock_sftp_client.putfo.assert_called_once_with(mock_fo, "path2.txt")

        calls = [
            call('path2.txt'),
            call().chmod(466),
            call().close()
        ]
        mock_sftp_client.file.assert_has_calls(calls, any_order=False)

    def test_get_sftp_client(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        client = ParamikoSSHClient(**conn_params)

        # 1. sftp connection is not opened yet, new one should be opened
        mock_client = Mock()
        mock_sft_client = Mock()
        mock_client.open_sftp.return_value = mock_sft_client
        client.client = mock_client

        self.assertEqual(mock_client.open_sftp.call_count, 0)
        self.assertEqual(client._get_sftp_client(), mock_sft_client)
        self.assertEqual(mock_client.open_sftp.call_count, 1)

        # 2. existing sftp connection which is already opened is re-used
        mock_client = Mock()
        mock_sft_client = Mock()
        client.client = mock_client
        client.sftp_client = mock_sft_client

        self.assertEqual(mock_client.open_sftp.call_count, 0)
        self.assertEqual(client._get_sftp_client(), mock_sft_client)
        self.assertEqual(mock_client.open_sftp.call_count, 0)

        # 3. existing connection is already opened, but it throws
        # "socket closed" error, we should establish a new one
        mock_client = Mock()
        mock_sftp_client = Mock()

        client.client = mock_client
        client.sftp_client = mock_sftp_client

        mock_sftp_client.listdir.side_effect = OSError("Socket is closed")

        self.assertEqual(mock_client.open_sftp.call_count, 0)
        sftp_client = client._get_sftp_client()
        self.assertTrue(sftp_client != mock_sft_client)
        self.assertTrue(sftp_client)
        self.assertTrue(client._get_sftp_client())
        self.assertEqual(mock_client.open_sftp.call_count, 1)

        # 4. fatal exceptions should be propagated
        mock_client = Mock()
        mock_sftp_client = Mock()

        client.client = mock_client
        client.sftp_client = mock_sftp_client

        mock_sftp_client.listdir.side_effect = Exception("Fatal exception")

        self.assertEqual(mock_client.open_sftp.call_count, 0)
        self.assertRaisesRegex(Exception, "Fatal exception", client._get_sftp_client)


class ShellOutSSHClientTests(LibcloudTestCase):

    def test_password_auth_not_supported(self):
        try:
            ShellOutSSHClient(hostname='localhost', username='foo',
                              password='bar')
        except ValueError as e:
            msg = str(e)
            self.assertTrue('ShellOutSSHClient only supports key auth' in msg)
        else:
            self.fail('Exception was not thrown')

    def test_ssh_executable_not_available(self):
        class MockChild(object):
            returncode = 127

            def communicate(*args, **kwargs):
                pass

        def mock_popen(*args, **kwargs):
            return MockChild()

        with patch('subprocess.Popen', mock_popen):
            try:
                ShellOutSSHClient(hostname='localhost', username='foo')
            except ValueError as e:
                msg = str(e)
                self.assertTrue('ssh client is not available' in msg)
            else:
                self.fail('Exception was not thrown')

    def test_connect_success(self):
        client = ShellOutSSHClient(hostname='localhost', username='root')
        self.assertTrue(client.connect())

    def test_close_success(self):
        client = ShellOutSSHClient(hostname='localhost', username='root')
        self.assertTrue(client.close())

    def test_get_base_ssh_command(self):
        client1 = ShellOutSSHClient(hostname='localhost', username='root')
        client2 = ShellOutSSHClient(hostname='localhost', username='root',
                                    key='/home/my.key')
        client3 = ShellOutSSHClient(hostname='localhost', username='root',
                                    key='/home/my.key', timeout=5)

        cmd1 = client1._get_base_ssh_command()
        cmd2 = client2._get_base_ssh_command()
        cmd3 = client3._get_base_ssh_command()

        self.assertEqual(cmd1, ['ssh', 'root@localhost'])
        self.assertEqual(cmd2, ['ssh', '-i', '/home/my.key',
                                'root@localhost'])
        self.assertEqual(cmd3, ['ssh', '-i', '/home/my.key',
                                '-oConnectTimeout=5', 'root@localhost'])


if __name__ == '__main__':
    sys.exit(unittest.main())
