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


import time
from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.ec2 import EC2Connection
from libcloud.loadbalancer.base import Driver, Algorithm, Member
from libcloud.loadbalancer.base import LoadBalancer
from libcloud.utils.xml import fixxpath, findtext, findattr, findall
from libcloud.loadbalancer.types import State
from libcloud.common.aws import AWSBaseResponse
from libcloud.utils.misc import reverse_dict

ELB_US_EAST_HOST = 'elasticloadbalancing.us-east-1.amazonaws.com'
ELB_US_WEST_HOST = 'elasticloadbalancing.us-west-1.amazonaws.com'
ELB_US_WEST_OREGON_HOST = 'elasticloadbalancing.us-west-2.amazonaws.com'
ELB_EU_WEST_HOST = 'elasticloadbalancing.eu-west-1.amazonaws.com'
ELB_AP_SOUTHEAST_HOST = 'elasticloadbalancing.ap-southeast-1.amazonaws.com'
ELB_AP_NORTHEAST_HOST = 'elasticloadbalancing.ap-northeast-1.amazonaws.com'
ELB_SA_EAST_HOST = 'elasticloadbalancing.sa-east-1.amazonaws.com'

API_VERSION = '2011-11-15'

NAMESPACE = "http://elasticloadbalancing.amazonaws.com/doc/%s/" % (API_VERSION)

class ELBResponse(AWSBaseResponse):
    pass

class ELBConnection(EC2Connection):
    host = ELB_US_EAST_HOST
    responseCls = ELBResponse

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = API_VERSION
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key,
                                                       self.action)
        return params

class ELBUSWestConnection(ELBConnection):
    host = ELB_US_WEST_HOST

class ELBUSWestOregonConnection(ELBConnection):
    host = ELB_US_WEST_OREGON_HOST

class ELBEUWestConnection(ELBConnection):
    host = ELB_EU_WEST_HOST

class ELBAPSEConnection(ELBConnection):
    host = ELB_AP_SOUTHEAST_HOST

class ELBAPNEConnection(ELBConnection):
    host = ELB_AP_NORTHEAST_HOST

class ELBSAEastConnection(ELBConnection):
    host = ELB_SA_EAST_HOST

class AWSLBDriver(Driver):
    connectionCls = ELBConnection
    path = '/'
    name = 'AWS'

    LB_STATE_MAP = { 'On': State.RUNNING,
                     'Unknown': State.UNKNOWN }

    def list_protocols(self):
        return ['tcp', 'http']

    def list_balancers(self):
        params = {'Action': 'DescribeLoadBalancers'}

        return self._to_balancers(self.connection.request('/', params=params).object)

    def create_balancer(self, name, port, protocol, algorithm, members):
        response = self._post('/%s/load_balancers' % API_VERSION, {
          'name': name,
          'nodes': list(map(self._member_to_node, members)),
          'policy': self._algorithm_to_value(algorithm),
          'listeners': [{'in': port, 'out': port, 'protocol': protocol}],
          'healthcheck': {'type': protocol, 'port': port}
        })

        return self._to_balancer(response.object)

    def destroy_balancer(self, balancer):
        response = self.connection.request('/%s/load_balancers/%s' %
                                           (API_VERSION, balancer.id),
                                           method='DELETE')

        return response.status == httplib.ACCEPTED

    def get_balancer(self, balancer_id):
        data = self.connection.request('/%s/load_balancers/%s' % (API_VERSION,
                                                         balancer_id)).object

        return self._to_balancer(data)

    def balancer_attach_compute_node(self, balancer, node):
        return self.balancer_attach_member(balancer, node)

    def balancer_attach_member(self, balancer, member):
        path = '/%s/load_balancers/%s/add_nodes' % (API_VERSION, balancer.id)

        response = self._post(path, {'nodes': [self._member_to_node(member)]})

        return member

    def balancer_detach_member(self, balancer, member):
        path = '/%s/load_balancers/%s/remove_nodes' % (API_VERSION,
                                                       balancer.id)

        response = self._post(path, {'nodes': [self._member_to_node(member)]})

        return response.status == httplib.ACCEPTED

    def balancer_list_members(self, balancer):
        path = '/%s/load_balancers/%s' % (API_VERSION, balancer.id)

        data = self.connection.request(path).object

        return list(map(self._node_to_member, data['nodes']))

    def _post(self, path, data={}):
        headers = {'Content-Type': 'application/json'}

        return self.connection.request(path, data=data, headers=headers,
                                       method='POST')

    def _to_balancers(self, elem):
        return [self._to_balancer(rs) for rs in findall(element=elem, 
            xpath='DescribeLoadBalancersResult/LoadBalancerDescriptions/member',
            namespace=NAMESPACE)]

    def _to_balancer(self, rs):
        return LoadBalancer(
            id=findtext(rs, 'LoadBalancerName', NAMESPACE),
            name=findtext(rs, 'LoadBalancerName', NAMESPACE),
            state=self.LB_STATE_MAP.get('On', State.UNKNOWN),
            ip=findtext(rs, 'DNSName', NAMESPACE),
            port=[findtext(r, 'Listener/LoadBalancerPort', NAMESPACE) 
            for r in findall(element=rs, 
                xpath='ListenerDescriptions/member', 
                namespace=NAMESPACE)],
            driver=self.connection.driver
        )

    def _member_to_node(self, member):
        return {'node': member.id}

    def _node_to_member(self, data):
        return Member(data['id'], None, None)

    def _public_ip(self, data):
        if len(data['cloud_ips']) > 0:
            ip = data['cloud_ips'][0]['public_ip']
        else:
            ip = None

