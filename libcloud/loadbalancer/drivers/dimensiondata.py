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

from libcloud.common.dimensiondata import DimensionDataConnection
from libcloud.common.dimensiondata import DimensionDataPool
from libcloud.common.dimensiondata import DimensionDataPoolMember
from libcloud.common.dimensiondata import API_ENDPOINTS
from libcloud.common.dimensiondata import DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.common.dimensiondata import SERVER_NS
from libcloud.utils.misc import find, reverse_dict
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Algorithm, Driver, LoadBalancer
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM, Member
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
        
        return True

    def list_balancers(self):
        """
        List all loadbalancers inside a geography.
        
        In Dimension Data terminology these are known as virtual listeners

        :rtype: ``list`` of :class:`LoadBalancer`
        """
        
        return self._to_balancers(
            self.connection
            .request_with_orgId_api_2('networkDomainVip/virtualListener').object)

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
        return ['dns', 'ftp', 'http', 'https', 'tcp', 'udp']

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
                ip=pool_member.ip_address,
                port=pool_member.port,
                balancer=balancer,
                extra=None
            ))
        return members

    def balancer_attach_member(self, balancer, member):
        return True

    def balancer_attach_compute_node(self, balancer, node):
        return True

    def balancer_detach_member(self, balancer, member):
        return True

    def destroy_balancer(self, balancer):
        return True

    def ex_create_node(self,
                       network_domain_id,
                       name,
                       ip,
                       ex_description,
                       connectionLimit=25000,
                       connectionRateLimit=2000):
        create_node_elm = ET.Element('createNode', {'xmlns': SERVER_NS})
        ET.SubElement(create_node_elm, "networkDomainId").text = network_domain_id
        ET.SubElement(create_node_elm, "description").text = ex_description
        ET.SubElement(create_node_elm, "name").text = name
        ET.SubElement(create_node_elm, "ipv4Address").text = ip
        ET.SubElement(create_node_elm, "connectionLimit").text = connectionLimit
        ET.SubElement(create_node_elm, "connectionRateLimit").text = connectionRateLimit

        self.connection.request_with_orgId_api_2(
            'networkDomainVip/createNode',
            method='POST',
            data=ET.tostring(create_node_elm)).object
        return True

    def ex_get_pools(self):
        pools = self.connection \
            .request_with_orgId_api_2('networkDomainVip/pool').object
        return self._to_pools(pools)

    def ex_get_pool(self, pool_id):
        pool = self.connection \
            .request_with_orgId_api_2('networkDomainVip/pool/%s'
                                      % pool_id).object
        return self._to_pool(pool)
    
    def ex_get_pool_members(self, pool_id):
        members = self.connection \
            .request_with_orgId_api_2('networkDomainVip/poolMember?poolId=%s'
                                      % pool_id).object
        return self._to_members(members)
    
    def ex_get_pool_member(self, pool_member_id):
        member = self.connection \
            .request_with_orgId_api_2('networkDomainVip/poolMember/%s'
                                      % pool_member_id).object
        return self._to_member(member)

    def _to_balancers(self, object ):
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
    
    def _to_members(self, object ):
        members = []
        for element in object.findall(fixxpath("poolMember", TYPES_URN)):
            members.append(self._to_member(element))

        return members
    
    def _to_member(self, element):
        pool = DimensionDataPoolMember(
            id=element.get('id'),
            name=element.find(fixxpath(
                'node',
                TYPES_URN)).get('name'),
            status=findtext(element, 'state', TYPES_URN),
            ip_address=element.find(fixxpath(
                'node',
                TYPES_URN)).get('ipAddress'),
            port=int(findtext(element, 'port', TYPES_URN))
        )
        return pool
    
    def _to_pools(self, object ):
        pools = []
        for element in object.findall(fixxpath("pool", TYPES_URN)):
            pools.append(self._to_pool(element))

        return pools
    
    def _to_pool(self, element):
        pool = DimensionDataPool(
            id=element.get('id'),
            name=findtext(element, 'name', TYPES_URN),
            status=findtext(element,'state', TYPES_URN),
            description=findtext(element, 'description', TYPES_URN)
        )
        return pool
