# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
"""
Softlayer driver
"""

import xmlrpclib

import libcloud
from libcloud.types import Provider, InvalidCredsException, NodeState
from libcloud.base import NodeDriver, Node, NodeLocation

DATACENTERS = {
    'sea01': {'country': 'US'},
    'wdc01': {'country': 'US'},
    'dal01': {'country': 'US'}
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'HALTED': NodeState.TERMINATED,
    'PAUSED': NodeState.TERMINATED,
}

class SoftLayerException(Exception):
    pass

class SoftLayerSafeTransport(xmlrpclib.SafeTransport):
    pass

class SoftLayerTransport(xmlrpclib.Transport):
    pass

class SoftLayerProxy(xmlrpclib.ServerProxy):
    transportCls = (SoftLayerTransport, SoftLayerSafeTransport)
    API_PREFIX = "http://api.service.softlayer.com/xmlrpc/v3"

    def __init__(self, service, user_agent, verbose=0):
        cls = self.transportCls[0]
        if SoftLayerProxy.API_PREFIX[:8] == "https://":
            cls = self.transportCls[1]
        t = cls(use_datetime=0)
        t.user_agent = user_agent
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s/%s" % (SoftLayerProxy.API_PREFIX, service),
            transport=t,
            verbose=verbose
        )

class SoftLayerConnection(object):
    proxyCls = SoftLayerProxy
    driver = None

    def __init__(self, user, key):
        self.user = user
        self.key = key 
        self.ua = []

    def request(self, service, method, *args, **kwargs):
        sl = self.proxyCls(service, self._user_agent())

        headers = {}
        headers.update(self._get_auth_headers())
        headers.update(self._get_init_params(service, kwargs.get('id')))
        headers.update(self._get_object_mask(service, kwargs.get('object_mask')))
        params = [{'headers': headers}] + list(args)

        try:
            return getattr(sl, method)(*params)
        except xmlrpclib.Fault, e:
            if e.faultCode == "SoftLayer_Account":
                raise InvalidCredsException(e.faultString)
            raise SoftLayerException(e)

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                libcloud.__version__,
                self.driver.name,
                "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, s):
        self.ua.append(s)

    def _get_auth_headers(self):
        return {
            'authenticate': {
                'username': self.user,
                'apiKey': self.key
            }
        }

    def _get_init_params(self, service, id):
        if id is not None:
            return {
                '%sInitParameters' % service: {'id': id}
            }
        else:
            return {}

    def _get_object_mask(self, service, mask):
        if mask is not None:
            return {
                '%sObjectMask' % service: {'mask': mask}
            }
        else:
            return {}

class SoftLayerNodeDriver(NodeDriver):
    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    type = Provider.SOFTLAYER

    def __init__(self, key, secret=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = self.connectionCls(key, secret)
        self.connection.driver = self

    def _to_node(self, host):
        return Node(
            id=host['id'],
            name=host['hostname'],
            state=NODE_STATE_MAP.get(
                host['powerState']['keyName'],
                NodeState.UNKNOWN
            ),
            public_ip=host['primaryIpAddress'],
            private_ip=host['primaryBackendIpAddress'],
            driver=self
        )
    
    def _to_nodes(self, hosts):
        return [self._to_node(h) for h in hosts]

    def destroy_node(self, node):
        billing_item = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "getBillingItem",
            id=node.id
        )

        if billing_item:
            res = self.connection.request(
                "SoftLayer_Billing_Item",
                "cancelService",
                id=billing_item['id']
            )
            return res
        else:
            return False

    def create_node(self, **kwargs):
        """
        Right now the best way to create a new node in softlayer is by 
        cloning an already created node, so size and image do not apply.

        @keyword    node:   A Node which will serve as the template for the new node
        @type       node:   L{Node}

        @keyword    domain:   e.g. libcloud.org
        @type       domain:   str
        """
        name = kwargs['name']
        location = kwargs['location']
        node = kwargs['node']
        domain = kwargs['domain']

        res = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "getOrderTemplate",
            "HOURLY",
            id=node.id
        )

        res['location'] = location.id
        res['complexType'] = 'SoftLayer_Container_Product_Order_Virtual_Guest'
        res['quantity'] = 1
        res['virtualGuests'] = [
            {
                'hostname': name,
                'domain': domain
            }
        ]

        res = self.connection.request(
            "SoftLayer_Product_Order",
            "placeOrder",
            res
        )

        return None # the instance won't be available for a while.

    def _to_loc(self, loc):
        return NodeLocation(
            id=loc['id'],
            name=loc['name'],
            country=DATACENTERS[loc['name']]['country'],
            driver=self
        )

    def list_locations(self):
        res = self.connection.request(
            "SoftLayer_Location_Datacenter",
            "getDatacenters"
        ) 

        # checking "in DATACENTERS", because some of the locations returned by getDatacenters are not useable.
        return [self._to_loc(l) for l in res if l['name'] in DATACENTERS]     

    def list_nodes(self):
        mask = {
            'virtualGuests': {'powerState': ''}
        }
        res = self.connection.request(
            "SoftLayer_Account",
            "getVirtualGuests",
            object_mask=mask
        )
        nodes = self._to_nodes(res)
        return nodes

    def reboot_node(self, node):
        res = self.connection.request(
            "SoftLayer_Virtual_Guest", 
            "rebootHard", 
            id=node.id
        )
        return res
