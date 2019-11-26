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
"""ProfitBricks Compute driver
"""
import base64

import json
import copy
import time

from libcloud.utils.py3 import b
from libcloud.utils.py3 import urlencode
from libcloud.compute.providers import Provider
from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume, VolumeSnapshot
from libcloud.compute.base import NodeAuthPassword, NodeAuthSSHKey
from libcloud.compute.base import UuidMixin
from libcloud.compute.types import NodeState
from libcloud.common.types import LibcloudError, MalformedResponseError
from libcloud.common.exceptions import BaseHTTPError

from collections import defaultdict

__all__ = [
    'API_VERSION',
    'API_HOST',
    'ProfitBricksNodeDriver',
    'Datacenter',
    'ProfitBricksNetworkInterface',
    'ProfitBricksFirewallRule',
    'ProfitBricksLan',
    'ProfitBricksIPFailover',
    'ProfitBricksLoadBalancer',
    'ProfitBricksAvailabilityZone',
    'ProfitBricksIPBlock'
]

API_HOST = 'api.profitbricks.com'
API_VERSION = '/cloudapi/v4/'


class ProfitBricksResponse(JsonResponse):
    """
    ProfitBricks response parsing.
    """
    def parse_error(self):
        http_code = None
        fault_code = None
        message = None
        try:
            body = json.loads(self.body)
            if 'httpStatus' in body:
                http_code = body['httpStatus']
            else:
                http_code = 'unknown'

            if 'messages' in body:
                message = ', '.join(list(map(
                    lambda item: item['message'], body['messages'])))
                fault_code = ', '.join(list(map(
                    lambda item: item['errorCode'], body['messages'])))
            else:
                message = 'No messages returned.'
                fault_code = 'unknown'
        except Exception:
            raise MalformedResponseError('Failed to parse Json',
                                         body=self.body,
                                         driver=ProfitBricksNodeDriver)

        return LibcloudError(
            '''
                HTTP Code: %s,
                Fault Code(s): %s,
                Message(s): %s
            '''
            % (http_code, fault_code, message), driver=self)


class ProfitBricksConnection(ConnectionUserAndKey):
    """
    Represents a single connection to the ProfitBricks endpoint.
    """
    host = API_HOST
    api_prefix = API_VERSION
    responseCls = ProfitBricksResponse

    def add_default_headers(self, headers):
        headers['Authorization'] = 'Basic %s' % (base64.b64encode(
            b('%s:%s' % (self.user_id, self.key))).decode('utf-8'))

        return headers

    def encode_data(self, data):
        """
        If a string is passed in, just return it
        or else if a dict is passed in, encode it
        as a json string.
        """
        if type(data) is str:
            return data

        elif type(data) is dict:
            return json.dumps(data)

        else:
            return ''

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False, with_full_url=False):

        """
        Some requests will use the href attribute directly.
        If this is not the case, then we should formulate the
        url based on the action specified.
        If we are using a full url, we need to remove the
        host and protocol components.
        """
        if not with_full_url or with_full_url is False:
            action = self.api_prefix + action.lstrip('/')
        else:
            action = action.replace(
                'https://{host}'.format(host=self.host),
                ''
            )

        return super(ProfitBricksConnection, self).request(
            action=action,
            params=params,
            data=data,
            headers=headers,
            method=method,
            raw=raw
        )


class Datacenter(UuidMixin):
    """
    Class which stores information about ProfitBricks datacenter
    instances.

    :param      id: The datacenter ID.
    :type       id: ``str``

    :param      href: The datacenter href.
    :type       href: ``str``

    :param      name: The datacenter name.
    :type       name: ``str``

    :param      version: Datacenter version.
    :type       version: ``str``

    :param      driver: ProfitBricks Node Driver.
    :type       driver: :class:`ProfitBricksNodeDriver`

    :param      extra: Extra properties for the Datacenter.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific.
    """
    def __init__(self, id, href, name, version, driver, extra=None):
        self.id = str(id)
        self.href = href
        self.name = name
        self.version = version
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return ((
            '<Datacenter: id=%s, href=%s name=%s, version=%s, driver=%s> ...>')
            % (self.id, self.href, self.name, self.version,
                self.driver.name))


class ProfitBricksNetworkInterface(object):
    """
    Class which stores information about ProfitBricks network
    interfaces.

    :param      id: The network interface ID.
    :type       id: ``str``

    :param      name: The network interface name.
    :type       name: ``str``

    :param      href: The network interface href.
    :type       href: ``str``

    :param      state: The network interface name.
    :type       state: ``int``

    :param      extra: Extra properties for the network interface.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific.
    """
    def __init__(self, id, name, href, state, extra=None):
        self.id = id
        self.name = name
        self.href = href
        self.state = state
        self.extra = extra or {}

    def __repr__(self):
        return (('<ProfitBricksNetworkInterface: id=%s, name=%s, href=%s>')
                % (self.id, self.name, self.href))


class ProfitBricksFirewallRule(object):
    """
    Extension class which stores information about a ProfitBricks
    firewall rule.

    :param      id: The firewall rule ID.
    :type       id: ``str``

    :param      name: The firewall rule name.
    :type       name: ``str``

    :param      href: The firewall rule href.
    :type       href: ``str``

    :param      state: The current state of the firewall rule.
    :type       state: ``int``

    :param      extra: Extra properties for the firewall rule.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific.

    """

    def __init__(self, id, name, href, state, extra=None):
        self.id = id
        self.name = name
        self.href = href
        self.state = state
        self.extra = extra or {}

    def __repr__(self):
        return (('<ProfitBricksFirewallRule: id=%s, name=%s, href=%s>')
                % (self.id, self.name, self.href))


class ProfitBricksLan(object):
    """
    Extension class which stores information about a
    ProfitBricks LAN

    :param      id: The ID of the lan.
    :param      id: ``str``

    :param      name: The name of the lan.
    :type       name: ``str``

    :param      href: The lan href.
    :type       href: ``str``

    :param      is_public: If public, the lan faces the public internet.
    :type       is_public: ``bool``

    :param      state: The current state of the lan.
    :type       state: ``int``

    :param      extra: Extra properties for the lan.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific.

    """

    def __init__(self, id, name, href, is_public, state, driver, extra=None):
        self.id = id
        self.name = name
        self.href = href
        self.is_public = is_public
        self.state = state
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (('<ProfitBricksLan: id=%s, name=%s, href=%s>')
                % (self.id, self.name, self.href))


class ProfitBricksIPFailover(object):
    """
    Extension class which stores information about a
    ProfitBricks LAN's failover

    :param      ip: The IP address to fail over.
    :type       ip: ``str``

    :param      nic_uuid: The ID of the NIC to fail over.
    :param      nic_uuid: ``str``

    Note: This class is ProfitBricks specific.

    """

    def __init__(self, ip, nic_uuid):
        self.ip = ip
        self.nic_uuid = nic_uuid

    def __repr__(self):
        return (('<ProfitBricksIPFailover: ip=%s, nic_uuid=%s>')
                % (self.ip, self.nic_uuid))


class ProfitBricksLoadBalancer(object):
    """
    Extention class which stores information about a
    ProfitBricks load balancer

    :param      id: The ID of the load balancer.
    :param      id: ``str``

    :param      name: The name of the load balancer.
    :type       name: ``str``

    :param      href: The load balancer href.
    :type       href: ``str``

    :param      state: The current state of the load balancer.
    :type       state: ``int``

    :param      extra: Extra properties for the load balancer.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific

    """

    def __init__(self, id, name, href, state, driver, extra=None):
        self.id = id
        self.name = name
        self.href = href
        self.state = state
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (('ProfitBricksLoadbalancer: id=%s, name=%s, href=%s>')
                % (self.id, self.name, self.href))


