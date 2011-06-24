from libcloud.common.cloudstack import CloudStackConnection, \
                                       CloudStackDriverMixIn
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.types import State, LibcloudLBImmutableError
from libcloud.utils import reverse_dict

class CloudStackLBDriver(CloudStackDriverMixIn, Driver):
    """Driver for CloudStack load balancers."""

    _VALUE_TO_ALGORITHM_MAP = {
        'roundrobin': Algorithm.ROUND_ROBIN,
        'leastconn': Algorithm.LEAST_CONNECTIONS
    }
    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    LB_STATE_MAP = {
        'Active': State.RUNNING,
    }

    def list_protocols(self):
        """We don't actually have any protocol awareness beyond TCP."""
        return [ 'tcp' ]

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
        if location is None:
            locations = self._sync_request('listZones')
            location = locations['zone'][0]['id']
        else:
            location = location.id
        if private_port is None:
            private_port = port

        result = self._async_request('associateIpAddress', zoneid=location)
        public_ip = result['ipaddress']

        result = self._sync_request('createLoadBalancerRule',
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
        return [self._to_member(m, balancer.ex_private_port) for m in members]

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

    def _to_member(self, obj, port):
        return Member(
            id=obj['id'],
            ip=obj['nic'][0]['ipaddress'],
            port=port
        )