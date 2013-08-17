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

import json
import re

from libcloud.utils.py3 import httplib
from libcloud.test import MockHttpTestCase
from libcloud.loadbalancer.types import State
from libcloud.test.file_fixtures import LoadBalancerFileFixtures
from libcloud.loadbalancer.base import Member, DEFAULT_ALGORITHM


class BrightboxLBMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('brightbox')

    routes = [
        ('^/1.0/load_balancers/(?P<balancer>[^/]+)$', '_1_0_load_balancers_BALANCERID'),
        ('^/1.0/load_balancers/(?P<balancer>[^/]+)/add_nodes$', '_1_0_load_balancers_BALANCERID_add_nodes'),
        ('^/1.0/load_balancers/(?P<balancer>[^/]+)/remove_nodes$', '_1_0_load_balancers_BALANCERID_remove_nodes'),
    ]

    @property
    def driver(self):
        return self.test.mock

    def _get_method_name(self, type, use_param, qs, path):
        for route, method_name in self.routes:
            if re.match(route, path):
                return method_name
        return MockHttpTestCase._get_method_name(self, type, use_param, qs, path)

    def _get_balancerid(self, url):
        return url.split('/')[3]

    def _to_json(self, balancer):
        state = {
            State.RUNNING: "active",
            State.PENDING: "creating",
        }[balancer.state]

        b = {
            "id": balancer.id,
            "resource_type": "load_balancer",
            "url": "https://api.gb1.brightbox.com/1.0/load_balancers/" + balancer.id,
            "name": balancer.name,
            "created_at": "2011-10-06T14:50:28Z",
            "deleted_at": None,
            "status": state,
            "listeners": [{"out": balancer.port, "protocol": '', "in": balancer.port}],
            "cloud_ips": [{
                "id": "cip-c2v98",
                "public_ip": "109.107.37.179",
                "resource_type": "cloud_ip",
                "reverse_dns": "cip-109-107-37-179.gb1.brightbox.com",
                "status": "mapped",
                "url": "https://api.gb1.brightbox.com/1.0/cloud_ips/cip-c2v98"
            }],
            "account": {
                "id": "acc-43ks4",
                "resource_type": "account",
                "url": "https://api.gb1.brightbox.com/1.0/account",
                "name": "Brightbox",
                "status": "active"
            },
            "nodes": [],
        }

        for m in balancer.list_members():
            b['nodes'].append({
                "id": m.id,
                "resource_type": "server",
                "url": "https://api.gb1.brightbox.com/1.0/servers/srv-lv426",
                "name": "web1",
                "created_at": "2011-10-01T01:00:00Z",
                "deleted_at": None,
                "hostname": "srv-lv426",
                "started_at": "2011-10-01T01:01:00Z",
                "status": "active",
            })

        return b

    def _token(self, method, url, body, headers):
        assert method == 'POST'
        body = json.dumps({
            "access_token": "k1bjflpsaj8wnrbrwzad0eqo36nxiha",
            "expires_in": 3600,
        })
        return self.response(httplib.OK, body)

    def _1_0_load_balancers(self, method, url, body, headers):
        if method == 'GET':
            balancers = [self._to_json(b) for b in self.driver.list_balancers()]
            balancers_json = json.dumps(balancers)
            return self.response(httplib.OK, balancers_json)
        elif method == 'POST':
            args = json.loads(body)
            listener = args['listeners'][0]
            balancer = self.driver.create_balancer(
                name=args['name'],
                port=listener['in'],
                protocol=listener['protocol'].lower(),
                algorithm=DEFAULT_ALGORITHM,
                members=[],
            )
            body = json.dumps(self._to_json(balancer))
            return self.response(httplib.ACCEPTED, body)

    def _1_0_load_balancers_BALANCERID(self, method, url, body, headers):
        balancer = self.driver.get_balancer(self._get_balancerid(url))
        if method == 'GET':
            body = json.dumps(self._to_json(balancer))
            return self.response(httplib.OK, body)
        elif method == 'DELETE':
            balancer.destroy()
            return self.response(httplib.ACCEPTED, '')

    def _1_0_load_balancers_BALANCERID_add_nodes(self, method, url, body,
                                                headers):
        balancer = self.driver.get_balancer(self._get_balancerid(url))
        data = json.loads(body)
        if method == 'POST':
            for node in data['nodes']:
                member = Member(id=node['node'], ip=None, port=None)
                balancer.attach_member(member)
            return self.response(httplib.ACCEPTED, '')

    def _1_0_load_balancers_BALANCERID_remove_nodes(self, method, url, body,
                                                   headers):
        balancer = self.driver.get_balancer(self._get_balancerid(url))
        data = json.loads(body)
        if method == 'POST':
            for node in data['nodes']:
                member = Member(id=node['node'], ip=None, port=None)
                balancer.detach_member(member)
            return self.response(httplib.ACCEPTED, '')

    def response(self, status, body):
        return (status, body, {'content-type': 'application/json'},
                httplib.responses[status])