class ProfitBricksAvailabilityZone(object):
    """
    Extension class which stores information about a ProfitBricks
    availability zone.

    :param      name: The availability zone name.
    :type       name: ``str``

    Note: This class is ProfitBricks specific.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return (('<ProfitBricksAvailabilityZone: name=%s>')
                % (self.name))


class ProfitBricksIPBlock(object):
    """
    Extension class which stores information about a ProfitBricks
    IP block.

    :param      id: The ID of the IP block.
    :param      id: ``str``

    :param      name: The name of the IP block.
    :type       name: ``str``

    :param      href: The IP block href.
    :type       href: ``str``

    :param      location: The location of the IP block.
    :type       location: ``str``

    :param      size: Number of IP addresses in the block.
    :type       size: ``int``

    :param      ips: A collection of IPs associated with the block.
    :type       ips: ``list``

    :param      state: The current state of the IP block.
    :type       state: ``int``

    :param      extra: Extra properties for the IP block.
    :type       extra: ``dict``

    Note: This class is ProfitBricks specific
    """

    def __init__(
        self, id, name, href, location,
        size, ips, state, driver,
        extra=None
    ):

        self.id = id
        self.name = name
        self.href = href
        self.location = location
        self.size = size
        self.ips = ips
        self.state = state
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (
            (
                '<ProfitBricksIPBlock: id=%s,'
                'name=%s, href=%s,location=%s, size=%s>'
            )
            % (self.id, self.name, self.href, self.location, self.size)
        )


class ProfitBricksNodeDriver(NodeDriver):
    """
    Base ProfitBricks node driver.
    """
    connectionCls = ProfitBricksConnection
    name = 'ProfitBricks'
    website = 'http://www.profitbricks.com'
    type = Provider.PROFIT_BRICKS

    PROVISIONING_STATE = {
        'AVAILABLE': NodeState.RUNNING,
        'BUSY': NodeState.PENDING,
        'INACTIVE': NodeState.PENDING
    }

    NODE_STATE_MAP = {
        'NOSTATE': NodeState.UNKNOWN,
        'RUNNING': NodeState.RUNNING,
        'BLOCKED': NodeState.STOPPED,
        'PAUSE': NodeState.PAUSED,
        'SHUTDOWN': NodeState.STOPPING,
        'SHUTOFF': NodeState.STOPPED,
        'CRASHED': NodeState.ERROR,
        'AVAILABLE': NodeState.RUNNING,
        'BUSY': NodeState.PENDING
    }

    AVAILABILITY_ZONE = {
        '1': {'name': 'AUTO'},
        '2': {'name': 'ZONE_1'},
        '3': {'name': 'ZONE_2'},
    }

    """
    ProfitBricks is unique in that they allow the user to define all aspects
    of the instance size, i.e. disk size, core size, and memory size.

    These are instance types that match up with what other providers support.

    You can configure disk size, core size, and memory size using the ``ex_``
    parameters on the create_node method.
    """

    PROFIT_BRICKS_GENERIC_SIZES = {
        '1': {
            'id': '1',
            'name': 'Micro',
            'ram': 1024,
            'disk': 50,
            'cores': 1
        },
        '2': {
            'id': '2',
            'name': 'Small Instance',
            'ram': 2048,
            'disk': 50,
            'cores': 1
        },
        '3': {
            'id': '3',
            'name': 'Medium Instance',
            'ram': 4096,
            'disk': 50,
            'cores': 2
        },
        '4': {
            'id': '4',
            'name': 'Large Instance',
            'ram': 7168,
            'disk': 50,
            'cores': 4
        },
        '5': {
            'id': '5',
            'name': 'ExtraLarge Instance',
            'ram': 14336,
            'disk': 50,
            'cores': 8
        },
        '6': {
            'id': '6',
            'name': 'Memory Intensive Instance Medium',
            'ram': 28672,
            'disk': 50,
            'cores': 4
        },
        '7': {
            'id': '7',
            'name': 'Memory Intensive Instance Large',
            'ram': 57344,
            'disk': 50,
            'cores': 8
        }
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

        for key, values in self.PROFIT_BRICKS_GENERIC_SIZES.items():
            node_size = self._to_node_size(values)
            sizes.append(node_size)

        return sizes

    def list_images(self, image_type=None, is_public=True):
        """
        List all images with an optional filter.

        :param  image_type: The image type (HDD, CDROM)
        :type   image_type: ``str``

        :param  is_public: Image is public
        :type   is_public: ``bool``

        :return: ``list`` of :class:`NodeImage`
        :rtype: ``list``
        """
        response = self.connection.request(
            action='images',
            params={'depth': 1},
            method='GET'
        )

        return self._to_images(response.object, image_type, is_public)

    def list_locations(self):
        """
        List all locations.

        :return: ``list`` of :class:`NodeLocation`
        :rtype: ``list``
        """
        return self._to_locations(self.connection.request(
            action='locations',
            params={'depth': 1},
            method='GET').object
        )

    """
    Node functions
    """

    def list_nodes(self):
        """
        List all nodes.

        :return: ``list`` of :class:`Node`
        :rtype: ``list``
        """
        datacenters = self.ex_list_datacenters()
        nodes = list()

        for datacenter in datacenters:
            servers_href = datacenter.extra['entities']['servers']['href']
            response = self.connection.request(
                action=servers_href,
                params={'depth': 3},
                method='GET',
                with_full_url=True
            )

            mapped_nodes = self._to_nodes(response.object)
            nodes += mapped_nodes

        return nodes

    def reboot_node(self, node):
        """
        Reboots the node.

        :rtype: ``bool``
        """
        action = node.extra['href'] + '/reboot'

        self.connection.request(
            action=action,
            method='POST',
            with_full_url=True
        )

        return True

    def create_node(
        self, name, image=None, size=None, location=None,
        ex_cpu_family=None, volume=None, ex_datacenter=None,
        ex_network_interface=True, ex_internet_access=True,
        ex_exposed_public_ports=[], ex_exposed_private_ports=[22],
        ex_availability_zone=None, ex_ram=None, ex_cores=None,
        ex_disk=None, ex_password=None, ex_ssh_keys=None,
        ex_bus_type=None, ex_disk_type=None, **kwargs
    ):
        """
        Creates a node.

        image is optional as long as you pass ram, cores, and disk
        to the method. ProfitBricks allows you to adjust compute
        resources at a much more granular level.

        :param  name: The name for the new node.
        :param  type: ``str``

        :param  image: The image to create the node with.
        :type   image: :class:`NodeImage`

        :param  size: Standard configured size offered by
            ProfitBricks - containing configuration for the
            number of cpu cores, amount of ram and disk size.
        :param  size: :class:`NodeSize`

        :param  location: The location of the new data center
            if one is not supplied.
        :type   location: :class:`NodeLocation`

        :param  ex_cpu_family: The CPU family to use (AMD_OPTERON, INTEL_XEON)
        :type   ex_cpu_family: ``str``

        :param  volume: If the volume already exists then pass this in.
        :type   volume: :class:`StorageVolume`

        :param  ex_datacenter: If you've already created the DC then pass
                           it in.
        :type   ex_datacenter: :class:`Datacenter`

        :param  ex_network_interface: Create with a network interface.
        :type   ex_network_interface: : ``bool``

        :param  ex_internet_access: Configure public Internet access.
        :type   ex_internet_access: : ``bool``

        :param  ex_exposed_public_ports: Ports to be opened
                                        for the public nic.
        :param  ex_exposed_public_ports: ``list`` of ``int``

        :param  ex_exposed_private_ports: Ports to be opened
                                        for the private nic.
        :param  ex_exposed_private_ports: ``list`` of ``int``

        :param  ex_availability_zone: The availability zone.
        :type   ex_availability_zone: class: `ProfitBricksAvailabilityZone`

        :param  ex_ram: The amount of ram required.
        :type   ex_ram: : ``int``

        :param  ex_cores: The number of cores required.
        :type   ex_cores: ``int``

        :param  ex_disk: The amount of disk required.
        :type   ex_disk: ``int``

        :param  ex_password: The password for the volume.
        :type   ex_password: :class:`NodeAuthPassword` or ``str``

        :param  ex_ssh_keys: Optional SSH keys for the volume.
        :type   ex_ssh_keys: ``list`` of :class:`NodeAuthSSHKey` or
                             ``list`` of ``str``

        :param  ex_bus_type: Volume bus type (VIRTIO, IDE).
        :type   ex_bus_type: ``str``

        :param  ex_disk_type: Volume disk type (SSD, HDD).
        :type   ex_disk_type: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """

        """
        If we have a volume we can determine the DC
        that it belongs to and set accordingly.
        """
        if volume is not None:
            dc_url_pruned = volume.extra['href'].split('/')[:-2]
            dc_url = '/'.join(item for item in dc_url_pruned)
            ex_datacenter = self.ex_describe_datacenter(
                ex_href=dc_url
            )

        if not ex_datacenter:
            '''
            Determine location for new DC by
            getting the location of the image.
            '''
            if not location:
                if image is not None:
                    location = self.ex_describe_location(
                        ex_location_id=image.extra['location']
                    )

            '''
            Creating a Datacenter for the node
            since one was not provided.
            '''
            new_datacenter = self._create_new_datacenter_for_node(
                name=name,
                location=location
            )

            '''
            Then wait for the operation to finish,
            assigning the full data center on completion.
            '''
            ex_datacenter = self._wait_for_datacenter_state(
                datacenter=new_datacenter
            )

        if not size:
            if not ex_ram:
                raise ValueError('You need to either pass a '
                                 'NodeSize or specify ex_ram as '
                                 'an extra parameter.')
            if not ex_cores:
                raise ValueError('You need to either pass a '
                                 'NodeSize or specify ex_cores as '
                                 'an extra parameter.')

        '''
        If passing in an image we need
        to enforce a password or ssh keys.
        '''
        if not volume and image is not None:
            if ex_password is None and ex_ssh_keys is None:
                raise ValueError(
                    (
                        'When creating a server without a '
                        'volume, you need to specify either an '
                        'array of SSH keys or a volume password.'
                    )
                )

            if not size:
                if not ex_disk:
                    raise ValueError('You need to either pass a '
                                     'StorageVolume, a NodeSize, or specify '
                                     'ex_disk as an extra parameter.')

        '''
        You can override the suggested sizes by passing in unique
        values for ram, cores, and disk allowing you to size it
        for your specific use.
        '''

        if image is not None:
            if not ex_disk:
                ex_disk = size.disk

        if not ex_disk_type:
            ex_disk_type = 'HDD'

        if not ex_bus_type:
            ex_bus_type = 'VIRTIO'

        if not ex_ram:
            ex_ram = size.ram

        if not ex_cores:
            ex_cores = size.extra['cores']

        action = ex_datacenter.href + '/servers'
        body = {
            'properties': {
                'name': name,
                'ram': ex_ram,
                'cores': ex_cores
            },
            'entities': {
                'volumes': {
                    'items': []
                }
            }
        }

        '''
        If we are using a pre-existing storage volume.
        '''
        if volume is not None:
            body['entities']['volumes']['items'].append({'id': volume.id})
        elif image is not None:
            new_volume = {
                'properties': {
                    'size': ex_disk,
                    'name': name + ' - volume',
                    'image': image.id,
                    'type': ex_disk_type,
                    'bus': ex_bus_type
                }
            }

            if ex_password is not None:
                if isinstance(ex_password, NodeAuthPassword):
                    new_volume['properties']['imagePassword'] = \
                        ex_password.password
                else:
                    new_volume['properties']['imagePassword'] = ex_password

            if ex_ssh_keys is not None:
                if isinstance(ex_ssh_keys[0], NodeAuthSSHKey):
                    new_volume['properties']['sshKeys'] = \
                        [ssh_key.pubkey for ssh_key in ex_ssh_keys]
                else:
                    new_volume['properties']['sshKeys'] = ex_ssh_keys

            body['entities']['volumes']['items'].append(new_volume)

        if ex_network_interface is True:
            body['entities']['nics'] = {}
            body['entities']['nics']['items'] = list()

            '''
            Get the LANs for the data center this node
            will be provisioned at.
            '''
            dc_lans = self.ex_list_lans(
                datacenter=ex_datacenter
            )

            private_lans = [lan for lan in dc_lans if lan.is_public is False]
            private_lan = None

            if private_lans:
                private_lan = private_lans[0]

            if private_lan is not None:
                private_nic = {
                    'properties': {
                        'name': name + ' - private nic',
                        'lan': private_lan.id,
                    },
                    'entities': {
                        'firewallrules': {
                            'items': []
                        }
                    }
                }

                for port in ex_exposed_private_ports:
                    private_nic['entities']['firewallrules']['items'].append(
                        {
                            'properties': {
                                'name': (
                                    '{name} - firewall rule:{port}'.format(
                                        name=name, port=port
                                    )
                                ),
                                'protocol': 'TCP',
                                'portRangeStart': port,
                                'portRangeEnd': port
                            }
                        }
                    )

                body['entities']['nics']['items'].append(private_nic)

            if ex_internet_access is not None and ex_internet_access is True:
                public_lans = [lan for lan in dc_lans if lan.is_public]
                public_lan = None

                if public_lans:
                    public_lan = public_lans[0]

                if public_lan is not None:
                    pub_nic = {
                        'properties': {
                            'name': name + ' - public nic',
                            'lan': public_lan.id,
                        },
                        'entities': {
                            'firewallrules': {
                                'items': []
                            }
                        }
                    }

                    for port in ex_exposed_public_ports:
                        pub_nic['entities']['firewallrules']['items'].append(
                            {
                                'properties': {
                                    'name': (
                                        '{name} - firewall rule:{port}'.format(
                                            name=name, port=port
                                        )
                                    ),
                                    'protocol': 'TCP',
                                    'portRangeStart': port,
                                    'portRangeEnd': port
                                }
                            }
                        )

                    body['entities']['nics']['items'].append(pub_nic)

        if ex_cpu_family is not None:
            body['properties']['cpuFamily'] = ex_cpu_family

        if ex_availability_zone is not None:
            body['properties']['availabilityZone'] = ex_availability_zone.name

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_node(response.object, response.headers)

    def destroy_node(self, node, ex_remove_attached_disks=False):
        """
        Destroys a node.

        :param node: The node you wish to destroy.
        :type volume: :class:`Node`

        :param ex_remove_attached_disks: True to destroy all attached volumes.
        :type ex_remove_attached_disks: : ``bool``

        :rtype:     : ``bool``
        """

        if ex_remove_attached_disks is True:
            for volume in self.ex_list_attached_volumes(node):
                self.destroy_volume(volume)

        action = node.extra['href']

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    def start_node(self, node):
        """
        Starts a node.

        :param  node: The node you wish to start.
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        action = node.extra['href'] + '/start'

        self.connection.request(
            action=action,
            method='POST',
            with_full_url=True
        )
        return True

    def stop_node(self, node):
        """
        Stops a node.

        This also deallocates the public IP space.

        :param  node: The node you wish to halt.
        :type   node: :class:`Node`

        :rtype:     : ``bool``
        """
        action = node.extra['href'] + '/stop'

        self.connection.request(
            action=action,
            method='POST',
            with_full_url=True
        )

        return True

    """
    Volume Functions
    """

    def list_volumes(self):
        """
        List all volumes attached to a data center.

        :return: ``list`` of :class:`StorageVolume`
        :rtype: ``list``
        """
        datacenters = self.ex_list_datacenters()
        volumes = list()

        for datacenter in datacenters:
            volumes_href = datacenter.extra['entities']['volumes']['href']

            response = self.connection.request(
                action=volumes_href,
                params={'depth': 3},
                method='GET',
                with_full_url=True
            )

            mapped_volumes = self._to_volumes(response.object)
            volumes += mapped_volumes

        return volumes

    def attach_volume(self, node, volume):
        """
        Attaches a volume.

        :param  node: The node to which you're attaching the volume.
        :type   node: :class:`Node`

        :param  volume: The volume you're attaching.
        :type   volume: :class:`StorageVolume`

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """
        action = node.extra['href'] + '/volumes'
        body = {
            'id': volume.id
        }

        data = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_volume(data.object, data.headers)

    def create_volume(
        self,
        size,
        ex_datacenter,
        name=None,
        image=None,
        ex_image_alias=None,
        ex_type=None,
        ex_bus_type=None,
        ex_ssh_keys=None,
        ex_password=None,
        ex_availability_zone=None
    ):
        """
        Creates a volume.

        :param  size: The size of the volume in GB.
        :type   size: ``int``

        :param  ex_datacenter: The datacenter you're placing
                              the storage in. (req)
        :type   ex_datacenter: :class:`Datacenter`

        :param  name: The name to be given to the volume.
        :param  name: ``str``

        :param  image: The OS image for the volume.
        :type   image: :class:`NodeImage`

        :param  ex_image_alias: An alias to a ProfitBricks public image.
                                Use instead of 'image'.
        :type   ex_image_alias: ``str``

        :param  ex_type: The type to be given to the volume (SSD or HDD).
        :param  ex_type: ``str``

        :param  ex_bus_type: Bus type. Either IDE or VIRTIO (default).
        :type   ex_bus_type: ``str``

        :param  ex_ssh_keys: Optional SSH keys.
        :type   ex_ssh_keys: ``list`` of :class:`NodeAuthSSHKey` or
                             ``list`` of ``str``

        :param  ex_password: Optional password for root.
        :type   ex_password: :class:`NodeAuthPassword` or ``str``

        :param  ex_availability_zone: Volume Availability Zone.
        :type   ex_availability_zone: ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """

        if not ex_datacenter:
            raise ValueError('You need to specify a data center'
                             ' to attach this volume to.')

        if image is not None:
            if image.extra['image_type'] != 'HDD':
                raise ValueError('Invalid type of {image_type} specified for '
                                 '{image_name}, which needs to be of type HDD'
                                 .format(image_type=image.extra['image_type'],
                                         image_name=image.name))

            if ex_datacenter.extra['location'] != image.extra['location']:
                raise ValueError(
                    'The image {image_name} '
                    '(location: {image_location}) you specified '
                    'is not available at the data center '
                    '{datacenter_name} '
                    '(location: {datacenter_location}).'
                    .format(
                        image_name=image.extra['name'],
                        datacenter_name=ex_datacenter.extra['name'],
                        image_location=image.extra['location'],
                        datacenter_location=ex_datacenter.extra['location']
                    )
                )
        else:
            if not ex_image_alias:
                raise ValueError('You need to specify an image or image alias'
                                 ' to create this volume from.')

        action = ex_datacenter.href + '/volumes'
        body = {
            'properties': {
                'size': size
            }
        }

        if image is not None:
            body['properties']['image'] = image.id
        else:
            body['properties']['imageAlias'] = ex_image_alias
        if name is not None:
            body['properties']['name'] = name
        if ex_type is not None:
            body['properties']['type'] = ex_type
        if ex_bus_type is not None:
            body['properties']['bus'] = ex_bus_type
        if ex_ssh_keys is not None:
            if isinstance(ex_ssh_keys[0], NodeAuthSSHKey):
                body['properties']['sshKeys'] = \
                    [ssh_key.pubkey for ssh_key in ex_ssh_keys]
            else:
                body['properties']['sshKeys'] = ex_ssh_keys
        if ex_password is not None:
            if isinstance(ex_password, NodeAuthPassword):
                body['properties']['imagePassword'] = ex_password.password
            else:
                body['properties']['imagePassword'] = ex_password
        if ex_availability_zone is not None:
            body['properties']['availabilityZone'] = ex_availability_zone

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_volume(response.object, response.headers)

    def detach_volume(self, node, volume):
        """
        Detaches a volume.

        :param  node: The node to which you're detaching the volume.
        :type   node: :class:`Node`

        :param volume: The volume you're detaching.
        :type volume: :class:`StorageVolume`

        :rtype:     :``bool``
        """

        action = node.extra['href'] + '/volumes/{volume_id}'.format(
            volume_id=volume.id
        )

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    def destroy_volume(self, volume):
        """
        Destroys a volume.

        :param volume: The volume you're destroying.
        :type volume: :class:`StorageVolume`

        :rtype:     : ``bool``
        """
        action = volume.extra['href']

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    Volume snapshot functions
    """

    def list_snapshots(self):
        """
        Fetches as a list of all snapshots

        :return:    ``list`` of class ``VolumeSnapshot``
        :rtype:     `list`
        """

        response = self.connection.request(
            action='snapshots',
            params={'depth': 3},
            method='GET'
        )

        return self._to_snapshots(response.object)

    def create_volume_snapshot(self, volume):
        """
        Creates a snapshot for a volume

        :param  volume: The volume you're creating a snapshot for.
        :type   volume: :class:`StorageVolume`

        :return:    Instance of class ``VolumeSnapshot``
        :rtype:     :class:`VolumeSnapshot`
        """

        action = volume.extra['href'] + '/create-snapshot'

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            method='POST',
            with_full_url=True
        )

        return self._to_snapshot(response.object, response.headers)

    def destroy_volume_snapshot(self, snapshot):
        """
        Delete a snapshot

        :param  snapshot: The snapshot you wish to delete.
        :type:  snapshot: :class:`VolumeSnapshot`

        :rtype  ``bool``
        """

        action = snapshot.extra['href']

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    Extension Functions
    """

    """
    Server Extension Functions
    """

    def ex_start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.start_node(node=node)

    def ex_stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.stop_node(node=node)

    def ex_list_availability_zones(self):
        """
        Returns a list of availability zones.

        :return: ``list`` of :class:`ProfitBricksAvailabilityZone`
        :rtype: ``list``
        """

        availability_zones = []

        for key, values in self.AVAILABILITY_ZONE.items():
            name = copy.deepcopy(values)["name"]

            availability_zone = ProfitBricksAvailabilityZone(
                name=name
            )
            availability_zones.append(availability_zone)

        return availability_zones

    def ex_list_attached_volumes(self, node):
        """
        Returns a list of attached volumes for a server

        :param  node: The node with the attached volumes.
        :type   node: :class:`Node`

        :return:    ``list`` of :class:`StorageVolume`
        :rtype:     ``list``
        """
        action = node.extra['entities']['volumes']['href']
        response = self.connection.request(
            action=action,
            params={'depth': 3},
            method='GET',
            with_full_url=True
        )

        return self._to_volumes(response.object)

    def ex_describe_node(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_node_id=None
    ):
        """
        Fetches a node directly by href or
        by a combination of the datacenter
        ID and the server ID.

        :param  ex_href: The href (url) of the node you wish to describe.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID for the data center.
        :type   ex_datacenter_id: ``str``

        :param  ex_node_id: The ID for the node (server).
        :type   ex_node_id: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class:`Node`
        """

        use_full_url = True

        if ex_href is None:
            if ex_datacenter_id is None or ex_node_id is None:
                raise ValueError(
                    'IDs for the data center and node are required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}/'
                    'servers/{server_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    server_id=ex_node_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            params={'depth': 3},
            with_full_url=use_full_url
        )

        return self._to_node(response.object)

    def ex_update_node(self, node, name=None, cores=None,
                       ram=None, availability_zone=None,
                       ex_licence_type=None, ex_boot_volume=None,
                       ex_boot_cdrom=None, ex_cpu_family=None):
        """
        Updates a node.

        :param  node: The node you wish to update.
        :type   node: :class:`Node`

        :param  name: The new name for the node.
        :type   name: ``str``

        :param  cores: The number of CPUs the node should have.
        :type   cores: : ``int``

        :param  ram: The amount of ram the node should have.
        :type   ram: : ``int``

        :param  availability_zone: Update the availability zone.
        :type   availability_zone: :class:`ProfitBricksAvailabilityZone`

        :param  ex_licence_type: Licence type (WINDOWS, WINDOWS2016, LINUX,
                                OTHER, UNKNOWN).
        :type   ex_licence_type: ``str``

        :param  ex_boot_volume: Setting the new boot (HDD) volume.
        :type   ex_boot_volume: :class:`StorageVolume`

        :param  ex_boot_cdrom: Setting the new boot (CDROM) volume.
        :type   ex_boot_cdrom: :class:`StorageVolume`

        :param  ex_cpu_family: CPU family (INTEL_XEON, AMD_OPTERON).
        :type   ex_cpu_family: ``str``

        :return:    Instance of class ``Node``
        :rtype:     :class: `Node`
        """
        action = node.extra['href']
        body = {}

        if name is not None:
            body['name'] = name

        if cores is not None:
            body['cores'] = cores

        if ram is not None:
            body['ram'] = ram

        if availability_zone is not None:
            body['availabilityZone'] = availability_zone.name

        if ex_licence_type is not None:
            body['licencetype'] = ex_licence_type

        if ex_boot_volume is not None:
            body['bootVolume'] = ex_boot_volume.id

        if ex_boot_cdrom is not None:
            body['bootCdrom'] = ex_boot_cdrom.id

        if ex_cpu_family is not None:
            body['allowReboot'] = True
            body['cpuFamily'] = ex_cpu_family

        response = self.connection.request(
            action=action,
            data=body,
            headers={
                'Content-Type':
                'application/json'
            },
            method='PATCH',
            with_full_url=True
        )

        return self._to_node(response.object, response.headers)

    """
    Data center Extension Functions
    """

    def ex_create_datacenter(
        self,
        name,
        location,
        description=None
    ):
        """
        Creates a datacenter.

        ProfitBricks has a concept of datacenters.
        These represent buckets into which you
        can place various compute resources.

        :param  name: The datacenter name.
        :type   name: : ``str``

        :param  location: instance of class ``NodeLocation``.
        :type   location: : ``NodeLocation``

        :param  description: The datacenter description.
        :type   description: : ``str``

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """
        body = {
            'properties': {
                'name': name,
                'location': location.id
            }
        }

        if description is not None:
            body['properties']['description'] = description

        body['entities'] = defaultdict(dict)
        body['entities']['lans']['items'] = [
            {
                'properties': {
                    'name': name + ' - public lan',
                    'public': True
                }
            },
            {
                'properties': {
                    'name': name + ' - private lan',
                    'public': False
                }
            }
        ]

        response = self.connection.request(
            action='datacenters',
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST'
        )

        return self._to_datacenter(response.object, response.headers)

    def ex_destroy_datacenter(self, datacenter):
        """
        Destroys a datacenter.

        :param datacenter: The DC you're destroying.
        :type datacenter: :class:`Datacenter`

        :rtype:     : ``bool``
        """
        action = datacenter.href

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    def ex_describe_datacenter(self, ex_href=None, ex_datacenter_id=None):
        """
        Fetches the details for a data center.

        :param  ex_href: The href for the data center
                        you are describing.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID for the data center
                                you are describing.
        :type   ex_datacenter_id: ``str``

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """

        use_full_url = True

        if ex_href is None:
            if ex_datacenter_id is None:
                raise ValueError(
                    'The data center ID is required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}'
                ).format(
                    datacenter_id=ex_datacenter_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            params={'depth': 3},
            with_full_url=use_full_url
        )

        return self._to_datacenter(response.object)

    def ex_list_datacenters(self):
        """
        Lists all datacenters.

        :return: ``list`` of :class:`DataCenter`
        :rtype: ``list``
        """
        response = self.connection.request(
            action='datacenters',
            params={'depth': 2},
            method='GET'
        )

        return self._to_datacenters(response.object)

    def ex_rename_datacenter(self, datacenter, name):
        """
        Update a datacenter.

        :param  datacenter: The DC you are renaming.
        :type   datacenter: :class:`Datacenter`

        :param  name: The DC name.
        :type   name: : ``str``

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """
        action = datacenter.href
        body = {
            'name': name
        }

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_datacenter(response.object, response.headers)

    """
    Image Extension Functions
    """

    def ex_describe_image(self, ex_href=None, ex_image_id=None):
        """
        Describe a ProfitBricks image

        :param      ex_href: The href for the image you are describing
        :type       ex_href: ``str``

        :param      ex_image_id: The ID for the image you are describing
        :type       ex_image_id: ``str``

        :return:    Instance of class ``Image``
        :rtype:     :class:`Image`
        """

        use_full_url = True

        if ex_href is None:
            if ex_image_id is None:
                raise ValueError(
                    'The image ID is required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'images/{image_id}'
                ).format(
                    image_id=ex_image_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_image(response.object)

    def ex_delete_image(self, image):
        """
        Delete a private image

        :param  image: The private image you are deleting.
        :type   image: :class:`NodeImage`

        :rtype:     : ``bool``
        """

        self.connection.request(
            action=image.extra['href'],
            method='DELETE',
            with_full_url=True
        )

        return True

    def ex_update_image(
        self, image, name=None, description=None,
        licence_type=None, cpu_hot_plug=None,
        cpu_hot_unplug=None, ram_hot_plug=None,
        ram_hot_unplug=None, nic_hot_plug=None,
        nic_hot_unplug=None, disc_virtio_hot_plug=None,
        disc_virtio_hot_unplug=None, disc_scsi_hot_plug=None,
        disc_scsi_hot_unplug=None
    ):
        """
        Update a private image

        :param  image: The private image you are deleting.
        :type   image: :class:`NodeImage`

        :return:    Instance of class ``Image``
        :rtype:     :class:`Image`
        """
        action = image.extra['href']
        body = {}

        if name is not None:
            body['name'] = name

        if description is not None:
            body['description'] = description

        if licence_type is not None:
            body['licenceType'] = licence_type

        if cpu_hot_plug is not None:
            body['cpuHotPlug'] = cpu_hot_plug

        if cpu_hot_unplug is not None:
            body['cpuHotUnplug'] = cpu_hot_unplug

        if ram_hot_plug is not None:
            body['ramHotPlug'] = ram_hot_plug

        if ram_hot_unplug is not None:
            body['ramHotUnplug'] = ram_hot_unplug

        if nic_hot_plug is not None:
            body['nicHotPlug'] = nic_hot_plug

        if nic_hot_unplug is not None:
            body['nicHotUnplug'] = nic_hot_unplug

        if disc_virtio_hot_plug is not None:
            body['discVirtioHotPlug'] = disc_virtio_hot_plug

        if disc_virtio_hot_unplug is not None:
            body['discVirtioHotUnplug'] = disc_virtio_hot_unplug

        if disc_scsi_hot_plug is not None:
            body['discScsiHotPlug'] = disc_scsi_hot_plug

        if disc_scsi_hot_unplug is not None:
            body['discScsiHotUnplug'] = disc_scsi_hot_unplug

        response = self.connection.request(
            action=action,
            headers={
                'Content-type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_image(response.object, response.headers)

    """
    Location Extension Functions
    """

    def ex_describe_location(self, ex_href=None, ex_location_id=None):
        """
        Fetch details for a ProfitBricks location.

        :param      ex_href: The href for the location
                            you are describing.
        :type       ex_href: ``str``

        :param      ex_location_id: The id for the location you are
                        describing ('de/fra', 'de/fkb', 'us/las', 'us/ewr')
        :type       ex_location_id: ``str``

        :return:    Instance of class ``NodeLocation``
        :rtype:     :class:`NodeLocation`
        """

        use_full_url = True

        if ex_href is None:
            if ex_location_id is None:
                raise ValueError(
                    'The location ID is required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'locations/{location_id}'
                ).format(
                    location_id=ex_location_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_location(response.object)

    """
    Network Interface Extension Functions
    """

    def ex_list_network_interfaces(self):
        """
        Fetch a list of all network interfaces from all data centers.

        :return:    ``list`` of class ``ProfitBricksNetworkInterface``
        :rtype:     `list`
        """
        nodes = self.list_nodes()
        nics = list()

        for node in nodes:
            action = node.extra['entities']['nics']['href']
            nics += self._to_interfaces(
                self.connection.request(
                    action=action,
                    params={'depth': 1},
                    method='GET',
                    with_full_url=True
                ).object)

        return nics

    def ex_describe_network_interface(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_server_id=None,
        ex_nic_id=None
    ):
        """
        Fetch information on a network interface.

        :param  ex_href: The href of the NIC you wish to describe.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID of parent data center
                            of the NIC you wish to describe.
        :type   ex_datacenter_id: ``str``

        :param  ex_server_id: The server the NIC is connected to.
        :type   ex_server_id: ``str``

        :param  ex_nic_id: The ID of the NIC
        :type   ex_nic_id: ``str``

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """

        use_full_url = True

        if ex_href is None:
            if (
                ex_datacenter_id is None or
                ex_server_id is None or
                ex_nic_id is None
            ):
                raise ValueError(
                    (
                        'IDs are required for the data center',
                        'server and network interface.'
                    )
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}'
                    '/servers/{server_id}'
                    '/nics/{nic_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    server_id=ex_server_id,
                    nic_id=ex_nic_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_interface(response.object)

    def ex_create_network_interface(self, node,
                                    lan_id=None, ips=None, nic_name=None,
                                    dhcp_active=True):
        """
        Creates a network interface.

        :param lan_id: The ID for the LAN.
        :type lan_id: : ``int``

        :param ips: The IP addresses for the NIC.
        :type ips: ``list``

        :param nic_name: The name of the NIC, e.g. PUBLIC.
        :type nic_name: ``str``

        :param dhcp_active: Set to false to disable.
        :type dhcp_active: ``bool``

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """

        if lan_id is not None:
            lan_id = str(lan_id)

        else:
            lan_id = str(1)

        action = node.extra['href'] + '/nics'
        body = {
            'properties': {
                'lan': lan_id,
                'dhcp': dhcp_active
            }
        }

        if ips is not None:
            body['properties']['ips'] = ips

        if nic_name is not None:
            body['properties']['name'] = nic_name

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_interface(response.object, response.headers)

    def ex_update_network_interface(self, network_interface, name=None,
                                    lan_id=None, ips=None,
                                    dhcp_active=None):
        """
        Updates a network interface.

        :param  network_interface: The network interface being updated.
        :type   network_interface: :class:`ProfitBricksNetworkInterface`

        :param  name: The name of the NIC, e.g. PUBLIC.
        :type   name: ``str``

        :param  lan_id: The ID for the LAN.
        :type   lan_id: : ``int``

        :param  ips: The IP addresses for the NIC as a list.
        :type   ips: ``list``

        :param  dhcp_active: Set to false to disable.
        :type   dhcp_active: ``bool``

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """

        if lan_id:
            lan_id = str(lan_id)

        action = network_interface.href
        body = {}

        if name is not None:
            body['name'] = name

        if lan_id is not None:
            body['lan'] = str(lan_id)

        if ips is not None:
            body['ips'] = ips

        if dhcp_active is not None:
            body['dhcp'] = dhcp_active

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_interface(response.object, response.headers)

    def ex_destroy_network_interface(self, network_interface):
        """
        Destroy a network interface.

        :param network_interface: The NIC you wish to describe.
        :type network_interface: :class:`ProfitBricksNetworkInterface`

        :rtype:     : ``bool``
        """

        action = network_interface.href

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    def ex_set_inet_access(self, network_interface, internet_access=True):
        """
        Add/remove public internet access to an interface.

        :param network_interface: The NIC you wish to update.
        :type network_interface: :class:`ProfitBricksNetworkInterface`

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """

        action = network_interface.href
        body = {
            'nat': internet_access
        }

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_interface(response.object, response.headers)

    """
    Firewall Rule Extension Functions
    """

    def ex_list_firewall_rules(self, network_interface):
        """
        Fetch firewall rules for a network interface.

        :param network_interface: The network interface.
        :type network_interface: :class:`ProfitBricksNetworkInterface`

        :return:    ``list`` of class ``ProfitBricksFirewallRule``
        :rtype:     `list`
        """
        action = network_interface.href + '/firewallrules'
        response = self.connection.request(
            action=action,
            method='GET',
            params={'depth': 3},
            with_full_url=True
        )

        return self._to_firewall_rules(response.object)

    def ex_describe_firewall_rule(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_server_id=None,
        ex_nic_id=None,
        ex_firewall_rule_id=None
    ):
        """
        Fetch data for a firewall rule.

        :param href: The href of the firewall rule you wish to describe.
        :type href: ``str``

        :param  ex_datacenter_id: The ID of parent data center
                            of the NIC you wish to describe.
        :type   ex_datacenter_id: ``str``

        :param  ex_server_id: The server the NIC is connected to.
        :type   ex_server_id: ``str``

        :param  ex_nic_id: The ID of the NIC.
        :type   ex_nic_id: ``str``

        :param  ex_firewall_rule_id: The ID of the firewall rule.
        :type   ex_firewall_rule_id: ``str``

        :return:    Instance class ``ProfitBricksFirewallRule``
        :rtype:     :class:`ProfitBricksFirewallRule`
        """

        use_full_url = True

        if ex_href is None:
            if (
                ex_datacenter_id is None or
                ex_server_id is None or
                ex_nic_id is None or
                ex_firewall_rule_id is None
            ):
                raise ValueError(
                    (
                        'IDs are required for the data '
                        'center, server, network interface',
                        'and firewall rule.'
                    )
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}'
                    '/servers/{server_id}'
                    '/nics/{nic_id}'
                    '/firewallrules/{firewall_rule_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    server_id=ex_server_id,
                    nic_id=ex_nic_id,
                    firewall_rule_id=ex_firewall_rule_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_firewall_rule(response.object)

    def ex_create_firewall_rule(self, network_interface, protocol,
                                name=None, source_mac=None,
                                source_ip=None, target_ip=None,
                                port_range_start=None, port_range_end=None,
                                icmp_type=None, icmp_code=None):
        """
        Create a firewall rule for a network interface.

        :param  network_interface: The network interface to
                        attach the firewall rule to.
        :type:  network_interface: :class:`ProfitBricksNetworkInterface`

        :param  protocol: The protocol for the rule (TCP, UDP, ICMP, ANY)
        :type   protocol: ``str``

        :param  name: The name for the firewall rule
        :type   name: ``str``

        :param  source_mac: Only traffic originating from the respective
                            MAC address is allowed.
                            Valid format: aa:bb:cc:dd:ee:ff.
                            Value null allows all source MAC address.
        :type   source_mac: ``str``

        :param  source_ip: Only traffic originating from the respective IPv4
                    address is allowed. Value null allows all source IPs.
        :type   source_ip: ``str``

        :param  target_ip: In case the target NIC has multiple IP addresses,
                        only traffic directed to the respective IP address
                        of the NIC is allowed.
                        Value null allows all target IPs.
        :type   target_ip: ``str``

        :param  port_range_start: Defines the start range of the allowed port
                        (from 1 to 65534) if protocol TCP or UDP is chosen.
                        Leave portRangeStart and portRangeEnd value null
                        to allow all ports.
        type:   port_range_start: ``int``

        :param  port_range_end: Defines the end range of the allowed port
                        (from 1 to 65534) if protocol TCP or UDP is chosen.
                        Leave portRangeStart and portRangeEnd value null
                        to allow all ports.
        type:   port_range_end: ``int``

        :param  icmp_type: Defines the allowed type (from 0 to 254) if the
                        protocol ICMP is chosen. Value null allows all types.
        :type   icmp_type: ``int``

        :param  icmp_code: Defines the allowed code (from 0 to 254) if
                    protocol ICMP is chosen. Value null allows all codes.
        :type   icmp_code: ``int``

        :return:    Instance class ``ProfitBricksFirewallRule``
        :rtype:     :class:`ProfitBricksFirewallRule`
        """

        action = network_interface.href + '/firewallrules'
        body = {
            'properties': {
                'protocol': protocol
            }
        }

        if name is not None:
            body['properties']['name'] = name

        if source_mac is not None:
            body['properties']['sourceMac'] = source_mac

        if source_ip is not None:
            body['properties']['sourceIp'] = source_ip

        if target_ip is not None:
            body['properties']['targetIp'] = target_ip

        if port_range_start is not None:
            body['properties']['portRangeStart'] = str(port_range_start)

        if port_range_end is not None:
            body['properties']['portRangeEnd'] = str(port_range_end)

        if icmp_type is not None:
            body['properties']['icmpType'] = str(icmp_type)

        if icmp_code is not None:
            body['properties']['icmpType'] = str(icmp_code)

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_firewall_rule(response.object, response.headers)

    def ex_update_firewall_rule(self, firewall_rule,
                                name=None, source_mac=None,
                                source_ip=None, target_ip=None,
                                port_range_start=None, port_range_end=None,
                                icmp_type=None, icmp_code=None):
        """
        Update a firewall rule

        :param  firewall_rule: The firewall rule to update
        :type:  firewall_rule: :class:`ProfitBricksFirewallRule`

        :param  name: The name for the firewall rule
        :type   name: ``str``

        :param  source_mac: Only traffic originating from the respective
                            MAC address is allowed.
                            Valid format: aa:bb:cc:dd:ee:ff.
                            Value null allows all source MAC address.
        :type   source_mac: ``str``

        :param  source_ip: Only traffic originating from the respective IPv4
                    address is allowed. Value null allows all source IPs.
        :type   source_ip: ``str``

        :param  target_ip: In case the target NIC has multiple IP addresses,
                        only traffic directed to the respective IP address
                        of the NIC is allowed.
                        Value null allows all target IPs.
        :type   target_ip: ``str``

        :param  port_range_start: Defines the start range of the allowed port
                        (from 1 to 65534) if protocol TCP or UDP is chosen.
                        Leave portRangeStart and portRangeEnd value null
                        to allow all ports.
        type:   port_range_start: ``int``

        :param  port_range_end: Defines the end range of the allowed port
                        (from 1 to 65534) if protocol TCP or UDP is chosen.
                        Leave portRangeStart and portRangeEnd value null
                        to allow all ports.
        type:   port_range_end: ``int``

        :param  icmp_type: Defines the allowed type (from 0 to 254) if the
                        protocol ICMP is chosen. Value null allows all types.
        :type   icmp_type: ``int``

        :param  icmp_code: Defines the allowed code (from 0 to 254) if
                    protocol ICMP is chosen. Value null allows all codes.
        :type   icmp_code: ``int``

        :return:    Instance class ``ProfitBricksFirewallRule``
        :rtype:     :class:`ProfitBricksFirewallRule`
        """

        action = firewall_rule.href
        body = {}

        if name is not None:
            body['name'] = name

        if source_mac is not None:
            body['sourceMac'] = source_mac

        if source_ip is not None:
            body['sourceIp'] = source_ip

        if target_ip is not None:
            body['targetIp'] = target_ip

        if port_range_start is not None:
            body['portRangeStart'] = str(port_range_start)

        if port_range_end is not None:
            body['portRangeEnd'] = str(port_range_end)

        if icmp_type is not None:
            body['icmpType'] = str(icmp_type)

        if icmp_code is not None:
            body['icmpType'] = str(icmp_code)

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_firewall_rule(response.object, response.headers)

    def ex_delete_firewall_rule(self, firewall_rule):
        """
        Delete a firewall rule

        :param  firewall_rule: The firewall rule to delete.
        :type:  firewall_rule: :class:`ProfitBricksFirewallRule`

        :rtype  ``bool``
        """
        action = firewall_rule.href

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    LAN extension functions
    """

    def ex_list_lans(self, datacenter=None):
        """
        List local area network on:
        - a datacenter if one is specified
        - all datacenters if none specified

        :param  datacenter: The parent DC for the LAN.
        :type   datacenter: :class:`Datacenter`

        :return:    ``list`` of class ``ProfitBricksLan``
        :rtype:     `list`
        """
        if datacenter is not None:
            action = datacenter.extra['entities']['lans']['href']
            request = self.connection.request(
                action=action,
                params={'depth': 3},
                method='GET',
                with_full_url=True
            )
            lans = self._to_lans(request.object)

        else:
            datacenters = self.ex_list_datacenters()
            lans = []
            for datacenter in datacenters:
                action = datacenter.extra['entities']['lans']['href']
                request = self.connection.request(
                    action=action,
                    params={'depth': 3},
                    method='GET',
                    with_full_url=True
                )
                lans += self._to_lans(request.object)

        return lans

    def ex_create_lan(self, datacenter, name=None, is_public=False, nics=None):
        """
        Create and attach a Lan to a data center.

        :param  datacenter: The parent DC for the LAN..
        :type   datacenter: :class:`Datacenter`

        :param  name: LAN name.
        :type   name: ``str``

        :param  is_public: True if the Lan is to have internet access.
        :type   is_public: ``bool``

        :param  nics: Optional network interfaces to attach to the lan.
        :param  nics: ``list`` of class ``ProfitBricksNetworkInterface``

        :return:    Instance class ``ProfitBricksLan``
        :rtype:     :class:`ProfitBricksLan`
        """

        action = datacenter.extra['entities']['lans']['href']
        body = {
            'properties': {
                'name':
                name or
                'LAN - {datacenter_name}'.format(
                    datacenter_name=datacenter.name
                ),
                'public': is_public
            }
        }

        if nics is not None:
            body['entities'] = defaultdict(dict)
            body['entities']['nics']['items'] = [
                {'id': nic.id} for nic in nics
            ]

        request = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_lan(request.object, request.headers)

    def ex_describe_lan(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_lan_id=None
    ):
        """
        Fetch data on a local area network

        :param  ex_href: The href of the lan you wish to describe.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID of the parent
                                datacenter for the LAN.
        :type   ex_datacenter_id: ``str``

        :param  ex_lan_id: The ID of LAN.
        :type   ex_lan_id: ``str``

        :return:    Instance class ``ProfitBricksLan``
        :rtype:     :class:`ProfitBricksLan`
        """

        use_full_url = True

        if ex_href is None:
            if ex_datacenter_id is None or ex_lan_id is None:
                raise ValueError(
                    'IDs for the data center and LAN are required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}/'
                    'lans/{lan_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    lan_id=ex_lan_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            params={'depth': 1},
            with_full_url=use_full_url
        )

        return self._to_lan(response.object)

    def ex_update_lan(self, lan, is_public, name=None, ip_failover=None):
        """
        Update a local area network

        :param  lan: The lan you wish to update.
        :type:  lan: :class:`ProfitBricksLan`

        :param  is_public: Boolean indicating if
                the lan faces the public internet.
        :type   is_public: ``bool``

        :param  name: The name of the lan.
        :type   name: ``str``

        :param  ip_failover: The IP to fail over.
        :type   ip_failover: ``list`` of :class: ``ProfitBricksIPFailover``

        :return:    Instance class ``ProfitBricksLan``
        :rtype:     :class:`ProfitBricksLan`
        """
        action = lan.href
        body = {
            'public': is_public
        }

        if name is not None:
            body['name'] = name

        if ip_failover is not None:
            body['ipFailover'] = [{'ip': item.ip, 'nicUuid': item.nic_uuid}
                                  for item in ip_failover]

        request = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_lan(request.object, request.headers)

    def ex_delete_lan(self, lan):
        """
        Delete a local area network

        :param  lan: The lan you wish to delete.
        :type:  lan: :class:`ProfitBrickLan`

        :rtype  ``bool``
        """

        action = lan.href

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    Volume extension functions
    """

    def ex_update_volume(
        self, volume, ex_storage_name=None, size=None, ex_bus_type=None
    ):
        """
        Updates a volume.

        :param volume: The volume you're updating.
        :type volume: :class:`StorageVolume`

        :param  ex_storage_name: The name of the volume.
        :type   ex_storage_name: ``str``

        :param  size: The desired size.
        :type   size: ``int``

        :param  ex_bus_type: Volume bus type (VIRTIO, IDE).
        :type   ex_bus_type: ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """

        if not ex_storage_name:
            ex_storage_name = volume.name
        if not size:
            size = str(volume.size)

        action = volume.extra['href']
        body = {
            'name': ex_storage_name,
            'size': size
        }

        if ex_bus_type is not None:
            body['bus'] = ex_bus_type

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_volume(response.object, response.headers)

    def ex_describe_volume(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_volume_id=None
    ):
        """
        Fetches and returns a volume

        :param  ex_href: The full href (url) of the volume.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID of the parent
                                datacenter for the volume.
        :type   ex_datacenter_id: ``str``

        :param  ex_volume_id: The ID of the volume.
        :type   ex_volume_id: ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """

        use_full_url = True

        if ex_href is None:
            if ex_datacenter_id is None or ex_volume_id is None:
                raise ValueError(
                    'IDs for the data center and volume are required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}/'
                    'volumes/{volume_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    volume_id=ex_volume_id
                )

        response = self.connection.request(
            action=ex_href,
            method='GET',
            params={'depth': 3},
            with_full_url=use_full_url
        )

        return self._to_volume(response.object)

    def ex_restore_volume_snapshot(self, volume, snapshot):
        """
        Restores a snapshot for a volume

        :param  volume: The volume you're restoring the snapshot to.
        :type   volume: :class:`StorageVolume`

        :param  snapshot: The snapshot you're restoring to the volume.
        :type   snapshot: :class:`ProfitBricksSnapshot`

        :rtype  ``bool``
        """

        action = volume.extra['href'] + '/restore-snapshot'
        data = {'snapshotId': snapshot.id}
        body = urlencode(data)

        self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/x-www-form-urlencoded'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return True

    """
    Volume snapshot extension functions
    """

    def ex_describe_snapshot(self, ex_href=None, ex_snapshot_id=None):
        """
        Fetches and returns a volume snapshot

        :param  ex_href: The full href (url) of the snapshot.
        :type   ex_href: ``str``

        :param  ex_snapshot_id: The ID of the snapshot.
        :type   ex_snapshot_id: ``str``

        :return:    Instance of class ``ProfitBricksSnapshot``
        :rtype:     :class:`ProfitBricksSnapshot`
        """

        use_full_url = True

        if ex_href is None:
            if ex_snapshot_id is None:
                raise ValueError(
                    'The snapshot ID is required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'snapshots/{snapshot_id}'
                ).format(
                    snapshot_id=ex_snapshot_id
                )

        response = self.connection.request(
            action=ex_href,
            params={'depth': 3},
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_snapshot(response.object)

    def ex_update_snapshot(
        self, snapshot, name=None, description=None, cpu_hot_plug=None,
        cpu_hot_unplug=None, ram_hot_plug=None, ram_hot_unplug=None,
        nic_hot_plug=None, nic_hot_unplug=None, disc_virtio_hot_plug=None,
        disc_virtio_hot_unplug=None, disc_scsi_hot_plug=None,
        disc_scsi_hot_unplug=None, licence_type=None
    ):
        """
        Updates a snapshot

        :param  snapshot: The snapshot you're restoring to the volume.
        :type   snapshot: :class:`VolumeSnapshot`

        :param  name: The snapshot name
        :type   name: `str`

        :param  description: The snapshot description
        :type   description: `str`

        :param  cpu_hot_plug: Snapshot CPU is hot pluggalbe
        :type   cpu_hot_plug: `str`

        :param  cpu_hot_unplug: Snapshot CPU is hot unpluggalbe
        :type   cpu_hot_unplug: `str`

        :param  ram_hot_plug: Snapshot RAM is hot pluggalbe
        :type   ram_hot_plug: `str`

        :param  ram_hot_unplug: Snapshot RAM is hot unpluggalbe
        :type   ram_hot_unplug: `str`

        :param  nic_hot_plug: Snapshot Network Interface is hot pluggalbe
        :type   nic_hot_plug: `str`

        :param  nic_hot_unplug: Snapshot Network Interface is hot unpluggalbe
        :type   nic_hot_unplug: `str`

        :param  disc_virtio_hot_plug: Snapshot VIRTIO disk is hot pluggalbe
        :type   disc_virtio_hot_plug: `str`

        :param  disc_virtio_hot_unplug: Snapshot VIRTIO disk is hot unpluggalbe
        :type   disc_virtio_hot_unplug: `str`

        :param  disc_scsi_hot_plug: Snapshot SCSI disk is hot pluggalbe
        :type   disc_scsi_hot_plug: `str`

        :param  disc_scsi_hot_unplug: Snapshot SCSI disk is hot unpluggalbe
        :type   disc_scsi_hot_unplug: `str`

        :param  licence_type: The snapshot licence_type
        :type   licence_type: `str`

        :return:    Instance of class ``VolumeSnapshot``
        :rtype:     :class:`VolumeSnapshot`
        """

        action = snapshot.extra['href']
        body = {}

        if name is not None:
            body['name'] = name

        if description is not None:
            body['description'] = description

        if cpu_hot_plug is not None:
            body['cpuHotPlug'] = cpu_hot_plug

        if cpu_hot_unplug is not None:
            body['cpuHotUnplug'] = cpu_hot_unplug

        if ram_hot_plug is not None:
            body['ramHotPlug'] = ram_hot_plug

        if ram_hot_unplug is not None:
            body['ramHotUnplug'] = ram_hot_unplug

        if nic_hot_plug is not None:
            body['nicHotPlug'] = nic_hot_plug

        if nic_hot_unplug is not None:
            body['nicHotUnplug'] = nic_hot_unplug

        if disc_virtio_hot_plug is not None:
            body['discVirtioHotPlug'] = disc_virtio_hot_plug

        if disc_virtio_hot_unplug is not None:
            body['discVirtioHotUnplug'] = disc_virtio_hot_unplug

        if disc_scsi_hot_plug is not None:
            body['discScsiHotPlug'] = disc_scsi_hot_plug

        if disc_scsi_hot_unplug is not None:
            body['discScsiHotUnplug'] = disc_scsi_hot_unplug

        if licence_type is not None:
            body['licenceType'] = licence_type

        response = self.connection.request(
            action=action,
            params={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_snapshot(response.object, response.headers)

    """
    Load balancer extension functions
    """

    def ex_list_load_balancers(self):
        """
        Fetches as a list of load balancers

        :return:    ``list`` of class ``ProfitBricksLoadBalancer``
        :rtype:     `list`
        """

        datacenters = self.ex_list_datacenters()
        load_balancers = list()

        for datacenter in datacenters:
            extra = datacenter.extra
            load_balancers_href = extra['entities']['loadbalancers']['href']

            response = self.connection.request(
                action=load_balancers_href,
                params={'depth': 3},
                method='GET',
                with_full_url=True
            )

            mapped_load_balancers = self._to_load_balancers(response.object)
            load_balancers += mapped_load_balancers

        return load_balancers

    def ex_describe_load_balancer(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_load_balancer_id=None
    ):
        """
        Fetches and returns a load balancer

        :param  href: The full href (url) of the load balancer.
        :type   href: ``str``

        :param  ex_datacenter_id: The ID of the parent data center
                                for the load balancer.
        :type   ex_datacenter_id: ``str``

        :param  ex_load_balancer_id: The load balancer ID.
        :type   ex_load_balancer_id: ``str``

        :return:    Instance of class ``ProfitBricksLoadBalancer``
        :rtype:     :class:`ProfitBricksLoadBalancer`
        """

        use_full_url = True

        if ex_href is None:
            if (
                ex_datacenter_id is None or
                ex_load_balancer_id is None
            ):
                raise ValueError(
                    (
                        'IDs for the data center and '
                        'load balancer are required.'
                    )
                )
            else:
                use_full_url = False
                ex_href = (
                    'datacenters/{datacenter_id}/'
                    'loadbalancers/{load_balancer_id}'
                ).format(
                    datacenter_id=ex_datacenter_id,
                    load_balancer_id=ex_load_balancer_id
                )

        response = self.connection.request(
            action=ex_href,
            params={'depth': 3},
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_load_balancer(response.object)

    def ex_create_load_balancer(
        self, datacenter, name=None,
        ip=None, dhcp=None, nics=None
    ):
        """
        Create and attach a load balancer to a data center.

        :param  datacenter: The parent DC for the load balancer.
        :type   datacenter: :class:`Datacenter`

        :param  name: Load balancer name.
        :type   name: ``str``

        :param  ip: Load balancer IPV4 address.
        :type   ip: ``str``

        :param  dhcp: If true, the load balancer
                will reserve an IP address using DHCP.
        :type   dhcp: ``bool``

        :param  nics: Optional network interfaces
                taking part in load balancing.
        :param  nics: ``list`` of class ``ProfitBricksNetworkInterface``

        :return:    Instance class ``ProfitBricksLoadBalancer``
        :rtype:     :class:`ProfitBricksLoadBalancer`
        """

        action = datacenter.extra['entities']['loadbalancers']['href']
        body = {
            'properties': {
                'name':
                name or
                'Load Balancer - {datacenter_name}'
                .format(datacenter_name=datacenter.name)
            }
        }

        if ip is not None:
            body['properties']['ip'] = ip

        if dhcp is not None:
            body['properties']['dhcp'] = dhcp

        if nics is not None:
            body['entities'] = defaultdict(dict)
            body['entities']['balancednics']['items'] = [
                {'id': nic.id} for nic in nics
            ]

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return self._to_load_balancer(response.object, response.headers)

    def ex_update_load_balancer(
        self, load_balancer, name=None,
        ip=None, dhcp=None
    ):
        """
        Update a load balancer

        :param  load_balancer: The load balancer you wish to update.
        :type:  load_balancer: :class:`ProfitBricksLoadBalancer`

        :param  name: The name of the load balancer.
        :type   name: ``str``

        :param  ip: The IPV4 address of the load balancer.
        :type   ip: ``str``

        :param  dhcp: If true, the load balancer
                will reserve an IP address using DHCP.
        :type   dhcp: ``bool``

        :return:    Instance class ``ProfitBricksLoadBalancer``
        :rtype:     :class:`ProfitBricksLoadBalancer`
        """
        action = load_balancer.href
        body = {}

        if name is not None:
            body['name'] = name

        if ip is not None:
            body['ip'] = ip

        if dhcp is not None:
            body['dhcp'] = dhcp

        response = self.connection.request(
            action=action,
            headers={
                'Content-Type':
                'application/json'
            },
            data=body,
            method='PATCH',
            with_full_url=True
        )

        return self._to_load_balancer(response.object, response.headers)

    def ex_list_load_balanced_nics(self, load_balancer):
        """
        List balanced network interfaces for a load balancer.

        :param  load_balancer: The load balancer you wish to update.
        :type:  load_balancer: :class:`ProfitBricksLoadBalancer`

        :return:    ``list`` of class ``ProfitBricksNetorkInterface``
        :rtype:     `list`
        """
        action = load_balancer.extra['entities']['balancednics']['href']

        response = self.connection.request(
            action=action,
            params={'depth': 3},
            method='GET',
            with_full_url=True
        )

        return self._to_interfaces(response.object)

    def ex_describe_load_balanced_nic(
        self,
        ex_href=None,
        ex_datacenter_id=None,
        ex_server_id=None,
        ex_nic_id=None
    ):
        """
        Fetch information on a load balanced network interface.

        :param  ex_href: The href of the load balanced
                        NIC you wish to describe.
        :type   ex_href: ``str``

        :param  ex_datacenter_id: The ID of parent data center
                            of the NIC you wish to describe.
        :type   ex_datacenter_id: ``str``

        :param  ex_server_id: The server the NIC is connected to.
        :type   ex_server_id: ``str``

        :param  ex_nic_id: The ID of the NIC
        :type   ex_nic_id: ``str``

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """
        return self.ex_describe_network_interface(
            ex_href=ex_href,
            ex_datacenter_id=ex_datacenter_id,
            ex_server_id=ex_server_id,
            ex_nic_id=ex_nic_id
        )

    def ex_attach_nic_to_load_balancer(
        self, load_balancer, network_interface
    ):
        """
        Attaches a network interface to a load balancer

        :param  load_balancer: The load balancer you wish
                to attach the network interface to.
        :type:  load_balancer: :class:`ProfitBricksLoadBalancer`

        :param  network_interface: The network interface
                being attached.
        :type:  network_interface: :class:`ProfitBricksNetworkInterface`

        :rtype  ``bool``
        """
        action = load_balancer.extra['entities']['balancednics']['href']
        body = {
            'id': network_interface.id
        }

        self.connection.request(
            action=action,
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST',
            with_full_url=True
        )

        return True

    def ex_remove_nic_from_load_balancer(
        self, load_balancer, network_interface
    ):
        """
        Removed a network interface from a load balancer

        :param  load_balancer: The load balancer you
                wish to remove the network interface from.
        :type:  load_balancer: :class:`ProfitBricksLoadBalancer`

        :param  network_interface: The network interface
                being removed.
        :type:  network_interface: :class:`ProfitBricksNetworkInterface`

        :rtype  ``bool``
        """
        action = load_balancer.href + '/balancednics/' + network_interface.id

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    def ex_delete_load_balancer(self, load_balancer):
        """
        Delete a load balancer

        :param  load_balancer: The load balancer you wish to delete.
        :type:  load_balancer: :class:`ProfitBricksLoadBalancer`

        :rtype  ``bool``
        """

        action = load_balancer.href

        self.connection.request(
            action=action,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    IP Block extension functions
    """

    def ex_list_ip_blocks(self):
        """
        List all IP blocks

        :return:    ``list`` of class ``ProfitBricksIPBlock``
        :rtype:     `list`
        """

        response = self.connection.request(
            action='ipblocks',
            params={'depth': 3},
            method='GET'
        )

        return self._to_ip_blocks(response.object)

    def ex_create_ip_block(self, location, size, name=None):
        """
        Create an IP block

        :param  location: The location of the IP block.
        :type   location: :class:`NodeLocation`

        :param  size: The size of the IP block.
        :type   size: ``int``

        :param  name: The name of the IP block.
        :type   name: ``str``

        :return:    Instance class ``ProfitBricksIPBlock``
        :rtype:     :class:`ProfitBricksIPBlock`
        """

        body = {
            'properties': {
                'location': location.id,
                'size': size
            }
        }

        if name is not None:
            body['properties']['name'] = name

        response = self.connection.request(
            action='ipblocks',
            headers={
                'Content-Type': 'application/json'
            },
            data=body,
            method='POST'
        )

        return self._to_ip_block(response.object, response.headers)

    def ex_describe_ip_block(self, ex_href=None, ex_ip_block_id=None):
        """
        Fetch an IP block

        :param  ex_href: The href of the IP block.
        :type   ex_href: ``str``

        :param  ex_ip_block_id: The ID of the IP block.
        :type   ex_ip_block_id: ``str``

        :return:    Instance class ``ProfitBricksIPBlock``
        :rtype:     :class:`ProfitBricksIPBlock`
        """

        use_full_url = True

        if ex_href is None:
            if ex_ip_block_id is None:
                raise ValueError(
                    'The IP block ID is required.'
                )
            else:
                use_full_url = False
                ex_href = (
                    'ipblocks/{ip_block_id}'
                ).format(
                    ip_block_id=ex_ip_block_id
                )

        response = self.connection.request(
            action=ex_href,
            params={'depth': 3},
            method='GET',
            with_full_url=use_full_url
        )

        return self._to_ip_block(response.object)

    def ex_delete_ip_block(self, ip_block):
        """
        Delete an IP block

        :param  ip_block: The IP block you wish to delete.
        :type:  ip_block: :class:`ProfitBricksIPBlock`

        :rtype  ``bool``
        """

        self.connection.request(
            action=ip_block.href,
            method='DELETE',
            with_full_url=True
        )

        return True

    """
    Private Functions
    """

    def _to_ip_blocks(self, object):
        return [self._to_ip_block(
            ip_block) for ip_block in object['items']]

    def _to_ip_block(self, ip_block, headers=None):
        nested = {
            'metadata': ip_block['metadata']
        }

        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        state = self.NODE_STATE_MAP.get(
            ip_block['metadata']['state'],
            NodeState.UNKNOWN
        )

        # self, id, name, href, location, size, ips, state, driver, extra=None

        return ProfitBricksIPBlock(
            id=ip_block['id'],
            name=ip_block['properties']['name'],
            href=ip_block['href'],
            location=ip_block['properties']['location'],
            size=ip_block['properties']['size'],
            ips=ip_block['properties']['ips'] or [],
            state=state,
            driver=self.connection.driver,
            extra=extra
        )

    def _to_load_balancers(self, object):
        return [self._to_load_balancer(
            load_balancer) for load_balancer in object['items']]

    def _to_load_balancer(self, load_balancer, headers=None):
        nested = {
            'props': load_balancer['properties'],
            'metadata': load_balancer['metadata']
        }

        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            },
            'props': {
                'name': 'name',
                'ip': 'ip',
                'dhcp': 'dhcp'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        if 'entities' in load_balancer:
            extra['entities'] = load_balancer['entities']

        state = self.NODE_STATE_MAP.get(
            load_balancer['metadata']['state'],
            NodeState.UNKNOWN
        )

        return ProfitBricksLoadBalancer(
            id=load_balancer['id'],
            name=load_balancer['properties']['name'],
            href=load_balancer['href'],
            state=state,
            driver=self.connection.driver,
            extra=extra
        )

    def _to_snapshots(self, object):
        return [self._to_snapshot(
            snapshot) for snapshot in object['items']]

    def _to_snapshot(self, snapshot, headers=None):
        nested = {
            'props': snapshot['properties'],
            'metadata': snapshot['metadata']
        }

        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            },
            'props': {
                'name': 'name',
                'description': 'description',
                'location': 'location',
                'size': 'size',
                'cpuHotPlug': 'cpu_hot_plug',
                'cpuHotUnplug': 'cpu_hot_unplug',
                'ramHotPlug': 'ram_hot_plug',
                'ramHotUnplug': 'ram_hot_unplug',
                'nicHotPlug': 'nic_hot_plug',
                'nicHotUnplug': 'nic_hot_unplug',
                'discVirtioHotPlug': 'disc_virtio_hot_plug',
                'discVirtioHotUnplug': 'disc_virtio_hot_unplug',
                'discScsiHotPlug': 'disc_scsi_hot_plug',
                'discScsiHotUnplug': 'disc_scsi_hot_unplug',
                'licenceType': 'licence_type'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        state = self.NODE_STATE_MAP.get(
            snapshot['metadata']['state'],
            NodeState.UNKNOWN
        )

        extra['href'] = snapshot['href']

        return VolumeSnapshot(
            id=snapshot['id'],
            driver=self.connection.driver,
            size=extra['size'],
            extra=extra,
            created=extra['created_date'],
            state=state,
            name=extra['name']
        )

    def _to_lans(self, object):
        return [self._to_lan(
            lan) for lan in object['items']]

    def _to_lan(self, lan, headers=None):
        nested = {
            'props': lan['properties'],
            'metadata': lan['metadata']
        }

        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            },
            'props': {
                'name': 'name',
                'public': 'is_public'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if 'entities' in lan:
            extra['entities'] = lan['entities']

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        extra['provisioning_state'] = self.PROVISIONING_STATE.get(
            lan['metadata']['state'],
            NodeState.UNKNOWN
        )

        state = self.NODE_STATE_MAP.get(
            lan['metadata']['state'],
            NodeState.UNKNOWN
        )

        return ProfitBricksLan(
            id=lan['id'],
            name=lan['properties']['name'],
            href=lan['href'],
            is_public=lan['properties']['public'],
            state=state,
            driver=self.connection.driver,
            extra=extra
        )

    def _to_datacenters(self, object):
        return [self._to_datacenter(
            datacenter) for datacenter in object['items']]

    def _to_datacenter(self, datacenter, headers=None):
        nested = {
            'props': datacenter['properties'],
            'metadata': datacenter['metadata']
        }

        if 'entities' in datacenter:
            nested['entities'] = datacenter['entities']

        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            },
            'props': {
                'description': 'description',
                'features': 'features',
                'location': 'location',
                'name': 'name',
                'version': 'version'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if 'entities' in datacenter:
            extra['entities'] = datacenter['entities']

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        extra['provisioning_state'] = self.PROVISIONING_STATE.get(
            datacenter['metadata']['state'],
            NodeState.UNKNOWN
        )

        return Datacenter(
            id=datacenter['id'],
            href=datacenter['href'],
            name=datacenter['properties']['name'],
            version=datacenter['properties']['version'],
            driver=self.connection.driver,
            extra=extra
        )

    def _to_images(self, object, image_type=None, is_public=True):

        if image_type is not None:
            images = [
                image for image in object['items']
                if image['properties']['imageType'] == image_type and
                image['properties']['public'] == is_public
            ]
        else:
            images = [
                image for image in object['items']
                if image['properties']['public'] == is_public
            ]

        return [self._to_image(image) for image in images]

    def _to_image(self, image, headers=None):
        nested = {
            'props': image['properties'],
            'metadata': image['metadata']
        }
        extra = {}

        MAPPED_ATTRS = {
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            },
            'props': {
                'name': 'name',
                'description': 'description',
                'location': 'location',
                'size': 'size',
                'cpuHotPlug': 'cpu_hot_plug',
                'cpuHotUnplug': 'cpu_hot_unplug',
                'ramHotPlug': 'ram_hot_plug',
                'ramHotUnplug': 'ram_hot_unplug',
                'nicHotPlug': 'nic_hot_plug',
                'nicHotUnplug': 'nic_hot_unplug',
                'discVirtioHotPlug': 'disc_virtio_hot_plug',
                'discVirtioHotUnplug': 'disc_virtio_hot_unplug',
                'discScsiHotPlug': 'disc_scsi_hot_plug',
                'discScsiHotUnplug': 'disc_scsi_hot_unplug',
                'licenceType': 'licence_type',
                'imageType': 'image_type',
                'imageAliases': 'image_aliases',
                'public': 'public'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        """
        Put the href inside extra
        because we cannot assign
        it to the NodeImage type.
        """
        extra['href'] = image['href']

        return NodeImage(
            id=image['id'],
            name=image['properties']['name'],
            driver=self.connection.driver,
            extra=extra
        )

    def _to_nodes(self, object):
        return [self._to_node(n) for n in object['items']]

    def _to_node(self, node, headers=None):
        """
        Convert the request into a node Node
        """
        nested = {
            'props': node['properties'],
            'metadata': node['metadata'],
            'entities': node['entities']
        }
        extra = {}

        MAPPED_ATTRS = {
            'props': {
                'name': 'name',
                'availabilityZone': 'availability_zone',
                'bootCdrom': 'boot_cdrom',
                'bootVolume': 'boot_volume',
                'cores': 'cores',
                'cpuFamily': 'cpu_family',
                'ram': 'ram',
                'vmState': 'vm_state'
            },
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedBy': 'last_modified_by',
                'lastModifiedDate': 'last_modified_date',
                'state': 'state'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        state = self.NODE_STATE_MAP.get(
            node['properties']['vmState'],
            NodeState.UNKNOWN
        )

        extra['entities'] = nested['entities']
        extra['href'] = node['href']

        public_ips = []
        private_ips = []

        if 'nics' in nested['entities']:
            if 'items' in nested['entities']['nics']:
                for nic in nested['entities']['nics']['items']:
                    if nic['properties']['nat'] is True:
                        public_ips += nic['properties']['ips']
                    elif nic['properties']['nat'] is False:
                        private_ips += nic['properties']['ips']

        return Node(
            id=node['id'],
            name=nested['props']['name'],
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra=extra
        )

    def _to_volumes(self, object):
        return [self._to_volume(
            volume) for volume in object['items']]

    def _to_volume(self, volume, headers=None):

        nested = {
            'props': volume['properties'],
            'metadata': volume['metadata']
        }
        extra = {}

        MAPPED_ATTRS = {
            'props': {
                'bus': 'bus',
                'size': 'size',
                'cpuHotPlug': 'cpu_hot_plug',
                'cpuHotUnplug': 'cpu_hot_unplug',
                'discScsiHotPlug': 'disc_scsi_hot_plug',
                'discScsiHotUnplug': 'disc_scsi_hot_unplug',
                'discVirtioHotPlug': 'disc_virtio_hot_plug',
                'discVirtioHotUnplug': 'disc_virtio_hot_unplug',
                'image': 'image',
                'imagePassword': 'image_password',
                'licenceType': 'licence_type',
                'name': 'name',
                'nicHotPlug': 'nic_hot_plug',
                'nicHotUnplug': 'nic_hot_unplug',
                'ramHotPlug': 'ram_hot_plug',
                'ramHotUnplug': 'ram_hot_unplug',
                'sshKeys': 'ssh_keys',
                'type': 'type',
                'deviceNumber': 'device_number'
            },
            'metadata': {
                'createdBy': 'created_by',
                'createdDate': 'created_date',
                'etag': 'etag',
                'lastModifiedBy': 'last_modified_by',
                'lastModifiedDate': 'last_modified_date',
                'state': 'state'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        extra['provisioning_state'] = self.PROVISIONING_STATE.get(
            volume['metadata']['state'],
            NodeState.UNKNOWN
        )

        extra['href'] = volume['href']

        if 'availabilityZone' in volume['properties']:
            properties = volume['properties']
            extra['availability_zone'] = properties['availabilityZone']

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        return StorageVolume(
            id=volume['id'],
            name=volume['properties']['name'],
            size=volume['properties']['size'],
            driver=self.connection.driver,
            extra=extra
        )

    def _to_interfaces(self, object):
        return [self._to_interface(
            interface) for interface in object['items']]

    def _to_interface(self, interface, headers=None):
        nested = {
            'props': interface['properties'],
            'metadata': interface['metadata']
        }
        extra = {}

        MAPPED_ATTRS = {
            'props': {
                'dhcp': 'dhcp',
                'firewallActive': 'firewall_active',
                'ips': 'ips',
                'lan': 'lan',
                'mac': 'mac',
                'name': 'name',
                'nat': 'nat'
            },
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedBy': 'last_modified_by',
                'lastModifiedDate': 'last_modified_date',
                'state': 'state'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if 'entities' in interface:
            extra['entities'] = interface['entities']

        state = self.NODE_STATE_MAP.get(
            interface['metadata']['state'],
            NodeState.UNKNOWN
        )

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        return ProfitBricksNetworkInterface(
            id=interface['id'],
            name=interface['properties']['name'],
            href=interface['href'],
            state=state,
            extra=extra
        )

    def _to_firewall_rules(self, object):
        return [self._to_firewall_rule(
            firewall_rule) for firewall_rule in object['items']]

    def _to_firewall_rule(self, firewallrule, headers=None):
        nested = {
            'props': firewallrule['properties'],
            'metadata': firewallrule['metadata']
        }
        extra = {}

        MAPPED_ATTRS = {
            'props': {
                'name': 'name',
                'protocol': 'protocol',
                'sourceMac': 'source_mac',
                'sourceIp': 'source_ip',
                'targetIp': 'target_ip',
                'icmpCode': 'icmp_code',
                'icmpType': 'icmp_type',
                'portRangeStart': 'port_range_start',
                'portRangeEnd': 'port_range_end'
            },
            'metadata': {
                'createdDate': 'created_date',
                'createdBy': 'created_by',
                'etag': 'etag',
                'lastModifiedDate': 'last_modified_date',
                'lastModifiedBy': 'last_modified_by',
                'state': 'state'
            }
        }

        for k, v in MAPPED_ATTRS.items():
            for original_name, altered_name in v.items():
                extra[altered_name] = nested[k][original_name]

        if headers is not None:
            if 'location' in headers:
                extra['status_url'] = headers['location']

        state = self.NODE_STATE_MAP.get(
            firewallrule['metadata']['state'],
            NodeState.UNKNOWN
        )

        return ProfitBricksFirewallRule(
            id=firewallrule['id'],
            name=firewallrule['properties']['name'],
            href=firewallrule['href'],
            state=state,
            extra=extra
        )

    def _to_locations(self, object):
        return [self._to_location(location) for location in object['items']]

    def _to_location(self, location):
        return NodeLocation(
            id=location['id'],
            name=location['properties']['name'],
            country=location['id'].split('/')[0],
            driver=self.connection.driver
        )

    def _to_node_size(self, data):
        """
        Convert the PROFIT_BRICKS_GENERIC_SIZES into NodeSize
        """
        return NodeSize(
            id=data["id"],
            name=data["name"],
            ram=data["ram"],
            disk=data["disk"],
            bandwidth=None,
            price=None,
            driver=self.connection.driver,
            extra={'cores': data["cores"]}
        )

    def _wait_for_datacenter_state(
        self, datacenter, state=NodeState.RUNNING,
        timeout=300, interval=5
    ):
        """
        Private function that waits the datacenter
        to transition into the specified state.

        :return: Datacenter object on success.
        :rtype: :class:`.Datacenter`
        """

        wait_time = 0
        attempts = 0

        while attempts < 5:
            attempts += 1
            try:
                datacenter = self.ex_describe_datacenter(
                    ex_datacenter_id=datacenter.id
                )
                break

            except BaseHTTPError:
                time.sleep(interval)

        if datacenter is None:
            raise Exception(
                'Data center was not ready in time to '
                'complete this operation.'
            )

        while (datacenter.extra['provisioning_state'] != state):
            datacenter = \
                self.ex_describe_datacenter(ex_href=datacenter.href)

            if datacenter.extra['provisioning_state'] == state:
                break

            if wait_time >= timeout:
                raise Exception(
                    'Datacenter didn\'t transition to %s state '
                    'in %s seconds' % (state, timeout)
                )

            wait_time += interval
            time.sleep(interval)

        return datacenter

    def _create_new_datacenter_for_node(
        self,
        name,
        location=None
    ):
        """
        Creates a Datacenter for a node.
        """
        dc_name = name + '-DC'

        if location is None:
            location = self.ex_describe_location(
                ex_location_id='us/las'
            )

        return self.ex_create_datacenter(
            name=dc_name,
            location=location
        )
