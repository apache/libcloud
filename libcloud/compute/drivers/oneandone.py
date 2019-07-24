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
1&1 Cloud Server Compute driver
"""
import json

from libcloud.compute.providers import Provider
from libcloud.common.base import JsonResponse, ConnectionKey
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation, \
    Node, NodeAuthPassword, NodeAuthSSHKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import NodeState
from libcloud.utils.py3 import httplib
from libcloud.compute.base import NodeDriver

from time import sleep

API_HOST = 'cloudpanel-api.1and1.com'
API_VERSION = '/v1/'

__all__ = [
    'API_HOST',
    'API_VERSION',
    'OneAndOneResponse',
    'OneAndOneConnection',
    'OneAndOneNodeDriver'
]


class OneAndOneResponse(JsonResponse):
    """
    OneAndOne response parsing.
    """
    valid_response_codes = [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_error(self):

        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body['message'])
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body['message'], self.status)
            else:
                error = body
            return error

    def success(self):
        return self.status in self.valid_response_codes


class OneAndOneConnection(ConnectionKey):
    """
    Connection class for the 1&1 driver
    """

    host = API_HOST
    api_prefix = API_VERSION
    responseCls = OneAndOneResponse

    def encode_data(self, data):
        return json.dumps(data)

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` and ``Content-Type`` to the request.
        """
        headers['X-Token'] = self.key
        headers['Content-Type'] = 'application/json'
        return headers

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False):
        """
        Some requests will use the href attribute directly.
        If this is not the case, then we should formulate the
        url based on the action specified.
        If we are using a full url, we need to remove the
        host and protocol components.
        """
        action = self.api_prefix + action.lstrip('/')

        return super(OneAndOneConnection, self). \
            request(action=action,
                    params=params,
                    data=data,
                    headers=headers,
                    method=method,
                    raw=raw)


