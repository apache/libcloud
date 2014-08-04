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

try:
    import simplejson as json  # pylint: disable=import-error
except ImportError:
    import json

from libcloud.utils.py3 import httplib

from libcloud.networking.types import Provider
from libcloud.networking.base import NetworkingDriver, Network, Subnet
from libcloud.networking.base import Port, FloatingIP, NetworkGateway

from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.openstack import OpenStackDriverMixin
from libcloud.common.openstack import OpenStackResponse

from libcloud.utils.networking import join_ipv4_segments
from libcloud.utils.networking import increment_ipv4_segments

__all__ = [
    'OpenStackFloatingIP',

    'OpenStackNovaNetworkingDriver',
    'OpenStackNeutronNetworkingDriver',
    'OpenStackQuantumNetworkingDriver'
]

DEFAULT_NOVA_NETWORKING_API_PATH = '/os-networks'


class OpenStackFloatingIP(FloatingIP):
    """
    OpenStack Specific Floating IP additions
    """

    def __init__(self, id, floating_ip_address, fixed_ip_address=None,
                 network_id=None, port_id=None, router_id=None, tenant_id=None,
                 extra=None, driver=None):
        super(OpenStackFloatingIP, self).__init__(
            id=id,
            floating_ip_address=floating_ip_address,
            fixed_ip_address=fixed_ip_address,
            network_id=network_id,
            port_id=port_id,
            extra=extra,
            driver=driver)
        self.router_id = router_id
        self.tenant_id = tenant_id


class OpenStackSubnet(Subnet):
    """
    OpenStack Specific Subnet additions
    """

    class AllocationPool(object):
        """
        An allocation pool has a start and end IP address
        """
        def __init__(self, start_ip, end_ip):
            self.start_ip = start_ip
            self.end_ip = end_ip

        def iterate_ip_addresses(self):
            """
            Generator for all ip addresses in the pool
            """
            current_segs = [int(seg) for seg in self.start_ip.split('.', 3)]
            end_segs = [int(seg) for seg in self.end_ip.split('.', 3)]

            current_ip_addresses = join_ipv4_segments(current_segs)
            end_ip_addresses = join_ipv4_segments(end_segs)

            while current_ip_addresses != end_ip_addresses:
                ip_addresses = join_ipv4_segments(current_segs)
                yield ip_addresses
                current_segs = increment_ipv4_segments(current_segs)

    def __init__(self, id=None, name=None, ip_version=None, cidr=None,
                 extra=None, driver=None, allocation_pools=None):
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
        super(OpenStackSubnet, self).__init__(id=id, name=name,
                                              ip_version=ip_version,
                                              cidr=cidr,
                                              extra=extra,
                                              driver=driver)
        self.allocation_pools = allocation_pools or []

    def iterate_allocation_pools(self):
        for pool in self.allocation_pools:
            yield pool


class OpenStackNetwork(Network):
    """
    OpenStack Specific Network additions

    Example:
             {
              "status": "ACTIVE",
              "subnets": ["7c3dff86-c469-41af-8c17-532f0c91fad2"],
              "name": "public",
              "router:external": true,
              "tenant_id": "e20690e421764c1280162e9cd7c90f31",
              "admin_state_up": true,
              "shared": false,
              "id": "06d3bdeb-5028-43e6-9aa8-eb2af3f7ca3a"
             }
    """

    def ex_get_subnet_ids(self):
        """
        Retrieve ID values for subnets associated with this network
        """
        return self.extra.get('subnets', [])


class OpenStackQuantumResponse(OpenStackResponse):
    def __init__(self, *args, **kwargs):
        # done because of a circular reference from
        # NodeDriver -> Connection -> Response
        self.node_driver = OpenStackQuantumNetworkingDriver
        super(OpenStackQuantumResponse, self).__init__(*args, **kwargs)

    def parse_error(self):
        """
        Parse a Quantum error response. Looks like:

        {"QuantumError": "Invalid input for cidr.
        Reason: '10.2.0.0.123/24' is not a valid IP subnet."}

        """
        text = None
        body = self.parse_body()

        if self.has_content_type('application/xml'):
            text = '; '.join([err.text or '' for err in body.getiterator()
                              if err.text])
        elif self.has_content_type('application/json'):
            values = list(body.values())
            if len(values) > 0:
                text = values[0]
            else:
                text = body
        else:
            # while we hope a response is always one of xml or json, we have
            # seen html or text in the past, its not clear we can really do
            # something to make it more readable here, so we will just pass
            # it along as the whole response body in the text variable.
            text = body

        return '%s %s %s' % (self.status, self.error, text)


