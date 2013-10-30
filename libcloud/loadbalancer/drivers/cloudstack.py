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

from libcloud.common.cloudstack import CloudStackDriverMixIn
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.types import State
from libcloud.utils.misc import reverse_dict


class CloudStackLBDriver(CloudStackDriverMixIn, Driver):
    """Driver for CloudStack load balancers."""

    api_name = 'cloudstack_lb'
    name = 'CloudStack'
    website = 'http://cloudstack.org/'
    type = Provider.CLOUDSTACK

    _VALUE_TO_ALGORITHM_MAP = {
        'roundrobin': Algorithm.ROUND_ROBIN,
        'leastconn': Algorithm.LEAST_CONNECTIONS
    }
    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    LB_STATE_MAP = {
        'Active': State.RUNNING,
    }

    def __init__(self, key, secret=None, secure=True, host=None,
                 path=None, port=None, *args, **kwargs):
        """
        @inherits: :class:`Driver.__init__`
        """
        host = host if host else self.host
        path = path if path else self.path

        if path is not None:
            self.path = path

        if host is not None:
            self.host = host

        if (self.type == Provider.CLOUDSTACK) and (not host or not path):
            raise Exception('When instantiating CloudStack driver directly ' +
                            'you also need to provide host and path argument')

        super(CloudStackLBDriver, self).__init__(key=key, secret=secret,
                                                 secure=secure,
                                                 host=host, port=port)

    def list_protocols(self):
        """
        We don't actually have any protocol awareness beyond TCP.

        :rtype: ``list`` of ``str``
        """
        return ['tcp']

    def list_balancers(self):
        balancers = self._sync_request('listLoadBalancerRules')
        balancers = balancers.get('loadbalancerrule', [])
        return [self._to_balancer(balancer) for balancer in balancers]

    def get_balancer(self, balancer_id):
        balancer = self._sync_request('listLoadBalancerRules', id=balancer_id)
        balancer = balancer.get('loadbalancerrule', [])
        if not balancer:
            raise Exception("no such load balancer: " + str(balancer_id))
        return self._to_balancer(balancer[0])

    def create_balancer(self, name, members, protocol='http', port=80,
                        algorithm=DEFAULT_ALGORITHM, location=None,
                        private_port=None):
        """
        @inherits: :class:`Driver.create_balancer`

        :param location: Location
        :type  location: :class:`NodeLocation`

        :param private_port: Private port
        :type  private_port: ``int``
        """
        if location is None:
            locations = self._sync_request('listZones')
            location = locations['zone'][0]['id']
        else:
            location = location.id
        if private_port is None:
            private_port = port

        result = self._async_request('associateIpAddress', zoneid=location)
        public_ip = result['ipaddress']

        result = self._sync_request(
            'createLoadBalancerRule',
            algorithm=self._ALGORITHM_TO_VALUE_MAP[algorithm],
            name=name,
            privateport=private_port,
            publicport=port,
            publicipid=public_ip['id'],
        )

        balancer = self._to_balancer(result['loadbalancer'])

        for member in members:
            balancer.attach_member(member)

        return balancer

    def destroy_balancer(self, balancer):
        self._async_request('deleteLoadBalancerRule', id=balancer.id)
        self._async_request('disassociateIpAddress',
                            id=balancer.ex_public_ip_id)

    def balancer_attach_member(self, balancer, member):
        member.port = balancer.ex_private_port
        self._async_request('assignToLoadBalancerRule', id=balancer.id,
                            virtualmachineids=member.id)
        return True

    def balancer_detach_member(self, balancer, member):
        self._async_request('removeFromLoadBalancerRule', id=balancer.id,
                            virtualmachineids=member.id)
        return True

    def balancer_list_members(self, balancer):
        members = self._sync_request('listLoadBalancerRuleInstances',
                                     id=balancer.id)
        members = members['loadbalancerruleinstance']
        return [self._to_member(m, balancer.ex_private_port, balancer)
                for m in members]

    def _to_balancer(self, obj):
        balancer = LoadBalancer(
            id=obj['id'],
            name=obj['name'],
            state=self.LB_STATE_MAP.get(obj['state'], State.UNKNOWN),
            ip=obj['publicip'],
            port=obj['publicport'],
            driver=self.connection.driver
        )
        balancer.ex_private_port = obj['privateport']
        balancer.ex_public_ip_id = obj['publicipid']
        return balancer

    def _to_member(self, obj, port, balancer):
        return Member(
            id=obj['id'],
            ip=obj['nic'][0]['ipaddress'],
            port=port,
            balancer=balancer
        )
