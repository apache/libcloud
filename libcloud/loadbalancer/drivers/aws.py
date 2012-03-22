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

AWS_AVAILABILITY_ZONE_MAP = {
    'us-east-1': ['us-east-1a', 'us-east-1b', 'us-east-1c', 
        'us-east-1d', 'us-east-1e'],
    'us-west-1': ['us-west-1a', 'us-west-1b', 'us-west-1c'],
    'us-west-2': ['us-west-2a', 'us-west-2b'],
    'eu-west-1': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
    'ap-northeast-1': ['ap-northeast-1a', 'ap-northeast-1b'],
    'ap-southeast-1': ['ap-southeast-1a', 'ap-southeast-1b'],
    'sa-east-1': ['sa-east-1a', 'sa-east-1b']
}

class ELBResponse(AWSBaseResponse):
    pass

class ELBConnection(EC2Connection):
    host = ELB_US_EAST_HOST
    responseCls = ELBResponse

    # hack to get the new API_VERSION in
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
        return ['TCP', 'HTTP', 'HTTPS']

    def list_balancers(self, ex_balancer_ids=None):
        params = {'Action': 'DescribeLoadBalancers'}

        if ex_balancer_ids:
            params.update(
                self._pathlist('LoadBalancerNames.member', ex_balancer_ids))

        return self._to_balancers(
            self.connection.request('/', params=params).object)

    def create_balancer(self, name, port, protocol, algorithm, members):
        params = {'Action': 'CreateLoadBalancer', 'LoadBalancerName': name}

        params.update(
            {'Listeners.member.1.LoadBalancerPort': str(port),
            'Listeners.member.1.InstancePort': str(members[0].port),
            'Listeners.member.1.Protocol': protocol})
        params.update(
            self._pathlist('AvailabilityZones.member', 
            AWS_AVAILABILITY_ZONE_MAP.get(self.region_name)))

        balancer = self._to_balancer_from_response(
            self.connection.request('/', params=params).object, name, port)

        # will now register instances to the loadbalancer
        map(self.balancer_attach_member, 
            [balancer for member in members], members)

        return balancer

    def destroy_balancer(self, balancer):
        params = {'Action': 'DeleteLoadBalancer', 
            'LoadBalancerName': balancer.name}

        response = self.connection.request('/', params=params)

        return response.status == httplib.OK

    def get_balancer(self, balancer_id):

        return self.list_balancers([balancer_id])[0]

    def balancer_attach_compute_node(self, balancer, node):
        return self.balancer_attach_member(balancer, node)

    def balancer_attach_member(self, balancer, member):
        params = {'Action': 'RegisterInstancesWithLoadBalancer', 
            'LoadBalancerName': balancer.name}
        params.update({'Instances.member.1.InstanceId': member.id})

        self.connection.request('/', params=params)
        return member

    def balancer_detach_member(self, balancer, member):
        params = {'Action': 'DeregisterInstancesFromLoadBalancer', 
            'LoadBalancerName': balancer.name}
        params.update({'Instances.member.1.InstanceId': member.id})

        response = self.connection.request('/', params=params)
        return response.status == httplib.OK

    def balancer_list_members(self, balancer):
        params = {'Action': 'DescribeLoadBalancers'}
        params.update(self._pathlist('LoadBalancerNames.member', [balancer.id]))

        data = self.connection.request('/', params=params).object
        rs = findall(
            element=data,
            xpath='DescribeLoadBalancersResult/LoadBalancerDescriptions/member',
            namespace=NAMESPACE)[0]

        node_elems = findall(
            element=rs,
            xpath='Instances/member',
            namespace=NAMESPACE)

        listener_elem = findall(
            element=rs,
            xpath='ListenerDescriptions/member',
            namespace=NAMESPACE)[0]

        port = findtext(
            listener_elem,
            'Listener/InstancePort',
            NAMESPACE)

        return list(map(self._node_to_member, node_elems, [port for e in node_elems]))

    def _pathlist(self, key, arr):
        """
        Converts a key and an array of values into AWS query param format.
        """
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def _to_balancer_from_response(self, response, name, port):
        # we parse the dns name from the response
        DNSName = findtext(response, 'DNSName', NAMESPACE)

        return LoadBalancer(
            id=name,
            name=name,
            state=self.LB_STATE_MAP.get('On', State.UNKNOWN),
            ip=DNSName,
            port=port,
            driver=self.connection.driver
        )

    def _post(self, path, data={}):
        headers = {'Content-Type': 'application/json'}

        return self.connection.request(path, data=data, headers=headers,
                                       method='POST')

    def _to_balancers(self, elem):
        return [self._to_balancer(rs) for rs in findall(
            element=elem, 
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

    def _node_to_member(self, data, port):
        return Member(findtext(data, 'InstanceId', NAMESPACE), None, port)

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
