# Copyright (C) 2015 Verizon.
#
# Licensed to You under the Apache License, Version 2.0
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

import hmac
import hashlib
import json
import time
import sys

from datetime import datetime
from base64 import b64encode
from libcloud.utils.py3 import httplib

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeSize
from libcloud.compute.types import Provider, NodeState, DeploymentError
from libcloud.compute.ssh import SSHClient
from libcloud.compute.ssh import have_paramiko

API_HOST = "services.enterprisecloud.terremark.com"
API_ROOT = "/cloudapi/ecloud"
API_VERSION = "2014-05-01"
NODE_ONLINE_WAIT_TIMEOUT = 600
SSH_CONNECT_TIMEOUT = 300
CLOUDSPACE = None

DEBUG = False


NODE_STATE_MAP = {
    'ON': NodeState.RUNNING,
    'OFF': NodeState.STOPPED,
    'IN_PROGRESS': NodeState.PENDING,
    'UNKNOWN': NodeState.UNKNOWN
}

NETWORK_MAP = {
    'dmz': 0,
    'int': 1
}

INSTANCE_TYPES = {
    's1': {
        'id': 's1',
        'name': 's1',
        'ram': 512,
        'cpu': 1
    },
    's2': {
        'id': 's2',
        'name': 's2',
        'ram': 1024,
        'cpu': 1
    },
    's3': {
        'id': 's3',
        'name': 's3',
        'ram': 1536,
        'cpu': 1
    },
    's4': {
        'id': 's4',
        'name': 's4',
        'ram': 2048,
        'cpu': 1
    },
    's5': {
        'id': 's5',
        'name': 's5',
        'ram': 4096,
        'cpu': 1
    },
    's6': {
        'id': 's6',
        'name': 's6',
        'ram': 8192,
        'cpu': 1
    },
    's7': {
        'id': 's7',
        'name': 's7',
        'ram': 12288,
        'cpu': 1
    },
    's8': {
        'id': 's8',
        'name': 's8',
        'ram': 16384,
        'cpu': 1
    },
    's9': {
        'id': 's9',
        'name': 's9',
        'ram': 512,
        'cpu': 2
    },
    's10': {
        'id': 's10',
        'name': 's10',
        'ram': 1024,
        'cpu': 2
    },
    's11': {
        'id': 's11',
        'name': 's11',
        'ram': 1536,
        'cpu': 2
    },
    's12': {
        'id': 's12',
        'name': 's12',
        'ram': 2048,
        'cpu': 2
    },
    's13': {
        'id': 's13',
        'name': 's13',
        'ram': 4096,
        'cpu': 2
    },
    's14': {
        'id': 's14',
        'name': 's14',
        'ram': 8192,
        'cpu': 2
    },
    's15': {
        'id': 's15',
        'name': 's15',
        'ram': 12288,
        'cpu': 2
    },
    's16': {
        'id': 's16',
        'name': 's16',
        'ram': 16384,
        'cpu': 2
    },
    's17': {
        'id': 's17',
        'name': 's17',
        'ram': 512,
        'cpu': 3
    },
    's18': {
        'id': 's18',
        'name': 's18',
        'ram': 1024,
        'cpu': 3
    },
    's19': {
        'id': 's19',
        'name': 's19',
        'ram': 1536,
        'cpu': 3
    },
    's20': {
        'id': 's20',
        'name': 's20',
        'ram': 2048,
        'cpu': 3
    },
    's21': {
        'id': 's21',
        'name': 's21',
        'ram': 4096,
        'cpu': 3
    },
    's22': {
        'id': 's22',
        'name': 's22',
        'ram': 8192,
        'cpu': 3
    },
    's23': {
        'id': 's23',
        'name': 's23',
        'ram': 12288,
        'cpu': 3
    },
    's24': {
        'id': 's24',
        'name': 's24',
        'ram': 16384,
        'cpu': 3
    },
    's25': {
        'id': 's25',
        'name': 's25',
        'ram': 512,
        'cpu': 4
    },
    's26': {
        'id': 's26',
        'name': 's26',
        'ram': 1024,
        'cpu': 4
    },
    's27': {
        'id': 's27',
        'name': 's27',
        'ram': 1536,
        'cpu': 4
    },
    's28': {
        'id': 's28',
        'name': 's28',
        'ram': 2048,
        'cpu': 4
    },
    's29': {
        'id': 's29',
        'name': 's29',
        'ram': 4096,
        'cpu': 4
    },
    's30': {
        'id': 's30',
        'name': 's30',
        'ram': 8192,
        'cpu': 4
    },
    's31': {
        'id': 's31',
        'name': 's31',
        'ram': 12288,
        'cpu': 4
    },
    's32': {
        'id': 's32',
        'name': 's32',
        'ram': 16384,
        'cpu': 4
    }
}


