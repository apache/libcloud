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

# This driver presents a libcloud interface around vmrun - the command line API
# for controlling VMWare VM's.

# Base image notes:
#1. Install vmware tools from packages.vmware.com/tools - the latest esx ones work with vmware fusion
#2. Don't forget to delete the persistent net rules
#3. There needs to be a user with a password/key that can get to root without sudo requiring a passphrase.


import os
import glob
import logging
import shutil
import uuid

from libcloud.common.types import LibcloudError
from libcloud.common.process import Connection
from libcloud.compute.base import NodeDriver, Node, NodeSize, NodeImage
from libcloud.compute.base import NodeState
from libcloud.compute.types import Provider


class VMWareDriver(NodeDriver):

    type = Provider.VMWARE
    name = "vmware"
    website = "http://www.vmware.com/products/fusion/"
    connectionCls = Connection

    def __init__(self, vm_library="~/.libcloud/vmware/library", vm_instances="~/.libcloud/vmware/instances", vmrun=None, hosttype=None):
        super(VMWareDriver, self).__init__(None)
        self.vm_library = os.path.expanduser(vm_library)
        self.vm_instances = os.path.expanduser(vm_instances)
        self.vmrun = vmrun or self._find_vmrun()
        self.hosttype = hosttype or self._find_hosttype()

    def _find_vmrun(self):
        known_locations = [
            "/Applications/VMWare Fusion.app/Contents/Library",
            "/usr/bin",
            ]
        for dir in known_locations:
            path = os.path.join(dir, "vmrun")
            if os.path.exists(path):
                return path
        raise LibcloudError('VMWareDriver requires \'vmrun\' executable to be present on system')

    def _find_hosttype(self):
        default_hosttypes = [
            'ws',
            'fusion',
            'player',
            ]
        for hosttype in default_hosttypes:
            command = [self.vmrun, "-T", hosttype, "list"]
            try:
                resp = self.connection.request(command)
            except LibcloudError:
                continue
            else:
                return hosttype
        raise LibcloudError('VMWareDriver is unable to find a default host type. Please specify the hosttype argument')

    def _action(self, *params):
        command = [self.vmrun, "-T", self.hosttype] + list(params)
        return self.connection.request(command).body

    def list_images(self, location=None):
        if not location:
            location = self.vm_library
        locs = []
        for match in glob.glob(os.path.join(location, "*", "*.vmx")):
            locs.append(NodeImage(id=match, name="VMWare Image", driver=self))
        return locs

    def list_sizes(self, location=None):
        return [
            NodeSize("small", "small", 1024, 0, 0, 0, self),
            NodeSize("medium", "medium", 4096, 0, 0, 0, self),
            NodeSize("large", "large", 8192, 0, 0, 0, self),
            ]

    def list_locations(self):
        return []

    def list_nodes(self):
        nodes = []
        lines = iter(self._action("list").strip().splitlines())
        lines.next() # Skip the summary line
        for line in lines:
            if not line.strip():
                continue
            n = Node(line.strip(), line.strip(), NodeState.UNKNOWN, None, None, self)
            n.name = self._action("readVariable", n.id, "runtimeConfig", "displayName")
            ip = self._action("readVariable", n.id, "guestVar", "ip").strip()
            if ip:
                n.public_ips = [ip]
                n.state = NodeState.RUNNING
            nodes.append(n)
        return nodes

    def create_node(self, name, size, image):
        source = image.id
        if not os.path.exists(source):
            raise LibcloudError("Base image is not valid")

        target_dir = os.path.join(self.vm_instances, str(uuid.uuid4()))
        target = os.path.join(target_dir, "vm.vmx")

        target_parent = os.path.dirname(target_dir)
        if not os.path.exists(target_parent):
            os.makedirs(target_parent)

        # First try to clone the VM with the VMWare commands. We do this in
        # the hope that they know what the fastest and most efficient way to
        # clone an image is. But if that fails we can just copy the entire
        # image directory.
        try:
            self._action("clone", source, target)
        except LibcloudError:
            src_path = os.path.dirname(source)
            shutil.copytree(src_path, target_dir)
            os.rename(os.path.join(target_dir, os.path.basename(source)), target)

        node = Node(target, name, NodeState.PENDING, None, None, self)

        # If a NodeSize is provided then we can control the amount of RAM the
        # VM has. Number of CPU's would be easy to scale too, but this isn't
        # exposed on a NodeSize

        # if size:
        #     if size.ram:
        #        self.ex_set_runtime_variable(node, "displayName", name, str(size.ram))
        #        self._action("writeVariable", target, "runtimeConfig", "memsize", str(size.ram))

        self._action("start", target, "nogui")
        self.ex_set_runtime_variable(node, "displayName", name)
        return Node(target, name, NodeState.PENDING, None, None, self)

    def reboot_node(self, node):
        self._action("reset", node.id, "hard")
        node.state = NodeState.REBOOTING

    def destroy_node(self, node):
        self._action("stop", node.id, "hard")
        self._action("deleteVM", node.id)
        shutil.rmtree(os.path.dirname(node.id))

    def ex_get_runtime_variable(self, node, variable):
        return self._action("readVariable", node.id, "runtimeConfig", variable)

    def ex_set_runtime_variable(self, node, variable, value):
        self._action("writeVariable", node.id, "runtimeConfig", variable, value)

