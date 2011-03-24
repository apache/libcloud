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
"""
Gandi driver
"""

import time
import xmlrpclib

import libcloud
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, NodeImage

# Global constants
API_VERSION = '2.0'
API_PREFIX = "https://rpc.gandi.net/xmlrpc/%s/" % API_VERSION

DEFAULT_TIMEOUT = 600   # operation pooling max seconds
DEFAULT_INTERVAL = 20   # seconds between 2 operation.info

NODE_STATE_MAP = {
    'running': NodeState.RUNNING,
    'halted': NodeState.TERMINATED,
    'paused': NodeState.TERMINATED,
    'locked' : NodeState.TERMINATED,
    'being_created' : NodeState.PENDING,
    'invalid' : NodeState.UNKNOWN,
    'legally_locked' : NodeState.PENDING,
    'deleted' : NodeState.TERMINATED
}

NODE_PRICE_HOURLY_USD = 0.02

class GandiException(Exception):
    """
    Exception class for Gandi driver
    """
    def __str__(self):
        return "(%u) %s" % (self.args[0], self.args[1])
    def __repr__(self):
        return "<GandiException code %u '%s'>" % (self.args[0], self.args[1])

class GandiSafeTransport(xmlrpclib.SafeTransport):
    pass

class GandiTransport(xmlrpclib.Transport):
    pass

class GandiProxy(xmlrpclib.ServerProxy):
    transportCls = (GandiTransport, GandiSafeTransport)

    def __init__(self,user_agent, verbose=0):
        cls = self.transportCls[0]
        if API_PREFIX.startswith("https://"):
            cls = self.transportCls[1]
        t = cls(use_datetime=0)
        t.user_agent = user_agent
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s" % (API_PREFIX),
            transport=t,
            verbose=verbose,
            allow_none=True
        )

class GandiConnection(object):
    """
    Connection class for the Gandi driver
    """

    proxyCls = GandiProxy
    driver = 'gandi'

    def __init__(self, user, password=None):
        self.ua = []

        # Connect only with an api_key generated on website
        self.api_key = user

        try:
            self._proxy = self.proxyCls(self._user_agent())
        except xmlrpclib.Fault, e:
            raise GandiException(1000, e)

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                libcloud.__version__,
                self.driver,
                "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, s):
        self.ua.append(s)

    def request(self,method,*args):
        """ Request xmlrpc method with given args"""
        try:
            return getattr(self._proxy, method)(self.api_key,*args)
        except xmlrpclib.Fault, e:
            raise GandiException(1001, e)


