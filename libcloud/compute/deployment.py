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
Provides generic deployment steps for machines post boot.
"""

from __future__ import with_statement

import os
import binascii

from libcloud.utils.py3 import basestring, PY3


class Deployment(object):
    """
    Base class for deployment tasks.
    """

    def run(self, node, client):
        """
        Runs this deployment task on C{node} using the C{client} provided.

        @type node: L{Node}
        @keyword node: Node to operate one

        @type client: L{BaseSSHClient}
        @keyword client: Connected SSH client to use.

        @return: L{Node}
        """
        raise NotImplementedError(
            'run not implemented for this deployment')

    def _get_string_value(self, argument_name, argument_value):
        if not isinstance(argument_value, basestring) and \
           not hasattr(argument_value, 'read'):
            raise TypeError('%s argument must be a string or a file-like '
                            'object' % (argument_name))

        if hasattr(argument_value, 'read'):
            argument_value = argument_value.read()

        return argument_value


class SSHKeyDeployment(Deployment):
    """
    Installs a public SSH Key onto a host.
    """

    def __init__(self, key):
        """
        @type key: C{str}
        @keyword key: Contents of the public key write
        """
        self.key = self._get_string_value(argument_name='key',
                                          argument_value=key)

    def run(self, node, client):
        """
        Installs SSH key into C{.ssh/authorized_keys}

        See also L{Deployment.run}
        """
        client.put(".ssh/authorized_keys", contents=self.key, mode='a')
        return node


class FileDeployment(Deployment):
    """
    Installs a file.
    """

    def __init__(self, source, target):
        """
        @type source: C{str}
        @keyword source: Local path of file to be installed

        @type target: C{str}
        @keyword target: Path to install file on node
        """
        self.source = source
        self.target = target

    def run(self, node, client):
        """
        Upload the file, retaining permissions

        See also L{Deployment.run}
        """
        perms = int(oct(os.stat(self.source).st_mode)[4:], 8)

        with open(self.source, 'rb') as fp:
            content = fp.read()

        client.put(path=self.target, chmod=perms,
                   contents=content)
        return node


class ScriptDeployment(Deployment):
    """
    Runs an arbitrary Shell Script task.
    """

    def __init__(self, script, name=None, delete=False):
        """
        @type script: C{str}
        @keyword script: Contents of the script to run

        @type name: C{str}
        @keyword name: Name of the script to upload it as, if not specified,
                       a random name will be choosen.

        @type delete: C{bool}
        @keyword delete: Whether to delete the script on completion.
        """
        script = self._get_string_value(argument_name='script',
                                        argument_value=script)

        self.script = script
        self.stdout = None
        self.stderr = None
        self.exit_status = None
        self.delete = delete
        self.name = name

        if self.name is None:
            # File is put under user's home directory
            # (~/libcloud_deployment_<random_string>.sh)
            self.name = 'libcloud_deployment_%s.sh' % (binascii.hexlify(os.urandom(4)))

    def run(self, node, client):
        """
        Uploads the shell script and then executes it.

        See also L{Deployment.run}
        """
        file_path = client.put(path=self.name, chmod=int('755', 8),
                               contents=self.script)

        # Pre-pend cwd if user specified a relative path
        if self.name[0] != '/':
            base_path = os.path.dirname(file_path)
            name = os.path.join(base_path, self.name)
        else:
            name = self.name

        self.stdout, self.stderr, self.exit_status = client.run(name)

        if self.delete:
            client.delete(self.name)

        return node


class ScriptFileDeployment(ScriptDeployment):
    """
    Runs an arbitrary Shell Script task from a file.
    """

    def __init__(self, script_file, name=None, delete=False):
        """
        @type script_file: C{str}
        @keyword script_file: Path to a file containing the script to run

        @type name: C{str}
        @keyword name: Name of the script to upload it as, if not specified,
                       a random name will be choosen.

        @type delete: C{bool}
        @keyword delete: Whether to delete the script on completion.
        """
        with open(script_file, 'rb') as fp:
            content = fp.read()

        if PY3:
            content = content.decode('utf-8')

        super(ScriptFileDeployment, self).__init__(script=content,
                                               name=name,
                                               delete=delete)


class MultiStepDeployment(Deployment):
    """
    Runs a chain of Deployment steps.
    """
    def __init__(self, add=None):
        """
        @type add: C{list}
        @keyword add: Deployment steps to add.
        """
        self.steps = []
        self.add(add)

    def add(self, add):
        """Add a deployment to this chain.

        @type add: Single L{Deployment} or a C{list} of L{Deployment}
        @keyword add: Adds this deployment to the others already in this object.
        """
        if add is not None:
            add = add if isinstance(add, (list, tuple)) else [add]
            self.steps.extend(add)

    def run(self, node, client):
        """
        Run each deployment that has been added.

        See also L{Deployment.run}
        """
        for s in self.steps:
            node = s.run(node, client)
        return node
