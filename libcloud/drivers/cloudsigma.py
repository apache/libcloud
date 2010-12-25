# -*- coding: utf-8 -*-
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
CloudSigma Driver
"""
import re
import time
import base64

from libcloud.types import Provider, NodeState, InvalidCredsError
from libcloud.base import ConnectionUserAndKey, Response
from libcloud.base import NodeDriver, NodeSize, Node
from libcloud.base import NodeImage

# API end-points
API_ENDPOINTS = {
    'zrh': {
        'name': 'Zurich',
        'country': 'Switzerland',
        'host': 'api.cloudsigma.com'
    },
}

# Default API end-point for the base connection clase.
DEFAULT_ENDPOINT = 'zrh'

# CloudSigma doesn't specify special instance types.
# Basically for CPU any value between 0.5 GHz and 20.0 GHz should work, 500 MB to 32000 MB for ram
# and 1 GB to 1024 GB for hard drive size.
# Plans in this file are based on examples listed on http://www.cloudsigma.com/en/pricing/price-schedules
INSTANCE_TYPES = {
    'micro-regular': {
        'id': 'micro-regular',
        'name': 'Micro/Regular instance',
        'cpu': 1100,
        'memory': 640,
        'disk': 50,
        'price': '0.0548',
        'bandwidth': None,
    },
    'micro-high-cpu': {
        'id': 'micro-high-cpu',
        'name': 'Micro/High CPU instance',
        'cpu': 2200,
        'memory': 640,
        'disk': 80,
        'price': '.381',
        'bandwidth': None,
    },
    'standard-small': {
        'id': 'standard-small',
        'name': 'Standard/Small instance',
        'cpu': 1100,
        'memory': 1741,
        'disk': 50,
        'price': '0.0796',
        'bandwidth': None,
    },
    'standard-large': {
        'id': 'standard-large',
        'name': 'Standard/Large instance',
        'cpu': 4400,
        'memory': 7680,
        'disk': 250,
        'price': '0.381',
        'bandwidth': None,
    },
    'standard-extra-large': {
        'id': 'standard-extra-large',
        'name': 'Standard/Extra Large instance',
        'cpu': 8800,
        'memory': 15360,
        'disk': 500,
        'price': '0.762',
        'bandwidth': None,
    },
    'high-memory-extra-large': {
        'id': 'high-memory-extra-large',
        'name': 'High Memory/Extra Large instance',
        'cpu': 7150,
        'memory': 17510,
        'disk': 250,
        'price': '0.642',
        'bandwidth': None,
    },
    'high-memory-double-extra-large': {
        'id': 'high-memory-double-extra-large',
        'name': 'High Memory/Double Extra Large instance',
        'cpu': 14300,
        'memory': 32768,
        'disk': 500,
        'price': '1.383',
        'bandwidth': None,
    },
    'high-cpu-medium': {
        'id': 'high-cpu-medium',
        'name': 'High CPU/Medium instance',
        'cpu': 5500,
        'memory': 1741,
        'disk': 150,
        'price': '0.211',
        'bandwidth': None,
    },
    'high-cpu-extra-large': {
        'id': 'high-cpu-extra-large',
        'name': 'High CPU/Extra Large instance',
        'cpu': 20000,
        'memory': 7168,
        'disk': 500,
        'price': '0.780',
        'bandwidth': None,
    },
}

NODE_STATE_MAP = {
    'active': NodeState.RUNNING,
    'stopped': NodeState.TERMINATED,
    'dead': NodeState.TERMINATED,
    'dumped': NodeState.TERMINATED,
}

# Default timeout (in seconds) for the drive imaging process
IMAGING_TIMEOUT = 20 * 60

class CloudSigmaException(Exception):
    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<CloudSigmaException '%s'>" % (self.args[0])

class CloudSigmaInsufficientFundsException(Exception):
    def __repr__(self):
        return "<CloudSigmaInsufficientFundsException '%s'>" % (self.args[0])

class CloudSigmaResponse(Response):
    def success(self):
        if self.status == 401:
            raise InvalidCredsError()

        return self.status >= 200 and self.status <= 299

    def parse_body(self):
        if not self.body:
            return self.body

        return str2dicts(self.body)

    def parse_error(self):
        return 'Error: %s' % (self.body.replace('errors:', '').strip())

class CloudSigmaNodeSize(NodeSize):
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

class CloudSigmaBaseConnection(ConnectionUserAndKey):
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']
    responseCls = CloudSigmaResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        headers['Authorization'] = 'Basic %s' % (base64.b64encode('%s:%s' % (self.user_id, self.key)))

        return headers

class CloudSigmaBaseNodeDriver(NodeDriver):
    type = Provider.CLOUDSIGMA
    name = 'CloudSigma'
    connectionCls = CloudSigmaBaseConnection

    def reboot_node(self, node):
        """
        Reboot a node.

        Because Cloudsigma API does not provide native reboot call, it's emulated using stop and start.
        """
        node = self._get_node(node.id)
        state = node.state

        if state == NodeState.RUNNING:
            stopped = self.ex_stop_node(node)
        else:
            stopped = True

        if not stopped:
            raise CloudSigmaException('Could not stop node with id %s' % (node.id))

        success = self.ex_start_node(node)

        return success

    def destroy_node(self, node):
        """
        Destroy a node (all the drives associated with it are NOT destroyed).

        If a node is still running, it's stopped before it's destroyed.
        """
        node = self._get_node(node.id)
        state = node.state

        # Node cannot be destroyed while running so it must be stopped first
        if state == NodeState.RUNNING:
            stopped = self.ex_stop_node(node)
        else:
            stopped = True

        if not stopped:
            raise CloudSigmaException('Could not stop node with id %s' % (node.id))

        response = self.connection.request(action = '/servers/%s/destroy' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def list_images(self, location=None):
        """
        Return a list of available standard images (this call might take up to 15 seconds to return).
        """
        response = self.connection.request(action = '/drives/standard/info').object

        images = []
        for value in response:
            if value.get('type'):
                if value['type'] == 'disk':
                    image = NodeImage(id = value['drive'], name = value['name'], driver = self.connection.driver,
                                    extra = {'size': value['size']})
                    images.append(image)

        return images

    def list_sizes(self, location = None):
        """
        Return a list of available node sizes.
        """
        sizes = []
        for key, value in INSTANCE_TYPES.iteritems():
            size = CloudSigmaNodeSize(id = value['id'], name = value['name'], cpu = value['cpu'], ram = value['memory'],
                            disk = value['disk'], bandwidth = value['bandwidth'], price = value['price'],
                            driver = self.connection.driver)
            sizes.append(size)

        return sizes

    def list_nodes(self):
        """
        Return a list of nodes.
        """
        response = self.connection.request(action = '/servers/info').object

        nodes = []
        for data in response:
            node = self._to_node(data)
            if node:
                nodes.append(node)
        return nodes

    def create_node(self, **kwargs):
        """
        Creates a CloudSigma instance

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
            raise CloudSigmaException('Invalid NIC model specified')

        drive_data = {}
        drive_data.update({'name': kwargs['name'], 'size': '%sG' % (kwargs['size'].disk)})

        response = self.connection.request(action = '/drives/%s/clone' % image.id, data = dict2str(drive_data),
                                           method = 'POST').object

        if not response:
            raise CloudSigmaException('Drive creation failed')

        drive_uuid = response[0]['drive']

        response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
        imaging_start = time.time()
        while response[0].has_key('imaging'):
            response = self.connection.request(action = '/drives/%s/info' % (drive_uuid)).object
            elapsed_time = time.time() - imaging_start
            if response[0].has_key('imaging') and elapsed_time >= IMAGING_TIMEOUT:
                raise CloudSigmaException('Drive imaging timed out')
            time.sleep(1)

        node_data = {}
        node_data.update({'name': kwargs['name'], 'cpu': size.cpu, 'mem': size.ram, 'ide:0:0': drive_uuid,
                          'boot': 'ide:0:0', 'smp': smp})
        node_data.update({'nic:0:model': nic_model, 'nic:0:dhcp': 'auto'})

        if vnc_password:
            node_data.update({'vnc:ip': 'auto', 'vnc:password': vnc_password})

        response = self.connection.request(action = '/servers/create', data = dict2str(node_data),
                                           method = 'POST').object

        if not isinstance(response, list):
            response = [ response ]

        node = self._to_node(response[0])
        if node is None:
            # Insufficient funds, destroy created drive
            self.ex_drive_destroy(drive_uuid)
            raise CloudSigmaInsufficientFundsException('Insufficient funds, node creation failed')

        # Start the node after it has been created
        started = self.ex_start_node(node)

        if started:
            node.state = NodeState.RUNNING

        return node

    def ex_destroy_node_and_drives(self, node):
        """
        Destroy a node and all the drives associated with it.
        """
        node = self._get_node_info(node)

        drive_uuids = []
        for key, value in node.iteritems():
            if (key.startswith('ide:') or key.startswith('scsi') or key.startswith('block')) and \
               not (key.endswith(':bytes') or key.endswith(':requests') or key.endswith('media')):
                drive_uuids.append(value)

        node_destroyed = self.destroy_node(self._to_node(node))

        if not node_destroyed:
            return False

        for drive_uuid in drive_uuids:
            self.ex_drive_destroy(drive_uuid)

        return True

    def ex_static_ip_list(self):
        """
        Return a list of available static IP addresses.
        """
        response = self.connection.request(action = '/resources/ip/list', method = 'GET')

        if response.status != 200:
            raise CloudSigmaException('Could not retrieve IP list')

        ips = str2list(response.body)
        return ips

    def ex_drives_list(self):
        """
        Return a list of all the available drives.
        """
        response = self.connection.request(action = '/drives/info', method = 'GET')

        result = str2dicts(response.body)
        return result

    def ex_static_ip_create(self):
        """
        Create a new static IP address.
        """
        response = self.connection.request(action = '/resources/ip/create', method = 'GET')

        result = str2dicts(response.body)
        return result

    def ex_static_ip_destroy(self, ip_address):
        """
        Destroy a static IP address.
        """
        response = self.connection.request(action = '/resources/ip/%s/destroy' % (ip_address), method = 'GET')

        return response.status == 204

    def ex_drive_destroy(self, drive_uuid):
        """
        Destroy a drive with a specified uuid.
        If the drive is currently mounted an exception is thrown.
        """
        response = self.connection.request(action = '/drives/%s/destroy' % (drive_uuid), method = 'POST')

        return response.status == 204


    def ex_set_node_configuration(self, node, **kwargs):
        """
        Update a node configuration.
        Changing most of the parameters requires node to be stopped.
        """
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
            raise CloudSigmaException('Invalid configuration key specified: %s' % (',' .join(invalid_keys)))

        response = self.connection.request(action = '/servers/%s/set' % (node.id), data = dict2str(kwargs),
                                           method = 'POST')

        return (response.status == 200 and response.body != '')

    def ex_start_node(self, node):
        """
        Start a node.
        """
        response = self.connection.request(action = '/servers/%s/start' % (node.id),
                                           method = 'POST')

        return response.status == 200

    def ex_stop_node(self, node):
        """
        Stop (shutdown) a node.
        """
        response = self.connection.request(action = '/servers/%s/stop' % (node.id),
                                           method = 'POST')
        return response.status == 204

    def ex_shutdown_node(self, node):
        """
        Stop (shutdown) a node.
        """
        return self.ex_stop_node(node)

    def ex_destroy_drive(self, drive_uuid):
        """
        Destroy a drive.
        """
        response = self.connection.request(action = '/drives/%s/destroy' % (drive_uuid),
                                           method = 'POST')
        return response.status == 204

    def _to_node(self, data):
        if data:
            try:
                state = NODE_STATE_MAP[data['status']]
            except KeyError:
                state = NodeState.UNKNOWN

            if 'server' not in data:
                # Response does not contain server UUID if the server
                # creation failed because of insufficient funds.
                return None

            public_ip = []
            if data.has_key('nic:0:dhcp'):
                if isinstance(data['nic:0:dhcp'], list):
                    public_ip = data['nic:0:dhcp']
                else:
                    public_ip = [data['nic:0:dhcp']]

            extra = {}
            extra_keys = [ ('cpu', 'int'), ('smp', 'auto'), ('mem', 'int'), ('status', 'str') ]
            for key, value_type in extra_keys:
                if data.has_key(key):
                    value = data[key]

                    if value_type == 'int':
                        value = int(value)
                    elif value_type == 'auto':
                        try:
                            value = int(value)
                        except ValueError:
                            pass

                    extra.update({key: value})

            if data.has_key('vnc:ip') and data.has_key('vnc:password'):
                extra.update({'vnc_ip': data['vnc:ip'], 'vnc_password': data['vnc:password']})

            node = Node(id = data['server'], name = data['name'], state =  state,
                        public_ip = public_ip, private_ip = None, driver = self.connection.driver,
                        extra = extra)

            return node
        return None

    def _get_node(self, node_id):
        nodes = self.list_nodes()
        node = [node for node in nodes if node.id == node.id]

        if not node:
            raise CloudSigmaException('Node with id %s does not exist' % (node_id))

        return node[0]

    def _get_node_info(self, node):
        response = self.connection.request(action = '/servers/%s/info' % (node.id))

        result = str2dicts(response.body)
        return result[0]

