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
import time

try:
    import json
except ImportError:
    import simplejson

from libcloud.resource.lb.base import LB, LBNode, LBDriver
from libcloud.resource.lb.types import Provider, LBState, LibcloudLBImmutableError
from libcloud.common.gogrid import GoGridConnection, BaseGoGridDriver

class GoGridLBDriver(BaseGoGridDriver, LBDriver):
    connectionCls = GoGridConnection
    type = Provider.RACKSPACE
    api_name = 'gogrid_lb'
    name = 'GoGrid LB'

    LB_STATE_MAP = { 'On': LBState.RUNNING,
                     'Unknown': LBState.UNKNOWN }

    def list_balancers(self):
        return self._to_balancers(
                self.connection.request('/api/grid/loadbalancer/list').object)

    def ex_create_balancer_nowait(self, **kwargs):
        name = kwargs['name']
        port = kwargs['port']
        nodes = kwargs['nodes']

        params = {'name': name,
                'virtualip.ip': self._get_first_ip(),
                'virtualip.port': port}
        params.update(self._nodes_to_params(nodes))

        resp = self.connection.request('/api/grid/loadbalancer/add',
                method='GET',
                params=params)
        return self._to_balancers(resp.object)[0]

    def create_balancer(self, **kwargs):
        balancer = self.ex_create_balancer_nowait(**kwargs)

        timeout = 60 * 20
        waittime = 0
        interval = 2 * 15

        if balancer.id is not None:
            return balancer
        else:
            while waittime < timeout:
                balancers = self.list_balancers()

                for i in balancers:
                    if i.name == balancer.name and i.id is not None:
                        return i

                waittime += interval
                time.sleep(interval)

        raise Exception('Failed to get id')

    def destroy_balancer(self, balancer):
        try:
            resp = self.connection.request('/api/grid/loadbalancer/delete',
                    method='POST', params={'id': balancer.id})
        except Exception as err:
            if "Update request for LoadBalancer" in str(err):
                raise LibcloudLBImmutableError("Cannot delete immutable object",
                        GoGridLBDriver)
            else:
                raise

        return resp.status == 200

    def balancer_detail(self, **kwargs):
        params = {}

        try:
            params['name'] = kwargs['balancer_name']
        except KeyError:
            try:
                balancer_id = kwargs['balancer_id']
            except KeyError:
                balancer_id = kwargs['balancer'].id

            params['id'] = balancer_id

        resp = self.connection.request('/api/grid/loadbalancer/get',
                params=params)

        return self._to_balancers(resp.object)[0]

    def balancer_attach_node(self, balancer, **kwargs):
        ip = kwargs['ip']
        port = kwargs['port']

        nodes = self.balancer_list_nodes(balancer)
        nodes.append(LBNode(None, ip, port))

        params = {"id": balancer.id}

        params.update(self._nodes_to_params(nodes))

        resp = self._update_node(params)

        return [ node for node in
                self._to_nodes(resp.object["list"][0]["realiplist"])
                if node.ip == ip ][0]

    def balancer_detach_node(self, balancer, node):
        nodes = self.balancer_list_nodes(balancer)

        remaining_nodes = [n for n in nodes if n.id != node.id]

        params = {"id": balancer.id}
        params.update(self._nodes_to_params(remaining_nodes))

        resp = self._update_node(params)

        return resp.status == 200

    def balancer_list_nodes(self, balancer):
        resp = self.connection.request('/api/grid/loadbalancer/get',
                params={'id': balancer.id})
        return self._to_nodes(resp.object["list"][0]["realiplist"])

    def _update_node(self, params):
        try:
            return self.connection.request('/api/grid/loadbalancer/edit',
                    method='POST',
                    params=params)
        except Exception as err:
            if "Update already pending" in str(err):
                raise LibcloudLBImmutableError("Balancer is immutable", GoGridLBDriver)

        return None

    def _nodes_to_params(self, nodes):
        """
        Helper method to convert list of L{LBNode} objects
        to GET params.

        """

        params = {}

        i = 0
        for node in nodes:
            params["realiplist.%s.ip" % i] = node.ip
            params["realiplist.%s.port" % i] = node.port
            i += 1

        return params

    def _to_balancers(self, object):
        return [ self._to_balancer(el) for el in object["list"] ]

    def _to_balancer(self, el):
        lb = LB(id=el.get("id"),
                name=el["name"],
                state=self.LB_STATE_MAP.get(
                    el["state"]["name"], LBState.UNKNOWN),
                ip=el["virtualip"]["ip"]["ip"],
                port=el["virtualip"]["port"],
                driver=self.connection.driver)
        return lb

    def _to_nodes(self, object):
        return [ self._to_node(el) for el in object ]

    def _to_node(self, el):
        lbnode = LBNode(id=el["ip"]["id"],
                ip=el["ip"]["ip"],
                port=el["port"])
        return lbnode
