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

import time
import logging

try:
    from pyVim import connect
    from pyVmomi import vim, vmodl
    from pyVim.task import WaitForTask
except ImportError:
    raise ImportError('Missing "pyvmomi" dependency. You can install it '
                      'using pip - pip install pyvmomi')

import atexit

from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeSize
from libcloud.compute.base import NodeImage, NodeLocation
from libcloud.compute.types import NodeState, Provider
from libcloud.utils.networking import is_public_subnet

logger = logging.getLogger('libcloud.compute.drivers.vsphere')


def recurse_snapshots(snapshot_list):
    ret = []
    for s in snapshot_list:
        ret.append(s)
        ret += recurse_snapshots(getattr(s, 'childSnapshotList', []))
    return ret


def format_snapshots(snapshot_list):
    ret = []
    for s in snapshot_list:
        ret.append({
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'created': s.createTime.strftime('%Y-%m-%d %H:%M'),
            'state': s.state})
    return ret


class VSphereNodeDriver(NodeDriver):
    name = 'VMware vSphere'
    website = 'http://www.vmware.com/products/vsphere/'
    type = Provider.VSPHERE

    NODE_STATE_MAP = {
        'poweredOn': NodeState.RUNNING,
        'poweredOff': NodeState.STOPPED,
        'suspended': NodeState.SUSPENDED,
    }

    def __init__(self, host, username, password, port=443):
        """Initialize a connection by providing a hostname,
        username and password
        """
        self.host = host
        try:
            self.connection = connect.SmartConnect(
                host=host, port=port, user=username, pwd=password
            )
            atexit.register(connect.Disconnect, self.connection)
        except Exception as exc:
            error_message = str(exc).lower()
            if 'incorrect user name' in error_message:
                raise InvalidCredsError('Check your username and '
                                        'password are valid')
            if 'connection refused' in error_message or 'is not a vim server' \
                                                        in error_message:
                raise LibcloudError('Check that the host provided is a '
                                    'vSphere installation')
            if 'name or service not known' in error_message:
                raise LibcloudError(
                    'Check that the vSphere host is accessible')
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

                self.connection = connect.SmartConnect(
                    host=host, port=port, user=username, pwd=password,
                    sslContext=context
                )
                atexit.register(connect.Disconnect, self.connection)
            else:
                raise LibcloudError('Cannot connect to vSphere')

    def list_locations(self):
        """
        Lists locations
        """
        content = self.connection.RetrieveContent()

        potential_locations = [dc for dc in
            content.viewManager.CreateContainerView(
                content.rootFolder,
                [vim.ClusterComputeResource, vim.HostSystem],
                recursive=True
            ).view
        ]

        # Add hosts and clusters with DRS enabled
        locations = []
        for location in potential_locations:
            if isinstance(location, vim.HostSystem):
                locations.append(self._to_location(location))
            elif isinstance(location, vim.ClusterComputeResource):
                if location.configuration.drsConfig.enabled:
                    locations.append(self._to_location(location))

        return locations

    def _to_location(self, data):
        try:
            if isinstance(data, vim.HostSystem):
                extra = {
                    "type": "host",
                    "state": data.runtime.connectionState,
                    "hypervisor": data.config.product.fullName,
                    "vendor": data.hardware.systemInfo.vendor,
                    "model": data.hardware.systemInfo.model,
                    "ram": data.hardware.memorySize,
                    "cpu": {
                        "packages": data.hardware.cpuInfo.numCpuPackages,
                        "cores": data.hardware.cpuInfo.numCpuCores,
                        "threads": data.hardware.cpuInfo.numCpuThreads,
                    },
                    "uptime": data.summary.quickStats.uptime,
                    "parent": str(data.parent)
                }
            elif isinstance(data, vim.ClusterComputeResource):
                extra = {
                    "type": "cluster",
                    "overallStatus": data.overallStatus,
                    "drs": data.configuration.drsConfig.enabled,
                    'hosts': [host.name for host in data.host],
                    'parent': str(data.parent)
                }
        except AttributeError as exc:
            logger.error('Cannot convert location %s: %r' % (data.name, exc))
            extra = {}

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

    def list_sizes(self):
        """
        Returns sizes
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


    def _collect_properties(self, content, view_ref, obj_type, path_set=None,
                            include_mors=False):
        """
        Collect properties for managed objects from a view ref
        Check the vSphere API documentation for example on retrieving
        object properties:
            - http://goo.gl/erbFDz
        Args:
            content     (ServiceInstance): ServiceInstance content
            view_ref (pyVmomi.vim.view.*): Starting point of inventory navigation
            obj_type      (pyVmomi.vim.*): Type of managed object
            path_set               (list): List of properties to retrieve
            include_mors           (bool): If True include the managed objects
                                        refs in the result
        Returns:
            A list of properties for the managed objects
        """
        collector = content.propertyCollector

        # Create object specification to define the starting point of
        # inventory navigation
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True

        # Create a traversal specification to identify the path for collection
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]

        # Identify the properties to the retrieved
        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = obj_type

        if not path_set:
            property_spec.all = True

        property_spec.pathSet = path_set

        # Add the object and property specification to the
        # property filter specification
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]

        # Retrieve properties
        props = collector.RetrieveContents([filter_spec])

        data = []
        for obj in props:
            properties = {}
            for prop in obj.propSet:
                properties[prop.name] = prop.val

            if include_mors:
                properties['obj'] = obj.obj

            data.append(properties)
        return data

    def list_nodes(self, enhance=True, max_properties=20):
        """
        List nodes, excluding templates
        """
        nodes = []
        vm_properties = [
            'config.template',
            'summary.config.name', 'summary.config.vmPathName',
            'summary.config.memorySizeMB', 'summary.config.numCpu',
            'summary.storage.committed', 'summary.config.guestFullName',
            'summary.runtime.host', 'summary.config.instanceUuid',
            'summary.config.annotation', 'summary.runtime.powerState',
            'summary.runtime.bootTime', 'summary.guest.ipAddress',
            'summary.overallStatus', 'customValue', 'snapshot'
        ]
        content = self.connection.RetrieveContent()
        view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True)
        i = 0
        vm_dict = {}
        while i < len(vm_properties):
            vm_list = self._collect_properties(content, view,
                                               vim.VirtualMachine,
                                               path_set=vm_properties[
                                                   i:i+max_properties],
                                               include_mors=True)
            i += max_properties
            for vm in vm_list:
                if not vm_dict.get(vm['obj']):
                    vm_dict[vm['obj']] = vm
                else:
                    vm_dict[vm['obj']].update(vm)

        vm_list = [vm_dict[k] for k in vm_dict]

        nodes.extend(self._to_nodes(vm_list))
        if enhance:
            nodes = self._enhance_metadata(nodes, content)

        return nodes

    def list_nodes_recursive(self, enhance=True):
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
                nodes.extend(self._to_nodes_recursive(vm_list))

        if enhance:
            nodes = self._enhance_metadata(nodes, content)

        return nodes

    def _enhance_metadata(self, nodes, content):
        nodemap = {}
        for node in nodes:
            node.extra['vSphere version'] = content.about.version
            nodemap[node.id] = node

        # Get VM deployment events to extract creation dates & images
        filter_spec = vim.event.EventFilterSpec(
            eventTypeId=['VmBeingDeployedEvent']
        )
        deploy_events = content.eventManager.QueryEvent(filter_spec)
        for event in deploy_events:
            try:
                uuid = event.vm.vm.config.instanceUuid
            except Exception:
                continue
            if uuid in nodemap:
                node = nodemap[uuid]
                try:  # Get source template as image
                    source_template_vm = event.srcTemplate.vm
                    image_id = source_template_vm.config.instanceUuid
                    node.extra['image_id'] = image_id
                except Exception:
                    logger.error('Cannot get instanceUuid from source template')
                try:  # Get creation date
                    node.created_at = event.createdTime
                except AttributeError:
                    logger.error('Cannot get creation date from VM deploy event')

        return nodes

    def _to_nodes(self, vm_list):
        nodes = []
        for vm in vm_list:
            if vm.get('config.template'):
                continue  # Do not include templates in node list
            nodes.append(self._to_node(vm))
        return nodes

    def _to_nodes_recursive(self, vm_list):
        nodes = []
        for virtual_machine in vm_list:
            if hasattr(virtual_machine, 'childEntity'):
                # If this is a group it will have children.
                # If it does, recurse into them and then return
                nodes.extend(self._to_nodes_recursive(virtual_machine.childEntity))
            elif isinstance(virtual_machine, vim.VirtualApp):
                # If this is a vApp, it likely contains child VMs
                # (vApps can nest vApps, but it is hardly
                # a common usecase, so ignore that)
                nodes.extend(self._to_nodes_recursive(virtual_machine.vm))
            else:
                if not hasattr(virtual_machine, 'config') or \
                    (virtual_machine.config and \
                     virtual_machine.config.template):
                    continue # Do not include templates in node list
                nodes.append(self._to_node_recursive(virtual_machine))
        return nodes

    def _to_node(self, vm):
        name = vm.get('summary.config.name')
        path = vm.get('summary.config.vmPathName')
        memory = vm.get('summary.config.memorySizeMB')
        cpus = vm.get('summary.config.numCpu')
        disk = vm.get('summary.storage.committed', 0)/(1024*1024*1024)
        size = ''
        if cpus:
            size = '%dvCPU' % cpus
            if memory:
                size += ', %dMB RAM' % memory
            if disk:
                size += ', %dGB disk' % disk

        operating_system = vm.get('summary.config.guestFullName')
        host = vm.get('summary.runtime.host')

        os_type = 'unix'
        if 'Microsoft' in str(operating_system):
            os_type = 'windows'

        uuid = vm.get('summary.config.instanceUuid')
        annotation = vm.get('summary.config.annotation')
        state = vm.get('summary.runtime.powerState')
        status = self.NODE_STATE_MAP.get(state, NodeState.UNKNOWN)
        boot_time = vm.get('summary.runtime.bootTime')

        ip_addresses = []
        if vm.get('summary.guest.ipAddress'):
            ip_addresses.append(vm.get('summary.guest.ipAddress'))

        overall_status = str(vm.get('summary.overallStatus'))
        public_ips = []
        private_ips = []

        extra = {
            'path': path,
            'operating_system': operating_system,
            'os_type': os_type,
            'memory_MB': memory,
            'cpus': cpus,
            'overall_status': overall_status,
            'metadata': {},
            'snapshots': []
        }

        if disk:
            extra['disk'] = disk

        if host:
            extra['host'] = host.name
            parent = host.parent
            while parent:
                if isinstance(parent, vim.ClusterComputeResource):
                    extra['cluster'] = parent.name
                    break
                parent = parent.parent

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
        if vm.get('snapshot'):
            extra['snapshots'] = format_snapshots(
                recurse_snapshots(vm.get('snapshot').rootSnapshotList))

        for custom_field in vm.get('customValue', []):
            key_id = custom_field.key
            key = self.find_custom_field_key(key_id)
            extra['metadata'][key] = custom_field.value

        node = Node(id=uuid, name=name, state=status, size=size,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, extra=extra)
        node._uuid = uuid
        return node

    def _to_node_recursive(self, virtual_machine):
        summary = virtual_machine.summary
        name = summary.config.name
        path = summary.config.vmPathName
        memory = summary.config.memorySizeMB
        cpus = summary.config.numCpu
        size = disk = ''
        if cpus:
            size = "%dvCPU" % cpus
            if memory:
                size += ", %dMB RAM" % memory
            if summary.storage:
                disk = summary.storage.committed/(1024*1024*1024)
                size += ", %dGB disk" % disk

        operating_system = summary.config.guestFullName
        host = summary.runtime.host

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
            "metadata": {},
            "snapshots": []
        }

        if disk:
            extra['disk'] = disk

        if host:
            extra['host'] = host.name
            parent = host.parent
            while parent:
                if isinstance(parent, vim.ClusterComputeResource):
                    extra['cluster'] = parent.name
                    break
                parent = parent.parent

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
        if virtual_machine.snapshot:
            snapshots = [{
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'created': s.createTime.strftime('%Y-%m-%d %H:%M'),
                'state': s.state,
                } for s in virtual_machine.snapshot.rootSnapshotList]
            extra['snapshots'] = snapshots

        for custom_field in virtual_machine.customValue:
            key_id = custom_field.key
            key = self.find_custom_field_key(key_id)
            extra["metadata"][key] = custom_field.value

        node = Node(id=uuid, name=name, state=status, size=size,
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, extra=extra)
        node._uuid = uuid
        return node

    def reboot_node(self, node):
        """
        """
        vm = self.find_by_uuid(node.id)
        return self.wait_for_task(vm.RebootGuest())

    def destroy_node(self, node):
        """
        """
        vm = self.find_by_uuid(node.id)
        if node.state != NodeState.STOPPED:
            self.ex_stop_node(node)
        return self.wait_for_task(vm.Destroy())

    def ex_stop_node(self, node):
        """
        """
        vm = self.find_by_uuid(node.id)
        return self.wait_for_task(vm.PowerOff())

    def ex_start_node(self, node):
        """
        """
        vm = self.find_by_uuid(node.id)
        return self.wait_for_task(vm.PowerOn())

    def ex_list_snapshots(self, node):
        """
        List node snapshots
        """
        vm = self.find_by_uuid(node.id)
        if not vm.snapshot:
            return []
        return format_snapshots(
            recurse_snapshots(vm.snapshot.rootSnapshotList))

    def ex_create_snapshot(self, node, snapshot_name, description='',
                           dump_memory=False, quiesce=False):
        """
        Create node snapshot
        """
        vm = self.find_by_uuid(node.id)
        return WaitForTask(
            vm.CreateSnapshot(snapshot_name, description, dump_memory, quiesce)
        )

    def ex_remove_snapshot(self, node, snapshot_name=None, remove_children=True):
        """
        Remove a snapshot from node.
        If snapshot_name is not defined remove the last one.
        """
        vm = self.find_by_uuid(node.id)
        if not vm.snapshot:
            raise LibcloudError(
                "Remove snapshot failed. No snapshots for node %s" % node.name)
        snapshots = recurse_snapshots(vm.snapshot.rootSnapshotList)
        if not snapshot_name:
            snapshot = snapshots[-1].snapshot
        else:
            for s in snapshots:
                if snapshot_name == s.name:
                    snapshot = s.snapshot
                    break
            else:
                raise LibcloudError("Snapshot `%s` not found" % snapshot_name)
        return self.wait_for_task(snapshot.RemoveSnapshot_Task(
            removeChildren=remove_children))

    def ex_revert_to_snapshot(self, node, snapshot_name=None):
        """
        Revert node to a specific snapshot.
        If snapshot_name is not defined revert to the last one.
        """
        vm = self.find_by_uuid(node.id)
        if not vm.snapshot:
            raise LibcloudError("Revert failed. No snapshots for node %s" % node.name)
        snapshots = recurse_snapshots(vm.snapshot.rootSnapshotList)
        if not snapshot_name:
            snapshot = snapshots[-1].snapshot
        else:
            for s in snapshots:
                if snapshot_name == s.name:
                    snapshot = s.snapshot
                    break
            else:
                raise LibcloudError("Snapshot `%s` not found" % snapshot_name)
        return self.wait_for_task(snapshot.RevertToSnapshot_Task())

    def find_by_uuid(self, node_uuid):
        """Searches VMs for a given uuid
        returns pyVmomi.VmomiSupport.vim.VirtualMachine
        """
        vm = self.connection.content.searchIndex.FindByUuid(None, node_uuid,
                                                            True, True)
        if not vm:
            raise LibcloudError("Unable to locate VirtualMachine.")
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

    def get_obj(self, vimtype, name):
        """
        Return an object by name, if name is None the
        first found object is returned
        """
        obj = None
        content = self.connection.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, vimtype, True)
        for c in container.view:
            if name:
                if c.name == name:
                    obj = c
                    break
            else:
                obj = c
                break

        return obj

    def wait_for_task(self, task, timeout=1800, interval=10):
        """ wait for a vCenter task to finish """
        start_time = time.time()
        task_done = False
        while not task_done:
            if (time.time() - start_time >= timeout):
                raise LibcloudError('Timeout while waiting '
                                    'for import task Id %s'
                                    % task.info.id)
            if task.info.state == 'success':
                if task.info.result and str(task.info.result) != 'success':
                    return task.info.result
                return True

            if task.info.state == 'error':
                raise LibcloudError(task.info.error.msg)
            time.sleep(interval)

    def create_node(self, **kwargs):
        """
        Creates and returns node.

        :keyword    ex_network: Name of a "Network" to connect the VM to ",
        :type       ex_network: ``str``

        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        network = kwargs.get('ex_network')

        template = self.find_by_uuid(image.id)

        cluster_name = kwargs.get('cluster') or kwargs.get('location')
        cluster = self.get_obj([vim.ClusterComputeResource], cluster_name)
        if not cluster:  # Get the first available cluster
            cluster = self.get_obj([vim.ClusterComputeResource], '')

        datacenter = None
        if not kwargs.get('datacenter'):  # Get datacenter from cluster
            parent = cluster.parent
            while parent:
                if isinstance(parent, vim.Datacenter):
                    datacenter = parent
                    break
                parent = parent.parent

        if kwargs.get('datacenter') or datacenter is None:
            datacenter = self.get_obj([vim.Datacenter],
                                      kwargs.get('datacenter'))

        if kwargs.get('folder'):
            folder = self.get_obj([vim.Folder], kwargs.get('folder'))
        else:
            folder = datacenter.vmFolder

        if kwargs.get('resource_pool'):
            resource_pool = self.get_obj([vim.ResourcePool],
                                         kwargs.get('resource_pool'))
        else:
            resource_pool = cluster.resourcePool

        if kwargs.get('datastore'):
            datastore = self.get_obj([vim.Datastore], kwargs.get('datastore'))
        else:
            datastore = self.get_obj([vim.Datastore], template.datastore[0].info.name)

        devices = []

        if network:
            nicspec = vim.vm.device.VirtualDeviceSpec()
            nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            nicspec.device = vim.vm.device.VirtualVmxnet3()
            nicspec.device.wakeOnLanEnabled = True
            nicspec.device.deviceInfo = vim.Description()

            portgroup = self.get_obj([vim.dvs.DistributedVirtualPortgroup], network)
            if portgroup:
                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = portgroup.key
                dvs_port_connection.switchUuid = portgroup.config.distributedVirtualSwitch.uuid
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nicspec.device.backing.port = dvs_port_connection
            else:
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicspec.device.backing.network = self.get_obj([vim.Network], network)
                nicspec.device.backing.deviceName = network
            nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nicspec.device.connectable.startConnected = True
            nicspec.device.connectable.connected = True
            nicspec.device.connectable.allowGuestControl = True
            devices.append(nicspec)

        # new_disk_kb = int(size.disk) * 1024 * 1024
        # disk_spec = vim.vm.device.VirtualDeviceSpec()
        # disk_spec.fileOperation = "create"
        # disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        # disk_spec.device = vim.vm.device.VirtualDisk()
        # disk_spec.device.backing = \
        #     vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        # if size.extra.get('disk_type') == 'thin':
        #     disk_spec.device.backing.thinProvisioned = True
        # disk_spec.device.backing.diskMode = 'persistent'
        # disk_spec.device.capacityInKB = new_disk_kb
        # disk_spec.device.controllerKey = controller.key
        # devices.append(disk_spec)

        vmconf = vim.vm.ConfigSpec(
            numCPUs=int(size.extra.get('cpu', 1)),
            memoryMB=int(size.ram),
            deviceChange=devices
        )

        if kwargs.get('datastore_cluster'):
            podsel = vim.storageDrs.PodSelectionSpec()
            pod = self.get_obj([vim.StoragePod], kwargs.get('datastore_cluster'))
            podsel.storagePod = pod
            storagespec = vim.storageDrs.StoragePlacementSpec()
            storagespec.podSelectionSpec = podsel
            storagespec.type = 'create'
            storagespec.folder = folder
            storagespec.resourcePool = resource_pool
            storagespec.configSpec = vmconf

            try:
                content = self.connection.RetrieveContent()
                rec = content.storageResourceManager.RecommendDatastores(
                    storageSpec=storagespec)
                rec_action = rec.recommendations[0].action[0]
                real_datastore_name = rec_action.destination.name
            except:
                real_datastore_name = template.datastore[0].info.name

            datastore = self.get_obj([vim.Datastore], real_datastore_name)

        clonespec = vim.vm.CloneSpec(config=vmconf)
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = resource_pool
        if 'location' in kwargs:
            location = kwargs.get('location')
            host = self.get_obj([vim.HostSystem], location.name)
            if host:
                relospec.host = host
        clonespec.location = relospec
        clonespec.powerOn = True

        task = template.Clone(
            folder=folder,
            name=name,
            spec=clonespec
        )

        return self._to_node_recursive(self.wait_for_task(task))

    def ex_connect_network(self, vm, network_name):
        spec = vim.vm.ConfigSpec()

        # add Switch here
        dev_changes = []
        network_spec = vim.vm.device.VirtualDeviceSpec()
        # network_spec.fileOperation = "create"
        network_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        network_spec.device = vim.vm.device.VirtualVmxnet3()

        network_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()

        network_spec.device.backing.useAutoDetect = False
        network_spec.device.backing.network = self.get_obj([vim.Network], network_name)

        network_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        network_spec.device.connectable.startConnected = True
        network_spec.device.connectable.connected = True
        network_spec.device.connectable.allowGuestControl = True

        dev_changes.append(network_spec)

        spec.deviceChange = dev_changes
        output = vm.ReconfigVM_Task(spec=spec)
        print(output.info)

    def ex_open_console(self, vm_uuid, console_port = '9443'):
        import OpenSSL
        import ssl
        content = self.connection.RetrieveContent()
        server_guid = content.about.instanceUuid
        search_index = content.searchIndex
        vm = search_index.FindByUuid(None, vm_uuid, True, True)
        vcenter_data = content.setting
        vm_moid = vm._moId
        vcenter_settings = vcenter_data.setting
        vcenter_fqdn = self.host

        for item in vcenter_settings:
            key = getattr(item, 'key')
            if key == 'VirtualCenter.FQDN':
                vcenter_fqdn = getattr(item, 'value')


        session_manager = content.sessionManager
        session = session_manager.AcquireCloneTicket()
        vc_cert = ssl.get_server_certificate((vcenter_fqdn, 443))
        vc_pem = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                 vc_cert)
        vc_fingerprint = vc_pem.digest('sha1')

        uri = "https://%s:%s/vsphere-client/webconsole.html?vmId=%s"\
              "&vmName=%s&serverGuid=%s&host=%s:443&sessionTicket=%s"\
              "&thumbprint=%s" % (vcenter_fqdn, console_port, str(vm_moid),
                                  vm.name, server_guid, vcenter_fqdn, session,
                                  vc_fingerprint)
        return uri

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
