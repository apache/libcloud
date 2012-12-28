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

from libcloud.utils.py3 import urlquote
from libcloud.utils.py3 import b

from libcloud.utils.xml import findtext, findall, fixxpath
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Driver, LoadBalancer, Algorithm, Member
from libcloud.common.types import LibcloudError
from libcloud.common.aws import AWSBaseResponse
from libcloud.common.base import ConnectionUserAndKey


API_VERSION = '2012-06-01'
API_HOST = 'elasticloadbalancing.eu-west-1.amazonaws.com'
API_ROOT = '/%s/' % (API_VERSION)
API_NAMESPACE = 'http://elasticloadbalancing.amazonaws.com/doc/%s/' % (API_VERSION, )


class ELBError(LibcloudError):
    def __init__(self, code, errors):
        self.code = code
        self.errors = errors or []

    def __str__(self):
        return 'Errors: %s' % (', '.join(self.errors))

    def __repr__(self):
        return('<ELB response code=%s>' %
               (self.code, len(self.errors)))


class ELBDNSResponse(AWSBaseResponse):
    """
    Amazon ELB response class.
    """
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def error(self):
        status = int(self.status)

        if status == 403:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)

        elif status == 400:
            context = self.connection.context
            messages = []
            if context['InvalidChangeBatch']['Messages']:
                for message in context['InvalidChangeBatch']['Messages']:
                    messages.append(message['Message'])

                raise ELBError('InvalidChangeBatch message(s): %s ',
                                   messages)


class ELBConnection(ConnectionUserAndKey):
    host = API_HOST

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


class ElasticLoadBalancerDriver(Driver):

    name = 'ELB'
    website = 'http://aws.amazon.com/elasticloadbalancing/'
    connectionCls = ELBConnection

    def list_protocols(self):
        return ["tcp", "ssl", "http", "https"]

    def list_balancers(self):
        params = {
            "Action": "DescribeLoadBalancers",
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)
        return self._to_balancers(data)

    def create_balancer(self, name, port, protocol, algorithm, members):
        params = {
            "Action": "CreateLoadBalancer",
            "LoadBalancerName": name,
            "Listeners.member.1.InstancePort": str(port),
            "Listeners.member.1.InstanceProtocol": protocol.upper(),
            "Listeners.member.1.LoadBalancerPort": str(port),
            "Listeners.member.1.Protocol": protocol.upper(),
            "AvailabilityZones.member.1": "eu-west-1a",
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)

        lb = LoadBalancer(
            id=name,
            name=name,
            state=State.UNKNOWN,
            ip=findtext(element=data, xpath="DNSName", namespace=API_NAMESPACE),
            port=port,
            driver=self.connection.driver
            )
        lb._members = []

        return lb

    def destroy_balancer(self, balancer):
        params = {
            "Action": "DeleteLoadBalancer",
            "LoadBalancerName": balancer.id,
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)

    def get_balancer(self, balancer_id):
        params = {
            "Action": "DescribeLoadBalancers",
            "LoadBalancerNames.member.1": balancer_id,
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)
        return self._to_balancers(data)[0]

    def balancer_attach_compute_node(self, balancer, node):
        params = {
            "Action": "RegisterInstancesWithLoadBalancer",
            "LoadBalancerName": balancer.id,
            "Instances.member.1.InstanceId": node.id,
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)
        balancer._members.append(Member(node.id, None, None, balancer=self))

    def balancer_attach_member(self, balancer, member):
        raise LibcloudError("Can only attach compute nodes to elastic load balancers")

    def balancer_detach_member(self, balancer, member):
        params = {
            "Action": "DeregisterInstancesFromLoadBalancer",
            "LoadBalancerName": balancer.id,
            "Instances.member.1.InstanceId": member.id,
            }
        results = self.connection.request(API_ROOT, params=params).object
        data = ET.XML(results)
        balancer._members = [m for m in balancer._members if m.id != member.id]

    def balancer_list_members(self, balancer):
        return balancer._members

    def _to_balancers(self, object):
        xpath = "DescribeLoadBalancersResult/LoadBalancerDescriptions/member"
        return [self._to_balancer(el)
                for el in findall(element=object,xpath=xpath,namespace=API_NAMESPACE)]

    def _to_balancer(self, element):
        name = findtext(element=element, xpath="LoadBalancerName", namespace=API_NAMESPACE)
        dns_name = findtext(element, xpath="DNSName", namespace=API_NAMESPACE)
        port = findtext(element, xpath="LoadBalancerPort", namespace=API_NAMESPACE)

        lb = LoadBalancer(
            id=name,
            name=name,
            state=State.UNKNOWN,
            ip=dns_name,
            port=port,
            driver=self.connection.driver
            )

        members = findall(element=element, xpath="Instances/member/InstanceId", namespace=API_NAMESPACE)
        lb._members = [Member(m.text, None, None, balancer=self) for m in members]

        return lb


