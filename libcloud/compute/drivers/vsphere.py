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
VMware vSphere driver. Uses pyvmomi - https://github.com/vmware/pyvmomi
Code inspired by https://github.com/vmware/pyvmomi-community-samples

Author: Markos Gogoulos -  mgogoulos@mist.io
"""

try:
    from pyVim import connect
    from pyVmomi import vmodl
except ImportError:
    raise ImportError('Missing "pyvmomi" dependency. You can install it '
                      'using pip - pip install pyvmomi')

import atexit

from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import NodeLocation
from libcloud.compute.base import NodeImage
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState, Provider
from libcloud.utils.networking import is_public_subnet


class VSphereNodeDriver(NodeDriver):
    name = 'VMware vSphere'
    website = 'http://www.vmware.com/products/vsphere/'
    type = Provider.VSPHERE

    NODE_STATE_MAP = {
        'poweredOn': NodeState.RUNNING,
        'poweredOff': NodeState.STOPPED,
        'suspended': NodeState.SUSPENDED,
    }

    def __init__(self, host, username, password):
        """Initialize a connection by providing a hostname,
        username and password
        """
        try:
            self.connection = connect.SmartConnect(host=host, user=username,
                                                   pwd=password)
            atexit.register(connect.Disconnect, self.connection)
        except Exception as exc:
            error_message = str(exc).lower()
            if 'incorrect user name' in error_message:
                raise InvalidCredsError('Check your username and '
                                        'password are valid')
            if 'connection refused' in error_message or 'is not a vim server' \
                                                        in error_message:
                raise Exception('Check that the host provided is a '
                                'vSphere installation')
            if 'name or service not known' in error_message:
                raise Exception('Check that the vSphere host is accessible')
            if 'certificate verify failed' in error_message:
                # bypass self signed certificates
                try:
                    import ssl
                    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                    context.verify_mode = ssl.CERT_NONE
                except ImportError:
                    raise ImportError('To use self signed certificates, '
                                      'please upgrade to python 2.7.11 and '
                                      'pyvmomi 6.0.0+')

                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.verify_mode = ssl.CERT_NONE
                try:
                    self.connection = connect.SmartConnect(host=host,
                                                           user=username,
                                                           pwd=password,
                                                           sslContext=context)
                    atexit.register(connect.Disconnect, self.connection)
                except Exception as exc:
                    error_message = str(exc).lower()
                    if 'incorrect user name' in error_message:
                        raise InvalidCredsError('Check your username and '
                                                'password are valid')
                    if 'connection refused' in error_message or \
                            'is not a vim server' in error_message:
                        raise Exception('Check that the host provided '
                                        'is a vSphere installation')
                    if 'name or service not known' in error_message:
                        raise Exception('Check that the vSphere host is '
                                        'accessible')
                    raise Exception('Cannot connect to vSphere using '
                                    'self signed certs')
            else:
                raise Exception('Cannot connect to vSphere')

    def list_locations(self):
        """
        Lists locations
        """
        return []

    def list_sizes(self):
        """
        Lists sizes
        """
        return []

    def list_images(self):
        """
        Lists images
        """
        return []

    def list_nodes(self):
        """
        Lists nodes
        """
        nodes = []
        content = self.connection.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if hasattr(child, 'vmFolder'):
                datacenter = child
            else:
            # some other non-datacenter type object
                continue
            vm_folder = datacenter.vmFolder
            vm_list = vm_folder.childEntity

            for virtual_machine in vm_list:
                node = self._to_node(virtual_machine, 10)
                if node:
                    nodes.append(node)
        return nodes

    def _to_node(self, virtual_machine, depth=1):
        maxdepth = 10
        # if this is a group it will have children.
        # if it does, recurse into them and then return
        if hasattr(virtual_machine, 'childEntity'):
            if depth > maxdepth:
                return
            vmList = virtual_machine.childEntity
            for c in vmList:
                self._to_node(c, depth + 1)
            return

        summary = virtual_machine.summary
        name = summary.config.name
        path = summary.config.vmPathName
        memory = summary.config.memorySizeMB
        cpus = summary.config.numCpu
        operating_system = summary.config.guestFullName
        # mist.io needs this metadata
        os_type = 'unix'
        if 'Microsoft' in str(operating_system):
            os_type = 'windows'
        uuid = summary.config.instanceUuid
        annotation = summary.config.annotation
        state = summary.runtime.powerState
        status = self.NODE_STATE_MAP.get(state, NodeState.UNKNOWN)
        boot_time = summary.runtime.bootTime

        if summary.guest is not None:
            ip_address = summary.guest.ipAddress

        overallStatus = str(summary.overallStatus)
        public_ips = []
        private_ips = []

        extra = {
            "path": path,
            "operating_system": operating_system,
            "os_type": os_type,
            "memory_MB": memory,
            "cpus": cpus,
            "overallStatus": overallStatus
        }

        if boot_time:
            extra['boot_time'] = boot_time.isoformat()
        if annotation:
            extra['annotation'] = annotation

        if ip_address:
            try:
                if is_public_subnet(ip_address):
                    public_ips.append(ip_address)
                else:
                    private_ips.append(ip_address)
            except:
                # IPV6 not supported
                pass

        node = Node(id=uuid, name=name, state=status,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, extra=extra)
        node._uuid = uuid
        return node

    def reboot_node(self, node):
        """
        """
        vm = self.find_by_uuid(node)
        try:
            vm.RebootGuest()
        except:
            pass
        return True

    def destroy_node(self, node):
        """
        """
        vm = self.find_by_uuid(node)
        try:
            vm.PowerOff()
        except:
            pass
        try:
            vm.Destroy()
        except:
            pass
        return True

    def ex_stop_node(self, node):
        """
        """
        vm = self.find_by_uuid(node)
        try:
            vm.PowerOff()
        except:
            pass
        return True

    def ex_start_node(self, node):
        """
        """
        vm = self.find_by_uuid(node)
        try:
            vm.PowerOn()
        except:
            pass
        return True

    def find_by_uuid(self, node):
        """Searches VMs for a given uuid
        returns pyVmomi.VmomiSupport.vim.VirtualMachine
        """
        vm = self.connection.content.searchIndex.FindByUuid(None, node.id,
                                                            True, True)
        if not vm:
            raise Exception("Unable to locate VirtualMachine.")
        return vm
