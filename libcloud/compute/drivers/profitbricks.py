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

import copy
import time

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.utils.networking import is_private_subnet
from libcloud.utils.py3 import b
from libcloud.compute.providers import Provider
from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume
from libcloud.compute.base import UuidMixin
from libcloud.compute.types import NodeState
from libcloud.common.types import LibcloudError, MalformedResponseError

__all__ = [
    'API_VERSION',
    'API_HOST',
    'ProfitBricksNodeDriver',
    'Datacenter',
    'ProfitBricksNetworkInterface',
    'ProfitBricksAvailabilityZone'
]

API_HOST = 'api.profitbricks.com'
API_VERSION = '/1.3/'


class ProfitBricksResponse(XmlResponse):
    """
    ProfitBricks response parsing.
    """
    def parse_error(self):
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError('Failed to parse XML',
                                         body=self.body,
                                         driver=ProfitBricksNodeDriver)

        for e in body.findall('.//detail'):
            if ET.iselement(e[0].find('httpCode')):
                http_code = e[0].find('httpCode').text
            else:
                http_code = None
            if ET.iselement(e[0].find('faultCode')):
                fault_code = e[0].find('faultCode').text
            else:
                fault_code = None
            if ET.iselement(e[0].find('message')):
                message = e[0].find('message').text
            else:
                message = None

        return LibcloudError('HTTP Code: %s, Fault Code: %s, Message: %s' %
                             (http_code, fault_code, message), driver=self)


class ProfitBricksConnection(ConnectionUserAndKey):
    """
    Represents a single connection to the ProfitBricks endpoint.
    """
    host = API_HOST
    api_prefix = API_VERSION
    responseCls = ProfitBricksResponse

    # Supporting xml + lxml is funky :S
    SOAPENV_NAMESPACE = 'http://schemas.xmlsoap.org/soap/envelope/'
    SOAPENV = '{%s}' % SOAPENV_NAMESPACE
    WS_NAMESPACE = 'http://ws.api.profitbricks.com/'
    WS = '{%s}' % WS_NAMESPACE
    NSMAP = {
        'soapenv': SOAPENV_NAMESPACE,
        'ws': WS_NAMESPACE,
    }

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'text/xml'
        headers['Authorization'] = 'Basic %s' % (base64.b64encode(
            b('%s:%s' % (self.user_id, self.key))).decode('utf-8'))

        return headers

    def encode_data(self, data):
        soap_env = ET.Element(self.SOAPENV + 'Envelope',
                              self.NSMAP, **self.NSMAP)
        ET.SubElement(soap_env, self.SOAPENV + 'Header')
        soap_body = ET.SubElement(soap_env, self.SOAPENV + 'Body')
        soap_req_body = ET.SubElement(soap_body, self.WS + data['action'])

        if 'request' in data.keys():
            soap_req_body = ET.SubElement(soap_req_body, 'request')
            for key, value in data.items():
                if key not in ['action', 'request']:
                    child = ET.SubElement(soap_req_body, key)
                    child.text = value
        else:
            for key, value in data.items():
                if key != 'action':
                    child = ET.SubElement(soap_req_body, key)
                    child.text = value

        soap_post = ET.tostring(soap_env)

        return soap_post

    def request(self, action, params=None, data=None, headers=None,
                method='POST', raw=False):
        action = self.api_prefix + action

        return super(ProfitBricksConnection, self).request(action=action,
                                                           params=params,
                                                           data=data,
                                                           headers=headers,
                                                           method=method,
                                                           raw=raw)


