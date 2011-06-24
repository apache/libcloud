from libcloud.common.cloudstack import CloudStackConnection, \
                                       CloudStackDriverMixIn
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.types import State, LibcloudLBImmutableError
from libcloud.utils import reverse_dict

class CloudStackLBDriver(CloudStackDriverMixIn, Driver):
    _VALUE_TO_ALGORITHM_MAP = {
        'roundrobin': Algorithm.ROUND_ROBIN,
        'leastconn': Algorithm.LEAST_CONNECTIONS
    }
    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    LB_STATE_MAP = {
        'Active': State.RUNNING,
    }

    def list_protocols(self):
        return [ 'tcp' ]

    def list_balancers(self):
        balancers = self._sync_request('listLoadBalancerRules')
        balancers = balancers['loadbalancerrule']
        return [self._to_balancer(balancer) for balancer in balancers]

    def get_balancer(self, balancer_id):
        balancer = self._sync_request('listLoadBalancerRules', id=balancer_id)
        balancer = balancer.get('loadbalancerrule', [])
        if not balancer:
            raise Exception("no such load balancer: " + str(balancer_id))
        return self._to_balancer(balancer[0])

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
        return balancer

    def _to_member(self, obj, port):
        return Member(
            id=obj['id'],
            ip=obj['nic'][0]['ipaddress'],
            port=port
        )