class CloudSigmaZrhConnection(CloudSigmaBaseConnection):
    """
    Connection class for the CloudSigma driver for the Zurich end-point
    """
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']

class CloudSigmaZrhNodeDriver(CloudSigmaBaseNodeDriver):
    """
    CloudSigma node driver for the Zurich end-point
    """
    connectionCls = CloudSigmaZrhConnection

# Utility methods (should we place them in libcloud/utils.py ?)
def str2dicts(data):
    """
    Create a list of dictionaries from a whitespace and newline delimited text.

    For example, this:
    cpu 1100
    ram 640

    cpu 2200
    ram 1024

    becomes:
    [{'cpu': '1100', 'ram': '640'}, {'cpu': '2200', 'ram': '1024'}]
    """
    list_data = []
    list_data.append({})
    d = list_data[-1]

    lines = data.split('\n')
    for line in lines:
        line = line.strip()

        if not line:
            d = {}
            list_data.append(d)
            d = list_data[-1]
            continue

        whitespace = line.find(' ')

        if not whitespace:
            continue

        key = line[0:whitespace]
        value = line[whitespace + 1:]
        d.update({key: value})

    list_data = [value for value in list_data if value != {}]
    return list_data

def str2list(data):
    """
    Create a list of values from a whitespace and newline delimited text (keys are ignored).

    For example, this:
    ip 1.2.3.4
    ip 1.2.3.5
    ip 1.2.3.6

    becomes:
    ['1.2.3.4', '1.2.3.5', '1.2.3.6']
    """
    list_data = []

    for line in data.split('\n'):
        line = line.strip()

        if not line:
            continue

        try:
            splitted = line.split(' ')
            # key = splitted[0]
            value = splitted[1]
        except Exception:
            continue

        list_data.append(value)

    return list_data

def dict2str(data):
    """
    Create a string with a whitespace and newline delimited text from a dictionary.

    For example, this:
    {'cpu': '1100', 'ram': '640', 'smp': 'auto'}

    becomes:
    cpu 1100
    ram 640
    smp auto

    cpu 2200
    ram 1024
    """
    result = ''
    for k in data:
        if data[k] != None:
            result += '%s %s\n' % (str(k), str(data[k]))
        else:
            result += '%s\n' % str(k)

    return result