class Datacenter(UuidMixin):
    """
    Class which stores information about ProfitBricks datacenter
    instances.

    :param      id: The datacenter ID.
    :type       id: ``str``

    :param      name: The datacenter name.
    :type       name: ``str``

    :param version: Datacenter version.
    :type version: ``str``


    Note: This class is ProfitBricks specific.
    """
    def __init__(self, id, name, version, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.version = version
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return ((
            '<Datacenter: id=%s, name=%s, version=%s, driver=%s> ...>')
            % (self.id, self.name, self.version,
                self.driver.name))


class ProfitBricksNetworkInterface(object):
    """
    Class which stores information about ProfitBricks network
    interfaces.

    :param      id: The network interface ID.
    :type       id: ``str``

    :param      name: The network interface name.
    :type       name: ``str``

    :param      state: The network interface name.
    :type       state: ``int``

    Note: This class is ProfitBricks specific.
    """
    def __init__(self, id, name, state, extra=None):
        self.id = id
        self.name = name
        self.state = state
        self.extra = extra or {}

    def __repr__(self):
        return (('<ProfitBricksNetworkInterface: id=%s, name=%s>')
                % (self.id, self.name))


class ProfitBricksAvailabilityZone(object):
    """
    Extension class which stores information about a ProfitBricks
    availability zone.

    Note: This class is ProfitBricks specific.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return (('<ProfitBricksAvailabilityZone: name=%s>')
                % (self.name))


class ProfitBricksNodeDriver(NodeDriver):
    """
    Base ProfitBricks node driver.
    """
    connectionCls = ProfitBricksConnection
    name = 'ProfitBricks'
    website = 'http://www.profitbricks.com'
    type = Provider.PROFIT_BRICKS

    PROVISIONING_STATE = {
        'INACTIVE': NodeState.PENDING,
        'INPROCESS': NodeState.PENDING,
        'AVAILABLE': NodeState.RUNNING,
        'DELETED': NodeState.TERMINATED,
    }

    NODE_STATE_MAP = {
        'NOSTATE': NodeState.UNKNOWN,
        'RUNNING': NodeState.RUNNING,
        'BLOCKED': NodeState.STOPPED,
        'PAUSE': NodeState.STOPPED,
        'SHUTDOWN': NodeState.PENDING,
        'SHUTOFF': NodeState.STOPPED,
        'CRASHED': NodeState.STOPPED,
    }

    REGIONS = {
        '1': {'region': 'us/las', 'country': 'USA'},
        '2': {'region': 'de/fra', 'country': 'DEU'},
        '3': {'region': 'de/fkb', 'country': 'DEU'},
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

        :rtype: ``list`` of :class:`NodeSize`
        """
        sizes = []

        for key, values in self.PROFIT_BRICKS_GENERIC_SIZES.items():
            node_size = self._to_node_size(values)
            sizes.append(node_size)

        return sizes

    def list_images(self):
        """
        List all images.

        :rtype: ``list`` of :class:`NodeImage`
        """

        action = 'getAllImages'
        body = {'action': action}

        return self._to_images(self.connection.request(action=action,
                               data=body, method='POST').object)

    def list_locations(self):
        """
        List all locations.
        """
        locations = []

        for key, values in self.REGIONS.items():
            location = self._to_location(values)
            locations.append(location)

        return locations

    def list_nodes(self):
        """
        List all nodes.

        :rtype: ``list`` of :class:`Node`
        """
        action = 'getAllServers'
        body = {'action': action}

        return self._to_nodes(self.connection.request(action=action,
                              data=body, method='POST').object)

    def reboot_node(self, node):
        """
        Reboots the node.

        :rtype: ``bool``
        """
        action = 'resetServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def create_node(self, name, image, size=None, location=None,
                    volume=None, ex_datacenter=None, ex_internet_access=True,
                    ex_availability_zone=None, ex_ram=None, ex_cores=None,
                    ex_disk=None, **kwargs):
        """
        Creates a node.

        image is optional as long as you pass ram, cores, and disk
        to the method. ProfitBricks allows you to adjust compute
        resources at a much more granular level.

        :param volume: If the volume already exists then pass this in.
        :type volume: :class:`StorageVolume`

        :param location: The location of the new data center
            if one is not supplied.
        :type location: : :class:`NodeLocation`

        :param ex_datacenter: If you've already created the DC then pass
                           it in.
        :type ex_datacenter: :class:`Datacenter`

        :param ex_internet_access: Configure public Internet access.
        :type ex_internet_access: : ``bool``

        :param ex_availability_zone: The availability zone.
        :type ex_availability_zone: class: `ProfitBricksAvailabilityZone`

        :param ex_ram: The amount of ram required.
        :type ex_ram: : ``int``

        :param ex_cores: The number of cores required.
        :type ex_cores: : ``int``

        :param ex_disk: The amount of disk required.
        :type ex_disk: : ``int``

        :return:    Instance of class ``Node``
        :rtype:     :class:`Node`
        """
        if not ex_datacenter:
            '''
            We generate a name from the server name passed into the function.
            '''

            'Creating a Datacenter for the node since one was not provided.'
            new_datacenter = self._create_new_datacenter_for_node(
                name=name,
                location=location
            )
            datacenter_id = new_datacenter.id

            'Waiting for the Datacenter create operation to finish.'
            self._wait_for_datacenter_state(datacenter=new_datacenter)
        else:
            datacenter_id = ex_datacenter.id
            new_datacenter = None

        if not size:
            if not ex_ram:
                raise ValueError('You need to either pass a '
                                 'NodeSize or specify ex_ram as '
                                 'an extra parameter.')
            if not ex_cores:
                raise ValueError('You need to either pass a '
                                 'NodeSize or specify ex_cores as '
                                 'an extra parameter.')

        if not volume:
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

        if not ex_disk:
            ex_disk = size.disk

        if not ex_ram:
            ex_ram = size.ram

        if not ex_cores:
            ex_cores = size.extra['cores']

        '''
        A pasword is automatically generated if it is
        not provided. This is then sent via email to
        the admin contact on record.
        '''

        if 'auth' in kwargs:
            auth = self._get_and_check_auth(kwargs["auth"])
            password = auth.password
        else:
            password = None

        '''
        Create a StorageVolume that can be attached to the
        server when it is created.
        '''
        if not volume:
            volume = self._create_node_volume(ex_disk=ex_disk,
                                              image=image,
                                              password=password,
                                              name=name,
                                              ex_datacenter=ex_datacenter,
                                              new_datacenter=new_datacenter)

            storage_id = volume.id

            'Waiting on the storage volume to be created before provisioning '
            'the instance.'
            self._wait_for_storage_volume_state(volume)
        else:
            if ex_datacenter:
                datacenter_id = ex_datacenter.id
            else:
                datacenter_id = volume.extra['datacenter_id']

            storage_id = volume.id

        action = 'createServer'
        body = {'action': action,
                'request': 'true',
                'serverName': name,
                'cores': str(ex_cores),
                'ram': str(ex_ram),
                'bootFromStorageId': storage_id,
                'internetAccess': str(ex_internet_access).lower(),
                'dataCenterId': datacenter_id
                }

        if ex_availability_zone:
            body['availabilityZone'] = ex_availability_zone.name

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        nodes = self._to_nodes(data)
        return nodes[0]

    def destroy_node(self, node, ex_remove_attached_disks=False):
        """
        Destroys a node.

        :param node: The node you wish to destroy.
        :type volume: :class:`Node`

        :param ex_remove_attached_disks: True to destroy all attached volumes.
        :type ex_remove_attached_disks: : ``bool``

        :rtype:     : ``bool``
        """
        action = 'deleteServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    """
    Volume Functions
    """

    def list_volumes(self):
        """
        Lists all voumes.
        """
        action = 'getAllStorages'
        body = {'action': action}

        return self._to_volumes(self.connection.request(action=action,
                                                        data=body,
                                                        method='POST').object)

    def attach_volume(self, node, volume, device=None, ex_bus_type=None):
        """
        Attaches a volume.

        :param volume: The volume you're attaching.
        :type volume: :class:`StorageVolume`

        :param node: The node to which you're attaching the volume.
        :type node: :class:`Node`

        :param device: The device number order.
        :type device: : ``int``

        :param ex_bus_type: Bus type. Either IDE or VIRTIO (default).
        :type ex_bus_type: ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """
        action = 'connectStorageToServer'
        body = {'action': action,
                'request': 'true',
                'storageId': volume.id,
                'serverId': node.id,
                'busType': ex_bus_type,
                'deviceNumber': str(device)
                }

        self.connection.request(action=action,
                                data=body, method='POST').object
        return volume

    def create_volume(self, size, name=None,
                      ex_datacenter=None, ex_image=None, ex_password=None):
        """
        Creates a volume.

        :param ex_datacenter: The datacenter you're placing
                              the storage in. (req)
        :type ex_datacenter: :class:`Datacenter`

        :param ex_image: The OS image for the volume.
        :type ex_image: :class:`NodeImage`

        :param ex_password: Optional password for root.
        :type ex_password: : ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """
        action = 'createStorage'
        body = {'action': action,
                'request': 'true',
                'size': str(size),
                'storageName': name,
                'mountImageId': ex_image.id
                }

        if ex_datacenter:
            body['dataCenterId'] = ex_datacenter.id

        if ex_password:
            body['profitBricksImagePassword'] = ex_password

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        volumes = self._to_volumes(data)
        return volumes[0]

    def detach_volume(self, volume):
        """
        Detaches a volume.

        :param volume: The volume you're detaching.
        :type volume: :class:`StorageVolume`

        :rtype:     :``bool``
        """
        node_id = volume.extra['server_id']

        action = 'disconnectStorageFromServer'
        body = {'action': action,
                'storageId': volume.id,
                'serverId': node_id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def destroy_volume(self, volume):
        """
        Destroys a volume.

        :param volume: The volume you're attaching.
        :type volume: :class:`StorageVolume`

        :rtype:     : ``bool``
        """
        action = 'deleteStorage'
        body = {'action': action,
                'storageId': volume.id}

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_update_volume(self, volume, storage_name=None, size=None):
        """
        Updates a volume.

        :param volume: The volume you're attaching..
        :type volume: :class:`StorageVolume`

        :param storage_name: The name of the volume.
        :type storage_name: : ``str``

        :param size: The desired size.
        :type size: ``int``

        :rtype:     : ``bool``
        """
        action = 'updateStorage'
        body = {'action': action,
                'request': 'true',
                'storageId': volume.id
                }

        if storage_name:
            body['storageName'] = storage_name
        if size:
            body['size'] = str(size)

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_describe_volume(self, volume_id):
        """
        Describes a volume.

        :param volume_id: The ID of the volume you're describing.
        :type volume_id: :class:`StorageVolume`

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """
        action = 'getStorage'
        body = {'action': action,
                'storageId': volume_id
                }

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        volumes = self._to_volumes(data)
        return volumes[0]

    """
    Extension Functions
    """

    ''' Server Extension Functions
    '''
    def ex_stop_node(self, node):
        """
        Stops a node.

        This also deallocates the public IP space.

        :param node: The node you wish to halt.
        :type node: :class:`Node`

        :rtype:     : ``bool``
        """
        action = 'stopServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_start_node(self, node):
        """
        Starts a volume.

        :param node: The node you wish to start.
        :type node: :class:`Node`

        :rtype:     : ``bool``
        """
        action = 'startServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_list_availability_zones(self):
        """
        Returns a list of availability zones.
        """

        availability_zones = []

        for key, values in self.AVAILABILITY_ZONE.items():
            name = copy.deepcopy(values)["name"]

            availability_zone = ProfitBricksAvailabilityZone(
                name=name
            )
            availability_zones.append(availability_zone)

        return availability_zones

    def ex_describe_node(self, node):
        """
        Describes a node.

        :param node: The node you wish to describe.
        :type node: :class:`Node`

        :return:    Instance of class ``Node``
        :rtype:     :class:`Node`
        """
        action = 'getServer'
        body = {'action': action,
                'serverId': node.id
                }

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        nodes = self._to_nodes(data)
        return nodes[0]

    def ex_update_node(self, node, name=None, cores=None,
                       ram=None, availability_zone=None):
        """
        Updates a node.

        :param cores: The number of CPUs the node should have.
        :type device: : ``int``

        :param ram: The amount of ram the machine should have.
        :type ram: : ``int``

        :param ex_availability_zone: Update the availability zone.
        :type ex_availability_zone: :class:`ProfitBricksAvailabilityZone`

        :rtype:     : ``bool``
        """
        action = 'updateServer'

        body = {'action': action,
                'request': 'true',
                'serverId': node.id
                }

        if name:
            body['serverName'] = name

        if cores:
            body['cores'] = str(cores)

        if ram:
            body['ram'] = str(ram)

        if availability_zone:
            body['availabilityZone'] = availability_zone.name

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    '''
    Datacenter Extension Functions
    '''

    def ex_create_datacenter(self, name, location):
        """
        Creates a datacenter.

        ProfitBricks has a concept of datacenters.
        These represent buckets into which you
        can place various compute resources.

        :param name: The DC name.
        :type name: : ``str``

        :param location: The DC region.
        :type location: : ``str``

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """
        action = 'createDataCenter'

        body = {'action': action,
                'request': 'true',
                'dataCenterName': name,
                'location': location.lower()
                }
        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        datacenters = self._to_datacenters(data)
        return datacenters[0]

    def ex_destroy_datacenter(self, datacenter):
        """
        Destroys a datacenter.

        :param datacenter: The DC you're destroying.
        :type datacenter: :class:`Datacenter`

        :rtype:     : ``bool``
        """
        action = 'deleteDataCenter'
        body = {'action': action,
                'dataCenterId': datacenter.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_describe_datacenter(self, datacenter_id):
        """
        Describes a datacenter.

        :param datacenter_id: The DC you are describing.
        :type datacenter_id: ``str``

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """

        action = 'getDataCenter'
        body = {'action': action,
                'dataCenterId': datacenter_id
                }

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        datacenters = self._to_datacenters(data)
        return datacenters[0]

    def ex_list_datacenters(self):
        """
        Lists all datacenters.

        :return:    ``list`` of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """
        action = 'getAllDataCenters'
        body = {'action': action}

        return self._to_datacenters(self.connection.request(
                                    action=action,
                                    data=body,
                                    method='POST').object)

    def ex_rename_datacenter(self, datacenter, name):
        """
        Update a datacenter.

        :param datacenter: The DC you are renaming.
        :type datacenter: :class:`Datacenter`

        :param name: The DC name.
        :type name: : ``str``

        :rtype:     : ``bool``
        """
        action = 'updateDataCenter'
        body = {'action': action,
                'request': 'true',
                'dataCenterId': datacenter.id,
                'dataCenterName': name
                }

        self.connection.request(action=action,
                                data=body,
                                method='POST').object

        return True

    def ex_clear_datacenter(self, datacenter):
        """
        Clear a datacenter.

        This removes all objects in a DC.

        :param datacenter: The DC you're clearing.
        :type datacenter: :class:`Datacenter`

        :rtype:     : ``bool``
        """
        action = 'clearDataCenter'
        body = {'action': action,
                'dataCenterId': datacenter.id
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    '''
    Network Interface Extension Functions
    '''

    def ex_list_network_interfaces(self):
        """
        Lists all network interfaces.

        :return:    ``list`` of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """
        action = 'getAllNic'
        body = {'action': action}

        return self._to_interfaces(
            self.connection.request(action=action,
                                    data=body,
                                    method='POST').object)

    def ex_describe_network_interface(self, network_interface):
        """
        Describes a network interface.

        :param network_interface: The NIC you wish to describe.
        :type network_interface: :class:`ProfitBricksNetworkInterface`

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """
        action = 'getNic'
        body = {'action': action,
                'nicId': network_interface.id
                }

        return self._to_interface(
            self.connection.request(
                action=action,
                data=body,
                method='POST').object.findall('.//return')[0])

    def ex_create_network_interface(self, node,
                                    lan_id=None, ip=None, nic_name=None,
                                    dhcp_active=True):
        """
        Creates a network interface.

        :param lan_id: The ID for the LAN.
        :type lan_id: : ``int``

        :param ip: The IP address for the NIC.
        :type ip: ``str``

        :param nic_name: The name of the NIC, e.g. PUBLIC.
        :type nic_name: ``str``

        :param dhcp_active: Set to false to disable.
        :type dhcp_active: ``bool``

        :return:    Instance of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """
        action = 'createNic'
        body = {'action': action,
                'request': 'true',
                'serverId': node.id,
                'dhcpActive': str(dhcp_active)
                }

        if lan_id:
            body['lanId'] = str(lan_id)
        else:
            body['lanId'] = str(1)

        if ip:
            body['ip'] = ip

        if nic_name:
            body['nicName'] = nic_name

        data = self.connection.request(action=action,
                                       data=body,
                                       method='POST').object
        interfaces = self._to_interfaces(data)
        return interfaces[0]

    def ex_update_network_interface(self, network_interface, name=None,
                                    lan_id=None, ip=None,
                                    dhcp_active=None):
        """
        Updates a network interface.

        :param lan_id: The ID for the LAN.
        :type lan_id: : ``int``

        :param ip: The IP address for the NIC.
        :type ip: ``str``

        :param name: The name of the NIC, e.g. PUBLIC.
        :type name: ``str``

        :param dhcp_active: Set to false to disable.
        :type dhcp_active: ``bool``

        :rtype:     : ``bool``
        """
        action = 'updateNic'
        body = {'action': action,
                'request': 'true',
                'nicId': network_interface.id
                }

        if name:
            body['nicName'] = name

        if lan_id:
            body['lanId'] = str(lan_id)

        if ip:
            body['ip'] = ip

        if dhcp_active is not None:
            body['dhcpActive'] = str(dhcp_active).lower()

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_destroy_network_interface(self, network_interface):
        """
        Destroy a network interface.

        :param network_interface: The NIC you wish to describe.
        :type network_interface: :class:`ProfitBricksNetworkInterface`

        :rtype:     : ``bool``
        """

        action = 'deleteNic'
        body = {'action': action,
                'nicId': network_interface.id}

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    def ex_set_inet_access(self, datacenter,
                           network_interface, internet_access=True):

        action = 'setInternetAccess'

        body = {'action': action,
                'dataCenterId': datacenter.id,
                'lanId': network_interface.extra['lan_id'],
                'internetAccess': str(internet_access).lower()
                }

        self.connection.request(action=action,
                                data=body, method='POST').object

        return True

    """
    Private Functions
    """

    def _to_datacenters(self, object):
        return [self._to_datacenter(
            datacenter) for datacenter in object.findall('.//return')]

    def _to_datacenter(self, datacenter):
        datacenter_id = datacenter.find('dataCenterId').text
        if ET.iselement(datacenter.find('dataCenterName')):
            datacenter_name = datacenter.find('dataCenterName').text
        else:
            datacenter_name = None
        version = datacenter.find('dataCenterVersion').text
        if ET.iselement(datacenter.find('provisioningState')):
            provisioning_state = datacenter.find('provisioningState').text
        else:
            provisioning_state = None
        if ET.iselement(datacenter.find('location')):
            location = datacenter.find('location').text
        else:
            location = None

        provisioning_state = self.PROVISIONING_STATE.get(provisioning_state,
                                                         NodeState.UNKNOWN)

        return Datacenter(id=datacenter_id,
                          name=datacenter_name,
                          version=version,
                          driver=self.connection.driver,
                          extra={'provisioning_state': provisioning_state,
                                 'location': location})

    def _to_images(self, object):
        return [self._to_image(image) for image in object.findall('.//return')]

    def _to_image(self, image):
        image_id = image.find('imageId').text
        image_name = image.find('imageName').text
        image_size = image.find('imageSize').text
        image_type = image.find('imageType').text
        os_type = image.find('osType').text
        public = image.find('public').text
        writeable = image.find('writeable').text

        if ET.iselement(image.find('cpuHotpluggable')):
            cpu_hotpluggable = image.find('cpuHotpluggable').text
        else:
            cpu_hotpluggable = None

        if ET.iselement(image.find('memoryHotpluggable')):
            memory_hotpluggable = image.find('memoryHotpluggable').text
        else:
            memory_hotpluggable = None

        if ET.iselement(image.find('location')):
            if image.find('region'):
                image_region = image.find('region').text
            else:
                image_region = None
        else:
            image_region = None

        return NodeImage(id=image_id,
                         name=image_name,
                         driver=self.connection.driver,
                         extra={'image_size': image_size,
                                'image_type': image_type,
                                'cpu_hotpluggable': cpu_hotpluggable,
                                'memory_hotpluggable': memory_hotpluggable,
                                'os_type': os_type,
                                'public': public,
                                'location': image_region,
                                'writeable': writeable})

    def _to_nodes(self, object):
        return [self._to_node(n) for n in object.findall('.//return')]

    def _to_node(self, node):
        """
        Convert the request into a node Node
        """
        ATTRIBUTE_NAME_MAP = {
            'dataCenterId': 'datacenter_id',
            'dataCenterVersion': 'datacenter_version',
            'serverId': 'node_id',
            'serverName': 'node_name',
            'cores': 'cores',
            'ram': 'ram',
            'internetAccess': 'internet_access',
            'provisioningState': 'provisioning_state',
            'virtualMachineState': 'virtual_machine_state',
            'creationTime': 'creation_time',
            'lastModificationTime': 'last_modification_time',
            'osType': 'os_type',
            'availabilityZone': 'availability_zone',
            'cpuHotPlug': 'cpu_hotpluggable',
            'ramHotPlug': 'memory_hotpluggable',
            'nicHotPlug': 'nic_hotpluggable',
            'discVirtioHotPlug': 'disc_virtio_hotplug',
            'discVirtioHotUnPlug': 'disc_virtio_hotunplug'
        }

        extra = {}
        for attribute_name, extra_name in ATTRIBUTE_NAME_MAP.items():
            elem = node.find(attribute_name)

            if ET.iselement(elem):
                value = elem.text
            else:
                value = None

            extra[extra_name] = value

        public_ips = []
        private_ips = []

        if ET.iselement(node.find('nics')):
            for nic in node.findall('.//nics'):
                n_elements = list(nic.findall('.//ips'))
                if len(n_elements) > 0:
                    ip = n_elements[0].text
                    if is_private_subnet(ip):
                        private_ips.append(ip)
                    else:
                        public_ips.append(ip)

        extra['provisioning_state'] = self.PROVISIONING_STATE.get(
            extra['provisioning_state'], NodeState.UNKNOWN)

        node_id = extra['node_id']
        node_name = extra['node_name']
        state = self.NODE_STATE_MAP.get(extra['virtual_machine_state'],
                                        NodeState.UNKNOWN)

        return Node(
            id=node_id,
            name=node_name,
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra=extra)

    def _to_volumes(self, object):
        return [self._to_volume(
            volume) for volume in object.findall('.//return')]

    def _to_volume(self, volume, node=None):
        ATTRIBUTE_NAME_MAP = {
            'dataCenterId': 'datacenter_id',
            'storageId': 'storage_id',
            'storageName': 'storage_name',
            'serverIds': 'server_id',
            'creationTime': 'creation_time',
            'lastModificationTime': 'last_modification_time',
            'provisioningState': 'provisioning_state',
            'size': 'size',
        }

        extra = {}
        for attribute_name, extra_name in ATTRIBUTE_NAME_MAP.items():
            elem = volume.find(attribute_name)

            if ET.iselement(elem):
                value = elem.text
            else:
                value = None

            extra[extra_name] = value

        if ET.iselement(volume.find('mountImage')):
            image_id = volume.find('mountImage')[0].text
            image_name = volume.find('mountImage')[1].text
        else:
            image_id = None
            image_name = None

        extra['image_id'] = image_id
        extra['image_name'] = image_name
        extra['size'] = int(extra['size']) if extra['size'] else 0
        extra['provisioning_state'] = \
            self.PROVISIONING_STATE.get(extra['provisioning_state'],
                                        NodeState.UNKNOWN)

        storage_id = extra['storage_id']
        storage_name = extra['storage_name']
        size = extra['size']

        return StorageVolume(
            id=storage_id,
            name=storage_name,
            size=size,
            driver=self.connection.driver,
            extra=extra)

    def _to_interfaces(self, object):
        return [self._to_interface(
            interface) for interface in object.findall('.//return')]

    def _to_interface(self, interface):
        ATTRIBUTE_NAME_MAP = {
            'nicId': 'nic_id',
            'nicName': 'nic_name',
            'serverId': 'server_id',
            'lanId': 'lan_id',
            'internetAccess': 'internet_access',
            'macAddress': 'mac_address',
            'dhcpActive': 'dhcp_active',
            'gatewayIp': 'gateway_ip',
            'provisioningState': 'provisioning_state',
            'dataCenterId': 'datacenter_id',
            'dataCenterVersion': 'datacenter_version'
        }

        extra = {}
        for attribute_name, extra_name in ATTRIBUTE_NAME_MAP.items():
            elem = interface.find(attribute_name)

            if ET.iselement(elem):
                value = elem.text
            else:
                value = None

            extra[extra_name] = value

        ips = []

        if ET.iselement(interface.find('ips')):
            for ip in interface.findall('.//ips'):
                ips.append(ip.text)

        extra['ips'] = ips

        nic_id = extra['nic_id']
        nic_name = extra['nic_name']
        state = self.PROVISIONING_STATE.get(extra['provisioning_state'],
                                            NodeState.UNKNOWN)

        return ProfitBricksNetworkInterface(
            id=nic_id,
            name=nic_name,
            state=state,
            extra=extra)

    def _to_location(self, data):

        return NodeLocation(id=data["region"],
                            name=data["region"],
                            country=data["country"],
                            driver=self.connection.driver)

    def _to_node_size(self, data):
        """
        Convert the PROFIT_BRICKS_GENERIC_SIZES into NodeSize
        """
        return NodeSize(id=data["id"],
                        name=data["name"],
                        ram=data["ram"],
                        disk=data["disk"],
                        bandwidth=None,
                        price=None,
                        driver=self.connection.driver,
                        extra={
                            'cores': data["cores"]})

    def _wait_for_datacenter_state(self, datacenter, state=NodeState.RUNNING,
                                   timeout=300, interval=5):
        """
        Private function that waits the datacenter to transition into the
        specified state.

        :return: Datacenter object on success.
        :rtype: :class:`.Datacenter`
        """
        wait_time = 0
        datacenter = self.ex_describe_datacenter(datacenter_id=datacenter.id)

        while (datacenter.extra['provisioning_state'] != state):
            datacenter = \
                self.ex_describe_datacenter(datacenter_id=datacenter.id)
            if datacenter.extra['provisioning_state'] == state:
                break

            if wait_time >= timeout:
                raise Exception('Datacenter didn\'t transition to %s state '
                                'in %s seconds' % (state, timeout))

            wait_time += interval
            time.sleep(interval)

        return datacenter

    def _create_new_datacenter_for_node(self, name, location):
        """
        Creates a Datacenter for a node.
        """
        dc_name = name + '-DC'

        if not location:
            loc = 'us/las'
        else:
            loc = location.id
        return self.ex_create_datacenter(name=dc_name, location=loc)

    def _wait_for_storage_volume_state(self, volume, state=NodeState.RUNNING,
                                       timeout=300, interval=5):
        """
        Wait for volume to transition into the specified state.

        :return: Volume object on success.
        :rtype: :class:`Volume`
        """
        wait_time = 0
        volume = self.ex_describe_volume(volume_id=volume.id)

        while (volume.extra['provisioning_state'] != state):
            volume = self.ex_describe_volume(volume_id=volume.id)
            if volume.extra['provisioning_state'] == state:
                break

            if wait_time >= timeout:
                raise Exception('Volume didn\'t transition to %s state '
                                'in %s seconds' % (state, timeout))

            wait_time += interval
            time.sleep(interval)

        return volume

    def _create_node_volume(self, ex_disk, image, password,
                            name, ex_datacenter=None, new_datacenter=None):

        volume_name = name + '-volume'

        if ex_datacenter:
            volume = self.create_volume(size=ex_disk,
                                        ex_datacenter=ex_datacenter,
                                        ex_image=image,
                                        ex_password=password,
                                        name=volume_name)
        else:
            volume = self.create_volume(size=ex_disk,
                                        ex_datacenter=new_datacenter,
                                        ex_image=image,
                                        ex_password=password,
                                        name=volume_name)

        return volume
