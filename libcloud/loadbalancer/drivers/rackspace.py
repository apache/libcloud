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

import os

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils import reverse_dict
from libcloud.common.base import JsonResponse
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.types import State
from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.rackspace import (
        AUTH_URL_US, AUTH_URL_UK)

class RackspaceResponse(JsonResponse):

    def parse_body(self):
        if not self.body:
            return None
        return super(RackspaceResponse, self).parse_body()

    def success(self):
        return 200 <= int(self.status) <= 299


class RackspaceConnection(OpenStackBaseConnection):
    responseCls = RackspaceResponse
    auth_url = AUTH_URL_US
    _url_key = "lb_url"

    def __init__(self, user_id, key, secure=True):
        super(RackspaceConnection, self).__init__(user_id, key, secure)
        self.api_version = 'v1.0'
        self.accept_format = 'application/json'

    def request(self, action, params=None, data='', headers=None, method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ('POST', 'PUT'):
            headers['Content-Type'] = 'application/json'
        if method == 'GET':
            params['cache-busing'] = os.urandom(8).encode('hex')

        return super(RackspaceConnection, self).request(action=action,
                params=params, data=data, method=method, headers=headers)


class RackspaceUKConnection(RackspaceConnection):
    auth_url = AUTH_URL_UK


class RackspaceLBDriver(Driver):
    connectionCls = RackspaceConnection
    api_name = 'rackspace_lb'
    name = 'Rackspace LB'

    LB_STATE_MAP = { 'ACTIVE': State.RUNNING,
                     'BUILD': State.PENDING }
    _VALUE_TO_ALGORITHM_MAP = {
        'RANDOM': Algorithm.RANDOM,
        'ROUND_ROBIN': Algorithm.ROUND_ROBIN,
        'LEAST_CONNECTIONS': Algorithm.LEAST_CONNECTIONS
    }
    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    def list_protocols(self):
        return self._to_protocols(
                   self.connection.request('/loadbalancers/protocols').object)

    def list_balancers(self):
        return self._to_balancers(
                self.connection.request('/loadbalancers').object)

    def create_balancer(self, name, members, protocol='http',
                        port=80, algorithm=DEFAULT_ALGORITHM):
        algorithm = self._algorithm_to_value(algorithm)

        balancer_object = {"loadBalancer":
                {"name": name,
                    "port": port,
                    "algorithm": algorithm,
                    "protocol": protocol.upper(),
                    "virtualIps": [{"type": "PUBLIC"}],
                    "nodes": [{"address": member.ip,
                        "port": member.port,
                        "condition": "ENABLED"} for member in members],
                    }
                }

        resp = self.connection.request('/loadbalancers',
                method='POST',
                data=json.dumps(balancer_object))
        return self._to_balancer(resp.object["loadBalancer"])

    def destroy_balancer(self, balancer):
        uri = '/loadbalancers/%s' % (balancer.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == 202

    def get_balancer(self, balancer_id):
        uri = '/loadbalancers/%s' % (balancer_id)
        resp = self.connection.request(uri)

        return self._to_balancer(resp.object["loadBalancer"])

    def balancer_attach_member(self, balancer, member):
        ip = member.ip
        port = member.port

        member_object = {"nodes":
                [{"port": port,
                    "address": ip,
                    "condition": "ENABLED"}]
                }

        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        resp = self.connection.request(uri, method='POST',
                data=json.dumps(member_object))
        return self._to_members(resp.object)[0]

    def balancer_detach_member(self, balancer, member):
        # Loadbalancer always needs to have at least 1 member.
        # Last member cannot be detached. You can only disable it or destroy the
        # balancer.
        uri = '/loadbalancers/%s/nodes/%s' % (balancer.id, member.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == 202

    def balancer_list_members(self, balancer):
        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        return self._to_members(
                self.connection.request(uri).object)

    def _to_protocols(self, object):
        protocols = []
        for item in object["protocols"]:
            protocols.append(item['name'].lower())
        return protocols

    def _to_balancers(self, object):
        return [ self._to_balancer(el) for el in object["loadBalancers"] ]

    def _to_balancer(self, el):
        lb = LoadBalancer(id=el["id"],
                name=el["name"],
                state=self.LB_STATE_MAP.get(
                    el["status"], State.UNKNOWN),
                ip=el["virtualIps"][0]["address"],
                port=el["port"],
                driver=self.connection.driver)
        return lb

    def _to_members(self, object):
        return [ self._to_member(el) for el in object["nodes"] ]

    def _to_member(self, el):
        lbmember = Member(id=el["id"],
                ip=el["address"],
                port=el["port"])
        return lbmember


class RackspaceUKLBDriver(RackspaceLBDriver):
    connectionCls = RackspaceUKConnection
