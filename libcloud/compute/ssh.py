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

"""
Wraps multiple ways to communicate over SSH
"""
have_paramiko = False

try:
    import paramiko
    have_paramiko = True
except ImportError:
    pass

# Depending on your version of Paramiko, it may cause a deprecation
# warning on Python 2.6.
# Ref: https://bugs.launchpad.net/paramiko/+bug/392973

import os
import subprocess
import logging

from os.path import split as psplit
from os.path import join as pjoin

from libcloud.utils.logging import ExtraLogFormatter


class BaseSSHClient(object):
    """
    Base class representing a connection over SSH/SCP to a remote node.
    """

    def __init__(self, hostname, port=22, username='root', password=None,
                 key=None, timeout=None):
        """
        :type hostname: ``str``
        :keyword hostname: Hostname or IP address to connect to.

        :type port: ``int``
        :keyword port: TCP port to communicate on, defaults to 22.

        :type username: ``str``
        :keyword username: Username to use, defaults to root.

        :type password: ``str``
        :keyword password: Password to authenticate with.

        :type key: ``list``
        :keyword key: Private SSH keys to authenticate with.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key = key
        self.timeout = timeout

    def connect(self):
        """
        Connect to the remote node over SSH.

        :return: True if the connection has been successfuly established, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'connect not implemented for this ssh client')

    def put(self, path, contents=None, chmod=None, mode='w'):
        """
        Upload a file to the remote node.

        :type path: ``str``
        :keyword path: File path on the remote node.

        :type contents: ``str``
        :keyword contents: File Contents.

        :type chmod: ``int``
        :keyword chmod: chmod file to this after creation.

        :type mode: ``str``
        :keyword mode: Mode in which the file is opened.

        :return: Full path to the location where a file has been saved.
        :rtype: ``str``
        """
        raise NotImplementedError(
            'put not implemented for this ssh client')

    def delete(self, path):
        """
        Delete/Unlink a file on the remote node.

        :type path: ``str``
        :keyword path: File path on the remote node.

        :return: True if the file has been successfuly deleted, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'delete not implemented for this ssh client')

    def run(self, cmd):
        """
        Run a command on a remote node.

        :type cmd: ``str``
        :keyword cmd: Command to run.

        :return ``list`` of [stdout, stderr, exit_status]
        """
        raise NotImplementedError(
            'run not implemented for this ssh client')

    def close(self):
        """
        Shutdown connection to the remote node.

        :return: True if the connection has been successfuly closed, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'close not implemented for this ssh client')

    def _get_and_setup_logger(self):
        logger = logging.getLogger('libcloud.compute.ssh')
        path = os.getenv('LIBCLOUD_DEBUG')

        if path:
            handler = logging.FileHandler(path)
            handler.setFormatter(ExtraLogFormatter())
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

        return logger


