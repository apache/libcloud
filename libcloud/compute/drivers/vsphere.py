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
    from pyVmomi import vim
except ImportError:
    raise ImportError('Missing "pyvmomi" dependency. You can install it '
                      'using pip - pip install pyvmomi')

import atexit

from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node
from libcloud.compute.base import NodeImage, NodeLocation
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
        #datacenters = [dc for dc in
        #    content.viewManager.CreateContainerView(
        #        content.rootFolder,
        #        [vim.Datacenter],
        #        recursive=True
        #    ).view
        #]

        # TODO: Clusters should be selectable as locations drs is enabled
        # check property cluster.configuration.drsConfig.enabled
        
        #clusters = [dc for dc in
        #    content.viewManager.CreateContainerView(
        #        content.rootFolder,
        #        [vim.ClusterComputeResource, vim.HostSystem],
        #        recursive=True
        #    ).view
        #]

        locations = []
        content = self.connection.RetrieveContent()
        hosts = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.HostSystem],
            recursive=True
        ).view

        for host in hosts:
            locations.append(self._to_location(host))

        return locations


    def _to_location(self, data):
        extra = {
            "state": data.runtime.connectionState,
            "type": data.config.product.fullName,
            "vendor": data.hardware.systemInfo.vendor,
            "model": data.hardware.systemInfo.model,
            "ram": data.hardware.memorySize,
            "cpu": {
                "packages": data.hardware.cpuInfo.numCpuPackages,
                "cores": data.hardware.cpuInfo.numCpuCores,
                "threads": data.hardware.cpuInfo.numCpuThreads,
            },
            "uptime": data.summary.quickStats.uptime
        }

        return NodeLocation(id=data.name, name=data.name, country=None,
                            extra=extra, driver=self)

    def ex_list_networks(self):
        """
        List networks
        """
        content = self.connection.RetrieveContent()
        networks = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Network],
            recursive=True
        ).view

        return [self._to_network(network) for network in networks]

    def _to_network(self, data):
        summary = data.summary
        extra = {
            'hosts': [h.name for h in data.host],
            'ip_pool_name': summary.ipPoolName,
            'ip_pool_id': summary.ipPoolId,
            'accessible': summary.accessible
        }
        return VSphereNetwork(id=data.name, name=data.name, extra=extra)

    def list_sizes(self, location=None):
        """
        Lists sizes
        """
        return []

    def list_images(self, location=None):
        """
        Lists VM templates as images
        """

        images = []
        content = self.connection.RetrieveContent()
        vms = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.VirtualMachine],
            recursive=True
        ).view

        for vm in vms:
            if vm.config.template:
                images.append(self._to_image(vm))

        return images

    def _to_image(self, data):
        summary = data.summary
        name = summary.config.name
        uuid = summary.config.instanceUuid
        memory = summary.config.memorySizeMB
        cpus = summary.config.numCpu
        operating_system = summary.config.guestFullName
        os_type = 'unix'
        if 'Microsoft' in str(operating_system):
            os_type = 'windows'
        annotation = summary.config.annotation
        extra = {
            "path": summary.config.vmPathName,
            "operating_system": operating_system,
            "os_type": os_type,
            "memory_MB": memory,
            "cpus": cpus,
            "overallStatus": str(summary.overallStatus),
            "metadata": {}
        }

        boot_time = summary.runtime.bootTime
        if boot_time:
            extra['boot_time'] = boot_time.isoformat()
        if annotation:
            extra['annotation'] = annotation


        for custom_field in data.customValue:
            key_id = custom_field.key
            key = self.find_custom_field_key(key_id)
            extra["metadata"][key] = custom_field.value

        return NodeImage(id=uuid, name=name, driver=self,
                         extra=extra)

    def list_nodes(self):
        """
        Lists nodes, excluding templates
        """
        nodes = []
        content = self.connection.RetrieveContent()
        children = content.rootFolder.childEntity
        # this will be needed for custom VM metadata
        if content.customFieldsManager:
            self.custom_fields = content.customFieldsManager.field
        else:
            self.custom_fields = []
        for child in children:
            if hasattr(child, 'vmFolder'):
                datacenter = child
                vm_folder = datacenter.vmFolder
                vm_list = vm_folder.childEntity
                nodes.extend(self._to_nodes(vm_list))
        for node in nodes:
            node.extra['vSphere version'] = content.about.version
        return nodes

    def _to_nodes(self, vm_list):
        nodes = []
        for virtual_machine in vm_list:
            if virtual_machine.config.template:
                continue # Do not include templates in node list
            if hasattr(virtual_machine, 'childEntity'):
                # If this is a group it will have children.
                # If it does, recurse into them and then return
                nodes.extend(self._to_nodes(virtual_machine.childEntity))
            elif isinstance(virtual_machine, vim.VirtualApp):
                # If this is a vApp, it likely contains child VMs
                # (vApps can nest vApps, but it is hardly
                # a common usecase, so ignore that)
                nodes.extend(self._to_nodes(virtual_machine.vm))
            else:
                nodes.append(self._to_node(virtual_machine))
        return nodes

    def _to_node(self, virtual_machine):
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
        ip_addresses = []
        if summary.guest is not None:
            ip_addresses.append(summary.guest.ipAddress)

        overall_status = str(summary.overallStatus)
        public_ips = []
        private_ips = []

        extra = {
            "path": path,
            "operating_system": operating_system,
            "os_type": os_type,
            "memory_MB": memory,
            "cpus": cpus,
            "overallStatus": overall_status,
            "metadata": {}
        }

        if boot_time:
            extra['boot_time'] = boot_time.isoformat()
        if annotation:
            extra['annotation'] = annotation

        for ip_address in ip_addresses:
            try:
                if is_public_subnet(ip_address):
                    public_ips.append(ip_address)
                else:
                    private_ips.append(ip_address)
            except:
                # IPV6 not supported
                pass

        for custom_field in virtual_machine.customValue:
            key_id = custom_field.key
            key = self.find_custom_field_key(key_id)
            extra["metadata"][key] = custom_field.value

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

    def find_custom_field_key(self, key_id):
        """Return custom field key name, provided it's id
        """
        if not hasattr(self, "custom_fields"):
            content = self.connection.RetrieveContent()
            if content.customFieldsManager:
                self.custom_fields = content.customFieldsManager.field
            else:
                self.custom_fields = []
        for k in self.custom_fields:
            if k.key == key_id:
                return k.name
        return None

class VSphereNetwork(object):
    """
    Represents information about a VPC (Virtual Private Cloud) network

    Note: This class is EC2 specific.
    """

    def __init__(self, id, name, extra=None):
        self.id = id
        self.name = name
        self.extra = extra or {}

    def __repr__(self):
        return (('<VSphereNetwork: id=%s, name=%s')
                % (self.id, self.name))