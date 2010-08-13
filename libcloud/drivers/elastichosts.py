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
# Copyright 2009 RedRata Ltd
"""
ElasticHosts Driver
"""
import re
import time
import base64

from libcloud.types import Provider, NodeState, InvalidCredsError, MalformedResponseError
from libcloud.base import ConnectionUserAndKey, Response
from libcloud.base import NodeDriver, NodeSize, Node
from libcloud.base import NodeImage

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try:
    import json
except:
    import simplejson as json

# API end-points
API_ENDPOINTS = {
    'uk-1': {
        'name': 'London Peer 1',
        'country': 'United Kingdom',
        'host': 'api.lon-p.elastichosts.com'
    },
     'uk-2': {
        'name': 'London BlueSquare',
        'country': 'United Kingdom',
        'host': 'api.lon-b.elastichosts.com'
    },
     'us-1': {
        'name': 'San Antonio Peer 1',
        'country': 'United States',
        'host': 'api.sat-p.elastichosts.com'
    },
}

# Default API end-point for the base connection clase.
DEFAULT_ENDPOINT = 'us-1'

# ElasticHosts doesn't specify special instance types, so I just specified
# some plans based on the pricing page (http://www.elastichosts.com/cloud-hosting/pricing)
# and other provides.
#
# Basically for CPU any value between 500Mhz and 20000Mhz should work,
# 256MB to 8192MB for ram and 1GB to 2TB for disk.
INSTANCE_TYPES = {
    'small': {
        'id': 'small',
        'name': 'Small instance',
        'cpu': 2000,
        'memory': 1700,
        'disk': 160,
        'bandwidth': None,
    },
    'large': {
        'id': 'large',
        'name': 'Large instance',
        'cpu': 4000,
        'memory': 7680,
        'disk': 850,
        'bandwidth': None,
    },
    'extra-large': {
        'id': 'extra-large',
        'name': 'Extra Large instance',
        'cpu': 8000,
        'memory': 8192,
        'disk': 1690,
        'bandwidth': None,
    },
    'high-cpu-medium': {
        'id': 'high-cpu-medium',
        'name': 'High-CPU Medium instance',
        'cpu': 5000,
        'memory': 1700,
        'disk': 350,
        'bandwidth': None,
    },
    'high-cpu-extra-large': {
        'id': 'high-cpu-extra-large',
        'name': 'High-CPU Extra Large instance',
        'cpu': 20000,
        'memory': 7168,
        'disk': 1690,
        'bandwidth': None,
    },
}

# Retrieved from http://www.elastichosts.com/cloud-hosting/api
STANDARD_DRIVES = {
    'cf82519b-01a0-4247-aff5-a2dadf4401ad': {
        'uuid': 'cf82519b-01a0-4247-aff5-a2dadf4401ad',
        'description': 'Debian Linux 4.0: Base system without X',
        'size_gunzipped': '1GB',
    },
    'e6111e4c-67af-4438-b1bc-189747d5a8e5': {
        'uuid': 'e6111e4c-67af-4438-b1bc-189747d5a8e5',
        'description': 'Debian Linux 5.0: Base system without X',
        'size_gunzipped': '1GB',
    },
    'bf1d943e-2a55-46bb-a8c7-6099e44a3dde': {
        'uuid': 'bf1d943e-2a55-46bb-a8c7-6099e44a3dde',
        'description': 'Ubuntu Linux 8.10: Base system with X',
        'size_gunzipped': '3GB',
    },
    '757586d5-f1e9-4d9c-b215-5a391c9a24bf': {
        'uuid': '757586d5-f1e9-4d9c-b215-5a391c9a24bf',
        'description': 'Ubuntu Linux 9.04: Base system with X',
        'size_gunzipped': '3GB',
    },
    'b9d0eb72-d273-43f1-98e3-0d4b87d372c0': {
        'uuid': 'b9d0eb72-d273-43f1-98e3-0d4b87d372c0',
        'description': 'Windows Web Server 2008',
        'size_gunzipped': '13GB',
    },
    '30824e97-05a4-410c-946e-2ba5a92b07cb': {
        'uuid': '30824e97-05a4-410c-946e-2ba5a92b07cb',
        'description': 'Windows Web Server 2008 R2',
        'size_gunzipped': '13GB',
    },
    '9ecf810e-6ad1-40ef-b360-d606f0444671': {
        'uuid': '9ecf810e-6ad1-40ef-b360-d606f0444671',
        'description': 'Windows Web Server 2008 R2 + SQL Server',
        'size_gunzipped': '13GB',
    },
    '10a88d1c-6575-46e3-8d2c-7744065ea530': {
        'uuid': '10a88d1c-6575-46e3-8d2c-7744065ea530',
        'description': 'Windows Server 2008 Standard R2',
        'size_gunzipped': '13GB',
    },
    '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47': {
        'uuid': '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47',
        'description': 'Windows Server 2008 Standard R2 + SQL Server',
        'size_gunzipped': '13GB',
    },
}

