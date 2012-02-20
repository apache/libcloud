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

from libcloud.compute.base import NodeDriver, NodeSize, Node
from libcloud.compute.base import NodeImage, NodeState
from libcloud.compute.types import Provider

try:
    import libvirt
    have_libvirt = True
except ImportError:
    have_libvirt = False


class LibvirtNodeDriver(NodeDriver):
    """
    Libvirt (http://libvirt.org/) node driver.

    Usage: LibvirtNodeDriver(uri='vbox:///session').
    To enable debug mode, set LIBVIR_DEBUG environment variable.
    """

    type = Provider.LIBVIRT

    NODE_STATE_MAP = {
        0: NodeState.TERMINATED,
        1: NodeState.RUNNING,
        2: NodeState.PENDING,
        3: NodeState.TERMINATED, # paused
        4: NodeState.TERMINATED, # shutting down
        5: NodeState.TERMINATED,
        6: NodeState.UNKNOWN, # crashed
        7: NodeState.UNKNOWN, # last
    }

    def __init__(self, uri):
        if not have_libvirt:
            raise RuntimeError('Libvirt driver requires \'libvirt\' Python package')

        self._uri = uri
        self.connection = libvirt.open(uri)

    def list_nodes(self):
       domain_ids = self.connection.listDomainsID()
       domains = [self.connection.lookupByID(id) for id in domain_ids]

       nodes = []
       for domain in domains:
           states = [state for state in domain.state(flags=0) if state != 0]

           if len(states) >= 1:
               state = self.NODE_STATE_MAP[states[0]]
           else:
               state = NodeState.UNKNOWN

           # TODO: Use XML config to get Mac address and then parse ips
           extra = {'uuid': domain.UUIDString(), 'os_type': domain.OSType(),
                    'types': self.connection.getType()}
           node = Node(id=domain.ID(), name=domain.name(), state=state,
                       public_ips=[], private_ips=[], driver=self,
                       extra=extra)
           nodes.append(node)

       return nodes

    def reboot_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.reboot(flags=0) == 0

    def destroy_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.destroy(flags=0) == 0

    def ex_start(self, node):
        """
        Start a stopped node.
        """
        domain = self._get_domain_for_node(node=node)
        return domain.create() == 0

    def ex_shutdown(self, node):
        """
        Shutdown a running node.
        """
        domain = self._get_domain_for_node(node=node)
        return domain.shutdown() == 0

    def ex_suspend(self, node):
        """
        Suspend a running node.
        """
        domain = self._get_domain_for_node(node=node)
        return domain.suspend() == 0

    def ex_resume(self, node):
        """
        Resume a suspended node.
        """
        domain = self._get_domain_for_node(node=node)
        return domain.resume() == 0

    def _get_domain_for_node(self, node):
        domain = self.connection.lookupByID(int(node.id))
        return domain