class ELBUSWestDriver(AWSLBDriver):
    """
    Driver class for EC2 in the South America (Sao Paulo) Region
    """

    api_name = 'elb_us_west'
    name = 'Amazon ELB (us-west-1)'
    friendly_name = 'Amazon US West N. California'
    country = 'US'
    region_name = 'us-west-1'
    connectionCls = ELBUSWestConnection

class ELBUSWestOregonDriver(AWSLBDriver):
    """
    Driver class for EC2 in the US West Oregon region.
    """

    api_name = 'elb_us_west_oregon'
    name = 'Amazon ELB (us-west-2)'
    friendly_name = 'Amazon US West - Oregon'
    country = 'US'
    region_name = 'us-west-2'
    connectionCls = ELBUSWestOregonConnection

class ELBEUWestDriver(AWSLBDriver):
    """
    Driver class for EC2 in the Western Europe Region
    """

    api_name = 'elb_eu_west'
    name = 'Amazon ELB (eu-west-1)'
    friendly_name = 'Amazon Europe Ireland'
    country = 'IE'
    region_name = 'eu-west-1'
    connectionCls = ELBEUWestConnection

class ELBAPSEDriver(AWSLBDriver):
    """
    Driver class for EC2 in the Southeast Asia Pacific Region
    """

    api_name = 'elb_ap_southeast'
    name = 'Amazon ELB (ap-southeast-1)'
    friendly_name = 'Amazon Asia-Pacific Singapore'
    country = 'SG'
    region_name = 'ap-southeast-1'
    connectionCls = ELBAPSEConnection

class ELBAPNEDriver(AWSLBDriver):
    """
    Driver class for EC2 in the Northeast Asia Pacific Region
    """

    api_name = 'elb_ap_northeast'
    name = 'Amazon ELB (ap-northeast-1)'
    friendly_name = 'Amazon Asia-Pacific Tokyo'
    country = 'JP'
    region_name = 'ap-northeast-1'
    connectionCls = ELBAPNEConnection

class ELBSAEastDriver(AWSLBDriver):
    """
    Driver class for EC2 in the South America (Sao Paulo) Region
    """

    api_name = 'elb_sa_east'
    name = 'Amazon ELB (sa-east-1)'
    friendly_name = 'Amazon South America Sao Paulo'
    country = 'BR'
    region_name = 'sa-east-1'
    connectionCls = ELBSAEastConnection
