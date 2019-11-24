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
Wraps multiple ways to communicate over SSH.
"""

from typing import Type
from typing import Optional
from typing import Tuple
from typing import List
from typing import Union
from typing import cast

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
import time
import subprocess
import logging
import warnings

from os.path import split as psplit
from os.path import join as pjoin

from libcloud.utils.logging import ExtraLogFormatter
from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import b

__all__ = [
    'BaseSSHClient',
    'ParamikoSSHClient',
    'ShellOutSSHClient',

    'SSHCommandTimeoutError'
]

SUPPORTED_KEY_TYPES_URL = 'https://libcloud.readthedocs.io/en/latest/compute/deployment.html#supported-private-ssh-key-types' # NOQA


class SSHCommandTimeoutError(Exception):
    """
    Exception which is raised when an SSH command times out.
    """
    def __init__(self, cmd, timeout):
        # type: (str, float) -> None
        self.cmd = cmd
        self.timeout = timeout
        message = 'Command didn\'t finish in %s seconds' % (timeout)
        super(SSHCommandTimeoutError, self).__init__(message)

    def __repr__(self):
        return ('<SSHCommandTimeoutError: cmd="%s",timeout=%s)>' %
                (self.cmd, self.timeout))

    def __str__(self):
        return self.message


class BaseSSHClient(object):
    """
    Base class representing a connection over SSH/SCP to a remote node.
    """

    def __init__(self,
                 hostname,  # type: str
                 port=22,  # type: int
                 username='root',  # type: str
                 password=None,  # type: Optional[str]
                 key=None,  # type: Optional[str]
                 key_files=None,  # type: Optional[Union[str, List[str]]]
                 timeout=None  # type: Optional[float]
                 ):
        """
        :type hostname: ``str``
        :keyword hostname: Hostname or IP address to connect to.

        :type port: ``int``
        :keyword port: TCP port to communicate on, defaults to 22.

        :type username: ``str``
        :keyword username: Username to use, defaults to root.

        :type password: ``str``
        :keyword password: Password to authenticate with or a password used
                           to unlock a private key if a password protected key
                           is used.

        :param key: Deprecated in favor of ``key_files`` argument.

        :type key_files: ``str`` or ``list``
        :keyword key_files: A list of paths to the private key files to use.
        """
        if key is not None:
            message = ('You are using deprecated "key" argument which has '
                       'been replaced with "key_files" argument')
            warnings.warn(message, DeprecationWarning)

            # key_files has precedent
            key_files = key if not key_files else key_files

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_files = key_files
        self.timeout = timeout

    def connect(self):
        # type: () -> bool
        """
        Connect to the remote node over SSH.

        :return: True if the connection has been successfully established,
                 False otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'connect not implemented for this ssh client')

    def put(self, path, contents=None, chmod=None, mode='w'):
        # type: (str, Optional[Union[str, bytes]], Optional[int], str) -> str
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
        # type: (str) -> bool
        """
        Delete/Unlink a file on the remote node.

        :type path: ``str``
        :keyword path: File path on the remote node.

        :return: True if the file has been successfully deleted, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'delete not implemented for this ssh client')

    def run(self, cmd):
        # type: (str) -> Tuple[str, str, int]
        """
        Run a command on a remote node.

        :type cmd: ``str``
        :keyword cmd: Command to run.

        :return ``list`` of [stdout, stderr, exit_status]
        """
        raise NotImplementedError(
            'run not implemented for this ssh client')

    def close(self):
        # type: () -> bool
        """
        Shutdown connection to the remote node.

        :return: True if the connection has been successfully closed, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'close not implemented for this ssh client')

    def _get_and_setup_logger(self):
        # type: () -> logging.Logger
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

    # Maximum number of bytes to read at once from a socket
    CHUNK_SIZE = 4096

    # How long to sleep while waiting for command to finish (to prevent busy
    # waiting)
    SLEEP_DELAY = 0.2

    def __init__(self,
                 hostname,  # type: str
                 port=22,  # type: int
                 username='root',  # type: str
                 password=None,  # type: Optional[str]
                 key=None,  # type: Optional[str]
                 key_files=None,  # type: Optional[Union[str, List[str]]]
                 key_material=None,  # type: Optional[str]
                 timeout=None  # type: Optional[float]
                 ):
        """
        Authentication is always attempted in the following order:

        - The key passed in (if key is provided)
        - Any key we can find through an SSH agent (only if no password and
          key is provided)
        - Any "id_rsa" or "id_dsa" key discoverable in ~/.ssh/ (only if no
          password and key is provided)
        - Plain username/password auth, if a password was given (if password is
          provided)
        """
        if key_files and key_material:
            raise ValueError(('key_files and key_material arguments are '
                              'mutually exclusive'))

        super(ParamikoSSHClient, self).__init__(hostname=hostname, port=port,
                                                username=username,
                                                password=password,
                                                key=key,
                                                key_files=key_files,
                                                timeout=timeout)

        self.key_material = key_material

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

        if self.key_files:
            conninfo['key_filename'] = self.key_files

        if self.key_material:
            conninfo['pkey'] = self._get_pkey_object(key=self.key_material)

        if not self.password and not (self.key_files or self.key_material):
            conninfo['allow_agent'] = True
            conninfo['look_for_keys'] = True

        if self.timeout:
            conninfo['timeout'] = self.timeout

        # This is a workaround for paramiko only supporting key files in
        # format staring with "BEGIN RSA PRIVATE KEY".
        # If key_files are provided and a key looks like a PEM formatted key
        # we try to convert it into a format supported by paramiko
        if (self.key_files and not isinstance(self.key_files, (list, tuple))
                and os.path.isfile(self.key_files)):
            with open(self.key_files, 'r') as fp:
                key_material = fp.read()

            try:
                pkey = self._get_pkey_object(key=key_material)
            except Exception:
                pass
            else:
                # It appears key is valid, but it was passed in in an invalid
                # format. Try to use the converted key directly
                del conninfo['key_filename']
                conninfo['pkey'] = pkey

        extra = {'_hostname': self.hostname, '_port': self.port,
                 '_username': self.username, '_timeout': self.timeout}

        if self.password:
            extra['_auth_method'] = 'password'
        else:
            extra['_auth_method'] = 'key_file'

            if self.key_files:
                extra['_key_file'] = self.key_files

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

    def run(self, cmd, timeout=None):
        # type: (str, Optional[float]) -> Tuple[str, str, int]
        """
        Note: This function is based on paramiko's exec_command()
        method.

        :param timeout: How long to wait (in seconds) for the command to
                        finish (optional).
        :type timeout: ``float``
        """
        extra1 = {'_cmd': cmd}
        self.logger.debug('Executing command', extra=extra1)

        # Use the system default buffer size
        bufsize = -1

        transport = self.client.get_transport()
        chan = transport.open_session()

        start_time = time.time()
        chan.exec_command(cmd)

        stdout = StringIO()
        stderr = StringIO()

        # Create a stdin file and immediately close it to prevent any
        # interactive script from hanging the process.
        stdin = chan.makefile('wb', bufsize)
        stdin.close()

        # Receive all the output
        # Note #1: This is used instead of chan.makefile approach to prevent
        # buffering issues and hanging if the executed command produces a lot
        # of output.
        #
        # Note #2: If you are going to remove "ready" checks inside the loop
        # you are going to have a bad time. Trying to consume from a channel
        # which is not ready will block for indefinitely.
        exit_status_ready = chan.exit_status_ready()

        if exit_status_ready:
            # It's possible that some data is already available when exit
            # status is ready
            stdout.write(self._consume_stdout(chan).getvalue())
            stderr.write(self._consume_stderr(chan).getvalue())

        while not exit_status_ready:
            current_time = time.time()
            elapsed_time = (current_time - start_time)

            if timeout and (elapsed_time > timeout):
                # TODO: Is this the right way to clean up?
                chan.close()

                raise SSHCommandTimeoutError(cmd=cmd, timeout=timeout)

            stdout.write(self._consume_stdout(chan).getvalue())
            stderr.write(self._consume_stderr(chan).getvalue())

            # We need to check the exist status here, because the command could
            # print some output and exit during this sleep below.
            exit_status_ready = chan.exit_status_ready()

            if exit_status_ready:
                break

            # Short sleep to prevent busy waiting
            time.sleep(self.SLEEP_DELAY)

        # Receive the exit status code of the command we ran.
        status = chan.recv_exit_status()  # type: int

        stdout_str = stdout.getvalue()  # type: str
        stderr_str = stderr.getvalue()  # type: str

        extra2 = {'_status': status, '_stdout': stdout_str,
                  '_stderr': stderr_str}
        self.logger.debug('Command finished', extra=extra2)

        result = (stdout_str, stderr_str, status)  # type: Tuple[str, str, int]
        return result

    def close(self):
        self.logger.debug('Closing server connection')

        self.client.close()
        return True

    def _consume_stdout(self, chan):
        """
        Try to consume stdout data from chan if it's receive ready.
        """
        stdout = self._consume_data_from_channel(
            chan=chan,
            recv_method=chan.recv,
            recv_ready_method=chan.recv_ready)
        return stdout

    def _consume_stderr(self, chan):
        """
        Try to consume stderr data from chan if it's receive ready.
        """
        stderr = self._consume_data_from_channel(
            chan=chan,
            recv_method=chan.recv_stderr,
            recv_ready_method=chan.recv_stderr_ready)
        return stderr

    def _consume_data_from_channel(self, chan, recv_method, recv_ready_method):
        """
        Try to consume data from the provided channel.

        Keep in mind that data is only consumed if the channel is receive
        ready.
        """
        result = StringIO()
        result_bytes = bytearray()

        if recv_ready_method():
            data = recv_method(self.CHUNK_SIZE)
            result_bytes += b(data)

            while data:
                ready = recv_ready_method()

                if not ready:
                    break

                data = recv_method(self.CHUNK_SIZE)
                result_bytes += b(data)

        # We only decode data at the end because a single chunk could contain
        # a part of multi byte UTF-8 character (whole multi bytes character
        # could be split over two chunks)
        result.write(result_bytes.decode('utf-8'))
        return result

    def _get_pkey_object(self, key, passpharse=None):
        """
        Try to detect private key type and return paramiko.PKey object.

        # NOTE: Paramiko only supports key in PKCS#1 PEM format.
        """

        for cls, key_type in [(paramiko.RSAKey, 'RSA'),
                              (paramiko.DSSKey, 'DSA'),
                              (paramiko.ECDSAKey, 'EC')]:
            # Work around for paramiko not recognizing keys which start with
            # "----BEGIN PRIVATE KEY-----"
            # Since key is already in PEM format, we just try changing the
            # header and footer
            key_split = key.strip().splitlines()
            if (key_split[0] == '-----BEGIN PRIVATE KEY-----' and
                    key_split[-1] == '-----END PRIVATE KEY-----'):
                key_split[0] = '-----BEGIN %s PRIVATE KEY-----' % (key_type)
                key_split[-1] = '-----END %s PRIVATE KEY-----' % (key_type)

                key_value = '\n'.join(key_split)
            else:
                # Already a valid key, us it as is
                key_value = key

            try:
                key = cls.from_private_key(StringIO(key_value), passpharse)
            except (paramiko.ssh_exception.SSHException, AssertionError):
                # Invalid key, try other key type
                pass
            else:
                return key

        msg = ('Invalid or unsupported key type (only RSA, DSS and ECDSA keys'
               ' in PEM format are supported). For more information on '
               ' supported key file types, see %s' % (SUPPORTED_KEY_TYPES_URL))
        raise paramiko.ssh_exception.SSHException(msg)