NODE_STATE_MAP = {
    'active': NodeState.RUNNING,
    'dead': NodeState.TERMINATED,
    'dumped': NodeState.TERMINATED,
}

# Default timeout (in seconds) for the drive imaging process
IMAGING_TIMEOUT = 10 * 60

class ElasticHostsException(Exception):
    """
    Exception class for ElasticHosts driver
    """

    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<ElasticHostsException '%s'>" % (self.args[0])

class ElasticHostsResponse(Response):
    def success(self):
        if self.status == 401:
            raise InvalidCredsError()

        return self.status >= 200 and self.status <= 299
    
    def parse_body(self):
        if not self.body:
            return self.body
        
        try:
            data = json.loads(self.body)
        except:
            raise MalformedResponseError("Failed to parse JSON", body=self.body, driver=ElasticHostsBaseNodeDriver)

        return data
    
    def parse_error(self):
        error_header = self.headers.get('x-elastic-error', '')
        return 'X-Elastic-Error: %s (%s)' % (error_header, self.body.strip())
    
class ElasticHostsNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, disk, bandwidth, price, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.cpu, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))

class ElasticHostsBaseConnection(ConnectionUserAndKey):
    """
    Base connection class for the ElasticHosts driver
    """
    
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']
    responseCls = ElasticHostsResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        headers['Authorization'] = 'Basic %s' % (base64.b64encode('%s:%s' % (self.user_id, self.key)))

        return headers