class VerizonException(Exception):
    def __str__(self):
        return self.args[0]

    def __repr__(self):
        return "<VerizonException '%s'>" % (self.args[0])


class VerizonResponse(JsonResponse):
    def success(self):
        return self.status >= httplib.OK and self.status < httplib.BAD_REQUEST

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise VerizonException(str(self.status) + ': ' + self.error)
            else:
                raise VerizonException(self.body)
        return self.body


class VerizonNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.driver = driver

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s driver=%s ...>')
                % (self.id, self.name, self.cpu, self.ram, self.driver.name))


class VerizonConnection(ConnectionUserAndKey):
    """
    Connection to the Verizon Cloud Compute API
    """
    host = API_HOST

    responseCls = VerizonResponse

    def add_default_headers(self, headers):
        timestamp = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers['Date'] = timestamp
        content_type = ''
        content_length = ''
        if self.method != 'GET':
            content_type = 'application/json'
        if 'Content-Length' in headers:
            content_length = str(headers['Content-Length'])
        headers['Content-Type'] = content_type
        headers['x-tmrk-authorization'] = self._build_request(self.action, timestamp, content_type, content_length)
        headers['x-tmrk-version'] = API_VERSION
        headers['Accept'] = 'application/json'
        if CLOUDSPACE is not None:
            headers['x-tmrk-cloudspace'] = CLOUDSPACE
        if DEBUG:
            print headers
        return headers

    def _build_request(self, path, timestamp, content_type, content_length):
        api_version = 'x-tmrk-version:%s' % API_VERSION
        if CLOUDSPACE is not None:
            cloudspace = 'x-tmrk-cloudspace:%s' % CLOUDSPACE
            string = "%s\n%s\n%s\n%s\n%s\n%s\n%s\n" % (self.method, content_length, content_type, timestamp, api_version, cloudspace, path)
        else:
            string = "%s\n%s\n%s\n%s\n%s\n%s\n" % (self.method, content_length, content_type, timestamp, api_version, path)
        if DEBUG:
            print string
        signature = b64encode(hmac.new(key=self.key, msg=string, digestmod=hashlib.sha256).digest())
        completed_signature = "CloudApi AccessKey=%s SignatureType=HmacSHA256 Signature=%s" % (self.user_id, signature)
        return completed_signature


