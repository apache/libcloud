# Licensed to libcloud.org under one or more
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

from libcloud.types import Provider, NodeState
from libcloud.base import ConnectionKey, Response, NodeDriver, Node

try:
    import json
except:
    import simplejson as json

class LinodeResponse(Response):

    def parse_body(self):
        return json.loads(self.body)

class LinodeConnection(ConnectionKey):
    host = 'api.linode.com'
    responseCls = LinodeResponse

    def add_default_params(self, params):
        params['api_key'] = self.key
        return params

class LinodeNodeDriver(NodeDriver):
    type = Provider.LINODE
    name = 'Linode'
    connectionCls = LinodeConnection

    NODE_STATE_MAP = { 2: NodeState.RUNNING }

    def list_nodes(self):
        params = {'api_action': 'linode.list'}
        obj = self.connection.request('/', params=params).object
        return [ self._to_node(node) for node in obj['DATA'] ]

    def _to_node(self, obj):
        """
        this transforms linode API output into a libcloud node object
        """
        # id is always the unique ID that came from the provider
        id = obj['LINODEID']
        public_ip = None
        private_ip = None

        # we have to do another API call, since linode does not return the 
        # ipaddress in the general node list
        params = {'api_action': 'linode.ip.list', 'LinodeID': id}
        ips = self.connection.request('/', params=params).object['DATA']
        for ip in ips:  
            addr = ip['IPADDRESS']
            if ip['ISPUBLIC']:
                public_ip = addr
            else:
                private_ip = addr

        # try to look up this status, otherwise report unknown
        state = self.NODE_STATE_MAP.get(obj['STATUS'], NodeState.UNKNOWN)
            
        n = Node(id=id,
                 name=obj['LABEL'],
                 state=state,
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver)

        return n
