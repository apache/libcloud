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

import sys
import unittest
import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse

from libcloud.common.types import LibcloudError
from libcloud.compute.base import Node
from libcloud.compute.drivers.dummy import DummyNodeDriver
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.gogrid import GoGridLBDriver

from libcloud.test import MockHttpTestCase
from libcloud.test.file_fixtures import LoadBalancerFileFixtures

from .elb import AWSParamAdaptor


# Helper methods to make GoGrid's odd serialization easier to generate
def list_container(iterable):
    return {
        'list': list(iterable),
    }

def option(description='', id=1, name='None', object='option'):
    return {
        'description': description,
        'id': id,
        'name': name,
        'object': object,
    }


class GoGridLBMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('gogrid')

    @property
    def driver(self):
        return self.test.mock

    def response(self, method, results):
        response = {
            'list': results,
            'method': method,
            'status': 'success',
            'summary': {
                'numpages': 0,
                'returned': len(results),
                'start': 0,
                'total': len(results)
            }
        }
        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _from_member(self, member):
        return {
            'ip': {
                'datacenter': option(description='US West 1 Datacenter', name='US-West-1'),
                'id': member.id,
                'ip': member.ip,
                'public': True,
                'state': option(description='IP is available to use', name='Unassigned'),
                'subnet': '10.0.0.64/255.255.255.240',
            },
            'object': 'ipportpair',
            'port': member.port,
        }

    def _from_balancer(self, balancer):
        datacenter = option(description='US West 1 Datacenter', name='US-West-1')

        members = []
        for member in balancer.list_members():
            members.append(self._from_member(member))

        return {
            'datacenter': datacenter,
            'id': balancer.id,
            'name': balancer.name,
            'object': 'loadbalancer',
            'os':  option(description='The F5 Load Balancer', name='F5'),
            'persistence': option(),
            'realiplist': members,
            'state': option(description='Loadbalancer is enabled and on.', name ='On'),
            'type': option(description='', name='Round Robin'),
            'virtualip': {
                'ip': {
                    'datacenter': datacenter,
                    'id': 1868101,
                    'ip': balancer.ip,
                    'object': 'ip',
                    'public': True,
                    'state': option(description='IP is reserved or in use', name='Assigned'),
                    'subnet': '10.0.0.64/255.255.255.240'
                },
                'object': 'ipportpair',
                'port': balancer.port,
            }
        }

    def _api_grid_loadbalancer_list(self, method, url, body, headers):
        balancers = []
        for balancer in self.driver.list_balancers():
            balancers.append(self._from_balancer(balancer))

        return self.response('/grid/loadbalancer/add', balancers)

    def _api_grid_ip_list(self, method, url, body, headers):
        results = []
        for i in range(16):
            results.append({
                "datacenter": {
                    "description": "US East 1 Datacenter",
                    "id": 2,
                    "name": "US-East-1",
                    "object": "option",
                    },
                'id': i,
                'ip': '10.0.0.1%d' % i,
                'object': 'ip',
                'public': 'true',
                'state': {
                    'description': 'IP is available to use',
                    'id': 1,
                    'name': 'Unassigned',
                    'object': 'option',
                    },
                'subnet': '10.0.0.0/255.255.255.0',
                })

        return self.response('/grid/ip/list', results)

    def _api_grid_loadbalancer_add(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)

        members = []
        for member in params.get_list_of_structs('realiplist'):
            members.append(Member(id=None, ip=member['ip'], port=int(member['port'])))

        balancer = self.driver.create_balancer(
            name=params['name'],
            algorithm=params['loadbalancer.type'],
            #p=params['virtualip.ip'],
            port=params['virtualip.port'],
            protocol='http',
            members=members,
            )

        return self.response('/grid/loadbalancer/add', [self._from_balancer(balancer)])

    def _api_grid_loadbalancer_delete(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        self.driver.get_balancer(params['id']).destroy()

        return self.response("/grid/loadbalancer/delete", [])

    def _api_grid_loadbalancer_get(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        id = params.get('id')
        name = params.get('name')

        balancers = []
        for balancer in self.driver.list_balancers():
            if id and balancer.id != id:
                continue
            if name and balancer.name != id:
                continue
            balancers.append(self._from_balancer(balancer))

        return self.response('/grid/loadbalancer/get', balancers)

    def _api_grid_loadbalancer_edit(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        balancer = self.driver.get_balancer(params['id'])

        members = []
        for member in params.get_list_of_structs('realiplist'):
            members.append(Member(id=None, ip=member['ip'], port=int(member['port'])))

        for outgoing in members:
            for incoming in balancer.list_members():
                if incoming.ip == outgoing.ip and incoming.port == outgoing.port:
                    break
            else:
                balancer.attach_member(outgoing)

        for incoming in balancer.list_members():
            for outgoing in members:
                if outgoing.ip == incoming.ip and outgoing.port == incoming.port:
                    break
            else:
                balancer.detach_member(incoming)

        return self.response('/grid/loadbalancer/edit', [self._from_balancer(balancer)])

    def _api_grid_ip_list_UNEXPECTED_ERROR(self, method, url, body, headers):
        return self._api_grid_ip_list(method, url, body, headers)

    def _api_grid_loadbalancer_add_UNEXPECTED_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('unexpected_error.json')
        return (httplib.INTERNAL_SERVER_ERROR, body, {}, httplib.responses[httplib.OK])

