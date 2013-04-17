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
Brightbox Driver
"""

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.brightbox import BrightboxConnection
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

import base64


API_VERSION = '1.0'


def _extract(d, keys):
    return dict((k, d[k]) for k in keys if k in d and d[k] is not None)


class BrightboxNodeDriver(NodeDriver):
    """
    Brightbox node driver
    """

    connectionCls = BrightboxConnection

    type = Provider.BRIGHTBOX
    name = 'Brightbox'
    website = 'http://www.brightbox.co.uk/'
    features = {'create_node': ['ssh_key']}

    NODE_STATE_MAP = {'creating': NodeState.PENDING,
                      'active': NodeState.RUNNING,
                      'inactive': NodeState.UNKNOWN,
                      'deleting': NodeState.UNKNOWN,
                      'deleted': NodeState.TERMINATED,
                      'failed': NodeState.UNKNOWN,
                      'unavailable': NodeState.UNKNOWN}

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=API_VERSION, **kwargs):
        super(BrightboxNodeDriver, self).__init__(key=key, secret=secret,
                                                  secure=secure,
                                                  host=host, port=port,
                                                  api_version=api_version,
                                                  **kwargs)

    def _to_node(self, data):
        extra_data = _extract(data, ['fqdn', 'user_data', 'status',
                                     'interfaces', 'snapshots',
                                     'server_groups', 'hostname',
                                     'started_at', 'created_at',
                                     'deleted_at', 'console_token',
                                     'console_token_expires'])
        # deleting servers will have an empty zone for brightbox
        extra_data['zone'] = None
        if data['zone']:
            extra_data['zone'] = self._to_location(data['zone'])

        return Node(
            id=data['id'],
            name=data['name'],
            state=self.NODE_STATE_MAP[data['status']],

            private_ips=[interface['ipv4_address']
                         for interface in data['interfaces']
                         if 'ipv4_address' in interface],

            public_ips=[cloud_ip['public_ip']
                        for cloud_ip in data['cloud_ips']] +
                        [interface['ipv6_address']
                        for interface in data['interfaces']
                        if 'ipv6_address' in interface],

            driver=self.connection.driver,
            size=self._to_size(data['server_type']),
            image=self._to_image(data['image']),
            extra=extra_data
        )

    def _to_image(self, data):
        extra_data = _extract(data, ['arch', 'compatibility_mode',
                                     'created_at', 'description',
                                     'disk_size', 'min_ram', 'official',
                                     'owner', 'public', 'source',
                                     'source_type', 'status', 'username',
                                     'virtual_size', 'licence_name'])

        if data.get('ancestor', None):
            extra_data['ancestor'] = self._to_image(data['ancestor'])

        return NodeImage(
            id=data['id'],
            name=data['name'],
            driver=self,
            extra=extra_data
        )

    def _to_size(self, data):
        return NodeSize(
            id=data['id'],
            name=data['name'],
            ram=data['ram'],
            disk=data['disk_size'],
            bandwidth=0,
            price=0,
            driver=self
        )

    def _to_location(self, data):
        return NodeLocation(
            id=data['id'],
            name=data['handle'],
            country='GB',
            driver=self
        )

    def _post(self, path, data={}):
        headers = {'Content-Type': 'application/json'}
        return self.connection.request(path, data=data, headers=headers,
                                       method='POST')

    def _put(self, path, data={}):
        headers = {'Content-Type': 'application/json'}
        return self.connection.request(path, data=data, headers=headers,
                                       method='PUT')

    def create_node(self, **kwargs):
        """
        Create a new Brightbox node
        Reference: https://api.gb1.brightbox.com/1.0/#server_create_server

        :param ex_userdata: User data
        :param ex_servergroup: Name or list of server group ids to
                                    add server to
        :returns: Node instance
        """
        data = {
            'name': kwargs['name'],
            'server_type': kwargs['size'].id,
            'image': kwargs['image'].id,
        }

        if 'ex_userdata' in kwargs:
            data['user_data'] = base64.b64encode(b(kwargs['ex_userdata'])) \
                                      .decode('ascii')

        if 'location' in kwargs:
            data['zone'] = kwargs['location'].id

        if 'ex_servergroup' in kwargs:
            if not isinstance(kwargs['ex_servergroup'], list):
                kwargs['ex_servergroup'] = [kwargs['ex_servergroup']]
            data['server_groups'] = kwargs['ex_servergroup']

        data = self._post('/%s/servers' % self.api_version, data).object
        return self._to_node(data)

    def destroy_node(self, node):
        response = self.connection.request(
            '/%s/servers/%s' % (self.api_version, node.id),
            method='DELETE')
        return response.status == httplib.ACCEPTED

    def list_nodes(self):
        data = self.connection.request('/%s/servers' % self.api_version).object
        return list(map(self._to_node, data))

    def get_node(self, server_id, raw=False):
        data = self.connection.request('/%s/servers/%s'
                                       % (self.api_version, server_id)).object
        if raw == False:
            return self._to_node(data)
        else:
            return data

    def list_images(self):
        data = self.connection.request('/%s/images' % self.api_version).object
        return list(map(self._to_image, data))

    def list_sizes(self):
        data = self.connection.request('/%s/server_types' % self.api_version) \
                              .object
        return list(map(self._to_size, data))

    def list_locations(self):
        data = self.connection.request('/%s/zones' % self.api_version).object
        return list(map(self._to_location, data))

    def ex_list_cloud_ips(self):
        """
        List Cloud IPs

        :returns: List of cloud IP dicts
        """
        return self.connection.request('/%s/cloud_ips' % self.api_version) \
                              .object

    def ex_create_cloud_ip(self, name=None, reverse_dns=None):
        """
        Requests a new cloud IP address for the account

        :param reverse_dns: Reverse DNS hostname
        :returns: cloud-ip as dict
        """
        params = {}

        if reverse_dns:
            params['reverse_dns'] = reverse_dns
        if name:
            params['name'] = name
        return self._post('/%s/cloud_ips' % self.api_version, params).object

    def ex_update_cloud_ip(self, cloud_ip_id, reverse_dns):
        """
        Update some details of the cloud IP address

        :param cloud_ip_id: The id of the cloud ip.
        :param reverse_dns: Reverse DNS hostname
        :returns: cloud-ip as dict
        """
        response = self._put('/%s/cloud_ips/%s' % (self.api_version,
                                                   cloud_ip_id),
                             {'reverse_dns': reverse_dns})
        return response.status == httplib.OK

    def ex_map_cloud_ip(self, cloud_ip_id, interface_id):
        """
        Maps (or points) a cloud IP address at a server's interface
        or a load balancer to allow them to respond to public requests

        :param cloud_ip_id: The id of the cloud ip.
        :param interface_id: The Interface ID or LoadBalancer ID to
                              which this Cloud IP should be mapped to
        :returns: True if the mapping was successful.
        """
        response = self._post('/%s/cloud_ips/%s/map' % (self.api_version,
                                                        cloud_ip_id),
                              {'destination': interface_id})
        return response.status == httplib.ACCEPTED

    def ex_unmap_cloud_ip(self, cloud_ip_id):
        """
        Unmaps a cloud IP address from its current destination making
        it available to remap. This remains in the account's pool
        of addresses

        :param cloud_ip_id: The id of the cloud ip.
        :returns: True if the unmap was successful.
        """
        response = self._post('/%s/cloud_ips/%s/unmap' % (self.api_version,
                                                          cloud_ip_id))
        return response.status == httplib.ACCEPTED

    def ex_destroy_cloud_ip(self, cloud_ip_id):
        """
        Release the cloud IP address from the account's ownership

        :param cloud_ip_id: The id of the cloud ip.
        :returns: True if the unmap was successful.
        """
        response = self.connection.request(
            '/%s/cloud_ips/%s' % (self.api_version,
                                  cloud_ip_id),
            method='DELETE')
        return response.status == httplib.OK

    #####
    # ! firewall policies
    def ex_list_firewall_policies(self):
        """
        List firewall policies

        :returns: Returns a list of firewall policies
        """
        return self.connection.request('/%s/firewall_policies'
                                       % self.api_version).object

    def ex_get_firewall_policy(self, fw_policy_id):
        """
        Gets a single firewall policy

        :param fw_policy_id: The firewall policy id
        :returns: the newly created firewall policy as dict
        """
        return self.connection.request('/%s/firewall_policies/%s'
                                    % (self.api_version, fw_policy_id)).object

    def ex_create_firewall_policy(self, name, server_group_id=None):
        """
        Creates new firewall policy

        :param name:
        :param server_group:
        """

        params = {
            'server_group': server_group_id,
            'name': name
        }
        return self._post('/%s/firewall_policies' % self.api_version, params).object

    def ex_update_firewall_policy(self, fw_policy_id, name=None,
                                  server_group_id=None):
        raise NotImplementedError()

    def ex_apply_firewall_policy(self, fw_policy_id, server_group_id):
        """
        Applies firewall policy to given server group

        :param fw_policy_id:
        :param server_group_id: server group to add to policy
        :returns: Boolean about the success of the operation
        """
        params = {
            'server_group': server_group_id,
        }
        response = self._post('/%s/firewall_policies/%s/apply_to'
                                    % (self.api_version, fw_policy_id),
                                    params)
        return response.status == httplib.ACCEPTED

    def ex_remove_firewall_policy(self, fw_policy_id, server_group_id):
        """
        Removes firewall policy from given server group

        :param fw_policy_id:
        :param server_group_id: server group to remove from policy
        :returns: Boolean about the success of the operation
        """
        params = {
            'server_group': server_group_id,
        }
        response = self._post('/%s/firewall_policies/%s/remove'
                                    % (self.api_version, fw_policy_id),
                                    params)
        return response.status == httplib.ACCEPTED

    def ex_destroy_firewall_policy(self, fw_policy_id):
        """
        Delete the firewall policy

        :param fw_policy_id: The id of the firewall policy
        :returns: Boolean about the success of the operation
        """
        response = self.connection.request(
            '/%s/firewall_policies/%s'
                % (self.api_version, fw_policy_id), method='DELETE')
        return response.status == httplib.ACCEPTED

    ######
    # !firewall rules

    def ex_list_firewall_rules(self, fw_policy_id):
        """
        list all rules for fw_policy

        :param fw_policy_id:
        """
        raise NotImplementedError()

    def ex_get_firewall_rule(self, fw_rule_id):
        """
        Get full details of the firewall rule.

        :param fw_rule_id:
        :returns: the newly created firewall rule as dict
        """
        return self.connection.request('/%s/firewall_rules/%s'
                                    % (self.api_version, fw_rule_id)).object

    def ex_create_firewall_rule(self, fw_policy_id, protocol=None, source=None,
                                source_port=None, destination=None,
                                destination_port=None, icmp_type=None,
                                description=None):
        """
        Create a new firewall rule for a firewall policy.

        :param fw_policy_id:
        :param protocol:
        :param source:
        :param source_port:
        :param destination:
        :param destination_port:
        :param icmp_type:
        :param description:
        """
        params = {
            'firewall_policy': fw_policy_id,
            'protocol': protocol,
            'source': source,
            'source_port': source_port,
            'destination': destination,
            'destination_port': destination_port,
            'icmp_type': icmp_type,
            'description': description,
        }
        return self._post('/%s/firewall_rules'
                          % self.api_version, params).object

    def ex_update_firewall_rule(self, fw_rule_id, protocol, source,
                                source_port, destination, destination_port,
                                icmp_type, description):
        """
        update a new firewall rule for a firewall policy.

        :param fw_policy_id:
        :param protocol:
        :param source:
        :param source_port:
        :param destination:
        :param destination_port:
        :param icmp_type:
        :param description:
        """
        raise NotImplementedError()

    def ex_destroy_firewall_rule(self, fw_rule_id):
        """
        Destroy the firewall rule.

        :param fw_rule_id: The id of the fw rule to destroy
        """
        response = self.connection.request(
            '/%s/firewall_rules/%s' % (self.api_version,
                                       fw_rule_id), method='DELETE')
        return response.status == httplib.ACCEPTED

    ######
    # !server group
    def ex_list_server_groups(self):
        """
        List server groups

        :returns: Returns a list of server group dicts
        """
        return self.connection.request('/%s/server_groups'
                                       % self.api_version).object

    def ex_get_server_group(self, server_group_id):
        """
        Gets a single server group

        :param server_group_id: The group id
        :returns: the newly created server group as dict
        """
        return self.connection.request('/%s/server_groups/%s'
                                % (self.api_version, server_group_id)).object

    def ex_create_server_group(self, name):
        """
        Requests a new server group for the account

        :param name: group name
        :returns: the newly created server group as dict
        """
        params = {}

        if name:
            params['name'] = name

        return self._post('/%s/server_groups' % self.api_version, params).object

    def ex_update_server_group(self, server_group_id, name=None, description=None):
        """
        Update one of more fields of a server group

        :param server_group_id: The id of the server group
        :param name: The name of the server group or None
        :param description: The description of the server group or None
        :returns: Boolean about the success of the operation
        """
        params = {}
        if name:
            params['name'] = name
        if description:
            params['description'] = description
        response = self._put('/%s/server_groups/%s' % (self.api_version,
                                                   server_group_id), params)
        return response.status == httplib.ACCEPTED

    def ex_add_to_server_group(self, server_group_id, server_id):
        """
        Add a server to a server group

        :param server_group_id: The id of the server group
        :param server_id: a server-id
        :returns: Boolean about the success of the operation
        """
        params = {}
        if server_id and "srv-" in server_id:
            params['servers'] = [{"server": server_id}]
        response = self._post("/%s/server_groups/%s/add_servers"
                              % (self.api_version, server_group_id), params)
        return response.status == httplib.ACCEPTED

    def ex_remove_from_server_group(self, server_group_id, server_id):
        """
        Removes a server from a server group

        :param server_group_id: The id of the server group
        :param server_id: a server-id
        :returns: Boolean about the success of the operation
        """
        params = {}
        if server_id and "srv-" in server_id:
            params['servers'] = [{"server": server_id}]
        url = "/%s/server_groups/%s/remove_servers" %  (self.api_version, server_group_id)
        response = self._post(url, params)
        return response.status == httplib.ACCEPTED

    def ex_destroy_server_group(self, server_group_id):
        """
        Delete the server group

        :param server_group_id: The id of the server group
        :returns: Boolean about the success of the operation
        """
        response = self.connection.request(
            '/%s/server_groups/%s' % (self.api_version,
                                            server_group_id), method='DELETE')
        return response.status == httplib.ACCEPTED
