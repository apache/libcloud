# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance withv
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
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.common.dimensiondata import DimensionDataConnection
from libcloud.common.dimensiondata import DimensionDataPool
from libcloud.common.dimensiondata import DimensionDataPoolMember
from libcloud.common.dimensiondata import DimensionDataVirtualListener
from libcloud.common.dimensiondata import DimensionDataVIPNode
from libcloud.common.dimensiondata import API_ENDPOINTS
from libcloud.common.dimensiondata import DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.utils.misc import reverse_dict
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Algorithm, Driver, LoadBalancer
from libcloud.loadbalancer.base import Member
from libcloud.loadbalancer.types import Provider


class DimensionDataLBDriver(Driver):
    """
    DimensionData node driver.
    """

    selected_region = None
    connectionCls = DimensionDataConnection
    name = 'Dimension Data Load Balancer'
    website = 'https://cloud.dimensiondata.com/'
    type = Provider.DIMENSIONDATA
    api_version = 1.0

    network_domain_id = None

    _VALUE_TO_ALGORITHM_MAP = {
        'ROUND_ROBIN': Algorithm.ROUND_ROBIN,
        'LEAST_CONNECTIONS': Algorithm.LEAST_CONNECTIONS,
        'SHORTEST_RESPONSE': Algorithm.SHORTEST_RESPONSE,
        'PERSISTENT_IP': Algorithm.PERSISTENT_IP
    }
    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    _VALUE_TO_STATE_MAP = {
        'NORMAL': State.RUNNING,
        'PENDING_ADD': State.PENDING,
        'PENDING_CHANGE': State.PENDING,
        'PENDING_DELETE': State.PENDING,
        'FAILED_ADD': State.ERROR,
        'FAILED_CHANGE': State.ERROR,
        'FAILED_DELETE': State.ERROR,
        'REQUIRES_SUPPORT': State.ERROR
    }

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS:
            raise ValueError('Invalid region: %s' % (region))

        self.selected_region = API_ENDPOINTS[region]

        super(DimensionDataLBDriver, self).__init__(key=key, secret=secret,
                                                    secure=secure, host=host,
                                                    port=port,
                                                    api_version=api_version,
                                                    region=region,
                                                    **kwargs)

    def _ex_connection_class_kwargs(self):
        """
            Add the region to the kwargs before the connection is instantiated
        """

        kwargs = super(DimensionDataLBDriver,
                       self)._ex_connection_class_kwargs()
        kwargs['region'] = self.selected_region
        return kwargs

    def create_balancer(self, name, port, protocol, algorithm, members):
        """
        Create a new load balancer instance

        :param name: Name of the new load balancer (required)
        :type  name: ``str``

        :param port: Port the load balancer should listen on,
                    defaults to 80 (required)
        :type  port: ``str``

        :param protocol: Loadbalancer protocol, defaults to http.
        :type  protocol: ``str``

        :param members: list of Members to attach to balancer (optional)
        :type  members: ``list`` of :class:`Member`

        :param algorithm: Load balancing algorithm, defaults to ROUND_ROBIN.
        :type algorithm: :class:`.Algorithm`

        :rtype: :class:`LoadBalancer`
        """
        network_domain_id = self.network_domain_id
        if port is None:
            port = 80
        if protocol is None:
            protocol = 'http'
        if algorithm is None:
            algorithm = Algorithm.ROUND_ROBIN

        # Create a pool first
        pool = self.ex_create_pool(
            network_domain_id=network_domain_id,
            name=name,
            ex_description=None,
            balancer_method=self._ALGORITHM_TO_VALUE_MAP[algorithm])

        # Attach the members to the pool as nodes
        if members is not None:
            for member in members:
                node = self.ex_create_node(
                    network_domain_id=network_domain_id,
                    name=member.ip,
                    ip=member.ip,
                    ex_description=None)
                self.ex_create_pool_member(
                    pool=pool,
                    node=node,
                    port=port)

        # Create the virtual listener (balancer)
        listener = self.ex_create_virtual_listener(
            network_domain_id=network_domain_id,
            name=name,
            ex_description=name,
            port=port,
            pool=pool)

        return LoadBalancer(
            id=listener.id,
            name=listener.name,
            state=State.RUNNING,
            ip=listener.ip,
            port=port,
            driver=self,
            extra={'pool_id': pool.id,
                   'network_domain_id': network_domain_id}
        )

    def list_balancers(self):
        """
        List all loadbalancers inside a geography.

        In Dimension Data terminology these are known as virtual listeners

        :rtype: ``list`` of :class:`LoadBalancer`
        """

        return self._to_balancers(
            self.connection
            .request_with_orgId_api_2('networkDomainVip/virtualListener')
            .object)

    def get_balancer(self, balancer_id):
        """
        Return a :class:`LoadBalancer` object.

        :param balancer_id: id of a load balancer you want to fetch
        :type  balancer_id: ``str``

        :rtype: :class:`LoadBalancer`
        """

        bal = self.connection \
            .request_with_orgId_api_2('networkDomainVip/virtualListener/%s'
                                      % balancer_id).object
        return self._to_balancer(bal)

    def list_protocols(self):
        """
        Return a list of supported protocols.

        Since all protocols are support by Dimension Data, this is a list
        of common protocols.

        :rtype: ``list`` of ``str``
        """
        return ['http', 'https', 'tcp', 'udp']

    def balancer_list_members(self, balancer):
        """
        Return list of members attached to balancer.

        In Dimension Data terminology these are the members of the pools
        within a virtual listener.

        :param balancer: LoadBalancer which should be used
        :type  balancer: :class:`LoadBalancer`

        :rtype: ``list`` of :class:`Member`
        """
        pool_members = self.ex_get_pool_members(balancer.extra['pool_id'])
        members = []
        for pool_member in pool_members:
            members.append(Member(
                id=pool_member.id,
                ip=pool_member.ip,
                port=pool_member.port,
                balancer=balancer,
                extra=None
            ))
        return members

    def balancer_attach_member(self, balancer, member):
        """
        Attach a member to balancer

        :param balancer: LoadBalancer which should be used
        :type  balancer: :class:`LoadBalancer`

        :param member: Member to join to the balancer
        :type member: :class:`Member`

        :return: Member after joining the balancer.
        :rtype: :class:`Member`
        """
        node = self.ex_create_node(
            network_domain_id=balancer.extra['network_domain_id'],
            name='Member.' + member.ip,
            ip=member.ip,
            ex_description=''
        )
        if node is False:
            return False
        pool = self.ex_get_pool(balancer.extra['pool_id'])
        pool_member = self.ex_create_pool_member(
            pool=pool,
            node=node,
            port=member.port)
        member.id = pool_member.id
        return member

    def balancer_detach_member(self, balancer, member):
        """
        Detach member from balancer

        :param balancer: LoadBalancer which should be used
        :type  balancer: :class:`LoadBalancer`

        :param member: Member which should be used
        :type member: :class:`Member`

        :return: ``True`` if member detach was successful, otherwise ``False``.
        :rtype: ``bool``
        """
        create_pool_m = ET.Element('removePoolMember', {'xmlns': TYPES_URN,
                                                        'id': member.id})

        result = self.connection.request_with_orgId_api_2(
            'networkDomainVip/removePoolMember',
            method='POST',
            data=ET.tostring(create_pool_m)).object
        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def destroy_balancer(self, balancer):
        """
        Destroy a load balancer (virtual listener)

        :param balancer: LoadBalancer which should be used
        :type  balancer: :class:`LoadBalancer`

        :return: ``True`` if the destroy was successful, otherwise ``False``.
        :rtype: ``bool``
        """
        delete_listener = ET.Element('deleteVirtualListener',
                                     {'xmlns': TYPES_URN,
                                      'id': balancer.id})

        result = self.connection.request_with_orgId_api_2(
            'networkDomainVip/deleteVirtualListener',
            method='POST',
            data=ET.tostring(delete_listener)).object
        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def ex_set_current_network_domain(self, network_domain_id):
        """
        Set the network domain (part of the network) of the driver

        :param network_domain_id: ID of the pool (required)
        :type  network_domain_id: ``str``
        """
        self.network_domain_id = network_domain_id

    def ex_get_current_network_domain(self):
        """
        Get the current network domain ID of the driver.

        :return: ID of the network domain
        :rtype: ``str``
        """
        return self.network_domain_id

    def ex_create_pool_member(self, pool, node, port):
        """
        Create a new member in an existing pool from an existing node

        :param pool: Instance of ``DimensionDataPool`` (required)
        :type  pool: ``DimensionDataPool``

        :param node: Instance of ``DimensionDataVIPNode`` (required)
        :type  node: ``DimensionDataVIPNode``

        :param port: Port the the service will listen on
        :type  port: ``str``

        :return: The node member, instance of ``DimensionDataPoolMember``
        :rtype: ``DimensionDataPoolMember``
        """
        create_pool_m = ET.Element('addPoolMember', {'xmlns': TYPES_URN})
        ET.SubElement(create_pool_m, "poolId").text = pool.id
        ET.SubElement(create_pool_m, "nodeId").text = node.id
        ET.SubElement(create_pool_m, "status").text = 'ENABLED'

        response = self.connection.request_with_orgId_api_2(
            'networkDomainVip/addPoolMember',
            method='POST',
            data=ET.tostring(create_pool_m)).object

        member_id = None
        node_name = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'poolMemberId':
                member_id = info.get('value')
            if info.get('name') == 'nodeName':
                node_name = info.get('value')

        return DimensionDataPoolMember(
            id=member_id,
            name=node_name,
            status=State.RUNNING,
            ip=node.ip,
            port=port,
            node_id=node.id
        )

    def ex_create_node(self,
                       network_domain_id,
                       name,
                       ip,
                       ex_description,
                       connection_limit=25000,
                       connection_rate_limit=2000):
        """
        Create a new node

        :param network_domain_id: Network Domain ID (required)
        :type  name: ``str``

        :param name: name of the node (required)
        :type  name: ``str``

        :param ip: IPv4 address of the node (required)
        :type  ip: ``str``

        :param ex_description: Description of the node
        :type  ex_description: ``str``

        :param connection_limit: Maximum number
                of concurrent connections per sec
        :type  connection_limit: ``int``

        :param connection_rate_limit: Maximum number of concurrent sessions
        :type  connection_rate_limit: ``int``

        :return: Instance of ``DimensionDataVIPNode``
        :rtype: ``DimensionDataVIPNode``
        """
        create_node_elm = ET.Element('createNode', {'xmlns': TYPES_URN})
        ET.SubElement(create_node_elm, "networkDomainId") \
            .text = network_domain_id
        ET.SubElement(create_node_elm, "name").text = name
        ET.SubElement(create_node_elm, "description").text \
            = str(ex_description)
        ET.SubElement(create_node_elm, "ipv4Address").text = ip
        ET.SubElement(create_node_elm, "status").text = 'ENABLED'
        ET.SubElement(create_node_elm, "connectionLimit") \
            .text = str(connection_limit)
        ET.SubElement(create_node_elm, "connectionRateLimit") \
            .text = str(connection_rate_limit)

        response = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/createNode',
            method='POST',
            data=ET.tostring(create_node_elm)).object

        node_id = None
        node_name = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'nodeId':
                node_id = info.get('value')
            if info.get('name') == 'name':
                node_name = info.get('value')
        return DimensionDataVIPNode(
            id=node_id,
            name=node_name,
            status=State.RUNNING,
            ip=ip
        )

    def ex_update_node(self, node):
        create_node_elm = ET.Element('editNode', {'xmlns': TYPES_URN})
        ET.SubElement(create_node_elm, "connectionLimit") \
            .text = str(node.connection_limit)
        ET.SubElement(create_node_elm, "connectionRateLimit") \
            .text = str(node.connection_rate_limit)

        self.connection.request_with_orgId_api_2(
            action='networkDomainVip/createNode',
            method='POST',
            data=ET.tostring(create_node_elm)).object
        return node

    def ex_set_node_state(self, node, enabled):
        create_node_elm = ET.Element('editNode', {'xmlns': TYPES_URN})
        ET.SubElement(create_node_elm, "status") \
            .text = "ENABLED" if enabled is True else "DISABLED"

        self.connection.request_with_orgId_api_2(
            action='networkDomainVip/editNode',
            method='POST',
            data=ET.tostring(create_node_elm)).object
        return node

    def ex_create_pool(self,
                       network_domain_id,
                       name,
                       balancer_method,
                       ex_description,
                       service_down_action='NONE',
                       slow_ramp_time=30):
        """
        Create a new pool

        :param network_domain_id: Network Domain ID (required)
        :type  name: ``str``

        :param name: name of the node (required)
        :type  name: ``str``

        :param balancer_method: The load balancer algorithm (required)
        :type  balancer_method: ``str``

        :param ex_description: Description of the node
        :type  ex_description: ``str``

        :param service_down_action: What to do when node
                                    is unavailable NONE, DROP or RESELECT
        :type  service_down_action: ``str``

        :param slow_ramp_time: Number of seconds to stagger ramp up of nodes
        :type  slow_ramp_time: ``int``

        :return: Instance of ``DimensionDataPool``
        :rtype: ``DimensionDataPool``
        """
        # Names cannot contain spaces.
        name.replace(' ', '_')
        create_node_elm = ET.Element('createPool', {'xmlns': TYPES_URN})
        ET.SubElement(create_node_elm, "networkDomainId") \
            .text = network_domain_id
        ET.SubElement(create_node_elm, "name").text = name
        ET.SubElement(create_node_elm, "description").text \
            = str(ex_description)
        ET.SubElement(create_node_elm, "loadBalanceMethod") \
            .text = str(balancer_method)
        ET.SubElement(create_node_elm, "serviceDownAction") \
            .text = service_down_action
        ET.SubElement(create_node_elm, "slowRampTime").text \
            = str(slow_ramp_time)

        response = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/createPool',
            method='POST',
            data=ET.tostring(create_node_elm)).object

        pool_id = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'poolId':
                pool_id = info.get('value')

        return DimensionDataPool(
            id=pool_id,
            name=name,
            description=ex_description,
            status=State.RUNNING,
            load_balance_method=str(balancer_method),
            health_monitor_id=None,
            service_down_action=service_down_action,
            slow_ramp_time=str(slow_ramp_time)
        )

    def ex_create_virtual_listener(self,
                                   network_domain_id,
                                   name,
                                   ex_description,
                                   port,
                                   pool,
                                   protocol='TCP',
                                   connection_limit=25000,
                                   connection_rate_limit=2000,
                                   source_port_preservation='PRESERVE'):
        """
        Create a new virtual listener (load balancer)

        :param network_domain_id: Network Domain ID (required)
        :type  name: ``str``

        :param name: name of the listener (required)
        :type  name: ``str``

        :param ex_description: Description of the node
        :type  ex_description: ``str``

        :param port: Description of the node
        :type  port: ``str``

        :param listener_type: The type of balancer, one of STANDARD (default)
                                or PERFORMANCE_LAYER_4
        :type  listener_type: ``str``

        :param protocol: For STANDARD type, ANY, TCP or UDP
                         for PERFORMANCE_LAYER_4 choice of ANY, TCP, UDP, HTTP
        :type  protcol: ``str``

        :param connection_limit: Maximum number
                                of concurrent connections per sec
        :type  connection_limit: ``int``

        :param connection_rate_limit: Maximum number of concurrent sessions
        :type  connection_rate_limit: ``int``

        :param source_port_preservation: Choice of PRESERVE,
                                        PRESERVE_STRICT or CHANGE
        :type  source_port_preservation: ``str``

        :return: Instance of the listener
        :rtype: ``DimensionDataVirtualListener``
        """
        if port is 80 or 443:
            listener_type = 'PERFORMANCE_LAYER_4'
            protocol = 'HTTP'
        else:
            listener_type = 'STANDARD'

        create_node_elm = ET.Element('createVirtualListener',
                                     {'xmlns': TYPES_URN})
        ET.SubElement(create_node_elm, "networkDomainId") \
            .text = network_domain_id
        ET.SubElement(create_node_elm, "name").text = name
        ET.SubElement(create_node_elm, "description").text = \
            str(ex_description)
        ET.SubElement(create_node_elm, "type").text = listener_type
        ET.SubElement(create_node_elm, "protocol") \
            .text = protocol
        ET.SubElement(create_node_elm, "port").text = str(port)
        ET.SubElement(create_node_elm, "enabled").text = 'true'
        ET.SubElement(create_node_elm, "connectionLimit") \
            .text = str(connection_limit)
        ET.SubElement(create_node_elm, "connectionRateLimit") \
            .text = str(connection_rate_limit)
        ET.SubElement(create_node_elm, "sourcePortPreservation") \
            .text = source_port_preservation
        ET.SubElement(create_node_elm, "poolId") \
            .text = pool.id

        response = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/createVirtualListener',
            method='POST',
            data=ET.tostring(create_node_elm)).object

        virtual_listener_id = None
        virtual_listener_ip = None
        for info in findall(response, 'info', TYPES_URN):
            if info.get('name') == 'virtualListenerId':
                virtual_listener_id = info.get('value')
            if info.get('name') == 'listenerIpAddress':
                virtual_listener_ip = info.get('value')

        return DimensionDataVirtualListener(
            id=virtual_listener_id,
            name=name,
            ip=virtual_listener_ip,
            status=State.RUNNING
        )

    def ex_get_pools(self):
        """
        Get all of the pools inside the current geography

        :return: Returns a ``list`` of type ``DimensionDataPool``
        :rtype: ``list`` of ``DimensionDataPool``
        """
        pools = self.connection \
            .request_with_orgId_api_2('networkDomainVip/pool').object
        return self._to_pools(pools)

    def ex_get_pool(self, pool_id):
        """
        Get a specific pool inside the current geography

        :param pool_id: The identifier of the pool
        :type  pool_id: ``str``

        :return: Returns an instance of ``DimensionDataPool``
        :rtype: ``DimensionDataPool``
        """
        pool = self.connection \
            .request_with_orgId_api_2('networkDomainVip/pool/%s'
                                      % pool_id).object
        return self._to_pool(pool)

    def ex_update_pool(self, pool):
        create_node_elm = ET.Element('editPool', {'xmlns': TYPES_URN})

        ET.SubElement(create_node_elm, "loadBalanceMethod") \
            .text = str(pool.load_balance_method)
        ET.SubElement(create_node_elm, "serviceDownAction") \
            .text = pool.service_down_action
        ET.SubElement(create_node_elm, "slowRampTime").text \
            = str(pool.slow_ramp_time)

        response = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/editPool',
            method='POST',
            data=ET.tostring(create_node_elm)).object
        responseCode = findtext(response, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def ex_destroy_pool(self, pool):
        """
        Destroy an existing pool

        :param pool: The instance of ``DimensionDataPool`` to destroy
        :type  pool: ``DimensionDataPool``

        :return: ``True`` for success, ``False`` for failure
        :rtype: ``bool``
        """
        destroy_request = ET.Element('deletePool',
                                     {'xmlns': TYPES_URN,
                                      'id': pool.id})

        result = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/deletePool',
            method='POST',
            data=ET.tostring(destroy_request)).object
        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def ex_get_pool_members(self, pool_id):
        """
        Get the members of a pool

        :param pool: The instance of a pool
        :type  pool: ``DimensionDataPool``

        :return: Returns an ``list`` of ``DimensionDataPoolMember``
        :rtype: ``list`` of ``DimensionDataPoolMember``
        """
        members = self.connection \
            .request_with_orgId_api_2('networkDomainVip/poolMember?poolId=%s'
                                      % pool_id).object
        return self._to_members(members)

    def ex_get_pool_member(self, pool_member_id):
        """
        Get a specific member of a pool

        :param pool: The id of a pool member
        :type  pool: ``str``

        :return: Returns an instance of ``DimensionDataPoolMember``
        :rtype: ``DimensionDataPoolMember``
        """
        member = self.connection \
            .request_with_orgId_api_2('networkDomainVip/poolMember/%s'
                                      % pool_member_id).object
        return self._to_member(member)

    def ex_set_pool_member_state(self, member, enabled=True):
        request = ET.Element('editPoolMember',
                             {'xmlns': TYPES_URN,
                              'id': member.id})
        state = "ENABLED" if enabled is True else "DISABLED"
        ET.SubElement(request, 'status').text = state

        result = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/editPoolMember',
            method='POST',
            data=ET.tostring(request)).object

        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def ex_destroy_pool_member(self, member, destroy_node=False):
        """
        Destroy a specific member of a pool

        :param pool: The instance of a pool member
        :type  pool: ``DimensionDataPoolMember``

        :param destroy_node: Also destroy the associated node
        :type  destroy_node: ``bool``

        :return: ``True`` for success, ``False`` for failure
        :rtype: ``bool``
        """
        # remove the pool member
        destroy_request = ET.Element('removePoolMember',
                                     {'xmlns': TYPES_URN,
                                      'id': member.id})

        result = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/removePoolMember',
            method='POST',
            data=ET.tostring(destroy_request)).object

        if member.node_id is not None and destroy_node is True:
            return self.ex_destroy_node(member.node_id)
        else:
            responseCode = findtext(result, 'responseCode', TYPES_URN)
            return responseCode == 'OK'

    def ex_get_nodes(self):
        """
        Get the nodes within this geography

        :return: Returns an ``list`` of ``DimensionDataVIPNode``
        :rtype: ``list`` of ``DimensionDataVIPNode``
        """
        nodes = self.connection \
            .request_with_orgId_api_2('networkDomainVip/node').object
        return self._to_nodes(nodes)

    def ex_get_node(self, node_id):
        """
        Get the node specified by node_id

        :return: Returns an instance of ``DimensionDataVIPNode``
        :rtype: Instance of ``DimensionDataVIPNode``
        """
        nodes = self.connection \
            .request_with_orgId_api_2('networkDomainVip/node/%s'
                                      % node_id).object
        return self._to_node(nodes)

    def ex_destroy_node(self, node_id):
        """
        Destroy a specific node

        :param node_id: The ID of of a ``DimensionDataVIPNode``
        :type  node_id: ``str``

        :return: ``True`` for success, ``False`` for failure
        :rtype: ``bool``
        """
        # Destroy the node
        destroy_request = ET.Element('deleteNode',
                                     {'xmlns': TYPES_URN,
                                      'id': node_id})

        result = self.connection.request_with_orgId_api_2(
            action='networkDomainVip/deleteNode',
            method='POST',
            data=ET.tostring(destroy_request)).object
        responseCode = findtext(result, 'responseCode', TYPES_URN)
        return responseCode == 'OK' or responseCode == 'IN_PROGRESS'

    def _to_nodes(self, object):
        nodes = []
        for element in object.findall(fixxpath("node", TYPES_URN)):
            nodes.append(self._to_node(element))

        return nodes

    def _to_node(self, element):
        ipaddress = findtext(element, 'ipv4Address', TYPES_URN)
        if ipaddress is None:
            ipaddress = findtext(element, 'ipv6Address', TYPES_URN)

        name = findtext(element, 'name', TYPES_URN)

        node = DimensionDataVIPNode(
            id=element.get('id'),
            name=name,
            status=self._VALUE_TO_STATE_MAP.get(
                findtext(element, 'state', TYPES_URN),
                State.UNKNOWN),
            connection_rate_limit=findtext(element,
                                           'connectionRateLimit', TYPES_URN),
            connection_limit=findtext(element, 'connectionLimit', TYPES_URN),
            ip=ipaddress)

        return node

    def _to_balancers(self, object):
        loadbalancers = []
        for element in object.findall(fixxpath("virtualListener", TYPES_URN)):
            loadbalancers.append(self._to_balancer(element))

        return loadbalancers

    def _to_balancer(self, element):
        ipaddress = findtext(element, 'listenerIpAddress', TYPES_URN)
        name = findtext(element, 'name', TYPES_URN)
        port = findtext(element, 'port', TYPES_URN)
        extra = {}

        extra['pool_id'] = element.find(fixxpath(
            'pool',
            TYPES_URN)).get('id')
        extra['network_domain_id'] = findtext(element, 'networkDomainId',
                                              TYPES_URN)

        balancer = LoadBalancer(
            id=element.get('id'),
            name=name,
            state=self._VALUE_TO_STATE_MAP.get(
                findtext(element, 'state', TYPES_URN),
                State.UNKNOWN),
            ip=ipaddress,
            port=port,
            driver=self.connection.driver,
            extra=extra
        )

        return balancer

    def _to_members(self, object):
        members = []
        for element in object.findall(fixxpath("poolMember", TYPES_URN)):
            members.append(self._to_member(element))

        return members

    def _to_member(self, element):
        port = findtext(element, 'port', TYPES_URN)
        if port is not None:
            port = int(port)
        pool_member = DimensionDataPoolMember(
            id=element.get('id'),
            name=element.find(fixxpath(
                'node',
                TYPES_URN)).get('name'),
            status=findtext(element, 'state', TYPES_URN),
            node_id=element.find(fixxpath(
                'node',
                TYPES_URN)).get('id'),
            ip=element.find(fixxpath(
                'node',
                TYPES_URN)).get('ipAddress'),
            port=port
        )
        return pool_member

    def _to_pools(self, object):
        pools = []
        for element in object.findall(fixxpath("pool", TYPES_URN)):
            pools.append(self._to_pool(element))

        return pools

    def _to_pool(self, element):
        pool = DimensionDataPool(
            id=element.get('id'),
            name=findtext(element, 'name', TYPES_URN),
            status=findtext(element, 'state', TYPES_URN),
            description=findtext(element, 'description', TYPES_URN),
            load_balance_method=findtext(element, 'loadBalanceMethod',
                                         TYPES_URN),
            health_monitor_id=findtext(element, 'healthMonitorId', TYPES_URN),
            service_down_action=findtext(element, 'serviceDownAction',
                                         TYPES_URN),
            slow_ramp_time=findtext(element, 'slowRampTime', TYPES_URN),
        )
        return pool
