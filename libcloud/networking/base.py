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
Provides base classes for working with networking APIs.
"""

from libcloud.common.base import BaseDriver
from libcloud.common.base import ConnectionUserAndKey

__all__ = [
    'Network',
    'Subnet',
    'NetworkGateway',
    'FloatingIP',
    'Port',
    'NetworkingDriver'
]


class FloatingIP(object):
    """
    Represents a public IP address that may be bound to an interface (usually
    an instance).
    """

    def __init__(self, id, floating_ip_address, fixed_ip_address=None,
                 network_id=None, port_id=None, extra=None, driver=None):
        self.id = id
        self.floating_ip_address = floating_ip_address
        self.fixed_ip_address = fixed_ip_address
        self.network_id = network_id
        self.port_id = port_id
        self.extra = extra or {}
        self.driver = driver

    def get_port(self):
        return self.driver.get_port(port_id=self.port_id)

    def __repr__(self):
        return (('<FloatingIP id=%s, floating_ip_address=%s, network_id=%s>' %
                 (self.id, self.floating_ip_address, self.network_id)))


class Port(object):
    """
    Represents a single port on a network. A port is an attachment point for IP
    addresses.
    """

    def __init__(self, id=None, name=None, mac_address=None, ip_addresses=None,
                 attached_device_id=None, driver=None):
        """
        :param id: Port id (must be unique).
        :type id: ``str``

        :param name: Port name.
        :type name: ``str``

        :param mac_address: MAC address associated with this network port
        :type mac_address: ``str``

        :param ip_addresses: IP addresses associated with this port
        :type ip_addresses: ``list`` of ''str''

        :param attached_device_id: Identifier associated with attached device
                                   (instance or router).
        :type attached_device_id: ``str``

        """
        self.id = id
        self.name = name
        self.mac_address = mac_address
        self.ip_addresses = ip_addresses or []
        self.attached_device_id = attached_device_id
        self.driver = driver

    def iterate_ip_addresses(self):
        """
        Generator which iterates over all ip addresses associated with the port
        """
        for ip_address in self.ip_addresses:
            yield ip_address

    def __repr__(self):
        return (('<Port id=%s, name=%s, attached_device_id=%s>' %
                 (self.id, self.name, self.attached_device_id)))


class Subnet(object):
    """
    Represents a range of contiguous IP address space assigned to a network.
    """

    def __init__(self, id=None, name=None, ip_version=None, cidr=None,
                 extra=None, driver=None):
        """
        :param id: Subnet id (must be unique).
        :type id: ``str``

        :param id: IP Version (4 or 6)
        :type id: ``int``

        :param cidr: Address range in CIDR format #.#.#.#/## or  #:#:#::/##
        :type cidr: ``str``

        :param extra: Extra attributes.
        :type extra: ``dict``
        """
        self.id = None if id is None else str(id)
        self.name = name
        self.ip_version = 4 if ip_version is None else int(ip_version)
        self.cidr = cidr
        self.extra = extra or {}
        self.driver = driver

    def delete(self):
        """
        Delete this subnet.
        """
        self.driver.delete_subnet(subnet=self)

    def __repr__(self):
        return ('<Subnet id=%s ip_version=%d cidr=%s>' %
                (self.id, self.ip_version, self.cidr))


class NetworkGateway(object):
    """
    Represents a network gateway
    """

    def __init__(self, id, name, state, network_id=None, driver=None):
        self.id = id
        self.name = name
        self.state = state
        self.network_id = network_id
        self.driver = driver

    def __repr__(self):
        return (('<NetworkGateway id=%s, name=%s, state=%s>' %
                 (self.id, self.name, self.state)))


class Network(object):
    """
    Represents a virtual network
    """

    def __init__(self, id=None, name=None, extra=None, driver=None):
        """
        :param id: Network unique id
        :type id: ``str``

        :param name: Network name
        :type name: ``str``

        :param extra: Extra attributes.
        :type extra: ``dict``

        :param driver: NetworkDriver instance.
        :type driver: :class:`NetworkDriver`
        """
        self.id = None if id is None else str(id)
        self.name = name
        self.extra = extra or {}
        self.driver = driver

    def list_subnets(self):
        return self.driver.list_network_subnets(network=self)

    def iterate_subnets(self):
        return self.driver.iterate_network_subnets(network=self)

    def create_subnet(self, subnet):
        """
        Create subnet on this existing Network.

        :param subnets: List of subnets to create and attach to network
        :type subnets: ``list`` of :class:`Subnet`

        :return: Created subnet instance.
        :rtype: :class:`.Subnet`
        """
        return self.driver.create_network_subnet(network=self,
                                                 subnet=subnet)

    def delete(self):
        """
        Delete this network. All associated subnets will also be deleted.
        """
        self.driver.delete_network(self)

    def __repr__(self):
        return '<Network id=%s name=%s>' % (self.id, self.name)


class NetworkingDriver(BaseDriver):
    """
    A base driver to derive from.
    """

    connectionCls = ConnectionUserAndKey
    name = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 **kwargs):
        super(NetworkingDriver, self).__init__(key=key, secret=secret,
                                               secure=secure, host=host,
                                               port=port, **kwargs)

    def list_networks(self):
        """
        Return a list of networks.

        :return: A list of Network instances.
        :rtype: ``list`` of :class:`Network`
        """
        return list(self.iterate_networks())

    def iterate_networks(self):
        """
        Return a generator of networks for the given account

        :return: A generator of Network instances.
        :rtype: ``generator`` of :class:`Network`
        """
        raise NotImplementedError(
            'iterate_networks not implemented for this driver')

    def create_network(self, network, subnet=None):
        """
        Create a new network with optional subnets.

        :param network: Network object with at least 'name' filled in
        :type network: :class:`Network`

        :param subnet: Optional subnet to create and attach to
                       network.
        :type subnet: :class:`.Subnet`

        :return: The created Network object
        :rtype: :class:`Network`
        """
        raise NotImplementedError(
            'create_network not implemented for this driver')

    def delete_network(self, network):
        """
        Delete an existing network

        :param network: Existing Network object with at least 'id' filled in
        :type network: :class:`Network`
        """
        raise NotImplementedError(
            'delete_network not implemented for this driver')

    def list_network_subnets(self, network):
        """
        Return a list of subnets for the given network.

        :param network: Existing Network object to operate on
        :type network: :class:`Network`

        :return: A list of Subnet instances.
        :rtype: ``list`` of :class:`Subnet`
        """
        return list(self.iterate_network_subnets(network=network))

    def iterate_network_subnets(self, network):
        """
        Return a generator of subnets for the given network

        :param network: Existing Network object to operate on
        :type network: :class:`Network`

        :return: A generator of Subnet instances.
        :rtype: ``generator`` of :class:`Subnet`
        """
        raise NotImplementedError(
            'iterate_network_subnets not implemented for this driver')

    def create_network_subnet(self, network, subnet):
        """
        Create subnet on an existing Network,

        :param network: Existing Network object to operate on
        :type network: :class:`Network`

        :param subnet: Subnet to create and attach to network
        :type subnet: class:`.Subnet`

        :return: A list of the created Subnet instances
        :rtype: ``list`` of :class:`Subnet`
        """
        raise NotImplementedError(
            'create_network_subnet not implemented for this driver')

    def delete_subnet(self, subnet):
        """
        Delete an existing subnet

        :param network: Existing Subnet object with at least 'id' filled in
        :type network: :class:`Subnet`
        """
        raise NotImplementedError(
            'delete_network not implemented for this driver')

    def list_network_gateways(self):
        """
        List all the network gateways for this account.

        :return: Network gateways for this account.
        :rtype: ``list`` of :class:`.NetworkGateway`
        """

        return list(self.iterate_network_gateways())

    def iterate_network_gateways(self):
        """
        Return a generator of network gateways for this account.

        :return: A generator of NetworkGateway instances.
        :rtype: ``generator`` of :class:`NetworkGateway`
        """
        raise NotImplementedError(
            'iterate_network_gateways not implemented for this driver')

    def list_floating_ips(self):
        """
        Return all the available floating ips.

        :rtype: ``list`` of :class:`.FloatingIP`
        """
        return list(self.iterate_floating_ips())

    def iterate_floating_ips(self):
        """
        Return a generator of floating ips.

        :return: A generator of FloatingIP instances.
        :rtype: ``generator`` of :class:`.FloatingIP`
        """
        raise NotImplementedError(
            'iterate_floating_ips not implemented for this driver')

    def create_floating_ip(self, network):
        """
        Create a new floating IP address.

        :param network: Network to create the floating IP in.
        :type network: :class:`.Network`

        :rtype: :class:`FloatingIP`
        :return: Created FloatingIP instance.
        """
        raise NotImplementedError(
            'create_floating_ip not implemented for this driver')

    def delete_floating_ip(self, floating_ip):
        """
        Delete a provided floating IP address.

        :param floating_ip: Floating IP to delete.
        :type floating_ip: :class:`FloatingIP`

        :return: ``True`` on success.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'delete_floating_ip not implemented for this driver')

    def attach_floating_ip_to_node(self, node, floating_ip):
        """
        Attach floating IP address to the compute node.

        :param node: Node to attach the IP to.
        :type node: :class:`libcloud.compute.base.Node`

        :param floating_ip: Floating IP to attach.
        :type floating_ip: :class:`.FloatingIP`

        :return: ``True`` on success.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'attach_floating_ip_to_node not implemented for this driver')

    def detatch_floating_ip_from_node(self, node, floating_ip):
        """
        Detach floating IP address from a compute node.

        :param node: Node to detach the IP from.
        :type node: :class:`libcloud.compute.base.Node`

        :param floating_ip: Floating IP to detach.
        :type floating_ip: :class:`.FloatingIP`

        :return: ``True`` on success.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'detatch_floating_ip_from_node not implemented for this driver')

    def list_ports(self):
        """
        List ports for this account.

        :rtype: ``list`` of :class:`.Port`
        """
        return list(self.iterate_ports())

    def iterate_ports(self):
        """
        Return a generator of ports for this account.

        :return: A generator of Port instances.
        :rtype: ``generator`` of :class:`.Port`
        """
        raise NotImplementedError(
            'iterate_ports not implemented for this driver')

    def get_port(self, port_id):
        """
        Retrieve a port by the ID.

        :param port_id: Port ID.
        :type port_id: ``str``

        :return: Port instance.
        :rtype: :class:`.Port`
        """
        raise NotImplementedError(
            'get_port not implemented for this driver')