class OpenStackNetworkingConnection(OpenStackBaseConnection):
    """
    Common base connection class for Quantum and Neutron connections.
    Should not be instantiated directly.
    """
    service_type = 'network'
    accept_format = 'application/json'
    default_content_type = 'application/json; charset=UTF-8'
    service_region = None
    responseCls = OpenStackQuantumResponse

    def encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        if isinstance(data, basestring):
            return data

        return json.dumps(data)


class OpenStackQuantumConnection(OpenStackNetworkingConnection):
    """
    Connection class for network API for OpenStack Grizzly and earlier
    """

    service_name = 'quantum'


class OpenStackNeutronConnection(OpenStackNetworkingConnection):
    """
    Connection class for network API for OpenStack Havana and later
    """

    service_name = 'neutron'


class OpenStackNovaConnection(OpenStackNetworkingConnection):
    """
    Connection class for network API for OpenStack Grizzly and earlier
    """

    service_name = 'compute'


class OpenStackNovaNetworkingDriver(NetworkingDriver, OpenStackDriverMixin):
    """
    Driver class for OpenStack nova networks.
    """

    api_name = 'openstack_nova_networking'
    name = 'OpenStack Nova Networking'
    website = 'http://www.openstack.org/'

    connectionCls = OpenStackNovaConnection
    type = Provider.OPENSTACK_NOVA

    _base_path = '/os-networks'

    def __init__(self, *args, **kwargs):
        OpenStackDriverMixin.__init__(self, **kwargs)
        super(OpenStackNovaNetworkingDriver, self).__init__(*args, **kwargs)

        self._base_path = kwargs.get('api_path',
                                     DEFAULT_NOVA_NETWORKING_API_PATH)

    def iterate_networks(self):
        response = self.connection.request(self._base_path).object
        return self._to_networks_generator(response)

    def create_network(self, network, subnet):
        data = {'network': {'cidr': subnet.cidr, 'label': network.name}}
        response = self.connection.request(self._base_path,
                                           method='POST', data=data).object
        return self._to_network(response['network'])

    def delete_network(self, network):
        resp = self.connection.request('%s/%s' % (self._base_path,
                                                  network.id),
                                       method='DELETE')
        return resp.status == httplib.ACCEPTED

    def iterate_floating_ips(self):
        response = self.connection.request('/os-floating-ips').object
        return self._to_floating_ips_generator(response)

    def create_floating_ip(self, network=None):
        resp = self.connection.request('/os-floating-ips',
                                       data={})

        data = resp.object['floating_ip']
        id = data['id']
        ip_address = data['ip']
        return FloatingIP(id=id,
                          floating_ip_address=ip_address,
                          driver=self)

    def delete_floating_ip(self, floating_ip):
        path = '/os-floating-ips/%s' % (floating_ip.id)
        resp = self.connection.request(path, method='DELETE')
        return resp.status in (httplib.NO_CONTENT, httplib.ACCEPTED)

    def attach_floating_ip_to_node(self, node, floating_ip):
        if hasattr(floating_ip, 'floating_ip_address'):
            address = floating_ip.floating_ip_address
        else:
            address = floating_ip

        data = {
            'addFloatingIp': {'address': address}
        }
        resp = self.connection.request('/servers/%s/action' % (node.id),
                                       method='POST', data=data)
        return resp.status == httplib.ACCEPTED

    def detatch_floating_ip_from_node(self, node, floating_ip):
        if hasattr(floating_ip, 'floating_ip_address'):
            address = floating_ip.floating_ip_address
        else:
            address = floating_ip

        data = {
            'removeFloatingIp': {'address': address}
        }
        resp = self.connection.request('/servers/%s/action' % (node.id),
                                       method='POST', data=data)
        return resp.status == httplib.ACCEPTED

    def _to_networks_generator(self, obj):
        networks = obj['networks']
        for network in networks:
            yield self._to_network(network)

    def _to_network(self, obj):
        extra = {
            'cidr': obj.get('cidr', None)
        }
        return OpenStackNetwork(id=obj['id'],
                                name=obj['label'],
                                extra=extra,
                                driver=self)

    def _to_floating_ips_generator(self, obj):
        ip_elements = obj['floating_ips']
        return [self._to_floating_ip(ip) for ip in ip_elements]

    def _to_floating_ip(self, obj):
        extra = {'node_id': obj['instance_id']}
        return FloatingIP(id=obj['id'],
                          floating_ip_address=obj['ip'],
                          extra=extra,
                          driver=self.connection.driver)

    def _ex_connection_class_kwargs(self):
        return self.openstack_connection_kwargs()