class OneAndOneNodeDriver(NodeDriver):
    """
      Base OneAndOne node driver.
    """
    connectionCls = OneAndOneConnection
    name = '1and1'
    website = 'http://www.1and1.com'
    type = Provider.ONEANDONE

    NODE_STATE_MAP = {
        'POWERING_ON': NodeState.STARTING,
        'POWERING_OFF': NodeState.PENDING,
        'POWERED_OFF': NodeState.STOPPING,
        'POWERED_ON': NodeState.RUNNING,
        'REBOOTING': NodeState.REBOOTING,
        'CONFIGURING': NodeState.RECONFIGURING,
        'REMOVING': NodeState.UNKNOWN,
        'DEPLOYING': NodeState.STARTING,
    }

    """
    Core Functions
    """

    def list_sizes(self):
        """
        Lists all sizes

        :return: A list of all configurable node sizes.
        :rtype: ``list`` of :class:`NodeSize`
        """
        sizes = []

        fixed_instances = self._list_fixed_instances()
        for value in fixed_instances:
            node_size = self._to_node_size(value)
            sizes.append(node_size)

        return sizes

    def list_locations(self):
        """
        Lists all locations

        :return: ``list`` of :class:`NodeLocation`
        :rtype: ``list``
        """
        datacenters = self.ex_list_datacenters()
        locations = []
        for values in datacenters:
            node_size = self._to_location(values)
            locations.append(node_size)

        return locations

    def list_images(self, image_type=None):
        """
        :return: ``list`` of :class: `NodeImage`
        :rtype: ``list``
        """
        response = self.connection.request(
            action='server_appliances',
            method='GET'
        )

        return self._to_images(response.object, image_type)

    def get_image(self, image_id):
        response = self.connection.request(
            action='server_appliances/%s' % image_id,
            method='GET'
        )
        return self._to_image(response.object)

    """
    Node functions
    """

    def create_node(self,
                    name,
                    image,
                    ex_fixed_instance_size_id,
                    location=None,
                    auth=None,
                    ex_ip=None,
                    ex_monitoring_policy_id=None,
                    ex_firewall_policy_id=None,
                    ex_loadbalancer_id=None,
                    ex_description=None,
                    ex_power_on=None):
        """
        Creates a node.

        :param name: The name of the new node
        :type name: `str`

        :param ex_fixed_instance_size_id:
        Fixed instance size ID from list_sizes
        :type ex_fixed_instance_size_id: ``str``

        :param location: 1&1 Data center Location
        :type location: `NodeLocation`

        :param ex_ip: IP address
        :type ex_ip: `str`

        :param ex_ssh_key: SSH Key
        :type ex_ssh_key: `str`

        :param password: Password
        :type password: `str`

        :param ex_monitoring_policy_id:
        :type ex_firewall_policy_id: `str`

        :param ex_firewall_policy_id:
        :type ex_firewall_policy_id: `str`

        :param ex_loadbalancer_id:
        :type ex_loadbalancer_id: `str`

        :param ex_description:
        :type ex_description: `str`

        :param ex_power_on:
        :type ex_power_on: `bool`

        :return:    Instance of class ``Node``
        :rtype:     :class:`Node`
        """

        body = {
            'name': name,
            'appliance_id': image.id,
            'hardware': {
                'fixed_instance_size_id': ex_fixed_instance_size_id
            },
        }

        if location is not None:
            body['datacenter_id'] = location.id
        if ex_power_on is not None:
            body['power_on'] = ex_power_on

        if ex_description is not None:
            body['description'] = ex_description

        if ex_firewall_policy_id is not None:
            body['firewall_policy_id'] = ex_firewall_policy_id

        if ex_monitoring_policy_id is not None:
            body['monitoring_policy_id'] = ex_monitoring_policy_id

        if ex_loadbalancer_id is not None:
            body['loadbalancer_id'] = ex_loadbalancer_id

        if auth is not None:
            if isinstance(auth, NodeAuthPassword):
                body['password'] = auth.password
            elif isinstance(auth, NodeAuthSSHKey):
                body['rsa_key'] = auth.pubkey
        if ex_ip is not None:
            body['ip_id'] = ex_ip

        response = self.connection.request(
            action='servers',
            data=body,
            method='POST',
        )

        return self._to_node(response.object)

    def list_nodes(self):
        """
        List all nodes.

        :return: ``list`` of :class:`Node`
        :rtype: ``list``
        """
        response = self.connection.request(
            action='servers',
            method='GET'
        )

        return self._to_nodes(response.object)

    def destroy_node(self, node, ex_keep_ips=False):
        """
        Destroys a node.

        :param node: The node you wish to destroy.
        :type volume: :class:`Node`

        :param ex_keep_ips: True to keep all IP addresses assigned to the node
        :type ex_keep_ips: : ``bool``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """
        self.ex_shutdown_server(node.id)

        self._wait_for_state(node.id, 'POWERED_OFF')

        response = self.connection.request(
            action='servers/%s' % node.id,
            params={'keep_ips': ex_keep_ips},
            method='DELETE'
        )

        return self._to_node(response.object)

    def reboot_node(self, node):
        """
        Reboots the node.

        :param node: The node you wish to destroy.
        :type volume: :class:`Node`

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """
        shutdown_body = {
            "action": "REBOOT",
            "method": "HARDWARE"
        }
        response = self.connection.request(
            action='servers/%s/status/action' % node.id,
            data=shutdown_body,
            method='PUT',
        )
        return self._to_node(response.object)

    """
    Extension functions
    """

    def ex_rename_server(self, server_id, name=None, description=None):
        """
        Renames the server
        :param  server_id: ID of the server you want to rename

        :param  name: New name of the server
        :type: ``str``

        :param description: New description of the server
        :type: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description

        response = self.connection.request(
            action='servers/%s' % server_id,
            data=body,
            method='PUT'
        )

        return self._to_node(response.object)

    def ex_get_server_hardware(self, server_id):
        """
        Gets all server hardware

        :param server_id: Id of the server
        :type: ``str``

        :return: Server's hardware
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='servers/%s/hardware' % server_id,
            method='GET'
        )
        return response.object

    """
    Hardware operations
    """

    def ex_modify_server_hardware(self, server_id,
                                  fixed_instance_size_id=None, vcore=None,
                                  cores_per_processor=None, ram=None):
        """
        Modifies server's hardware

        :param server_id:
        :type: ``str``

        :param fixed_instance_size_id: Id of the fixed instance size
        :type: ``str``

        :param vcore: Virtual cores count
        :type: ``int``

        :param cores_per_processor: Count of cores per procesor
        :type: ``int``

        :param ram: Amount of ram for the server
        :type: ``int``

        :return:    Instance of class ``Node``
        :type:     :class: `Node`
        """

        body = {}

        if fixed_instance_size_id is not None:
            body['fixed_instance_size_id'] = fixed_instance_size_id
        if vcore is not None:
            body['vcore'] = vcore
        if cores_per_processor is not None:
            body['cores_per_processor'] = cores_per_processor
        if ram is not None:
            body['ram'] = ram

        response = self.connection.request(
            action='servers/%s/hardware' % server_id,
            data=body,
            method='PUT'
        )

        return self._to_node(response.object)

    """
    HDD operations
    """

    def ex_modify_server_hdd(self, server_id, hdd_id=None, size=None):
        """
        Modifies server hard disk drives

        :param server_id: Id of the server
        :type: ``str``

        :param hdd_id: Id of the hard disk
        :type: ``str``

        :param size: Size of the hard disk
        :type: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        body = {}

        if size is not None:
            body['size'] = size

            response = self.connection.request(
                action='servers/%s/hardware/hdds/%s' % (server_id, hdd_id),
                data=body,
                method='PUT'
            )

            return self._to_node(response.object)

    def ex_add_hdd(self, server_id, size, is_main):
        """
        Add a hard disk to the server

        :param server_id: Id of the server
        :type: ``str``

        :param size: Size of the new disk
        :type: ``str``

        :param is_main: Indicates if the disk is going to be the boot disk
        :type: ``boolean``

        :return:    Instance of class ``Node``
        :type:     :class: `Node`
        """
        body = {
            'size': size,
            'is_main': is_main
        }

        response = self.connection.request(
            action='servers/%s/hardware/hdds' % server_id,
            data=body,
            method='POST'
        )

        return self._to_node(response.object)

    def ex_remove_hdd(self, server_id, hdd_id):
        """
        Removes existing hard disk

        :param server_id: Id of the server
        :type: ``str``

        :param hdd_id: Id of the hard disk
        :type: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        response = self.connection.request(
            action='servers/%s/hardware/hdds/%s' % (server_id, hdd_id),
            method='DELETE'
        )

        return self._to_node(response.object)

    """
    Data center operations
    """

    def ex_list_datacenters(self):
        """
        Lists all data centers

        :return: List of data centers
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='datacenters',
            method='GET'
        )

        return response.object

    def ex_get_server(self, server_id):
        """
        Gets a server

        :param server_id: Id of the server to be retrieved
        :type: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        response = self.connection.request(
            action='servers/%s' % (server_id),
            method='GET'
        )

        return self._to_node(response.object)

    def ex_shutdown_server(self, server_id, method='SOFTWARE'):
        """
        Shuts down the server

        :param server_id: Id of the server to be shut down
        :type: ``str``

        :param method: Method of shutting down "SOFTWARE" or "HARDWARE"

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        shutdown_body = {
            'action': 'POWER_OFF',
            'method': method
        }
        response = self.connection.request(
            action='servers/%s/status/action' % (server_id),
            data=shutdown_body,
            method='PUT',
        )
        return self._to_node(response.object)

    """
    Image operations
    """

    def ex_get_server_image(self, server_id):
        """
        Gets server image

        :param server_id: Id of the server
        :type: ``str``

        :return: Server image
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='servers/%s/image' % server_id,
            method='GET'
        )
        return response.object

    def ex_reinstall_server_image(self, server_id, image_id, password=None):
        """
        Installs a new image on the server

        :param server_id: Id of the server
        :type: ``str``

        :param image_id: Id of the image (Server Appliance)
        :type: ``str``

        :param password: New password for the server

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        body = {
            'id': image_id,
        }

        if password is not None:
            body['password'] = password

        response = self.connection.request(
            action='servers/%s/image' % server_id,
            data=body,
            method='PUT'
        )
        return self._to_node(response.object)

    """
    Server IP operations
    """

    def ex_list_server_ips(self, server_id):
        """
        Gets all server IP objects

        :param server_id: Id of the server
        :type: ``str``

        :return: List of server IP objects
        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request(
            action='servers/%s/ips' % server_id,
            method='GET'
        )

        return response.object

    def ex_get_server_ip(self, server_id, ip_id):
        """
        Get a single server IP object

        :param server_id: Id of the server
        :type: ``str``

        :param ip_id: ID of the IP address
        :type: ``str``

        :return: IP address object
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='servers/%s/ips/%s' % (server_id, ip_id),
            method='GET'
        )

        return response.object

    def ex_assign_server_ip(self, server_id, ip_type):
        """
        Assigns a new IP address to the server

        :param server_id: Id of the server
        :type: ``str``

        :param ip_type: Type of the IP address [IPV4,IPV6]
        :type: ``str``

        :return: ``Node`` instance
        :rtype: ``Node``
        """

        body = {
            'type': ip_type
        }

        response = self.connection.request(
            action='servers/%s/ips' % server_id,
            data=body,
            method='POST'
        )

        return self._to_node(response.object)

    def ex_remove_server_ip(self, server_id, ip_id, keep_ip=None):
        """
        Removes an IP address from the server

        :param server_id: Id of the server
        :type: ``str``

        :param ip_id: ID of the IP address
        :type: ``str``

        :param keep_ip: Indicates whether IP address will be removed from
                        the Cloud Panel
        :type: ``boolean``

        :return: ``Node`` instance
        :rtype: ``Node``
        """

        body = {}
        if keep_ip is not None:
            body['keep_ip'] = keep_ip

        response = self.connection.request(
            action='servers/%s/ips/%s' % (server_id, ip_id),
            data=body,
            method='DELETE'
        )

        return self._to_node(response.object)

    def ex_get_server_firewall_policies(self, server_id, ip_id):
        """
        Gets a firewall policy of attached to the server's IP

        :param server_id: Id of the server
        :type: ``str``

        :param ip_id: ID of the IP address
        :type: ``str``

        :return: IP address object
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='/servers/%s/ips/%s/firewall_policy' % (server_id, ip_id),
            method='GET'
        )

        return response.object

    def ex_add_server_firewall_policy(self, server_id, ip_id, firewall_id):
        """
        Adds a firewall policy to the server's IP address

        :param server_id: Id of the server
        :type: ``str``

        :param ip_id: ID of the IP address
        :type: ``str``

        :param firewall_id: ID of the firewall policy
        :type: ``str``

        :return: ``Node`` instance
        :rtype: ``Node``
        """
        body = {
            'id': firewall_id
        }
        response = self.connection.request(
            action='/servers/%s/ips/%s/firewall_policy' % (server_id, ip_id),
            data=body,
            method='POST'
        )

        return self._to_node(response.object)

    """
    Firewall Policy operations
    """

    def ex_create_firewall_policy(self, name, rules, description=None):
        """
        Creates a firewall Policy.

        :param name:
        :param description:
        :param rules:

        :rtype: `dict`
        :return: `dict` firewall policy

        """
        body = {
            'name': name
        }

        if description is not None:
            body['description'] = description

        if len(rules) == 0:
            raise ValueError(
                'At least one firewall rule is required.'
            )
        else:
            body['rules'] = rules

        response = self.connection.request(
            action='firewall_policies',
            data=body,
            method='POST',
        )

        return response.object

    def ex_list_firewall_policies(self):
        """"
        List firewall policies

        :return: 'dict'
        """

        response = self.connection.request(
            action='firewall_policies',
            method='GET'
        )

        return response.object

    def ex_get_firewall_policy(self, fw_id):
        """
        Gets firewall policy

        :param fw_id: ID of the firewall policy
        :return: 'dict'
        """

        response = self.connection.request(
            action='firewall_policy/%s' % fw_id,
            method='GET'
        )

        return response.object

    def ex_delete_firewall_policy(self, fw_id):
        """
        Deletes firewall policy

        :param fw_id: ID of the Firewall
        :return: 'dict'
        """
        response = self.connection.request(
            action='firewall_policy/%s' % fw_id,
            method='DELETE'
        )

        return response.object

    """
    Shared storage operations
    """

    def ex_list_shared_storages(self):
        """
        List of shared storages
        :return: 'dict'
        """
        response = self.connection.request(
            action='shared_storages',
            method='GET'
        )

        return response.object

    def ex_get_shared_storage(self, storage_id):
        """
        Gets a shared storage
        :return: 'dict'
        """
        response = self.connection.request(
            action='shared_storages/%s' % (storage_id),
            method='GET'
        )

        return response.object

    def ex_create_shared_storage(self, name, size, datacenter_id=None,
                                 description=None):
        """
        Creates a shared storage
        :param name: Name of the storage
        :param size: Size of the storage
        :param datacenter_id: datacenter where storage should be created
        :param description: description ot the  storage
        :return: 'dict'
        """

        body = {
            'name': name,
            'size': size,
            'datacenter_id': datacenter_id
        }

        if description is not None:
            body['description'] = description

        response = self.connection.request(
            action='shared_storages',
            data=body,
            method='POST'
        )

        return response.object

    def ex_delete_shared_storage(self, storage_id):
        """
        Removes a shared storage

        :param storage_id: Id of the shared storage
        :type: ``str``

        :return: Instnace of shared storage
        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request(
            action='shared_storages/%s' % storage_id,
            method='DELETE'
        )

        return response.object

    def ex_attach_server_to_shared_storage(self, storage_id,
                                           server_id, rights):
        """
        Attaches a single server to a shared storage

        :param storage_id: Id of the shared storage
        :param server_id: Id of the server to be attached to the shared storage
        :param rights:
        :return:
        :rtype: 'dict'
        """
        body = {
            'severs': [
                {
                    'id': server_id,
                    'rights': rights
                }
            ]
        }

        response = self.connection.request(
            action='shared_storages/%s/servers' % storage_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_get_shared_storage_server(self, storage_id, server_id):
        """
        Gets a shared storage's server
        :param storage_id:
        :param server_id:
        :return:
        """
        response = self.connection.request(
            action='shared_storages/%s/servers/%s' % (storage_id, server_id),
        )

        return response.object

    def ex_detach_server_from_shared_storage(self, storage_id,
                                             server_id):
        """
        Detaches a server from shared storage

        :param storage_id: Id of the shared storage
        :type: ``str``

        :param server_id: Id of the server
        :type: ``str``

        :return: Instance of shared storage
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='shared_storages/%s/servers/%s' % (storage_id, server_id),
            method='DELETE'
        )

        return response.object

    """
    Load Balancers operations
    """

    def ex_create_load_balancer(self, name, method, rules,
                                persistence=None,
                                persistence_time=None,
                                health_check_test=None,
                                health_check_interval=None,
                                health_check_path=None,
                                health_check_parser=None,
                                datacenter_id=None,
                                description=None):
        """

        :param name: Name of the load balancer

        :param method: Load balancer method

        :param rules: Load balancer rules
        :type rules: ``list`` of ``dict``

        :param persistence: Indictes if persistance is set
        :type persistence: ``boolean``

        :param persistence_time: Persistance time
        :type persistence_time: ``int``

        :param health_check_test: Type of test
        :type health_check_test:``str``

        :param health_check_interval: Interval of the check

        :param health_check_path: Path
        :type health_check_path: ``str``

        :param health_check_parser: Parser
        :type health_check_parser:``str``

        :param datacenter_id: Data center id
        :type datacenter_id:``str``

        :param description: Description of load balancer
        :type description:``str``

        :return: ``dict``
        """

        body = {
            'name': name,
            'method': method,
        }

        body['rules'] = []
        body['rules'] = rules

        if persistence is not None:
            body['persistence'] = persistence
        if persistence_time is not None:
            body['persistence_time'] = persistence_time
        if health_check_test is not None:
            body['health_check_test'] = health_check_test
        if health_check_interval is not None:
            body['health_check_interval'] = health_check_interval
        if health_check_path is not None:
            body['health_check_path'] = health_check_path
        if health_check_parser is not None:
            body['health_check_parser'] = health_check_parser
        if datacenter_id is not None:
            body['datacenter_id'] = datacenter_id
        if description is not None:
            body['description'] = description

        response = self.connection.request(
            action='load_balancers',
            data=body,
            method='POST'
        )

        return response.object

    def ex_update_load_balancer(self, lb_id, name=None, description=None,
                                health_check_test=None,
                                health_check_interval=None,
                                persistence=None,
                                persistence_time=None,
                                method=None):
        body = {}

        if name is not None:
            body['name'] = name
        if description is not None:
            body['description'] = description
        if health_check_test is not None:
            body['health_check_test'] = health_check_test
        if health_check_interval is not None:
            body['health_check_interval'] = health_check_interval
        if persistence is not None:
            body['persistence'] = persistence
        if persistence_time is not None:
            body['persistence_time'] = persistence_time
        if method is not None:
            body['method'] = method

        response = self.connection.request(
            action='load_balancers/%s' % lb_id,
            data=body,
            method='PUT'
        )

        return response.object

    def ex_add_servers_to_load_balancer(self, lb_id, server_ips=[]):
        """
        Adds server's IP address to load balancer

        :param lb_id: Load balancer ID
        :type: ``str``

        :param server_ips: Array of server IP IDs
        :type: ``list`` of ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """
        body = {
            'server_ips': server_ips,
        }

        response = self.connection.request(
            action='load_balancers/%s/server_ips' % lb_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_remove_server_from_load_balancer(self, lb_id, server_ip):
        """
        Removes server's IP from load balancer

        :param lb_id: Load balancer ID
        :type: ``str``

        :param server_ip: ID of the server IP
        :type: ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='/load_balancers/%s/server_ips/%s' % (lb_id, server_ip),
            method='DELETE'
        )

        return response.object

    def ex_add_load_balancer_rule(self, lb_id, protocol, port_balancer,
                                  port_server, source=None):
        """
        Adds a rule to load balancer

        :param lb_id: Load balancer ID
        :rtype: ``str``

        :param protocol: Load balancer protocol
        :rtype: ``str``

        :param port_balancer: Port to be balananced
        :rtype: ``int``

        :param port_server: Server port
        :rtype: ``int``

        :param source: Source IP address
        :rtype: ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """

        body = {
            'rules': [
                {
                    'protocol': protocol,
                    'port_balancer': port_balancer,
                    'port_server': port_server
                }
            ]
        }

        if source is not None:
            body['rules'][0]['source'] = source

        response = self.connection.request(
            action='/load_balancers/%s/rules' % lb_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_remove_load_balancer_rule(self, lb_id, rule_id):
        """
        Removes load balancer rule

        :param lb_id: Load balancer ID
        :rtype: ``str``

        :param rule_id: Rule ID
        :rtype: ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='/load_balancers/%s/rules/%s' % (lb_id, rule_id),
            method='DELETE'
        )

        return response.object

    def ex_list_load_balancers(self):
        """
        Lists all load balancers

        :return: List of load balancers
        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request(
            action='load_balancers',
            method='GET'
        )
        return response.object

    def ex_get_load_balancer(self, lb_id):
        """
        Gets a single load balancer

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s' % lb_id,
            method='GET'
        )

        return response.object

    def ex_list_load_balancer_server_ips(self, lb_id):
        """
        List balanced server IP addresses

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :return: Array of IP address IDs
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s/server_ips' % lb_id,
            method='GET'
        )

        return response.object

    def ex_get_load_balancer_server_ip(self, lb_id, server_ip):
        """
        Gets load balanced server id

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :param server_ip: ID of the server IP
        :type server_ip: ``str``

        :return: Server IP
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s/server_ips/%s' % (lb_id, server_ip),
            method='GET'
        )

        return response.object

    def ex_list_load_balancer_rules(self, lb_id):
        """
        Lists loadbalancer rules

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :return: Lists of rules
        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s/rules' % lb_id,
            method='GET'
        )

        return response.object

    def ex_get_load_balancer_rule(self, lb_id, rule_id):
        """
        Get a load balancer rule

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :param rule_id: Rule ID
        :type rule_id: ``str``

        :return: A load balancer rule
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s/rules/%s' % (lb_id, rule_id),
            method='GET'
        )

        return response.object

    def ex_delete_load_balancer(self, lb_id):
        """
        Deletes a load balancer rule

        :param lb_id: ID of the load balancer
        :type lb_id: ``str``

        :param rule_id: Rule ID
        :type rule_id: ``str``

        :return: Instance of load balancer
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='load_balancers/%s' % lb_id,
            method='DELETE'
        )

        return response.object

    """
    Public IP operations
    """

    def ex_list_public_ips(self):
        """
        Lists all public IP addresses

        :return: Array of public addresses
        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request(
            action='public_ips',
            method='GET'
        )

        return response.object

    def ex_create_public_ip(self, type, reverse_dns=None, datacenter_id=None):
        """
        Creates a public IP

        :param type: Type of IP (IPV4 or IPV6)
        :type type: ``str``

        :param reverse_dns: Reverse DNS
        :type reverse_dns: ``str``

        :param datacenter_id: Datacenter ID where IP address will be crated
        :type datacenter_id: ``str``

        :return: Instance of Public IP
        :rtype: ``dict``
        """
        body = {
            'type': type
        }

        if reverse_dns is not None:
            body['reverse_dns'] = reverse_dns
        if datacenter_id is not None:
            body['datacenter_id'] = datacenter_id

        response = self.connection.request(
            action='public_ips',
            data=body,
            method='POST'
        )

        return response.object

    def ex_get_public_ip(self, ip_id):
        """
        Gets a Public IP

        :param ip_id: ID of the IP
        :type ip_id: ``str``

        :return: Instance of Public IP
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='public_ips/%s' % ip_id,
            method='GET'
        )

        return response.object

    def ex_delete_public_ip(self, ip_id):
        """
        Deletes a public IP

        :param ip_id: ID of public IP
        :type ip_id: ``str``

        :return: Instance of IP Address
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='public_ips/%s' % ip_id,
            method='DELETE'
        )

        return response

    def ex_update_public_ip(self, ip_id, reverse_dns):
        """
        Updates a Public IP

        :param ip_id: ID of public IP
        :type ip_id: ``str``

        :param reverse_dns: Reverse DNS
        :type reverse_dns: ``str``

        :return: Instance of Public IP
        :rtype: ``dict``
        """

        body = {
            'reverse_dns': reverse_dns
        }
        response = self.connection.request(
            action='public_ips/%s' % ip_id,
            data=body,
            method='DELETE'
        )

        return response.object

    """
    Private Network Operations
    """

    def ex_list_private_networks(self):
        """
        Lists all private networks

        :return: List of private networks
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='private_networks',
            method='GET'
        )

        return response.object

    def ex_create_private_network(self, name, description=None,
                                  datacenter_id=None,
                                  network_address=None,
                                  subnet_mask=None):
        """
        Creates a private network

        :param name: Name of the private network
        :type name: ``str``

        :param description: Description of the private network
        :type description: ``str``

        :param datacenter_id: ID of the data center for the private network
        :type datacenter_id: ``str``

        :param network_address: Network address of the private network
        :type network_address: ``str``

        :param subnet_mask: Subnet mask of the private network
        :type subnet_mask: ``str``

        :return: Newly created private network
        :rtype: ``dict``
        """

        body = {
            'name': name
        }

        if description is not None:
            body['description'] = description
        if datacenter_id is not None:
            body['datacenter_id'] = datacenter_id
        if network_address is not None:
            body['network_address'] = network_address
        if subnet_mask is not None:
            body['subnet_maks'] = subnet_mask

        response = self.connection.request(
            action='private_networks',
            data=body,
            method='POST'
        )
        return response.object

    def ex_delete_private_network(self, network_id):
        """
        Deletes a private network

        :param network_id: Id of the private network
        :type network_id: ``str``

        :return: Instance of the private network being deleted
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='private_networks' % network_id,
            method='DELETE'
        )

        return response.object

    def ex_update_private_network(self, network_id,
                                  name=None, description=None,
                                  datacenter_id=None,
                                  network_address=None,
                                  subnet_mask=None):
        """
       Updates a private network

       :param name: Name of the private network
       :type name: ``str``

       :param description: Description of the private network
       :type description: ``str``

       :param datacenter_id: ID of the data center for the private network
       :type datacenter_id: ``str``

       :param network_address: Network address of the private network
       :type network_address: ``str``

       :param subnet_mask: Subnet mask of the private network
       :type subnet_mask: ``str``

       :return: Instance of private network
       :rtype: ``dict``
       """
        body = {}

        if name is not None:
            body['name'] = name
        if description is not None:
            body['description'] = description
        if datacenter_id is not None:
            body['datacenter_id'] = datacenter_id
        if network_address is not None:
            body['network_address'] = network_address
        if subnet_mask is not None:
            body['subnet_maks'] = subnet_mask

        response = self.connection.request(
            action='private_networks/%s',
            data=body,
            method='PUT'
        )

        return response.object

    def ex_list_private_network_servers(self, network_id):
        """
        Lists all private network servers

        :param network_id: Private network ID
        :type network_id: ``str``

        :return: List of private network servers
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='/private_networks/%s/servers' % network_id,
            method='GET'
        )
        return response.object

    def ex_add_private_network_server(self, network_id, server_ids):
        """
        Add servers to private network

        :param network_id: Private Network ID
        :type network_id: ``str``

        :param server_ids: List of server IDs
        :type server_ids: ``list`` of ``str``

        :return: List of attached servers
        :rtype: ``dict``

        """
        body = {
            'servers': server_ids

        }

        response = self.connection.request(
            action='/private_networks/%s/servers' % network_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_remove_server_from_private_network(self, network_id, server_id):
        """
        Removes a server from the private network

        :param network_id: Private Network ID
        :type network_id: ``str``

        :param server_id: Id of the server
        :type server_id: ``str``

        :return: Instance of the private network
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='/private_networks/%s/servers/%s' % (network_id, server_id),
            method='POST'
        )
        return response.object

    """
    Monitoring policy operations
    """

    def ex_list_monitoring_policies(self):
        """
        Lists all monitoring policies

        :return: List of monitoring policies
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='monitoring_policies',
            method='GET'
        )

        return response.object

    def ex_create_monitoring_policy(self, name, thresholds,
                                    ports,
                                    processes,
                                    description=None,
                                    email=None,
                                    agent=None,
                                    ):
        """
        Creates a monitoring policy

        :param name: Name for the monitoring policy
        :type name: ``str``

        :param thresholds: Thresholds for the monitoring policy
        :type thresholds: ``dict``

        :param ports: Monitoring policies for ports
        :type ports: ``list`` of ``dict``

        :param processes: Processes to be monitored
        :type processes: ``list`` of ``dict``

        :param description: Description for the monitoring policy
        :type description: ``str``

        :param email: Email for notifications
        :type email: ``str``

        :param agent: Indicates if agent application will be installed
        :type agent: ``boolean``

        :return: Newly created instance of monitofing policy
        :rtype: ``dict``
        """
        body = {
            'name': name,
            'thresholds': thresholds,
            'ports': ports,
            'processes': processes
        }

        if description is not None:
            body['description'] = description
        if email is not None:
            body['email'] = email
        if agent is not None:
            body['agent'] = agent

        response = self.connection.request(
            action='monitoring_policies',
            data=body,
            method='POST'
        )
        return response.object

    def ex_delete_monitoring_policy(self, policy_id):
        """
        Deletes a monitoring policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :return: Instance of the monitoring policy being deleted
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='monitoring_policies' % policy_id,
            method='DELETE'
        )

        return response.object

    def ex_update_monitoring_policy(self, policy_id,
                                    email,
                                    thresholds,
                                    name=None, description=None):
        """
        Updates monitoring policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param email: Email to send notifications to
        :type email: ``str``

        :param thresholds: Thresholds for the monitoring policy
        :type thresholds: ``dict``

        :param name: Name of the monitoring policy
        :type name: ``str``

        :param description: Description of the monitoring policy
        :type description: ``str``

        :return: Instance of the monitoring policy being deleted
        :rtype: ``dict``
        """

        body = {}

        if name is not None:
            body['name'] = name
        if description is not None:
            body['description'] = description
        if thresholds is not None:
            body['thresholds'] = thresholds
        if email is not None:
            body['email'] = email

        response = self.connection.request(
            action='monitoring_policies/%s' % policy_id,
            data=body,
            method='PUT'
        )

        return response.object

    def ex_get_monitoring_policy(self, policy_id):
        """
        Fetches a monitoring policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='monitoring_policies/%s' % policy_id,
            method='GET'
        )

        return response.object

    def ex_get_monitoring_policy_ports(self, policy_id):
        """
        Fetches monitoring policy ports

        :param policy_id: Id of the monitoring policy
        :type policy_id:

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/ports' % policy_id,
            method='GET'
        )

        return response.object

    def ex_get_monitoring_policy_port(self, policy_id, port_id):
        """
        Fetches monitoring policy port

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param port_id: Id of the port
        :type port_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/ports/%s' % (policy_id, port_id),
            method='GET'
        )

        return response.object

    def ex_remove_monitoring_policy_port(self, policy_id, port_id):
        """
        Removes monitoring policy port

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param port_id: Id of the port
        :type port_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/ports/%s' % (policy_id, port_id),
            method='DELETE'
        )

        return response.object

    def ex_add_monitoring_policy_ports(self, policy_id, ports):
        """
        Add monitoring policy ports

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param ports: List of ports
        :type ports: ``dict``
        [
           {
              'protocol':'TCP',
              'port':'80',
              'alert_if':'RESPONDING',
              'email_notification':true
           }
        ]

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        body = {'ports': ports}

        response = self.connection.request(
            action='monitoring_policies/%s/ports' % policy_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_get_monitoring_policy_processes(self, policy_id):
        """
        Fetches monitoring policy processes

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/processes' % policy_id,
            method='GET'
        )

        return response.object

    def ex_get_monitoring_policy_process(self, policy_id, process_id):
        """
        Fetches monitoring policy process

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param process_id: Id of the process
        :type process_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/processes/%s'
                   % (policy_id, process_id),
            method='GET'
        )

        return response.object

    def ex_remove_monitoring_policy_process(self, policy_id, process_id):
        """
        Removes monitoring policy process

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param process_id: Id of the process
        :type process_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/processes/%s'
                   % (policy_id, process_id),
            method='DELETE'
        )

        return response.object

    def ex_add_monitoring_policy_processes(self, policy_id, processes):
        """
        Add monitoring policy processes

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param processes: List of processes
        :type processes: ``list`` of ``dict``
        [
          {
            'process': 'taskmmgr',
            'alert_if': 'RUNNING',
            'email_notification': true
          }
        ]

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """

        body = {'processes': processes}

        response = self.connection.request(
            action='monitoring_policies/%s/processes' % policy_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_list_monitoring_policy_servers(self, policy_id):
        """
        List all servers that are being monitoried by the policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :return: List of servers being monitored
        :rtype: ``list`` of ``dict``
        """

        response = self.connection.request(
            action='monitoring_policies/%s/servers' % policy_id,
            method='GET'
        )

        return response.object

    def ex_add_servers_to_monitoring_policy(self, policy_id, servers):
        """
        Adds servers to monitoring policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param servers: List of server ID
        :type servers: ``list`` of ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """
        body = {
            'servers': servers
        }
        response = self.connection.request(
            action='monitoring_policies/%s/servers' % policy_id,
            data=body,
            method='POST'
        )

        return response.object

    def ex_remove_server_from_monitoring_policy(self, policy_id, server_id):
        """
        Removes a server from monitoring policy

        :param policy_id: Id of the monitoring policy
        :type policy_id: ``str``

        :param server_id: Id of the server
        :type server_id: ``str``

        :return: Instance of a monitoring policy
        :rtype: ``dict``
        """
        response = self.connection.request(
            action='monitoring_policies/%s/servers/%s'
                   % (policy_id, server_id),
            method='DELETE'
        )

        return response.object

    """
    Private Functions
    """

    def _to_images(self, object, image_type=None):
        if image_type is not None:
            images = [image for image in object if image['type'] == image_type]
        else:
            images = [image for image in object]

        return [self._to_image(image) for image in images]

    def _to_image(self, data):
        extra = {
            'os_family': data['os_family'],
            'os': data['os'],
            'os_version': data['os_version'],
            'os_architecture': data['os_architecture'],
            'os_image_type': data['os_image_type'],
            'min_hdd_size': data['min_hdd_size'],
            'available_datacenters': data['available_datacenters'],
            'licenses': data['licenses'],
            'version': data['version'],
            'categories': data['categories']
        }
        return NodeImage(id=data['id'], name=data['name'], driver=self,
                         extra=extra)

    def _to_node_size(self, data):
        return NodeSize(
            id=data['id'],
            name=data['name'],
            ram=data['hardware']['ram'],
            disk=data['hardware']['hdds'][0]['size'],
            bandwidth=None,
            price=None,
            driver=self.connection.driver,
            extra={
                'vcores': data['hardware']['vcore'],
                'cores_per_processor': data['hardware']['cores_per_processor']}

        )

    def _to_location(self, location):
        return NodeLocation(
            id=location['id'],
            name=location['country_code'],
            country=location['location'],
            driver=self.connection.driver
        )

    def _to_nodes(self, servers):
        return [self._to_node(
            server) for server in servers]

    def _to_node(self, server):
        extra = {}
        extra['datacenter'] = server['datacenter']

        if 'description' in server:
            extra['description'] = server['description']
        if 'status' in server:
            extra['status'] = server['status']
        if 'image' in server:
            extra['image'] = server['image']
        if 'hardware' in server:
            extra['hardware'] = server['hardware']
        if 'dvd' in server:
            extra['dvd'] = server['dvd']
        if 'snapshot' in server:
            extra['snapshot'] = server['snapshot']
        if 'ips' in server:
            extra['ips'] = server['ips']
        if 'alerts' in server:
            extra['alerts'] = server['alerts']
        if 'monitoring_policy' in server:
            extra['monitoring_policy'] = server['monitoring_policy']
        if 'private_networks' in server:
            extra['private_networks'] = server['private_networks']

        ips = []

        if server['ips'] is not None:
            for ip in server['ips']:
                ips.append(ip['ip'])
        state = self.NODE_STATE_MAP.get(
            server['status']['state'])

        return Node(
            id=server['id'],
            state=state,
            name=server['name'],
            driver=self.connection.driver,
            public_ips=ips,
            private_ips=None,
            extra=extra
        )

    def _wait_for_state(self, server_id, state, retries=50):
        for i in (0, retries):
            server = self.ex_get_server(server_id)

            if server.extra['status']['state'] == state:
                return
            sleep(5)

            if i == retries:
                raise Exception('Retries count reached')

    def _list_fixed_instances(self):
        response = self.connection.request(
            action='/servers/fixed_instance_sizes',
            method='GET'
        )

        return response.object
