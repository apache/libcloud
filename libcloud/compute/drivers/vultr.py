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
Vultr Driver
"""

import time

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlencode

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.compute.types import Provider, NodeState
from libcloud.common.types import LibcloudError, InvalidCredsError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation


class VultrResponse(JsonResponse):
    def parse_error(self):
        if self.status == httplib.OK:
            body = self.parse_body()
            return body
        elif self.status == httplib.FORBIDDEN:
            raise InvalidCredsError(self.body)
        else:
            raise LibcloudError(self.body)


class SSHKey(object):
    def __init__(self, id, name, pub_key):
        self.id = id
        self.name = name
        self.pub_key = pub_key

    def __repr__(self):
        return (('<SSHKey: id=%s, name=%s, pub_key=%s>') %
                (self.id, self.name, self.pub_key))


class VultrConnection(ConnectionKey):
    """
    Connection class for the Vultr driver.
    """

    host = 'api.vultr.com'
    responseCls = VultrResponse

    def add_default_params(self, params):
        """
        Add parameters that are necessary for every request

        This method add ``api_key`` to
        the request.
        """
        params['api_key'] = self.key
        return params

    def encode_data(self, data):
        return urlencode(data)

    def get(self, url):
        return self.request(url)

    def post(self, url, data):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.request(url, data=data, headers=headers, method='POST')


class VultrNodeDriver(NodeDriver):
    """
    VultrNode node driver.
    """

    connectionCls = VultrConnection

    type = Provider.VULTR
    name = 'Vultr'
    website = 'https://www.vultr.com'

    NODE_STATE_MAP = {'pending': NodeState.PENDING,
                      'active': NodeState.RUNNING}

    EX_CREATE_YES_NO_ATTRIBUTES = ['enable_ipv6',
                                   'enable_private_network',
                                   'auto_backups',
                                   'notify_activate',
                                   'ddos_protection']

    EX_CREATE_ID_ATTRIBUTES = {'iso_id': 'ISOID',
                               'script_id': 'SCRIPTID',
                               'snapshot_id': 'SNAPSHOTID',
                               'app_id': 'APPID'}

    EX_CREATE_ATTRIBUTES = ['ipxe_chain_url',
                            'label',
                            'userdata',
                            'reserved_ip_v4',
                            'hostname',
                            'tag']
    EX_CREATE_ATTRIBUTES.extend(EX_CREATE_YES_NO_ATTRIBUTES)
    EX_CREATE_ATTRIBUTES.extend(EX_CREATE_ID_ATTRIBUTES.keys())

    def list_nodes(self):
        return self._list_resources('/v1/server/list', self._to_node)

    def list_key_pairs(self):
        """
        List all the available SSH keys.
        :return: Available SSH keys.
        :rtype: ``list`` of :class:`SSHKey`
        """
        return self._list_resources('/v1/sshkey/list', self._to_ssh_key)

    def create_key_pair(self, name, public_key=''):
        """
        Create a new SSH key.
        :param name: Name of the new SSH key
        :type name: ``str``

        :key public_key: Public part of the new SSH key
        :type name: ``str``

        :return: True on success
        :rtype: ``bool``
        """
        params = {'name': name, 'ssh_key': public_key}
        res = self.connection.post('/v1/sshkey/create', params)
        return res.status == httplib.OK

    def delete_key_pair(self, key_pair):
        """
        Delete an SSH key.
        :param key_pair: The SSH key to delete
        :type key_pair: :class:`SSHKey`

        :return: True on success
        :rtype: ``bool``
        """
        params = {'SSHKEYID': key_pair.id}
        res = self.connection.post('/v1/sshkey/destroy', params)
        return res.status == httplib.OK

    def list_locations(self):
        return self._list_resources('/v1/regions/list', self._to_location)

    def list_sizes(self):
        return self._list_resources('/v1/plans/list', self._to_size)

    def list_images(self):
        return self._list_resources('/v1/os/list', self._to_image)

    def create_node(self, name, size, image, location, ex_ssh_key_ids=None,
                    ex_create_attr=None):
        """
        Create a node

        :param name: Name for the new node
        :type name: ``str``

        :param size: Size of the new node
        :type size: :class:`NodeSize`

        :param image: Image for the new node
        :type image: :class:`NodeImage`

        :param location: Location of the new node
        :type location: :class:`NodeLocation`

        :param ex_ssh_key_ids: IDs of the SSH keys to initialize
        :type ex_sshkeyid: ``list`` of ``str``

        :param ex_create_attr: Extra attributes for node creation
        :type ex_create_attr: ``dict``

        The `ex_create_attr` parameter can include the following dictionary
        key and value pairs:

        * `ipxe_chain_url`: ``str`` for specifying URL to boot via IPXE
        * `iso_id`: ``str`` the ID of a specific ISO to mount,
          only meaningful with the `Custom` `NodeImage`
        * `script_id`: ``int`` ID of a startup script to execute on boot,
          only meaningful when the `NodeImage` is not `Custom`
        * 'snapshot_id`: ``str`` Snapshot ID to restore for the initial
          installation, only meaningful with the `Snapshot` `NodeImage`
        * `enable_ipv6`: ``bool`` Whether an IPv6 subnet should be assigned
        * `enable_private_network`: ``bool`` Whether private networking
          support should be added
        * `label`: ``str`` Text label to be shown in the control panel
        * `auto_backups`: ``bool`` Whether automatic backups should be enabled
        * `app_id`: ``int`` App ID to launch if launching an application,
          only meaningful when the `NodeImage` is `Application`
        * `userdata`: ``str`` Base64 encoded cloud-init user-data
        * `notify_activate`: ``bool`` Whether an activation email should be
          sent when the server is ready
        * `ddos_protection`: ``bool`` Whether DDOS protection should be enabled
        * `reserved_ip_v4`: ``str`` IP address of the floating IP to use as
          the main IP of this server
        * `hostname`: ``str`` The hostname to assign to this server
        * `tag`: ``str`` The tag to assign to this server

        :return: The newly created node.
        :rtype: :class:`Node`

        """
        params = {'DCID': location.id, 'VPSPLANID': size.id,
                  'OSID': image.id, 'label': name}

        if ex_ssh_key_ids is not None:
            params['SSHKEYID'] = ','.join(ex_ssh_key_ids)

        ex_create_attr = ex_create_attr or {}
        for key, value in ex_create_attr.items():
            if key in self.EX_CREATE_ATTRIBUTES:
                if key in self.EX_CREATE_YES_NO_ATTRIBUTES:
                    params[key] = 'yes' if value else 'no'
                else:
                    if key in self.EX_CREATE_ID_ATTRIBUTES:
                        key = self.EX_CREATE_ID_ATTRIBUTES[key]
                    params[key] = value

        result = self.connection.post('/v1/server/create', params)
        if result.status != httplib.OK:
            return False

        subid = result.object['SUBID']

        retry_count = 3
        created_node = None

        for i in range(retry_count):
            try:
                nodes = self.list_nodes()
                created_node = [n for n in nodes if n.id == subid][0]
            except IndexError:
                time.sleep(1)
                pass
            else:
                break

        return created_node

    def reboot_node(self, node):
        params = {'SUBID': node.id}
        res = self.connection.post('/v1/server/reboot', params)

        return res.status == httplib.OK

    def destroy_node(self, node):
        params = {'SUBID': node.id}
        res = self.connection.post('/v1/server/destroy', params)

        return res.status == httplib.OK

    def _list_resources(self, url, tranform_func):
        data = self.connection.get(url).object
        sorted_key = sorted(data)
        return [tranform_func(data[key]) for key in sorted_key]

    def _to_node(self, data):
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
            if state == NodeState.RUNNING and \
               data['power_status'] != 'running':
                state = NodeState.STOPPED
        else:
            state = NodeState.UNKNOWN

        if 'main_ip' in data and data['main_ip'] is not None:
            public_ips = [data['main_ip']]
        else:
            public_ips = []

        extra_keys = []
        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['SUBID'], name=data['label'], state=state,
                    public_ips=public_ips, private_ips=None, extra=extra,
                    driver=self)

        return node

    def _to_location(self, data):
        return NodeLocation(id=data['DCID'], name=data['name'],
                            country=data['country'], driver=self)

    def _to_size(self, data):
        extra = {'vcpu_count': int(data['vcpu_count'])}
        ram = int(data['ram'])
        disk = int(data['disk'])
        bandwidth = float(data['bandwidth'])
        price = float(data['price_per_month'])

        return NodeSize(id=data['VPSPLANID'], name=data['name'],
                        ram=ram, disk=disk,
                        bandwidth=bandwidth, price=price,
                        extra=extra, driver=self)

    def _to_image(self, data):
        extra = {'arch': data['arch'], 'family': data['family']}
        return NodeImage(id=data['OSID'], name=data['name'], extra=extra,
                         driver=self)

    def _to_ssh_key(self, data):
        return SSHKey(id=data['SSHKEYID'], name=data['name'],
                      pub_key=data['ssh_key'])