class ElasticHostsBaseNodeDriver(NodeDriver):
    """
    Base ElasticHosts node driver
    """

    type = Provider.ELASTICHOSTS
    name = 'ElasticHosts'
    connectionCls = ElasticHostsBaseConnection

    def reboot_node(self, node):
        # Reboots the node
        response = self.connection.request(action = '/servers/%s/reset' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def destroy_node(self, node):
        # Kills the server immediately
        response = self.connection.request(action = '/servers/%s/destroy' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def list_images(self, location=None):
        # Returns a list of available pre-installed system drive images
        images = []
        for key, value in STANDARD_DRIVES.iteritems():
            image = NodeImage(id = value['uuid'], name = value['description'], driver = self.connection.driver,
                               extra = {'size_gunzipped': value['size_gunzipped']})
            images.append(image)

        return images

    def list_sizes(self, location=None):
        sizes = []
        for key, value in INSTANCE_TYPES.iteritems():
            size = ElasticHostsNodeSize(id = value['id'], name = value['name'], cpu = value['cpu'], ram = value['memory'],
                            disk = value['disk'], bandwidth = value['bandwidth'], price = '',
                            driver = self.connection.driver)
            sizes.append(size)

        return sizes

    def list_nodes(self):
        # Returns a list of active (running) nodes
        response = self.connection.request(action = '/servers/info').object

        nodes = []
        for data in response:
            node = self._to_node(data)
            nodes.append(node)

        return nodes

    def create_node(self, **kwargs):
        """Creates a ElasticHosts instance

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    name: String with a name for this new node (required)
        @type       name: C{string}
        
        @keyword    smp: Number of virtual processors or None to calculate based on the cpu speed
        @type       smp: C{int}
        
        @keyword    nic_model: e1000, rtl8139 or virtio (is not specified, e1000 is used)
        @type       nic_model: C{string}

        @keyword    vnc_password: If not set, VNC access is disabled.
        @type       vnc_password: C{bool}
        """
        size = kwargs['size']
        image = kwargs['image']
        smp = kwargs.get('smp', 'auto')
        nic_model = kwargs.get('nic_model', 'e1000')
        vnc_password = kwargs.get('vnc_password', None)

        if nic_model not in ['e1000', 'rtl8139', 'virtio']:
            raise ElasticHostsException('Invalid NIC model specified')

        # check that drive size is not smaller then pre installed image size

        # First we create a drive with the specified size
        drive_data = {}
        drive_data.update({'name': kwargs['name'], 'size': '%sG' % (kwargs['size'].disk)})

        response = self.connection.request(action = '/drives/create', data = json.dumps(drive_data),
                                           method = 'POST').object

        if not response:
            raise ElasticHostsException('Drive creation failed')

        drive_uuid = response['drive']

        # Then we image the selected pre-installed system drive onto it
        response = self.connection.request(action = '/drives/%s/image/%s/gunzip' % (drive_uuid, image.id),
                                           method = 'POST')

        if response.status != 204:
            raise ElasticHostsException('Drive imaging failed')

        # We wait until the drive is imaged and then boot up the node (in most cases, the imaging process
        # shouldn't take longer then a few minutes)
        response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
        imaging_start = time.time()
        while response.has_key('imaging'):
            response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
            elapsed_time = time.time() - imaging_start
            if response.has_key('imaging') and elapsed_time >= IMAGING_TIMEOUT:
                raise ElasticHostsException('Drive imaging timed out')
            time.sleep(1)

        node_data = {}
        node_data.update({'name': kwargs['name'], 'cpu': size.cpu, 'mem': size.ram, 'ide:0:0': drive_uuid,
                          'boot': 'ide:0:0', 'smp': smp})
        node_data.update({'nic:0:model': nic_model, 'nic:0:dhcp': 'auto'})

        if vnc_password:
            node_data.update({'vnc:ip': 'auto', 'vnc:password': vnc_password})

        response = self.connection.request(action = '/servers/create', data = json.dumps(node_data),
                                           method = 'POST').object

        if isinstance(response, list):
            nodes = [self._to_node(node) for node in response]
        else:
            nodes = self._to_node(response)

        return nodes

    # Extension methods
    def ex_set_node_configuration(self, node, **kwargs):
        # Changes the configuration of the running server
        valid_keys = ('^name$', '^parent$', '^cpu$', '^smp$', '^mem$', '^boot$', '^nic:0:model$', '^nic:0:dhcp',
                      '^nic:1:model$', '^nic:1:vlan$', '^nic:1:mac$', '^vnc:ip$', '^vnc:password$', '^vnc:tls',
                      '^ide:[0-1]:[0-1](:media)?$', '^scsi:0:[0-7](:media)?$', '^block:[0-7](:media)?$')

        invalid_keys = []
        for key in kwargs.keys():
            matches = False
            for regex in valid_keys:
                if re.match(regex, key):
                    matches = True
                    break
            if not matches:
                invalid_keys.append(key)

        if invalid_keys:
            raise ElasticHostsException('Invalid configuration key specified: %s' % (',' .join(invalid_keys)))

        response = self.connection.request(action = '/servers/%s/set' % (node.id), data = json.dumps(kwargs),
                                           method = 'POST')

        return (response.status == 200 and response.body != '')

    def ex_shutdown_node(self, node):
        # Sends the ACPI power-down event
        response = self.connection.request(action = '/servers/%s/shutdown' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def ex_destroy_drive(self, drive_uuid):
        # Deletes a drive
        response = self.connection.request(action = '/drives/%s/destroy' % (drive_uuid),
                                           method = 'POST')
        return response.status == 204

    # Helper methods
    def _to_node(self, data):
        try:
            state = NODE_STATE_MAP[data['status']]
        except KeyError:
            state = NodeState.UNKNOWN

        if isinstance(data['nic:0:dhcp'], list):
            public_ip = data['nic:0:dhcp']
        else:
            public_ip = [data['nic:0:dhcp']]

        extra = {'cpu': data['cpu'], 'smp': data['smp'], 'mem': data['mem'], 'started': data['started']}

        if data.has_key('vnc:ip') and data.has_key('vnc:password'):
            extra.update({'vnc_ip': data['vnc:ip'], 'vnc_password': data['vnc:password']})

        node = Node(id = data['server'], name = data['name'], state =  state,
                    public_ip = public_ip, private_ip = None, driver = self.connection.driver,
                    extra = extra)

        return node

class ElasticHostsUK1Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for the London Peer 1 end-point
    """

    host = API_ENDPOINTS['uk-1']['host']

class ElasticHostsUK1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Peer 1 end-point
    """
    connectionCls = ElasticHostsUK1Connection

class ElasticHostsUK2Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for the London Bluesquare end-point
    """
    host = API_ENDPOINTS['uk-2']['host']

class ElasticHostsUK2NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Bluesquare end-point
    """
    connectionCls = ElasticHostsUK2Connection

class ElasticHostsUS1Connection(ElasticHostsBaseConnection):
    """
    Connection class for the ElasticHosts driver for the San Antonio Peer 1 end-point
    """
    host = API_ENDPOINTS['us-1']['host']

class ElasticHostsUS1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the San Antonio Peer 1 end-point
    """
    connectionCls = ElasticHostsUS1Connection