class VerizonNodeDriver(NodeDriver):
    def __new__(cls, key, secret=None, secure=True, host=None, port=None,
                cloudspace=None, **kwargs):
        global CLOUDSPACE
        CLOUDSPACE = cloudspace
        return super(VerizonNodeDriver, cls).__new__(cls)

    type = "verizon"
    connectionCls = VerizonConnection

    def list_images(self):
        """
        List available images

        :rtype: ``list`` of :class:`NodeImage`
        """
        pool = self.ex_get_default_pool()
        url = API_ROOT + '/templates/computepools/' + pool
        result = self.connection.request(url).object
        templates = []
        for i in result['Families'][0]['Categories']:
            for x in i['OperatingSystems']:
                for y in x['Templates']:
                    templates.append(y)
        return [self._to_image(i) for i in templates]

    def list_nodes(self):
        """
        List all nodes

        :rtype: ``list`` of :class:`Node`
        """
        pool = self.ex_get_default_pool()
        url = API_ROOT + '/virtualmachines/computepools/' + pool
        result = self.connection.request(url).object
        nodes = []
        for i in result['Items']:
            result = self.connection.request(i['href']).object
            nodes.append(result)
        return [self._to_node(i) for i in nodes]

    def list_sizes(self):
        """
        List all node sizes

        :rtype: ``list`` of :class:`VerizonNodeSize`
        """
        sizes = []
        for key, value in INSTANCE_TYPES.items():
            size = VerizonNodeSize(
                id=value['id'], name=value['name'], cpu=value['cpu'],
                ram=value['ram'], driver=self.connection.driver
            )
            sizes.append(size)

        return sizes

    def destroy_node(self, node=None):
        """
        Destroy a node

        :param node: Node object to destory
        :type  node: :class:`Node`

        :rtype: ``bool``
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        if self.ex_get_node_state(node) != 5:
            self.ex_poweroff_node(node=node)
        time.sleep(60)
        self.ex_remove_node(node=node)
        return True

    def create_node(self, name=None, size=None, image=None, ssh_admin_key=None,
                    pool=None, network=None, ipaddr=None, row=None, group=None, **kwargs):
        """
        Create a new node from a image. Will test for a libcloud group/row and
        create them if not provided.

        For any keywords that are not mandatory sane defaults will tried to be
        obtained via API calls

        :keyword name: Name of the node (mandatory)
        :type    name: ``str``

        :keyword size: the plan size to create (mandatory)
        :type    size: :class:`NodeSize`

        :keyword image: Which image to use
        :type    image: :class:`NodeImage` (mandatory)

        :keyword ssh_admin_key: SSH key to inject for the admin user. 
        :type    ssh_admin_key: ``str``

        :keyword pool: Compute pool to deploy in
        :type    pool: ``str``

        :keyword network: Network to attach
        :type       pool: ``str``

        :keyword ipaddr: IP address to use
        :type    ipaddr: ``str``

        :keyword row: Row to deploy on
        :type    row: ``str``

        :keyword group: Group to deploy on
        :type    group: ``str``

        :return: Node object of newly created node
        :rtype: :class: `Node`

        """
        if name is None:
            raise VerizonException('Parameter name is required')
        if image is None:
            raise VerizonException('Parameter image is required')
        if size is None:
            raise VerizonException('Parameter size is required')

        layout_hrefs = {}

        if row is None and group is None:
            layout_hrefs = self._libcloud_layout_check()
        else:
            layout_hrefs['row'] = row
            layout_hrefs['group'] = group

        if ssh_admin_key is None:
            ssh_admin_key = self.ex_get_ssh_key()

        if pool is None:
            pool = self.ex_get_default_pool()

        if network is None:
            network = self.ex_get_network(type='int')
            ipaddr = self.ex_get_address(network_href=network)
            if ipaddr is None:
                raise VerizonException('No ips are available')

        vm = {}
        vm['name'] = name
        vm['PoweredOn'] = False
        vm['ProcessorCount'] = size.cpu
        vm['Template'] = {'href': image.id}

        vm['Memory'] = {'Unit': 'MB',
                        'Value': size.ram}

        vm['Layout'] = {'Row': {'href': layout_hrefs['row']},
                        'Group': {'href': layout_hrefs['group']}}

        vm['LinuxCustomization'] = {'SshKey': {'href': ssh_admin_key},
                                    'NetworkSettings': {
                                        'NetworkAdapterSettings': [{
                                            'Network': {'href': network},
                                            'IpAddress': ipaddr}]
                                        }
                                    }

        url = '%s/virtualmachines/computepools/%s/action/createvirtualmachine' % (API_ROOT, pool)

        headers = {'Content-Length': len(json.dumps(vm))}

        result = self.connection.request(url, method='POST', headers=headers, data=json.dumps(vm)).object
        result['ip'] = ipaddr
        return self._to_node(result)

    def deploy_node(self, deploy=None, **kwargs):
        """
        Slightly modifed from the default deploy_node function.
        """
        if deploy is None:
            raise VerizonException('Parameter deploy is required')

        if not have_paramiko:
            raise RuntimeError('paramiko is not installed. You can install ' +
                               'it using pip: pip install paramiko')

        if 'auth' in kwargs:
            auth = kwargs['auth']
            if not isinstance(auth, (NodeAuthSSHKey, NodeAuthPassword)):
                raise NotImplementedError(
                    'If providing auth, only NodeAuthSSHKey or'
                    'NodeAuthPassword is supported')
        elif 'ssh_key' in kwargs:
            # If an ssh_key is provided we can try deploy_node
            pass
        elif 'create_node' in self.features:
            f = self.features['create_node']
            if 'generates_password' not in f and "password" not in f:
                raise NotImplementedError(
                    'deploy_node not implemented for this driver')
        else:
            raise NotImplementedError(
                'deploy_node not implemented for this driver')

        node = self.create_node(**kwargs)

        if self.ex_wait_create(node=node):
            self.ex_poweron_node(node=node)

        max_tries = kwargs.get('max_tries', 3)

        password = None
        if 'auth' in kwargs:
            if isinstance(kwargs['auth'], NodeAuthPassword):
                password = kwargs['auth'].password
        elif 'password' in node.extra:
            password = node.extra['password']

        ssh_interface = kwargs.get('ssh_interface', 'public_ips')
        ip_addresses = node.public_ips

        ssh_username = kwargs.get('ssh_username', 'root')
        ssh_alternate_usernames = kwargs.get('ssh_alternate_usernames', [])
        ssh_port = kwargs.get('ssh_port', 22)
        ssh_timeout = kwargs.get('ssh_timeout', 10)
        ssh_key_file = kwargs.get('ssh_key', None)
        timeout = kwargs.get('timeout', SSH_CONNECT_TIMEOUT)

        deploy_error = None

        for username in ([ssh_username] + ssh_alternate_usernames):
            try:
                self._connect_and_run_deployment_script(
                    task=deploy, node=node,
                    ssh_hostname=ip_addresses[0], ssh_port=ssh_port,
                    ssh_username=username, ssh_password=password,
                    ssh_key_file=ssh_key_file, ssh_timeout=ssh_timeout,
                    timeout=timeout, max_tries=max_tries)
            except Exception:
                # Try alternate username
                # Todo: Need to fix paramiko so we can catch a more specific
                # exception
                e = sys.exc_info()[1]
                deploy_error = e
            else:
                # Script successfully executed, don't try alternate username
                deploy_error = None
                break

        if deploy_error is not None:
            raise DeploymentError(node=node, original_exception=deploy_error,
                                  driver=self)

        return self.ex_get_node(node=node)

    def ex_get_default_org(self):
        """
        Returns default organization

        :rtype: ``str``
        """
        url = API_ROOT + '/organizations'
        result = self.connection.request(url).object
        for i in result['Items'][0]['Links']:
            if i['type'] == 'application/vnd.tmrk.cloud.environment; type=collection':
                href = i['href']
        return href.split('/')[5]

    def ex_get_default_env(self, org=None):
        """
        Returns default environment

        :keyword  org:    Organization ID
        :type     org:    ``str``

        :rtype: ``str``
        """
        if org is None:
            org = self.ex_get_default_org()
        url = API_ROOT + '/environments/organizations/' + org
        href = self.connection.request(url).object['Items'][0]['href']
        return href.split('/')[4]

    def ex_get_default_pool(self, org=None):
        """
        Returns default compute pool

        :keyword org:    Organization ID
        :type    org:    ``str``

        :rtype: ``str``
        """
        if org is None:
            org = self.ex_get_default_org()
        url = API_ROOT + '/environments/organizations/' + org
        href = self.connection.request(url).object['Items'][0]['ComputePools'][0]['href']
        return href.split('/')[4]

    def ex_create_row(self, name=None, env=None):
        """
        Creates a row

        :keyword name:   Name of the row
        :type    name:   ``str``

        :keyword env:   Environment to use
        :type    env:   ``str``

        :return:        href to row
        :rtype: ``str``
        """
        if name is None:
            raise VerizonException('Argument "name" required')
        if env is None:
            env = self.ex_get_default_env()

        url = '%s/layoutrows/environments/%s/action/createlayoutrow' % (API_ROOT, env)
        body = {'name': name}
        headers = {'Content-Length': len(json.dumps(body))}
        href = self.connection.request(url, method='POST', headers=headers, data=json.dumps(body)).object['href']
        return href

    def ex_create_group(self, name=None, env=None, row_href=None):
        """
        Creates a row

        :keyword name:   Name of the group
        :type    name:   ``str``

        :keyword env:   Environment ID
        :type    env:   ``str``

        :keyword row:   Row href
        :type    row:   ``str``

        :return: href to group
        :rtype: ``str``
        """
        if name is None:
            raise VerizonException('Argument "name" required')
        if env is None:
            raise VerizonException('Argument "env" required')
        if row_href is None:
            raise VerizonException('Argument "row_href" required')

        url = '%s/layoutgroups/environments/%s/action/createlayoutgroup' % (API_ROOT, env)
        body = {"name": name, "Row": {"href": row_href}}
        headers = {'Content-Length': len(json.dumps(body))}
        href = self.connection.request(url, method='POST', headers=headers, data=json.dumps(body)).object['href']
        return href

    def ex_get_network(self, type=None):
        """
        Get either the dmz or int network

        :keyword type: dmz or int (mandatory)
        :type    type: ``str``

        :return: href to network
        :rtpe:   ``str``
        """
        if type is None:
            raise VerizonException('Argument "type" required')
        if type not in ('int', 'dmz'):
            raise VerizonException('Argument "type" should be either "dmz" or "int"')
        env = self.ex_get_default_env()
        url = '%s/networks/environments/%s' % (API_ROOT, env)
        result = self.connection.request(url).object['Items']
        href = None
        for i in result:
            if i['NetworkType'] == NETWORK_MAP[type]:
                href = i['href']
        return href

    def ex_get_address(self, network_href=None):
        """
        Get an availabe ip

        :keyword          : network_href
        :type network_href: ``str``

        :return: ip name
        :rtpe:   ``str``
        """
        if network_href is None:
            raise VerizonException('Argument "network_href" required')
        result = self.connection.request(network_href).object['IpAddresses']
        ipaddr = None
        for i in result:
            if i['Reserved'] is False and i['DetectedOn'] is None and i['Host'] is None:
                ipaddr = i['name']
                break
        if ipaddr is None:
            raise VerizonException('No addressess are available')
        return ipaddr

    def ex_get_ssh_key(self):
        """
        Grab the default ssh key

        :return: href to key
        :rtype:  ``str``
        """
        org = self.ex_get_default_org()
        url = '%s/admin/sshkeys/organizations/%s' % (API_ROOT, org)
        result = self.connection.request(url).object['Items']
        ssh_href = None
        for i in result:
            if i['Default']:
                ssh_href = i['href']
        if ssh_href is None:
            raise VerizonException('No default key found')
        return ssh_href

    def ex_poweron_node(self, node=None):
        """
        Power on a node
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :return: status
        :rtype : ``str``
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        href = None
        for i in node.extra['Actions']:
            if i is not None:
                if i['name'] == 'power:powerOn':
                    href = i['href']
        headers = {'Content-Length': 0}
        return self.connection.request(href,headers=headers,method='POST').object

    def ex_wait_create(self, node=None, timeout=900):
        """
        Wait for node to power on
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :keyword timeout: Time to wait until failing
        :type    timeout: ``int``

        :rtype : ``bool``
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        end_time = int(time.time()) + timeout
        while True:
            if self.ex_get_node_state(node) == 5:
                break
            if int(time.time()) > end_time:
                raise VerizonException('Time %s exceeded' % timeout)
            time.sleep(10)
        return True

    def ex_get_node_state(self, node=None):
        """
        Get node state
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :return: State of the node
        :rtype: :class: `Node`
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        result = self.connection.request(node.id).object
        return self._to_node(result).state

    def ex_get_node(self, node=None):
        """
        Returns a node
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :return: State of the node
        :rtype: :class: `Node`
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        result = self.connection.request(node.id).object
        return self._to_node(result)

    def ex_poweroff_node(self, node=None):
        """
        Power off a node
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :return: State of the node
        :rtype: :class: `Node`
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        href = None
        for i in node.extra['Actions']:
            if i is not None:
                if i['name'] == 'power:powerOff':
                    href = i['href']
        headers = {'Content-Length': 0}
        return self.connection.request(href,headers=headers,method='POST').object

    def ex_remove_node(self, node=None):
        """
        Deletes a node
        :keyword node: Node object
        :type    node: :class:`Node` (mandatory)

        :return: State of the node
        :rtype: :class: `Node`
        """
        if node is None:
            raise VerizonException('Parameter node is required')
        headers = {'Content-Length': 0}
        return self.connection.request(node.id,headers=headers,method='DELETE').object

    def _to_node(self, node):
        public_ips = []
        private_ips = []
        state = 'UNKNOWN'

        if node['IpAddresses']['AssignedIpAddresses']['Networks'] is not None:
            for i in node['IpAddresses']['AssignedIpAddresses']['Networks']:
                for a in i['IpAddresses']:
                    public_ips.append(a)

        if 'ip' in node:
            public_ips.append(node['ip'])

        if node['PoweredOn'] is True:
            state = 'ON'
        if node['PoweredOn'] is False:
            state = 'OFF'
        if node['Status'] == '3':
            state = 'IN_PROGRESS'
        if node['CustomizationPending'] is True:
            state = 'IN_PROGRESS'

        return Node(node['href'], node['name'], NODE_STATE_MAP[state], public_ips, private_ips, driver=self, extra=node)

    def _to_image(self, image):
        return NodeImage(id=image['href'], name=image['name'], driver=self)

    def _libcloud_layout_check(self):
        """
        Check to see if a libcloud row and column exist. If not, create
        """
        env = self.ex_get_default_env()
        url = API_ROOT + '/layout/environments/' + env
        rows = self.connection.request(url).object['Rows']
        row = None
        grp = None
        for i in rows:
            if i['name'] == 'libcloud':
                row = i['href']
                if i['Groups'] is not None:
                    for x in i['Groups']:
                        if x['name'] == 'libcloud':
                            grp = x['href']
        hrefs = {}

        if row is None:
            hrefs['row'] = self.ex_create_row(name='libcloud')
            grp = self.ex_create_group(name='libcloud', env=env, row_href=hrefs['row'])
        else:
            hrefs['row'] = row

        if grp is None:
            hrefs['group'] = self.ex_create_group(name='libcloud', env=env, row_href=row)
        else:
            hrefs['group'] = grp

        return hrefs