class ShellOutSSHClient(BaseSSHClient):
    """
    This client shells out to "ssh" binary to run commands on the remote
    server.

    Note: This client should not be used in production.
    """

    def __init__(self,
                 hostname,  # type: str
                 port=22,  # type: int
                 username='root',  # type: str
                 password=None,  # type: Optional[str]
                 key=None,  # type: Optional[str]
                 key_files=None,  # type: Optional[str]
                 timeout=None  # type: Optional[float]
                 ):
        super(ShellOutSSHClient, self).__init__(hostname=hostname,
                                                port=port, username=username,
                                                password=password,
                                                key=key,
                                                key_files=key_files,
                                                timeout=timeout)
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
        # type: () -> List[str]
        cmd = ['ssh']

        if self.key_files:
            self.key_files = cast(str, self.key_files)
            cmd += ['-i', self.key_files]

        if self.timeout:
            cmd += ['-oConnectTimeout=%s' % (self.timeout)]

        cmd += ['%s@%s' % (self.username, self.hostname)]

        return cmd

    def _run_remote_shell_command(self, cmd):
        # type: (List[str]) -> Tuple[str, str, int]
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

        stdout_str = cast(str, stdout)
        stderr_str = cast(str, stdout)

        return (stdout_str, stderr_str, child.returncode)


class MockSSHClient(BaseSSHClient):
    pass


SSHClient = ParamikoSSHClient  # type: Type[BaseSSHClient]
if not have_paramiko:
    SSHClient = MockSSHClient  # type: ignore