class OpenStackQuantumNetworkingDriver(NetworkingDriver, OpenStackDriverMixin):
    """
    OpenStack network driver for OpenStack Grizzly and earlier
    """
    api_name = 'openstack_quantum'
    name = 'OpenStack Quantum'
    website = 'http://www.openstack.org/'

    connectionCls = OpenStackQuantumConnection
    type = Provider.OPENSTACK_QUANTUM

    def __init__(self, *args, **kwargs):
        OpenStackDriverMixin.__init__(self, **kwargs)
        super(OpenStackQuantumNetworkingDriver, self).__init__(*args, **kwargs)

    def iterate_networks(self):
        response = self.connection.request('/v2.0/networks.json')
        return self._to_network_generator(response.object)

    def create_network(self, network, subnet=None):
        request_data = {'network': {'name': network.name,
                                    'admin_state_up': True}}
        response = self.connection.request('/v2.0/networks.json',
                                           method='POST',
                                           data=request_data).object

        network = self._to_network(response['network'])

        if subnet:
            self.create_network_subnet(network=network, subnet=subnet)

        return network

    def delete_network(self, network):
        resp = self.connection.request('/v2.0/networks/%s.json' % (network.id),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def iterate_network_subnets(self, network):
        # Form id parameters.
        params = {}
        subnets = network.ex_get_subnet_ids()
        if len(subnets) > 0:
            params = {'id': subnets}

        response = self.connection.request('/v2.0/subnets.json',
                                           params=params).object
        return self._to_subnet_generator(response)

    def create_network_subnet(self, network, subnet):
        request_data = {'subnet': {'network_id': network.id,
                                   'ip_version': subnet.ip_version,
                                   'cidr': subnet.cidr}}

        if subnet.name is not None:
            request_data['subnet']['name'] = subnet.name

        response = self.connection.request('/v2.0/subnets.json',
                                           method='POST',
                                           data=request_data).object
        subnet = self._to_subnet(response['subnet'])
        return subnet

    def delete_subnet(self, subnet):
        resp = self.connection.request('/v2.0/subnets/%s.json' % (subnet.id),
                                       method='DELETE')

        return resp.status == httplib.NO_CONTENT

    def iterate_floating_ips(self):
        response = self.connection.request('/v2.0/floatingips.json')
        return self._to_floating_ips_generator(response.object)

    def create_floating_ip(self, network):
        data = {
            'floatingip': {
                'floating_network_id': network.id
            }
        }
        response = self.connection.request('/v2.0/floatingips',
                                           method='POST',
                                           data=data).object
        floating_ip = self._to_floating_ip(obj=response['floatingip'])
        return floating_ip

    def delete_floating_ip(self, floating_ip):
        resp = self.connection.request('/v2.0/floatingips/%s' %
                                       (floating_ip.id),
                                       method='DELETE')

        return resp.status == httplib.NO_CONTENT

    def iterate_ports(self):
        response = self.connection.request('/v2.0/ports.json')
        return self._to_port_generator(response.object)

    def get_port(self, port_id):
        """
        Lookup a port by id.

        :type port_id: ``str``
        """
        response = self.connection.request('/v2.0/ports/%s.json' %
                                           (port_id))
        return self._to_port(response.object.get('port', None))

    def iterate_network_gateways(self):
        response = self.connection.request('/v2.0/routers.json')
        return self._to_network_gateway_generator(response.object)

    def _to_network_gateway_generator(self, obj):
        """
        Convert from OpenStack response to list of NetworkGateway objects.
        """
        for gw in obj.get('routers', []):
            yield self._to_network_gateway(gw)

    def _to_network_gateway(self, obj):
        """
        Convert from Openstack response to NetworkGateway object.
        """
        # Retrieve the associated network id, if one is set
        network_id = None

        if isinstance(obj['external_gateway_info'], dict):
            ext_gw_info = obj['external_gateway_info']
            network_id = ext_gw_info.get('network_id', None)

        return NetworkGateway(id=obj['id'],
                              name=obj['name'],
                              state=obj['status'],
                              network_id=network_id,
                              driver=self)

    def _to_floating_ips_generator(self, obj):
        """
        Convert from OpenStack response to list of FloatingIP objects.
        """
        for ip in obj.get('floatingips', []):
            yield self._to_floating_ip(ip)

    def _to_floating_ip(self, obj):
        """
        Convert from Openstack response to OpenStackFloatingIP object.
        """
        floating_ip_address = obj['floating_ip_address']
        fixed_ip_address = obj['fixed_ip_address']

        return OpenStackFloatingIP(id=obj['id'],
                                   floating_ip_address=floating_ip_address,
                                   fixed_ip_address=fixed_ip_address,
                                   network_id=obj['floating_network_id'],
                                   port_id=obj['port_id'],
                                   driver=self,
                                   router_id=obj['router_id'],
                                   tenant_id=obj['tenant_id'])

    def _to_port_generator(self, obj):
        """
        Convert from OpenStack response to list of Port objects.
        """
        for port in obj.get('ports', []):
            yield self._to_port(port)

    def _to_port(self, obj):
        """
        Convert from Openstack response to Port object.
        """

        # Form list of ip addresses attached to this port
        ip_addresses = []
        for fixed_ip in obj.get('fixed_ips', []):
            ip_address = fixed_ip.get('ip_address', None)
            if ip_address:
                ip_addresses.append(ip_address)

        return Port(id=obj['id'],
                    name=obj['name'],
                    mac_address=obj['mac_address'],
                    ip_addresses=ip_addresses,
                    attached_device_id=obj['device_id'],
                    driver=self)

    def _to_subnet_generator(self, obj):
        """
        Convert from OpenStack response to list of Subnet objects.
        """
        for subnet in obj.get('subnets', []):
            yield self._to_subnet(subnet)

    def _to_subnet(self, obj):
        """
        Convert from Openstack response to Subnet object.
        """
        # Record allocation pools from subnet
        object_pools = obj.get('allocation_pools', [])

        allocation_pools = []
        for pool in object_pools:
            ap = OpenStackSubnet.AllocationPool(start_ip=pool['start'],
                                                end_ip=pool['end'])
            allocation_pools.append(ap)

        return OpenStackSubnet(id=obj['id'],
                               name=obj['name'],
                               ip_version=obj['ip_version'],
                               cidr=obj['cidr'],
                               allocation_pools=allocation_pools)

    def _to_network_generator(self, obj):
        """
        Convert from OpenStack response to list of Network objects.
        """
        for network in obj.get('networks', []):
            yield self._to_network(network)

    def _to_network(self, obj):
        """
        Convert from Openstack response to Network object.
        """
        extra = {}

        # TODO: Normalize common fields with other Network drivers
        fields = ['status', 'subnets', 'router:external', 'tenant_id',
                  'admin_state_up', 'shared']
        for field in fields:
            if field in obj:
                extra[field] = obj[field]

        return OpenStackNetwork(obj['id'], obj['name'], extra, self)

    def _ex_connection_class_kwargs(self):
        return self.openstack_connection_kwargs()


class OpenStackNeutronNetworkingDriver(OpenStackQuantumNetworkingDriver):
    """
    OpenStack network driver for OpenStack Havana and later
    """
    api_name = 'openstack_neutron'
    name = 'OpenStack Neutron'
    website = 'http://www.openstack.org/'

    connectionCls = OpenStackNeutronConnection
    type = Provider.OPENSTACK_NEUTRON