class GandiNodeDriver(NodeDriver):
    """
    Gandi node driver

    """
    connectionCls = GandiConnection
    name = 'Gandi'
    api_name = 'gandi'
    friendly_name = 'Gandi.net'
    country = 'FR'
    type = Provider.GANDI
    # TODO : which features to enable ?
    features = { }

    def __init__(self, key, secret=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = self.connectionCls(key, secret)
        self.connection.driver = self

    # Specific methods for gandi
    def _wait_operation(self, id, timeout=DEFAULT_TIMEOUT, check_interval=DEFAULT_INTERVAL):
        """ Wait for an operation to succeed"""

        for i in range(0, timeout, check_interval):
            try:
                op = self.connection.request('operation.info', int(id))

                if op['step'] == 'DONE':
                    return True
                if op['step'] in  ['ERROR','CANCEL']:
                    return False
            except (KeyError, IndexError):
                pass
            except Exception, e:
                raise GandiException(1002, e)

            time.sleep(check_interval)
        return False

    def _node_info(self,id):
        try:
            obj = self.connection.request('vm.info',int(id))
            return obj
        except Exception,e:
            raise GandiException(1003, e)
        return None

    # Generic methods for driver
    def _to_node(self, vm):
        return Node(
            id=vm['id'],
            name=vm['hostname'],
            state=NODE_STATE_MAP.get(
                vm['state'],
                NodeState.UNKNOWN
            ),
            public_ip=vm.get('ip'),
            private_ip='',
            driver=self,
            extra={
                'ai_active' : vm.get('ai_active'),
                'datacenter_id' : vm.get('datacenter_id'),
                'description' : vm.get('description')
            }
        )

    def _to_nodes(self, vms):
        return [self._to_node(v) for v in vms]

    def list_nodes(self):
        vms = self.connection.request('vm.list')
        ips = self.connection.request('ip.list')
        for vm in vms:
            for ip in ips:
                if vm['ifaces_id'][0] == ip['iface_id']:
                    vm['ip'] = ip.get('ip')

        nodes = self._to_nodes(vms)
        return nodes

    def reboot_node(self, node):
        op = self.connection.request('vm.reboot',int(node.id))
        op_res = self._wait_operation(op['id'])
        vm = self.connection.request('vm.info',int(node.id))
        if vm['state'] == 'running':
            return True
        return False

    def destroy_node(self, node):
        vm = self._node_info(node.id)
        if vm['state'] == 'running':
            # Send vm_stop and wait for accomplish
            op_stop = self.connection.request('vm.stop',int(node.id))
            if not self._wait_operation(op_stop['id']):
                raise GandiException(1010, 'vm.stop failed')
        # Delete
        op = self.connection.request('vm.delete',int(node.id))
        if self._wait_operation(op['id']):
            return True
        return False

    def deploy_node(self, **kwargs):
        raise NotImplementedError, \
            'deploy_node not implemented for gandi driver'

    def create_node(self, **kwargs):
        """Create a new Gandi node

        @keyword    name:   String with a name for this new node (required)
        @type       name:   str

        @keyword    image:  OS Image to boot on node. (required)
        @type       image:  L{NodeImage}

        @keyword    location: Which data center to create a node in. If empty,
                              undefined behavoir will be selected. (optional)
        @type       location: L{NodeLocation}

        @keyword    size:   The size of resources allocated to this node.
                            (required)
        @type       size:   L{NodeSize}

        @keyword    login:  user name to create for login on this machine (required)
        @type       login: String

        @keyword    password: password for user that'll be created (required)
        @type       password: String

        @keywork    inet_family: version of ip to use, default 4 (optional)
        @type       inet_family: int
        """

        if kwargs.get('login') is None or kwargs.get('password') is None:
            raise GandiException(1020, 'login and password must be defined for node creation')

        location = kwargs.get('location')
        if location and isinstance(location,NodeLocation):
            dc_id = int(location.id)
        else:
            raise GandiException(1021, 'location must be a subclass of NodeLocation')

        size = kwargs.get('size')
        if not size and not isinstance(size,NodeSize):
            raise GandiException(1022, 'size must be a subclass of NodeSize')

        src_disk_id = int(kwargs['image'].id)

        disk_spec = {
            'datacenter_id': dc_id,
            'name': 'disk_%s' % kwargs['name']
            }

        vm_spec = {
            'datacenter_id': dc_id,
            'hostname': kwargs['name'],
            'login': kwargs['login'],
            'password': kwargs['password'],  # TODO : use NodeAuthPassword
            'memory': int(size.ram),
            'cores': int(size.id),
            'bandwidth' : int(size.bandwidth),
            'ip_version':  kwargs.get('inet_family',4),
            }

        # Call create_from helper api. Return 3 operations : disk_create,
        # iface_create,vm_create
        (op_disk,op_iface,op_vm) = self.connection.request(
            'vm.create_from',
            vm_spec,disk_spec,src_disk_id
        )

        # We wait for vm_create to finish
        if self._wait_operation(op_vm['id']):
            # after successful operation, get ip information thru first interface
            node = self._node_info(op_vm['vm_id'])
            ifaces = node.get('ifaces')
            if len(ifaces) > 0:
                ips = ifaces[0].get('ips')
                if len(ips) > 0:
                    node['ip'] = ips[0]['ip']
            return self._to_node(node)

        return None

    def _to_image(self, img):
        return NodeImage(
            id=img['disk_id'],
            name=img['label'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        try:
            if location:
                filtering = { 'datacenter_id' : int(location.id) }
            else:
                filtering = {}
            images = self.connection.request('image.list', filtering )
            return [self._to_image(i) for i in images]
        except Exception, e:
            raise GandiException(1011, e)

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name='%s cores' % id,
            ram=size['memory'],
            disk=size['disk'],
            bandwidth=size['bandwidth'],
            price=(self._get_size_price(size_id='1') * id),
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        account = self.connection.request('account.info')
        # Look for available shares, and return a list of share_definition
        available_res = account['resources']['available']

        if available_res['shares'] == 0:
            return None
        else:
            share_def = account['share_definition']
            available_cores = available_res['cores']
            # 0.75 core given when creating a server
            max_core = int(available_cores + 0.75)
            shares = []
            if available_res['servers'] < 1:
                # No server quota, no way
                return shares
            for i in range(1,max_core + 1):
                share = {id:i}
                share_is_available = True
                for k in ['memory', 'disk', 'bandwidth']:
                    if share_def[k] * i > available_res[k]:
                        # We run out for at least one resource inside
                        share_is_available = False
                    else:
                        share[k] = share_def[k] * i
                if share_is_available:
                    nb_core = i
                    shares.append(self._to_size(nb_core,share))
            return shares

    def _to_loc(self, loc):
        return NodeLocation(
            id=loc['id'],
            name=loc['name'],
            country=loc['country'],
            driver=self
        )

    def list_locations(self):
        res = self.connection.request("datacenter.list")
        return [self._to_loc(l) for l in res]
