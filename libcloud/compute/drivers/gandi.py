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
Gandi driver for compute
"""
import sys
from datetime import datetime

from libcloud.common.gandi import BaseGandiDriver, GandiException, \
    NetworkInterface, IPAddress, Disk
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation


NODE_STATE_MAP = {
    'running': NodeState.RUNNING,
    'halted': NodeState.TERMINATED,
    'paused': NodeState.TERMINATED,
    'locked': NodeState.TERMINATED,
    'being_created': NodeState.PENDING,
    'invalid': NodeState.UNKNOWN,
    'legally_locked': NodeState.PENDING,
    'deleted': NodeState.TERMINATED
}

NODE_PRICE_HOURLY_USD = 0.02


class GandiNodeDriver(BaseGandiDriver, NodeDriver):
    """
    Gandi node driver

    """
    api_name = 'gandi'
    friendly_name = 'Gandi.net'
    country = 'FR'
    type = Provider.GANDI
    # TODO : which features to enable ?
    features = {}

    def _node_info(self, id):
        try:
            obj = self.connection.request('vm.info', int(id))
            return obj
        except Exception:
            e = sys.exc_info()[1]
            raise GandiException(1003, e)
        return None

    # Generic methods for driver
    def _to_node(self, vm):
        return Node(
            id=vm['id'],
            name=vm['hostname'],
            state=NODE_STATE_MAP.get(
                vm['state'],
                NodeState.UNKNOWN
            ),
            public_ips=vm.get('ips', []),
            private_ips=[],
            driver=self,
            extra={
                'ai_active': vm.get('ai_active'),
                'datacenter_id': vm.get('datacenter_id'),
                'description': vm.get('description')
            }
        )

    def _to_nodes(self, vms):
        return [self._to_node(v) for v in vms]

    def list_nodes(self):
        vms = self.connection.request('vm.list')
        ips = self.connection.request('ip.list')
        for vm in vms:
            vm['ips'] = []
            for ip in ips:
                if vm['ifaces_id'][0] == ip['iface_id']:
                    ip = ip.get('ip', None)
                    if ip:
                        vm['ips'].append(ip)

        nodes = self._to_nodes(vms)
        return nodes

    def reboot_node(self, node):
        op = self.connection.request('vm.reboot', int(node.id))
        self._wait_operation(op['id'])
        vm = self.connection.request('vm.info', int(node.id))
        if vm['state'] == 'running':
            return True
        return False

    def destroy_node(self, node):
        vm = self._node_info(node.id)
        if vm['state'] == 'running':
            # Send vm_stop and wait for accomplish
            op_stop = self.connection.request('vm.stop', int(node.id))
            if not self._wait_operation(op_stop['id']):
                raise GandiException(1010, 'vm.stop failed')
        # Delete
        op = self.connection.request('vm.delete', int(node.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def deploy_node(self, **kwargs):
        raise NotImplementedError(
            'deploy_node not implemented for gandi driver')

    def create_node(self, **kwargs):
        """Create a new Gandi node

        @keyword    name:   String with a name for this new node (required)
        @type       name:   str

        @keyword    image:  OS Image to boot on node. (required)
        @type       image:  L{NodeImage}

        @keyword    location: Which data center to create a node in. If empty,
                              undefined behavoir will be selected. (optional)
        @type       location: L{NodeLocation}

        @keyword    size:   The size of resources allocated to this node.
                            (required)
        @type       size:   L{NodeSize}

        @keyword    login:  user name to create for login on machine (required)
        @type       login: String

        @keyword    password: password for user that'll be created (required)
        @type       password: String

        @keywork    inet_family: version of ip to use, default 4 (optional)
        @type       inet_family: int
        """

        if kwargs.get('login') is None or kwargs.get('password') is None:
            raise GandiException(1020,
                'login and password must be defined for node creation')

        location = kwargs.get('location')
        if location and isinstance(location, NodeLocation):
            dc_id = int(location.id)
        else:
            raise GandiException(1021,
                'location must be a subclass of NodeLocation')

        size = kwargs.get('size')
        if not size and not isinstance(size, NodeSize):
            raise GandiException(1022,
                'size must be a subclass of NodeSize')

        src_disk_id = int(kwargs['image'].id)

        disk_spec = {
            'datacenter_id': dc_id,
            'name': 'disk_%s' % kwargs['name']
            }

        vm_spec = {
            'datacenter_id': dc_id,
            'hostname': kwargs['name'],
            'login': kwargs['login'],
            'password': kwargs['password'],  # TODO : use NodeAuthPassword
            'memory': int(size.ram),
            'cores': int(size.id),
            'bandwidth': int(size.bandwidth),
            'ip_version':  kwargs.get('inet_family', 4),
            }

        # Call create_from helper api. Return 3 operations : disk_create,
        # iface_create,vm_create
        (op_disk, op_iface, op_vm) = self.connection.request(
            'vm.create_from',
            vm_spec, disk_spec, src_disk_id
        )

        # We wait for vm_create to finish
        if self._wait_operation(op_vm['id']):
            # after successful operation, get ip information
            # thru first interface
            node = self._node_info(op_vm['vm_id'])
            ifaces = node.get('ifaces')
            if len(ifaces) > 0:
                ips = ifaces[0].get('ips')
                if len(ips) > 0:
                    node['ip'] = ips[0]['ip']
            return self._to_node(node)

        return None

    def _to_image(self, img):
        return NodeImage(
            id=img['disk_id'],
            name=img['label'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        try:
            if location:
                filtering = {'datacenter_id': int(location.id)}
            else:
                filtering = {}
            images = self.connection.request('image.list', filtering)
            return [self._to_image(i) for i in images]
        except Exception:
            e = sys.exc_info()[1]
            raise GandiException(1011, e)

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name='%s cores' % id,
            ram=size['memory'],
            disk=size['disk'],
            bandwidth=size['bandwidth'],
            price=(self._get_size_price(size_id='1') * id),
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        account = self.connection.request('account.info')
        # Look for available shares, and return a list of share_definition
        available_res = account['resources']['available']

        if available_res['shares'] == 0:
            return None
        else:
            share_def = account['share_definition']
            available_cores = available_res['cores']
            # 0.75 core given when creating a server
            max_core = int(available_cores + 0.75)
            shares = []
            if available_res['servers'] < 1:
                # No server quota, no way
                return shares
            for i in range(1, max_core + 1):
                share = {id: i}
                share_is_available = True
                for k in ['memory', 'disk', 'bandwidth']:
                    if share_def[k] * i > available_res[k]:
                        # We run out for at least one resource inside
                        share_is_available = False
                    else:
                        share[k] = share_def[k] * i
                if share_is_available:
                    nb_core = i
                    shares.append(self._to_size(nb_core, share))
            return shares

    def _to_loc(self, loc):
        return NodeLocation(
            id=loc['id'],
            name=loc['name'],
            country=loc['country'],
            driver=self
        )

    def list_locations(self):
        res = self.connection.request("datacenter.list")
        return [self._to_loc(l) for l in res]

    def _to_iface(self, iface):
        ips = []
        for ip in iface.get('ips', []):
            new_ip = IPAddress(
                ip['id'],
                NODE_STATE_MAP.get(
                    ip['state'],
                    NodeState.UNKNOWN
                ),
                ip['ip'],
                self.connection.driver,
                version=ip.get('version'),
                extra={'reverse': ip['reverse']}
                )
            ips.append(new_ip)
        return NetworkInterface(
            iface['id'],
            NODE_STATE_MAP.get(
                iface['state'],
                NodeState.UNKNOWN
            ),
            mac_address=None,
            driver=self.connection.driver,
            ips=ips,
            node_id=iface.get('vm_id'),
            extra={'bandwidth': iface['bandwidth']},
        )

    def _to_ifaces(self, ifaces):
        return [self._to_iface(i) for i in ifaces]

    def ex_list_interfaces(self):
        """Specific method to list network interfaces"""
        ifaces = self.connection.request('iface.list')
        ips = self.connection.request('ip.list')
        for iface in ifaces:
            iface['ips'] = list(filter(lambda i: i['iface_id'] == iface['id'], ips))
        return self._to_ifaces(ifaces)

    def _to_disk(self, element):
        disk = Disk(
            id=element['id'],
            state=NODE_STATE_MAP.get(
                element['state'],
                NodeState.UNKNOWN
            ),
            name=element['name'],
            driver=self.connection.driver,
            size=element['size'],
            extra={'can_snapshot': element['can_snapshot']}
        )
        return disk

    def _to_disks(self, elements):
        return [self._to_disk(el) for el in elements]

    def ex_list_disks(self):
        """Specific method to list all disk"""
        res = self.connection.request('disk.list', {})
        return self._to_disks(res)

    def ex_node_attach_disk(self, node, disk):
        """Specific method to attach a disk to a node"""
        op = self.connection.request('vm.disk_attach',
            int(node.id), int(disk.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def ex_node_detach_disk(self, node, disk):
        """Specific method to detach a disk from a node"""
        op = self.connection.request('vm.disk_detach',
            int(node.id), int(disk.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def ex_node_attach_interface(self, node, iface):
        """Specific method to attach an interface to a node"""
        op = self.connection.request('vm.iface_attach',
            int(node.id), int(iface.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def ex_node_detach_interface(self, node, iface):
        """Specific method to detach an interface from a node"""
        op = self.connection.request('vm.iface_detach',
            int(node.id), int(iface.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def ex_snapshot_disk(self, disk, name=None):
        """Specific method to make a snapshot of a disk"""
        if not disk.extra.get('can_snapshot'):
            raise GandiException(1021, "Disk %s can't snapshot" % disk.id)
        if not name:
            suffix = datetime.today().strftime("%Y%m%d")
            name = "snap_%s" % (suffix)
        op = self.connection.request('disk.create_from',
            {
                'name': name,
                'type': 'snapshot',
            },
            int(disk.id),
            )
        if self._wait_operation(op['id']):
            return True
        return False

    def ex_update_disk(self, disk, new_size=None, new_name=None):
        """Specific method to update size or name of a disk
        WARNING: if a server is attached it'll be rebooted
        """
        params = {}
        if new_size:
            params.update({'size': new_size})
        if new_name:
            params.update({'name': new_name})
        op = self.connection.request('disk.update',
            int(disk.id),
            params)
        if self._wait_operation(op['id']):
            return True
        return False
