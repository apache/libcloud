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

__all__ = [
    'ElasticLBDriver'
]


from libcloud.utils.xml import findtext, findall
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Driver, LoadBalancer, Member
from libcloud.common.aws import AWSGenericResponse, SignedAWSConnection


VERSION = '2012-06-01'
HOST = 'elasticloadbalancing.%s.amazonaws.com'
ROOT = '/%s/' % (VERSION)
NS = 'http://elasticloadbalancing.amazonaws.com/doc/%s/' % (VERSION, )


class ELBResponse(AWSGenericResponse):
    """
    Amazon ELB response class.
    """
    namespace = NS
    exceptions = {}
    xpath = 'Error'


class ELBConnection(SignedAWSConnection):
    version = VERSION
    host = HOST
    responseCls = ELBResponse


class ElasticLBDriver(Driver):
    name = 'ELB'
    website = 'http://aws.amazon.com/elasticloadbalancing/'
    connectionCls = ELBConnection

    def __init__(self, access_id, secret, region):
        super(ElasticLBDriver, self).__init__(access_id, secret)
        self.region = region
        self.connection.host = HOST % (region)

    def list_protocols(self):
        return ['tcp', 'ssl', 'http', 'https']

    def list_balancers(self):
        params = {'Action': 'DescribeLoadBalancers'}
        data = self.connection.request(ROOT, params=params).object
        return self._to_balancers(data)

    def create_balancer(self, name, port, protocol, algorithm, members,
                        ex_members_availability_zones=None):
        if ex_members_availability_zones is None:
            ex_members_availability_zones = ['a']

        params = {
            'Action': 'CreateLoadBalancer',
            'LoadBalancerName': name,
            'Listeners.member.1.InstancePort': str(port),
            'Listeners.member.1.InstanceProtocol': protocol.upper(),
            'Listeners.member.1.LoadBalancerPort': str(port),
            'Listeners.member.1.Protocol': protocol.upper(),
        }

        for i, z in enumerate(ex_members_availability_zones):
            zone = ''.join((self.region, z))
            params['AvailabilityZones.member.%d' % (i + 1)] = zone

        data = self.connection.request(ROOT, params=params).object

        balancer = LoadBalancer(
            id=name,
            name=name,
            state=State.PENDING,
            ip=findtext(element=data, xpath='DNSName', namespace=NS),
            port=port,
            driver=self.connection.driver
        )
        balancer._members = []
        return balancer

    def destroy_balancer(self, balancer):
        params = {
            'Action': 'DeleteLoadBalancer',
            'LoadBalancerName': balancer.id
        }
        self.connection.request(ROOT, params=params)
        return True

    def get_balancer(self, balancer_id):
        params = {
            'Action': 'DescribeLoadBalancers',
            'LoadBalancerNames.member.1': balancer_id
        }
        data = self.connection.request(ROOT, params=params).object
        return self._to_balancers(data)[0]

    def balancer_attach_compute_node(self, balancer, node):
        params = {
            'Action': 'RegisterInstancesWithLoadBalancer',
            'LoadBalancerName': balancer.id,
            'Instances.member.1.InstanceId': node.id
        }
        self.connection.request(ROOT, params=params)
        balancer._members.append(Member(node.id, None, None, balancer=self))

    def balancer_detach_member(self, balancer, member):
        params = {
            'Action': 'DeregisterInstancesFromLoadBalancer',
            'LoadBalancerName': balancer.id,
            'Instances.member.1.InstanceId': member.id
        }
        self.connection.request(ROOT, params=params)
        balancer._members = [m for m in balancer._members if m.id != member.id]
        return True

    def balancer_list_members(self, balancer):
        return balancer._members

    def _to_balancers(self, data):
        xpath = 'DescribeLoadBalancersResult/LoadBalancerDescriptions/member'
        return [self._to_balancer(el)
                for el in findall(element=data, xpath=xpath, namespace=NS)]

    def _to_balancer(self, el):
        name = findtext(element=el, xpath='LoadBalancerName', namespace=NS)
        dns_name = findtext(el, xpath='DNSName', namespace=NS)
        port = findtext(el, xpath='LoadBalancerPort', namespace=NS)

        balancer = LoadBalancer(
            id=name,
            name=name,
            state=State.UNKNOWN,
            ip=dns_name,
            port=port,
            driver=self.connection.driver
        )

        xpath = 'Instances/member/InstanceId'
        members = findall(element=el, xpath=xpath, namespace=NS)
        balancer._members = []

        for m in members:
            balancer._members.append(Member(m.text, None, None,
                                            balancer=balancer))

        return balancer
