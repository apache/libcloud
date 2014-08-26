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
import httplib
import base64
import xml.etree.ElementTree as ET
import xml.dom.minidom
import json
import copy
import time

from xml.etree.ElementTree import tostring

from libcloud.utils.networking import is_private_subnet
from libcloud.utils.py3 import urlparse, b
from libcloud.compute.providers import Provider
from libcloud.common.base import ConnectionUserAndKey, XmlResponse, Response
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume
from libcloud.compute.base import KeyPair, UuidMixin
from libcloud.compute.types import NodeState
from libcloud.common.types import LibcloudError

__version__ = '1.0.0'

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
            raise MalformedResponseError("Failed to parse XML",
                                         body=self.body, driver=ProfitBricksNodeDriver)

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

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'text/xml'
        headers['Authorization'] = 'Basic %s' % (base64.b64encode(
            b('%s:%s' % (self.user_id, self.key))).decode('utf-8'))

        return headers

    def encode_data(self, data):
        soap_env = ET.Element('soapenv:Envelope',{
            'xmlns:soapenv' : 'http://schemas.xmlsoap.org/soap/envelope/',
            'xmlns:ws' : 'http://ws.api.profitbricks.com/'
            })
        soap_header = ET.SubElement(soap_env, 'soapenv:Header')
        soap_body = ET.SubElement(soap_env, 'soapenv:Body')
        soap_req_body = ET.SubElement(soap_body, 'ws:%s' % (data['action']))

        if 'request' in data.keys():
            soap_req_body = ET.SubElement(soap_req_body, 'request')
            for key, value in data.iteritems():
                if not (key == 'action' or key == 'request'):
                    child = ET.SubElement(soap_req_body, key)
                    child.text = value
        else:
            for key, value in data.iteritems():
                if not (key == 'action'):
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

    :param datacenter_version: Datacenter version.
    :type datacenter_version: ``str``


    Note: This class is ProfitBricks specific. 
    """
    def __init__(self, id, name, datacenter_version, driver, extra=None):
        self.id = str(id)
        if name is None:
            self.name = None
        else:
            self.name = name
        self.datacenter_version = datacenter_version
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return (('<Datacenter: id=%s, name=%s, datacenter_version=%s, driver=%s> ...>')
                % (self.id, self.name, self.datacenter_version, self.driver.name))

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
        return (('<ProfitBricksNetworkInterface: id=%s, name=%s')
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
        return (('<ExProfitBricksAvailabilityZone: name=%s>')
                % (self.name))

class ProfitBricksNodeDriver(NodeDriver):
    """
    Base ProfitBricks node driver. 
    """
    connectionCls = ProfitBricksConnection
    name = "ProfitBricks Node Provider"
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
        '1': {'region': 'us/las','country': 'USA'},
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

    You can configure disk size, core size, and memory size using the ex_
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

    """ Core Functions    
    """

    def list_sizes(self):
        """
        Lists all sizes

        :rtype: ``list`` of :class:`NodeSize`
        """
        sizes = []

        for key, values in self.PROFIT_BRICKS_GENERIC_SIZES.items():
            node_size = self._to_node_size(copy.deepcopy(values))
            sizes.append(node_size)

        return sizes

    def list_images(self):
        """
        List all images. 

        :rtype: ``list`` of :class:`NodeImage`
        """

        action = 'getAllImages'
        body = {'action': action}

        return self._to_images(self.connection.request(action=action,data=body,method='POST').object)

    def list_locations(self):
        """
        List all locations. 
        """        
        locations = []

        for key, values in self.REGIONS.items():
            location = self._to_location(copy.deepcopy(values))
            locations.append(location)

        return locations

    def list_nodes(self):
        """
        List all nodes.

        :rtype: ``list`` of :class:`Node` 
        """        
        action = 'getAllServers'
        body = {'action': action}

        return self._to_nodes(self.connection.request(action=action,data=body,method='POST').object)

    def reboot_node(self, node=None):
        """
        Reboots the node.

        :rtype: ``bool`` 
        """                
        action = 'resetServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,data=body,method='POST').object

        return True

    def create_node(self, name, image, size=None, volume=None, 
        datacenter=None, internet_access=True, 
        availability_zone=None, **kwargs):
        """
        Creates a node.

        image is optional as long as you pass ram, cores, and disk
        to the method. ProfitBricks allows you to adjust compute
        resources at a much more granular level.

        :param volume: If the volume already exists then pass this in.
        :type volume: :class:`StorageVolume`

        :param datacenter: If you've already created the DC then pass 
                           it in.
        :type datacenter: :class:`Datacenter`

        :param internet_access: Configure public Internet access.
        :type internet_access: : ``bool``

        :param availability_zone: The availability zone.
        :type availability_zone: class: `ProfitBricksAvailabilityZone`

        :param ram: The amount of ram required.
        :type ram: : ``int``

        :param cores: The number of cores required.
        :type cores: : ``int``

        :param disk: The amount of disk required.
        :type disk: : ``int``

        :return:    Instance of class ``Node``
        :rtype:     :class:`Node`
        """                


        if not datacenter:
            '''
            We generate a name from the server name passed into the function.
            '''

            datacenter_name = name + "-DC"
            dc = self.ex_create_datacenter(name=datacenter_name, location="us/las")
            datacenter_id = dc[0].id

            dc_operation_status = self.ex_describe_datacenter(dc[0])

            timeout = 60 * 5
            waittime = 0
            interval = 5

            while dc_operation_status[0].extra['provisioning_state'] == 3 and waittime < timeout:
                dc_operation_status = self.ex_describe_volume(volume[0])
                if dc_operation_status[0].extra['provisioning_state'] == 0:
                    break

                waittime += interval
                time.sleep(interval)
        else:
            datacenter_id = datacenter.id

        if not size:
            if 'ram' not in kwargs:
                raise ValueError("You need to either pass a ' \
                    'NodeSize or specify 'ram' as an extra parameter.")
            if 'cores' not in kwargs:
                raise ValueError("You need to either pass a ' \
                    'NodeSize or specify 'cores' as an extra parameter.")

        if not volume:
            if not size:
                if 'disk' not in kwargs:
                    raise ValueError("You need to either pass a ' \
                        'StorageVolume', a 'NodeSize', or specify ' \
                        'disk' as an extra parameter.")

        '''
        You can override the suggested sizes by passing in unique
        values for ram, cores, and disk allowing you to size it
        for your specific use. 
        '''

        if 'disk' in kwargs:
            disk = kwargs['disk']
        else:
            disk = size.disk

        if 'ram' in kwargs:
            ram = kwargs['ram'] 
        else:
            ram = size.ram

        if 'cores' in kwargs:
            cores = kwargs['cores']
        else:
            cores = size.extra['cores']

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
            volume_name = name + "-volume"

            if datacenter:
                volume = self.create_volume(size=disk, 
                    ex_datacenter=datacenter, ex_image=image,
                    ex_password=password, name=volume_name
                    )
            else:
                volume = self.create_volume(size=disk, 
                    ex_datacenter=dc[0], ex_image=image,
                    ex_password=password, name=volume_name
                    )

            storage_id = volume[0].id        
        else:
            if datacenter:
                datacenter_id = datacenter.id
            else:
                datacenter_id = volume.extra['datacenter_id']

            storage_id = volume.id

        action = 'createServer'
        body = {'action': action,
                'request': 'true',
                'serverName': name,
                'cores': str(cores),
                'ram': str(ram),
                'bootFromStorageId': storage_id,
                'internetAccess': str(internet_access).lower(),
                'dataCenterId': datacenter_id
                }

        if availability_zone:
            body['availabilityZone'] = availability_zone.name

        operation_status = self.ex_describe_volume(volume[0])

        timeout = 60 * 5
        waittime = 0
        interval = 5

        while operation_status[0].extra['provisioning_state'] == 3 and waittime < timeout:
            operation_status = self.ex_describe_volume(volume[0])
            if operation_status[0].extra['provisioning_state'] == 0:
                break

            waittime += interval
            time.sleep(interval)

        return self._to_nodes(self.connection.request(action=action,data=body,method='POST').object)

    def destroy_node(self, node, remove_attached_disks=None):
        """
        Destroys a node.

        :param node: The node you wish to destroy.
        :type volume: :class:`Node`

        :param remove_attached_disks: True to destory all attached volumes.
        :type remove_attached_disks: : ``bool``

        :rtype:     : ``bool``
        """     
        action = 'deleteServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,data=body,method='POST').object

        return True

    """ Volume Functions
    """

    def list_volumes(self):
        """
        Lists all voumes.
        """
        action = 'getAllStorages'
        body = {'action': action}

        return self._to_volumes(self.connection.request(action=action,data=body,method='POST').object)

    def attach_volume(self, node, volume, device=None, bus_type=None):
        """
        Attaches a volume.

        :param volume: The volume you're attaching..
        :type volume: :class:`StorageVolume`

        :param node: The node to which you're attaching the volume.
        :type node: :class:`Node`

        :param device: The device number order.
        :type device: : ``int``

        :param bus_type: Bus type. Either IDE or VIRTIO (def).
        :type bus_type: ``str``

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """     
        action = 'connectStorageToServer'
        body = {'action': action,
                'request': 'true',
                'storageId': volume.id,
                'serverId': node.id,
                'busType': bus_type,
                'deviceNumber': str(device)
                }

        self.connection.request(action=action,data=body,method='POST').object

        return True

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

        return self._to_volumes(self.connection.request(action=action,data=body,method='POST').object)

    def detach_volume(self, node, volume):
        """
        Detaches a volume.

        :param volume: The volume you're attaching..
        :type volume: :class:`StorageVolume`

        :rtype:     :``bool``
        """  
        action = 'disconnectStorageFromServer'
        body = {'action': action,
                'storageId': volume.id,
                'serverId': node.id
                }

        self.connection.request(action=action,data=body,method='POST').object

        return True

    def destroy_volume(self, volume):
        """
        Destroys a volume.

        :param volume: The volume you're attaching..
        :type volume: :class:`StorageVolume`

        :rtype:     : ``bool``
        """  
        action = 'deleteStorage'
        body = {'action': action,
                'storageId': volume.id}

        self.connection.request(action=action,data=body,method='POST').object

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

        self.connection.request(action=action,data=body,method='POST').object
        
        return True

    def ex_describe_volume(self, volume):
        """
        Describes a volume.

        :param volume: The volume you're attaching..
        :type volume: :class:`StorageVolume`

        :return:    Instance of class ``StorageVolume``
        :rtype:     :class:`StorageVolume`
        """  
        action = 'getStorage'
        body = {'action': action, 
                'storageId': volume.id
                }

        return self._to_volumes(self.connection.request(action=action,data=body,method='POST').object)

    """ Extension Functions
    """

    ''' Server Extension Functions
    '''
    def ex_stop_node(self, node):
        """
        Stops a node.

        This also dealloctes the public IP space.

        :param node: The node you wish to halt.
        :type node: :class:`Node`

        :rtype:     : ``bool``
        """  
        action = 'stopServer'
        body = {'action': action,
                'serverId': node.id
                }

        self.connection.request(action=action,data=body,method='POST').object

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

        self.connection.request(action=action,data=body,method='POST').object

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

        return self._to_nodes(self.connection.request(action=action,data=body,method='POST').object)

    def ex_update_node(self, node, name=None, cores=None, 
        ram=None, availability_zone=None):
        """
        Updates a node.

        :param cores: The number of CPUs the node should have.
        :type device: : ``int``

        :param ram: The amount of ram the machine should have.
        :type ram: : ``int``

        :param availability_zone: Update the availability zone.
        :type availability_zone: :class:`ProfitBricksAvailabilityZone`

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

        self.connection.request(action=action,data=body,method='POST').object

        return True

    ''' Datacenter Extension Functions
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

        if not name:
            raise ValueError("You must provide a datacenter name.")

        return self._to_datacenters(self.connection.request(action=action,data=body,method='POST').object)

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

        request = self.connection.request(action=action,data=body,method='POST').object

        return True

    def ex_describe_datacenter(self, datacenter):
        """
        Describes a datacenter.

        :param datacenter: The DC you're destroying.
        :type datacenter: :class:`Datacenter`

        :return:    Instance of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """  

        action = 'getDataCenter'
        body = {'action': action,
                'dataCenterId': datacenter.id
                }
        
        return self._to_datacenters(self.connection.request(action=action,data=body,method='POST').object)

    def ex_list_datacenters(self):
        """
        Lists all datacenters.

        :return:    ``list`` of class ``Datacenter``
        :rtype:     :class:`Datacenter`
        """  
        action = 'getAllDataCenters'
        body = {'action': action}

        return self._to_datacenters(self.connection.request(action=action,data=body,method='POST').object)

    def ex_update_datacenter(self, datacenter, name):
        """
        Update a datacenter.

        :param datacenter: The DC you're destroying.
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

        request = self.connection.request(action=action,data=body,method='POST').object

        return True

    def ex_clear_datacenter(self, datacenter):
        """
        Clear a datacenter.

        This removes all objects in a DC.

        :param datacenter: The DC you're destroying.
        :type datacenter: :class:`Datacenter`

        :rtype:     : ``bool``
        """  
        action = 'clearDataCenter'
        body = {'action': action,
                'dataCenterId': datacenter.id
                }

        self.connection.request(action=action,data=body,method='POST').object
        
        return True

    ''' Network Interface Extension Functions
    '''

    def ex_list_network_interfaces(self):
        """
        Lists all network interfaces.

        :return:    ``list`` of class ``ProfitBricksNetworkInterface``
        :rtype:     :class:`ProfitBricksNetworkInterface`
        """  
        action = 'getAllNic'
        body = {'action': action}

        return self._to_interfaces(self.connection.request(action=action,data=body,method='POST').object)

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

        return self._to_interfaces(self.connection.request(action=action,data=body,method='POST').object)

    def ex_create_network_interface(self, node, 
        lan_id=None, ip=None, nic_name=None, dhcp_active=True):
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

        return self._to_interfaces(self.connection.request(action=action,data=body,method='POST').object)

    def ex_update_network_interface(self, network_interface, name=None, 
        lan_id=None, ip=None, dhcp_active=None):
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

        self.connection.request(action=action,data=body,method='POST').object

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

        self.connection.request(action=action,data=body,method='POST').object

        return True

    def ex_set_inet_access(self, datacenter, network_interface, internet_access=True):
        # Results in strange behavior within the provider, so for now
        # this is commented out.

        action = 'setInternetAccess'

        body = {'action': action,
                'dataCenterId': datacenter.id,
                'lanId': network_interface.extra['lan_id'],
                'internetAccess': str(internet_access).lower()
                }

        self.connection.request(action=action,data=body,method='POST').object

        return True

    """ Snapshot Functions Not Implemented
    """
    def create_volume_snapshot(self):
        raise NotImplementedError(
            'While supported, this is '
            'not implemented at this time.')

    """Private Functions
    """

    def _to_datacenters(self, object):
        return [self._to_datacenter(datacenter) for datacenter in object.findall('.//return')]

    def _to_datacenter(self, datacenter):
        elements = list(datacenter.iter())
        datacenter_id = elements[0].find('dataCenterId').text
        if ET.iselement(elements[0].find('dataCenterName')):
            datacenter_name = elements[0].find('dataCenterName').text
        else:
            datacenter_name = None
        datacenter_version = elements[0].find('dataCenterVersion').text
        if ET.iselement(elements[0].find('provisioningState')):
            provisioning_state = elements[0].find('provisioningState').text
        else:
            provisioning_state = None
        if ET.iselement(elements[0].find('location')):
            location = elements[0].find('location').text
        else:
            location = None

        return Datacenter(id=datacenter_id,
                        name=datacenter_name,
                        datacenter_version=datacenter_version,
                        driver=self.connection.driver,
                        extra={
                            'provisioning_state': provisioning_state,
                            'location': location}
                        )

    def _to_images(self, object):
        return [self._to_image(image) for image in object.findall('.//return')]

    def _to_image(self, image):
        elements = list(image.iter())
        image_id = elements[0].find('imageId').text
        image_name = elements[0].find('imageName').text
        image_size = elements[0].find('imageSize').text
        image_type = elements[0].find('imageType').text
        os_type = elements[0].find('osType').text
        public = elements[0].find('public').text
        writeable = elements[0].find('writeable').text

        if ET.iselement(elements[0].find('cpuHotpluggable')):
            cpu_hotpluggable = elements[0].find('cpuHotpluggable').text
        else:
            cpu_hotpluggable = None

        if ET.iselement(elements[0].find('memoryHotpluggable')):
            memory_hotpluggable = elements[0].find('memoryHotpluggable').text
        else:
            memory_hotpluggable = None

        if ET.iselement(elements[0].find('location')):
            image_region = elements[0].find('region').text
        else:
            image_region = None

        return NodeImage(id=image_id,
                        name=image_name,
                        driver=self.connection.driver,
                        extra={
                                'image_size': image_size,
                                'image_type': image_type,
                                'cpu_hotpluggable': cpu_hotpluggable,
                                'memory_hotpluggable': memory_hotpluggable,
                                'os_type': os_type,
                                'public': public,
                                'location': image_region,
                                'writeable': writeable
                            }
                        )

    def _to_nodes(self, object):
        return [self._to_node(n) for n in object.findall('.//return')]

    def _to_node(self, node):
        """
        Convert the request into a node Node
        """
        elements = list(node.iter())
        datacenter_id = elements[0].find('dataCenterId').text
        datacenter_version = elements[0].find('dataCenterVersion').text
        node_id = elements[0].find('serverId').text

        # all optional as they don't appear in create responses.
        if ET.iselement(elements[0].find('serverName')):
            node_name = elements[0].find('serverName').text
        else:
            node_name = None

        if ET.iselement(elements[0].find('cores')):
            cores = elements[0].find('cores').text
        else:
            cores = None

        if ET.iselement(elements[0].find('ram')):
            ram = elements[0].find('ram').text
        else:
            ram = None

        if ET.iselement(elements[0].find('internetAccess')):
            internet_access = elements[0].find('internetAccess').text
        else:
            internet_access = None

        if ET.iselement(elements[0].find('provisioningState')):
            provisioning_state = elements[0].find('provisioningState').text
        else:
            provisioning_state = None

        if ET.iselement(elements[0].find('virtualMachineState')):
            virtual_machine_state = elements[0].find('virtualMachineState').text
        else:
            virtual_machine_state = None

        if ET.iselement(elements[0].find('creationTime')):
            creation_time = elements[0].find('creationTime').text
        else:
            creation_time = None

        if ET.iselement(elements[0].find('lastModificationTime')):
            last_modification_time = elements[0].find('lastModificationTime').text
        else:
            last_modification_time = None

        if ET.iselement(elements[0].find('osType')):
            os_type = elements[0].find('osType').text
        else:
            os_type = None

        if ET.iselement(elements[0].find('availabilityZone')):
            availability_zone = elements[0].find('availabilityZone').text
        else:
            availability_zone = None

        public_ips = []
        private_ips = []

        if ET.iselement(elements[0].find('nics')):
            for nic in elements[0].findall('.//nics'):
                n_elements = list(nic.iter())
                if ET.iselement(n_elements[0].find('ips')):
                    ip = n_elements[0].find('ips').text
                    if is_private_subnet(ip):
                        private_ips.append(ip)
                    else:
                        public_ips.append(ip)

        if ET.iselement(elements[0].find('cpuHotPlug')):
            cpu_hotpluggable = elements[0].find('cpuHotPlug').text
        else:
            cpu_hotpluggable = None

        if ET.iselement(elements[0].find('ramHotPlug')):
            memory_hotpluggable = elements[0].find('ramHotPlug').text
        else:
            memory_hotpluggable = None

        if ET.iselement(elements[0].find('nicHotPlug')):
            nic_hotpluggable = elements[0].find('nicHotPlug').text
        else:
            nic_hotpluggable = None

        if ET.iselement(elements[0].find('nicHotUnPlug')):
            nic_hot_unpluggable = elements[0].find('nicHotUnPlug').text
        else:
            nic_hot_unpluggable = None

        if ET.iselement(elements[0].find('discVirtioHotPlug')):
            disc_virtio_hotplug = elements[0].find('discVirtioHotPlug').text
        else:
            disc_virtio_hotplug = None

        if ET.iselement(elements[0].find('discVirtioHotUnPlug')):
            disc_virtio_hotunplug = elements[0].find('discVirtioHotUnPlug').text
        else:
            disc_virtio_hotunplug = None

        return Node(
            id=node_id,
            name=node_name,
            state=self.NODE_STATE_MAP.get(
                virtual_machine_state, NodeState.UNKNOWN),
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra={
                'datacenter_id': datacenter_id,
                'datacenter_version': datacenter_version,
                'provisioning_state': self.PROVISIONING_STATE.get(
                    provisioning_state, NodeState.UNKNOWN),
                'creation_time': creation_time,
                'last_modification_time': last_modification_time,
                'os_type': os_type,
                'ram': ram,
                'cores': cores,
                'availability_zone': availability_zone,
                'internet_access': internet_access,
                'cpu_hotpluggable': cpu_hotpluggable,
                'memory_hotpluggable': memory_hotpluggable,
                'nic_hotpluggable': nic_hotpluggable,
                'nic_hot_unpluggable': nic_hot_unpluggable,
                'disc_virtio_hotplug': disc_virtio_hotplug,
                'disc_virtio_hotunplug': disc_virtio_hotunplug
                })

    def _to_volumes(self, object):
        return [self._to_volume(volume) for volume in object.findall('.//return')]

    def _to_volume(self, volume, node=None):
        elements = list(volume.iter())

        # if node:
        #     if node.id == elements[0].find('server_id').text:

        datacenter_id = elements[0].find('dataCenterId').text
        datacenter_version = elements[0].find('dataCenterVersion').text
        storage_id = elements[0].find('storageId').text

        if ET.iselement(elements[0].find('storageName')):
            storage_name = elements[0].find('storageName').text
        else:
            storage_name = None

        if ET.iselement(elements[0].find('serverIds')):
            server_id = elements[0].find('serverIds').text
        else:
            server_id = None

        if ET.iselement(elements[0].find('creationTime')):
            creation_time = elements[0].find('creationTime').text
        else:
            creation_time = None

        if ET.iselement(elements[0].find('lastModificationTime')):
            last_modification_time = elements[0].find('lastModificationTime').text
        else:
            last_modification_time = None

        if ET.iselement(elements[0].find('provisioningState')):
            provisioning_state = elements[0].find('provisioningState').text
        else:
            provisioning_state = None

        if ET.iselement(elements[0].find('size')):
            size = elements[0].find('size').text
        else:
            size = 0

        if ET.iselement(elements[0].find('mountImage')):
            image_id = elements[0].find('mountImage')[0].text
        else:
            image_id = None

        if ET.iselement(elements[0].find('mountImage')):
            image_name = elements[0].find('mountImage')[1].text
        else:
            image_name = None

        return StorageVolume(id=storage_id, 
                            name=storage_name,
                            size=int(size), 
                            driver=self.connection.driver,
                            extra={
                                    'datacenter_id': datacenter_id,
                                    'creation_time': creation_time,
                                    'last_modification_time': last_modification_time,
                                    'provisioning_state': self.PROVISIONING_STATE.get(
                                        provisioning_state, NodeState.UNKNOWN),
                                    'server_id': server_id,
                                    'image_id': image_id,
                                    'image_name': image_name
                                }
                            )

    def _to_interfaces(self, object):
        return [self._to_interface(interface) for interface in object.findall('.//return')]

    def _to_interface(self, interface):
        elements = list(interface.iter())

        nic_id = elements[0].find('nicId').text
        
        if ET.iselement(elements[0].find('nicName')):
            nic_name = elements[0].find('nicName').text
        else:
            nic_name = None

        if ET.iselement(elements[0].find('serverId')):
            server_id = elements[0].find('serverId').text
        else:
            server_id = None

        if ET.iselement(elements[0].find('lanId')):
            lan_id = elements[0].find('lanId').text
        else:
            lan_id = None

        if ET.iselement(elements[0].find('internetAccess')):
            internet_access = elements[0].find('internetAccess').text
        else:
            internet_access = None

        if ET.iselement(elements[0].find('macAddress')):
            mac_address = elements[0].find('macAddress').text
        else:
            mac_address = None

        if ET.iselement(elements[0].find('dhcpActive')):
            dhcp_active = elements[0].find('dhcpActive').text
        else:
            dhcp_active = None

        if ET.iselement(elements[0].find('gatewayIp')):
            gateway_ip = elements[0].find('gatewayIp').text
        else:
            gateway_ip = None

        if ET.iselement(elements[0].find('provisioningState')):
            provisioning_state = elements[0].find('provisioningState').text
        else:
            provisioning_state = None

        if ET.iselement(elements[0].find('dataCenterId')):
            datacenter_id = elements[0].find('dataCenterId').text
        else:
            datacenter_id = None

        if ET.iselement(elements[0].find('dataCenterVersion')):
            datacenter_version = elements[0].find('dataCenterVersion').text
        else:
            datacenter_version = None

        ips = []

        if ET.iselement(elements[0].find('ips')):
            for ip in elements[0].findall('.//ips'):
                ip = elements[0].find('ips').text
                ips.append(ip)
                
        return ProfitBricksNetworkInterface(id=nic_id, 
                            name=nic_name,
                            state=self.PROVISIONING_STATE.get(
                                        provisioning_state, NodeState.UNKNOWN),
                            extra={
                                    'datacenter_id': datacenter_id,
                                    'datacenter_version': datacenter_version,
                                    'server_id': server_id,
                                    'lan_id': lan_id,
                                    'internet_access': internet_access,
                                    'mac_address': mac_address,
                                    'dhcp_active': dhcp_active,
                                    'gateway_ip': gateway_ip,
                                    'ips': ips
                                }
                            )

    def _to_location(self, data):

        return NodeLocation(
            id=data["region"],
            name=data["region"],
            country=data["country"],
            driver=self.connection.driver)

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
            extra={
                'cores' : data["cores"]
            })
