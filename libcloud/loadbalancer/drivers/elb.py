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
    'ElasticLoadBalancerDriver'
]

import base64
import hmac
import datetime
import uuid
import time

from hashlib import sha256
from xml.etree import ElementTree as ET

from libcloud.utils.py3 import httplib, urlquote, b
from libcloud.utils.xml import findtext, findall, fixxpath
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Driver, LoadBalancer, Algorithm, Member
from libcloud.common.types import LibcloudError
from libcloud.common.aws import AWSBaseResponse
from libcloud.common.base import ConnectionUserAndKey


API_VERSION = '2012-06-01'
API_HOST = 'elasticloadbalancing.%s.amazonaws.com'
API_ROOT = '/%s/' % (API_VERSION)
API_NAMESPACE = 'http://elasticloadbalancing.amazonaws.com/doc/%s/' % (API_VERSION, )


class ELBResponse(AWSBaseResponse):
    """
    Amazon ELB response class.
    """
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_error(self):
        status = int(self.status)

        if status == 403:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)


class ELBConnection(ConnectionUserAndKey):
    host = API_HOST
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

    def _get_aws_auth_param(self, params, secret_key, path='/'):
        """
        Creates the signature required for AWS, per
        http://bit.ly/aR7GaQ [docs.amazonwebservices.com]:

        StringToSign = HTTPVerb + "\n" +
                       ValueOfHostHeaderInLowercase + "\n" +
                       HTTPRequestURI + "\n" +
                       CanonicalizedQueryString <from the preceding step>
        """
        keys = list(params.keys())
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urlquote(key, safe='') + '=' +
                         urlquote(params[key], safe='-_~'))

        qs = '&'.join(pairs)

        hostname = self.host
        if (self.secure and self.port != 443) or \
           (not self.secure and self.port != 80):
            hostname += ":" + str(self.port)

        string_to_sign = '\n'.join(('GET', hostname, path, qs))

        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key), b(string_to_sign),
                     digestmod=sha256).digest()
        )
        return b64_hmac.decode('utf-8')


class ElasticLBDriver(Driver):

    name = 'ELB'
    website = 'http://aws.amazon.com/elasticloadbalancing/'
    connectionCls = ELBConnection

    def __init__(self, access_id, secret, region):
        super(ElasticLBDriver, self).__init__(access_id, secret)
        self.region = region
        self.connection.host = API_HOST % region

    def list_protocols(self):
        return ['tcp', 'ssl', 'http', 'https']

    def list_balancers(self):
        params = {
            'Action': 'DescribeLoadBalancers',
            }
        data = self.connection.request(API_ROOT, params=params).object
        return self._to_balancers(data)

    def create_balancer(self, name, port, protocol, algorithm, members, ex_members_availability_zones=None):
        if not ex_members_availability_zones:
            ex_members_availability_zones = ['a']
        params = {
            'Action': 'CreateLoadBalancer',
            'LoadBalancerName': name,
            'Listeners.member.1.InstancePort': str(port),
            'Listeners.member.1.InstanceProtocol': protocol.upper(),
            'Listeners.member.1.LoadBalancerPort': str(port),
            'Listeners.member.1.Protocol': protocol.upper(),
            }
        for i, z in enumerate(ex_members_availability_zones, 1):
            params['AvailabilityZones.member.%d' % i] = '-'.join(self.region, z)

        data = self.connection.request(API_ROOT, params=params).object

        lb = LoadBalancer(
            id=name,
            name=name,
            state=State.PENDING,
            ip=findtext(element=data, xpath='DNSName', namespace=API_NAMESPACE),
            port=port,
            driver=self.connection.driver
            )
        lb._members = []

        return lb

    def destroy_balancer(self, balancer):
        params = {
            'Action': 'DeleteLoadBalancer',
            'LoadBalancerName': balancer.id,
            }
        data = self.connection.request(API_ROOT, params=params).object
        return True

    def get_balancer(self, balancer_id):
        params = {
            'Action': 'DescribeLoadBalancers',
            'LoadBalancerNames.member.1': balancer_id,
            }
        data = self.connection.request(API_ROOT, params=params).object
        return self._to_balancers(data)[0]

    def balancer_attach_compute_node(self, balancer, node):
        params = {
            'Action': 'RegisterInstancesWithLoadBalancer',
            'LoadBalancerName': balancer.id,
            'Instances.member.1.InstanceId': node.id,
            }
        data = self.connection.request(API_ROOT, params=params).object
        balancer._members.append(Member(node.id, None, None, balancer=self))

    def balancer_detach_member(self, balancer, member):
        params = {
            'Action': 'DeregisterInstancesFromLoadBalancer',
            'LoadBalancerName': balancer.id,
            'Instances.member.1.InstanceId': member.id,
            }
        data = self.connection.request(API_ROOT, params=params).object
        balancer._members = [m for m in balancer._members if m.id != member.id]
        return True

    def balancer_list_members(self, balancer):
        return balancer._members

    def _to_balancers(self, object):
        xpath = 'DescribeLoadBalancersResult/LoadBalancerDescriptions/member'
        return [self._to_balancer(el)
                for el in findall(element=object,xpath=xpath,namespace=API_NAMESPACE)]

    def _to_balancer(self, element):
        name = findtext(element=element, xpath='LoadBalancerName', namespace=API_NAMESPACE)
        dns_name = findtext(element, xpath='DNSName', namespace=API_NAMESPACE)
        port = findtext(element, xpath='LoadBalancerPort', namespace=API_NAMESPACE)

        lb = LoadBalancer(
            id=name,
            name=name,
            state=State.UNKNOWN,
            ip=dns_name,
            port=port,
            driver=self.connection.driver
            )

        members = findall(element=element, xpath='Instances/member/InstanceId', namespace=API_NAMESPACE)
        lb._members = [Member(m.text, None, None, balancer=lb) for m in members]

        return lb