class ParamikoSSHClient(BaseSSHClient):

    """
    A SSH Client powered by Paramiko.
    """
    def __init__(self, hostname, port=22, username='root', password=None,
                 key=None, timeout=None):
        super(ParamikoSSHClient, self).__init__(hostname, port, username,
                                                password, key, timeout)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.logger = self._get_and_setup_logger()

    def connect(self):
        conninfo = {'hostname': self.hostname,
                    'port': self.port,
                    'username': self.username,
                    'allow_agent': False,
                    'look_for_keys': False}

        if self.password:
            conninfo['password'] = self.password
        elif self.key:
            conninfo['key_filename'] = self.key
        else:
            conninfo['allow_agent'] = True
            conninfo['look_for_keys'] = True

        if self.timeout:
            conninfo['timeout'] = self.timeout

        extra = {'_hostname': self.hostname, '_port': self.port,
                 '_username': self.username, '_timeout': self.timeout}
        self.logger.debug('Connecting to server', extra=extra)

        self.client.connect(**conninfo)
        return True

    def put(self, path, contents=None, chmod=None, mode='w'):
        extra = {'_path': path, '_mode': mode, '_chmod': chmod}
        self.logger.debug('Uploading file', extra=extra)

        sftp = self.client.open_sftp()
        # less than ideal, but we need to mkdir stuff otherwise file() fails
        head, tail = psplit(path)

        if path[0] == "/":
            sftp.chdir("/")
        else:
            # Relative path - start from a home directory (~)
            sftp.chdir('.')

        for part in head.split("/"):
            if part != "":
                try:
                    sftp.mkdir(part)
                except IOError:
                    # so, there doesn't seem to be a way to
                    # catch EEXIST consistently *sigh*
                    pass
                sftp.chdir(part)

        cwd = sftp.getcwd()

        ak = sftp.file(tail, mode=mode)
        ak.write(contents)
        if chmod is not None:
            ak.chmod(chmod)
        ak.close()
        sftp.close()

        if path[0] == '/':
            file_path = path
        else:
            file_path = pjoin(cwd, path)

        return file_path

    def delete(self, path):
        extra = {'_path': path}
        self.logger.debug('Deleting file', extra=extra)

        sftp = self.client.open_sftp()
        sftp.unlink(path)
        sftp.close()
        return True

    def run(self, cmd):
        extra = {'_cmd': cmd}
        self.logger.debug('Executing command', extra=extra)

        # based on exec_command()
        bufsize = -1
        t = self.client.get_transport()
        chan = t.open_session()
        chan.exec_command(cmd)
        stdin = chan.makefile('wb', bufsize)
        stdout = chan.makefile('rb', bufsize)
        stderr = chan.makefile_stderr('rb', bufsize)
        #stdin, stdout, stderr = self.client.exec_command(cmd)
        stdin.close()
        status = chan.recv_exit_status()
        so = stdout.read()
        se = stderr.read()

        extra = {'_status': status, '_stdout': so, '_stderr': se}
        self.logger.debug('Command finished', extra=extra)

        return [so, se, status]

    def close(self):
        self.logger.debug('Closing server connection')

        self.client.close()
        return True


class ShellOutSSHClient(BaseSSHClient):
    """
    This client shells out to "ssh" binary to run commands on the remote
    server.

    Note: This client should not be used in production.
    """

    def __init__(self, hostname, port=22, username='root', password=None,
                 key=None, timeout=None):
        super(ShellOutSSHClient, self).__init__(hostname, port, username,
                                                password, key, timeout)
        if self.password:
            raise ValueError('ShellOutSSHClient only supports key auth')

        child = subprocess.Popen(['ssh'], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        child.communicate()

        if child.returncode == 127:
            raise ValueError('ssh client is not available')

        self.logger = self._get_and_setup_logger()

    def connect(self):
        """
        This client doesn't support persistent connections establish a new
        connection every time "run" method is called.
        """
        return True

    def run(self, cmd):
        return self._run_remote_shell_command([cmd])

    def put(self, path, contents=None, chmod=None, mode='w'):
        if mode == 'w':
            redirect = '>'
        elif mode == 'a':
            redirect = '>>'
        else:
            raise ValueError('Invalid mode: ' + mode)

        cmd = ['echo "%s" %s %s' % (contents, redirect, path)]
        self._run_remote_shell_command(cmd)
        return path

    def delete(self, path):
        cmd = ['rm', '-rf', path]
        self._run_remote_shell_command(cmd)
        return True

    def close(self):
        return True

    def _get_base_ssh_command(self):
        cmd = ['ssh']

        if self.key:
            cmd += ['-i', self.key]

        if self.timeout:
            cmd += ['-oConnectTimeout=%s' % (self.timeout)]

        cmd += ['%s@%s' % (self.username, self.hostname)]

        return cmd

    def _run_remote_shell_command(self, cmd):
        """
        Run a command on a remote server.

        :param      cmd: Command to run.
        :type       cmd: ``list`` of ``str``

        :return: Command stdout, stderr and status code.
        :rtype: ``tuple``
        """
        base_cmd = self._get_base_ssh_command()
        full_cmd = base_cmd + [' '.join(cmd)]

        self.logger.debug('Executing command: "%s"' % (' '.join(full_cmd)))

        child = subprocess.Popen(full_cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = child.communicate()
        return (stdout, stderr, child.returncode)


class MockSSHClient(BaseSSHClient):
    pass


SSHClient = ParamikoSSHClient
if not have_paramiko:
    SSHClient = MockSSHClient
