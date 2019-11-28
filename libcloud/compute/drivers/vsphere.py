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
VMware vSphere driver supporting vSphere v5.5.

Note: This driver requires pysphere package
(https://pypi.python.org/pypi/pysphere) which can be installed using pip. For
more information, please refer to the official documentation.
"""

import os
import atexit

try:
    import pysphere
    pysphere
except ImportError:
    raise ImportError('Missing "pysphere" dependency. You can install it '
                      'using pip - pip install pysphere')

from pysphere import VIServer
from pysphere.vi_task import VITask
from pysphere.vi_mor import VIMor, MORTypes
from pysphere.resources import VimService_services as VI
from pysphere.vi_virtual_machine import VIVirtualMachine

from libcloud.utils.decorators import wrap_non_libcloud_exceptions
from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.types import LibcloudError
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import NodeLocation
from libcloud.compute.base import NodeImage
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState, Provider
from libcloud.utils.networking import is_public_subnet

__all__ = [
    'VSphereNodeDriver',
    'VSphere_5_5_NodeDriver'
]

DEFAULT_API_VERSION = '5.5'
DEFAULT_CONNECTION_TIMEOUT = 5  # default connection timeout in seconds


class VSphereConnection(ConnectionUserAndKey):
    def __init__(self, user_id, key, secure=True,
                 host=None, port=None, url=None, timeout=None, **kwargs):
        if host and url:
            raise ValueError('host and url arguments are mutually exclusive')

        if host:
            host_or_url = host
        elif url:
            host_or_url = url
        else:
            raise ValueError('Either "host" or "url" argument must be '
                             'provided')

        self.host_or_url = host_or_url
        self.client = None
        super(VSphereConnection, self).__init__(user_id=user_id,
                                                key=key, secure=secure,
                                                host=host, port=port,
                                                url=url, timeout=timeout,
                                                **kwargs)

    def connect(self):
        self.client = VIServer()

        trace_file = os.environ.get('LIBCLOUD_DEBUG', None)

        try:
            self.client.connect(host=self.host_or_url, user=self.user_id,
                                password=self.key,
                                sock_timeout=DEFAULT_CONNECTION_TIMEOUT,
                                trace_file=trace_file)
        except Exception as e:
            message = e.message
            if hasattr(e, 'strerror'):
                message = getattr(e, 'strerror', e.message)

            fault = getattr(e, 'fault', None)

            if fault == 'InvalidLoginFault':
                raise InvalidCredsError(message)
            raise LibcloudError(value=message, driver=self.driver)

        atexit.register(self.disconnect)

    def disconnect(self):
        if not self.client:
            return

        try:
            self.client.disconnect()
        except Exception:
            # Ignore all the disconnect errors
            pass

    def run_client_method(self, method_name, **method_kwargs):
        method = getattr(self.client, method_name, None)
        return method(**method_kwargs)


class VSphereNodeDriver(NodeDriver):
    name = 'VMware vSphere'
    website = 'http://www.vmware.com/products/vsphere/'
    type = Provider.VSPHERE
    connectionCls = VSphereConnection

    NODE_STATE_MAP = {
        'POWERED ON': NodeState.RUNNING,
        'POWERED OFF': NodeState.STOPPED,
        'SUSPENDED': NodeState.SUSPENDED,
        'POWERING ON': NodeState.PENDING,
        'POWERING OFF': NodeState.PENDING,
        'SUSPENDING': NodeState.PENDING,
        'RESETTING': NodeState.PENDING,
        'BLOCKED ON MSG': NodeState.ERROR,
        'REVERTING TO SNAPSHOT': NodeState.PENDING
    }

    def __new__(cls, username, password, secure=True, host=None, port=None,
                url=None, api_version=DEFAULT_API_VERSION, **kwargs):
        if cls is VSphereNodeDriver:
            if api_version == '5.5':
                cls = VSphere_5_5_NodeDriver
            else:
                raise NotImplementedError('Unsupported API version: %s' %
                                          (api_version))
        return super(VSphereNodeDriver, cls).__new__(cls)

    def __init__(self, username, password, secure=True,
                 host=None, port=None, url=None, timeout=None):
        self.url = url
        super(VSphereNodeDriver, self).__init__(key=username, secret=password,
                                                secure=secure, host=host,
                                                port=port, url=url)

    @wrap_non_libcloud_exceptions
    def list_locations(self):
        """
        List available locations.

        In vSphere case, a location represents a datacenter.
        """
        datacenters = self.connection.client.get_datacenters()

        locations = []
        for id, name in datacenters.items():
            location = NodeLocation(id=id, name=name, country=None,
                                    driver=self)
            locations.append(location)

        return locations

    @wrap_non_libcloud_exceptions
    def list_images(self):
        """
        List available images (templates).
        """
        server = self.connection.client

        names = ['name', 'config.uuid', 'config.template']
        properties = server._retrieve_properties_traversal(
            property_names=names,
            from_node=None,
            obj_type=MORTypes.VirtualMachine)

        images = []
        for prop in properties:
            id = None
            name = None
            is_template = False

            for item in prop.PropSet:
                if item.Name == 'config.uuid':
                    id = item.Val
                if item.Name == 'name':
                    name = item.Val
                elif item.Name == 'config.template':
                    is_template = item.Val

            if is_template:
                image = NodeImage(id=id, name=name, driver=self)
                images.append(image)

            return images

    @wrap_non_libcloud_exceptions
    def list_nodes(self):
        vm_paths = self.connection.client.get_registered_vms()
        nodes = self._to_nodes(vm_paths=vm_paths)

        return nodes

    @wrap_non_libcloud_exceptions
    @wrap_non_libcloud_exceptions
    def ex_clone_node(self, node, name, power_on=True, template=False):
        """
        Clone the provided node.

        :param node: Node to clone.
        :type node: :class:`libcloud.compute.base.Node`

        :param name: Name of the new node.
        :type name: ``str``

        :param power_on: Power the new node on after being created.
        :type power_on: ``bool``

        :param template: Specifies whether or not the new virtual machine
                         should be marked as a template.
        :type template: ``bool``

        :return: New node.
        :rtype: :class:`libcloud.compute.base.Node`
        """
        vm = self._get_vm_for_node(node=node)
        new_vm = vm.clone(name=name, power_on=power_on, template=template)
        new_node = self._to_node(vm=new_vm)

        return new_node

    @wrap_non_libcloud_exceptions
    def ex_migrate_node(self, node, resource_pool=None, host=None,
                        priority='default'):
        """
        Migrate provided node to a new host or resource pool.

        :param node: Node to clone.
        :type node: :class:`libcloud.compute.base.Node`

        :param resource_pool: ID of the target resource pool to migrate the
                              node into.
        :type resource_pool: ``str``

        :param host: Target host to migrate the host to.
        :type host: ``str``

        :param priority: Migration task priority. Possible values: default,
                         high, low.
        :type priority: ``str``

        :return: True on success.
        :rtype: ``bool``
        """
        vm = self._get_vm_for_node(node=node)
        vm.migrate(priority=priority, resource_pool=resource_pool, host=host)

        return True

    @wrap_non_libcloud_exceptions
    def reboot_node(self, node):
        vm = self._get_vm_for_node(node=node)
        vm.reset()

        return True

    @wrap_non_libcloud_exceptions
    def destroy_node(self, node, ex_remove_files=True):
        """
        :param ex_remove_files: Remove all the files from the datastore.
        :type ex_remove_files: ``bool``
        """
        ex_remove_files = False
        vm = self._get_vm_for_node(node=node)

        server = self.connection.client

        # Based on code from
        # https://pypi.python.org/pypi/pyxenter
        if ex_remove_files:
            request = VI.Destroy_TaskRequestMsg()

            _this = request.new__this(vm._mor)
            _this.set_attribute_type(vm._mor.get_attribute_type())
            request.set_element__this(_this)

            # pylint: disable=no-member
            ret = server._proxy.Destroy_Task(request)._returnva
            # pylint: enable=no-member
            task = VITask(ret, server)

            # Wait for the task to finish
            status = task.wait_for_state([task.STATE_SUCCESS,
                                          task.STATE_ERROR])

            if status == task.STATE_ERROR:
                raise LibcloudError('Error destroying node: %s' %
                                    (task.get_error_message()))
        else:
            request = VI.UnregisterVMRequestMsg()

            _this = request.new__this(vm._mor)
            _this.set_attribute_type(vm._mor.get_attribute_type())
            request.set_element__this(_this)
            ret = server._proxy.UnregisterVM(request)
            task = VITask(ret, server)

        return True

    @wrap_non_libcloud_exceptions
    def start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        vm = self._get_vm_for_node(node=node)
        vm.power_on()

        return True

    @wrap_non_libcloud_exceptions
    def stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        vm = self._get_vm_for_node(node=node)
        vm.power_off()

        return True

    @wrap_non_libcloud_exceptions
    def ex_start_node(self, node):
        return self.start_node(node=node)

    @wrap_non_libcloud_exceptions
    def ex_stop_node(self, node):
        return self.stop_node(node=node)

    @wrap_non_libcloud_exceptions
    def ex_suspend_node(self, node):
        vm = self._get_vm_for_node(node=node)
        vm.suspend()

        return True

    @wrap_non_libcloud_exceptions
    def ex_get_resource_pools(self):
        """
        Return all the available resource pools.

        :rtype: ``dict``
        """
        result = self.connection.client.get_resource_pools()
        return result

    @wrap_non_libcloud_exceptions
    def ex_get_resource_pool_name(self, node):
        """
        Retrieve resource pool name for the provided node.

        :rtype: ``str``
        """
        vm = self._get_vm_for_node(node=node)
        return vm.get_resource_pool_name()

    @wrap_non_libcloud_exceptions
    def ex_get_hosts(self):
        """
        Return all the available hosts.

        :rtype: ``dict``
        """
        result = self.connection.client.get_hosts()
        return result

    @wrap_non_libcloud_exceptions
    def ex_get_datastores(self):
        """
        Return all the available datastores.

        :rtype: ``dict``
        """
        result = self.connection.client.get_datastores()
        return result

    @wrap_non_libcloud_exceptions
    def ex_get_node_by_path(self, path):
        """
        Retrieve Node object for a VM with a provided path.

        :type path: ``str``
        :rtype: :class:`libcloud.compute.base.Node`
        """
        vm = self.connection.client.get_vm_by_path(path)
        node = self._to_node(vm=vm)
        return node

    def ex_get_node_by_uuid(self, uuid):
        """
        Retrieve Node object for a VM with a provided uuid.

        :type uuid: ``str``
        """
        vm = self._get_vm_for_uuid(uuid=uuid)
        node = self._to_node(vm=vm)
        return node

    @wrap_non_libcloud_exceptions
    def ex_get_server_type(self):
        """
        Return VMware installation type.

        :rtype: ``str``
        """
        return self.connection.client.get_server_type()

    @wrap_non_libcloud_exceptions
    def ex_get_api_version(self):
        """
        Return API version of the vmware provider.

        :rtype: ``str``
        """
        return self.connection.client.get_api_version()

    def _get_vm_for_uuid(self, uuid, datacenter=None):
        """
        Retrieve VM for the provided UUID.

        :type uuid: ``str``
        """
        server = self.connection.client

        dc_list = []
        if datacenter and VIMor.is_mor(datacenter):
            dc_list.append(datacenter)
        else:
            dc = server.get_datacenters()
            if datacenter:
                dc_list = [k for k, v in dc.iteritems() if v == datacenter]
            else:
                dc_list = list(dc.iterkeys())

        for mor_dc in dc_list:
            request = VI.FindByUuidRequestMsg()
            search_index = server._do_service_content.SearchIndex
            mor_search_index = request.new__this(search_index)
            mor_search_index.set_attribute_type(MORTypes.SearchIndex)
            request.set_element__this(mor_search_index)

            mor_datacenter = request.new_datacenter(mor_dc)
            mor_datacenter.set_attribute_type(MORTypes.Datacenter)
            request.set_element_datacenter(mor_datacenter)

            request.set_element_vmSearch(True)
            request.set_element_uuid(uuid)

            try:
                # pylint: disable=no-member
                vm = server._proxy.FindByUuid(request)._returnval
                # pylint: enable=no-member
            except VI.ZSI.FaultException:
                pass
            else:
                if vm:
                    return VIVirtualMachine(server, vm)

            return None

    def _to_nodes(self, vm_paths):
        nodes = []
        for vm_path in vm_paths:
            vm = self.connection.client.get_vm_by_path(vm_path)
            node = self._to_node(vm=vm)
            nodes.append(node)

        return nodes

    def _to_node(self, vm):
        assert(isinstance(vm, VIVirtualMachine))

        properties = vm.get_properties()
        status = vm.get_status()

        uuid = vm.properties.config.uuid
        instance_uuid = vm.properties.config.instanceUuid

        id = uuid
        name = properties['name']
        public_ips = []
        private_ips = []

        state = self.NODE_STATE_MAP.get(status, NodeState.UNKNOWN)
        ip_address = properties.get('ip_address', None)
        net = properties.get('net', [])
        resource_pool_id = str(vm.properties.resourcePool._obj)

        try:
            operating_system = vm.properties.summary.guest.guestFullName,
        except Exception:
            operating_system = 'unknown'

        extra = {
            'uuid': uuid,
            'instance_uuid': instance_uuid,
            'path': properties['path'],
            'resource_pool_id': resource_pool_id,
            'hostname': properties.get('hostname', None),
            'guest_id': properties['guest_id'],
            'devices': properties.get('devices', {}),
            'disks': properties.get('disks', []),
            'net': net,

            'overall_status': vm.properties.overallStatus,
            'operating_system': operating_system,

            'cpus': vm.properties.config.hardware.numCPU,
            'memory_mb': vm.properties.config.hardware.memoryMB
        }

        # Add primary IP
        if ip_address:
            if is_public_subnet(ip_address):
                public_ips.append(ip_address)
            else:
                private_ips.append(ip_address)

        # Add other IP addresses
        for nic in net:
            ip_addresses = nic['ip_addresses']
            for ip_address in ip_addresses:
                try:
                    is_public = is_public_subnet(ip_address)
                except Exception:
                    # TODO: Better support for IPv6
                    is_public = False

                if is_public:
                    public_ips.append(ip_address)
                else:
                    private_ips.append(ip_address)

        # Remove duplicate IPs
        public_ips = list(set(public_ips))
        private_ips = list(set(private_ips))

        node = Node(id=id, name=name, state=state, public_ips=public_ips,
                    private_ips=private_ips, driver=self, extra=extra)
        return node

    def _get_vm_for_node(self, node):
        uuid = node.id
        vm = self._get_vm_for_uuid(uuid=uuid)
        return vm

    def _ex_connection_class_kwargs(self):
        kwargs = {
            'url': self.url
        }

        return kwargs


class VSphere_5_5_NodeDriver(VSphereNodeDriver):
    name = 'VMware vSphere v5.5'
