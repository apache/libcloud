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

from os.path import split as psplit

class BaseSSHClient(object):
    """
    Base class representing a connection over SSH/SCP to a remote node.
    """

    def __init__(self, hostname, port=22, username='root', password=None,
                 key=None, timeout=None):
        """
        @type hostname: C{str}
        @keyword hostname: Hostname or IP address to connect to.

        @type port: C{int}
        @keyword port: TCP port to communicate on, defaults to 22.

        @type username: C{str}
        @keyword username: Username to use, defaults to root.

        @type password: C{str}
        @keyword password: Password to authenticate with.

        @type key: C{list}
        @keyword key: Private SSH keys to authenticate with.
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

        @return: C{bool}
        """
        raise NotImplementedError(
            'connect not implemented for this ssh client')

    def put(self, path, contents=None, chmod=None):
        """
        Upload a file to the remote node.

        @type path: C{str}
        @keyword path: File path on the remote node.

        @type contents: C{str}
        @keyword contents: File Contents.

        @type chmod: C{int}
        @keyword chmod: chmod file to this after creation.
        """
        raise NotImplementedError(
            'put not implemented for this ssh client')

    def delete(self, path):
        """
        Delete/Unlink a file on the remote node.

        @type path: C{str}
        @keyword path: File path on the remote node.
        """
        raise NotImplementedError(
            'delete not implemented for this ssh client')

    def run(self, cmd):
        """
        Run a command on a remote node.

        @type cmd: C{str}
        @keyword cmd: Command to run.

        @return C{list} of [stdout, stderr, exit_status]
        """
        raise NotImplementedError(
            'run not implemented for this ssh client')

    def close(self):
        """
        Shutdown connection to the remote node.
        """
        raise NotImplementedError(
            'close not implemented for this ssh client')

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
            raise Exception('must specify either password or key_filename')

        if self.timeout:
            conninfo['timeout'] = self.timeout

        self.client.connect(**conninfo)
        return True

    def put(self, path, contents=None, chmod=None):
        sftp = self.client.open_sftp()
        # less than ideal, but we need to mkdir stuff otherwise file() fails
        head, tail = psplit(path)
        if path[0] == "/":
            sftp.chdir("/")
        for part in head.split("/"):
            if part != "":
                try:
                    sftp.mkdir(part)
                except IOError:
                    # so, there doesn't seem to be a way to
                    # catch EEXIST consistently *sigh*
                    pass
                sftp.chdir(part)
        ak = sftp.file(tail,  mode='w')
        ak.write(contents)
        if chmod is not None:
            ak.chmod(chmod)
        ak.close()
        sftp.close()

    def delete(self, path):
        sftp = self.client.open_sftp()
        sftp.unlink(path)
        sftp.close()

    def run(self, cmd):
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
        return [so, se, status]

    def close(self):
        self.client.close()

class ShellOutSSHClient(BaseSSHClient):
    # TODO: write this one
    pass

SSHClient = ParamikoSSHClient
if not have_paramiko:
    SSHClient = ShellOutSSHClient
