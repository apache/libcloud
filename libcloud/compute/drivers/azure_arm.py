import json
import sys

import time

from libcloud.common.azure import AzureResourceManagerConnection, AzureRedirectException
from libcloud.common.exceptions import RateLimitReachedError
from libcloud.compute.base import NodeDriver, NodeLocation, NodeSize, Node
from libcloud.compute.drivers.azure import AzureHTTPRequest
from libcloud.compute.drivers.vcloud import urlparse
from libcloud.compute.types import Provider, NodeState

from libcloud.utils.py3 import urlquote as url_quote, ensure_string

AZURE_RESOURCE_MANAGEMENT_HOST = 'management.azure.com'
DEFAULT_API_VERSION = '2016-07-01'
MAX_RETRIES = 5
if sys.version_info < (3,):
    _unicode_type = unicode

    def _str(value):
        if isinstance(value, unicode):
            return value.encode('utf-8')

        return str(value)
else:
    _str = str
    _unicode_type = str


class AzureARMNodeDriver(NodeDriver):
    connectionCls = AzureResourceManagerConnection
    name = 'Azure Virtual machines'
    website = 'http://azure.microsoft.com/en-us/services/virtual-machines/'
    type = Provider.AZURE_ARM

    def __init__(self, subscription_id=None, token=None, **kwargs):
        """
        subscription_id contains the Azure subscription id in the form of GUID
        key_file contains the Azure X509 certificate in .pem form
        """
        self.subscription_id = subscription_id
        self.token = token
        self.follow_redirects = kwargs.get('follow_redirects', True)
        super(AzureARMNodeDriver, self).__init__(
            self.subscription_id,
            self.token,
            secure=True,
            **kwargs
        )

    def list_locations(self, resource_group):
        """
        Lists all locations

        :rtype: ``list`` of :class:`NodeLocation`
        """
        path = '%slocations' % self._default_path_prefix
        json_response = self._perform_get(path)
        raw_data = json_response.parse_body()
        return [self._to_location(x) for x in raw_data['value']]

    def list_sizes(self, location):
        """
        List all image sizes available for location
        """
        path = '%sproviders/Microsoft.Compute/locations/%s/vmSizes' % (self._default_path_prefix, location)
        json_response = self._perform_get(path, api_version='2016-03-30')
        raw_data = json_response.parse_body()
        return [self._to_size(x) for x in raw_data['value']]

    def list_nodes(self, resource_group):
        """
        List all nodes in a resource group
        """
        path = '%sresourceGroups/%s/providers/Microsoft.Compute/virtualmachines' % \
               (self._default_path_prefix, resource_group)
        json_response = self._perform_get(path, api_version='2016-03-30')
        raw_data = json_response.parse_body()
        return [self._to_node(x) for x in raw_data['value']]

    def create_node(self, name, location, node_size,
                    ex_resource_group_name,
                    ex_storage_account_name,
                    ex_virtual_network_name,
                    ex_subnet_name,
                    ex_admin_username,
                    ex_marketplace_image,
                    ex_os_disk_size=30,
                    ex_data_disk_size=None,
                    ex_availability_set=None,
                    ex_public_key=None):
        """
        Create Azure Virtual Machine using Resource Management model.

        For now this only creates a Linux machine, always default to public IP address, and only support 1 data disk.

        It also assumes you have created these things:
        - A resource group
        - A storage account
        - A virtual network
        - A valid subnet inside the virtual network

        @inherits: :class:`NodeDriver.create_node`

        :keyword     name: Required. The name given to this node
        :type        name:  `str`

        :keyword     location: Required.  The location of the node to create
        :type        location: `NodeLocation`

        :keyword     node_size: Required.  The size of the node to create
        :type        node_size: `NodeSize`

        :keyword     ex_resource_group_name: Required.
                     The name of the resource group the node belongs to
        :type        ex_resource_group_name: `str`

        :keyword     ex_storage_account_name: Required.
                     The name of the storage account the disks on the node
                                              belongs to
        :type        ex_storage_account_name: `str`

        :keyword     ex_virtual_network_name: Required.
                     The name of the virtual network the node would be connected to
        :type        ex_virtual_network_name: `str`

        :keyword     ex_subnet_name: Required.
                     The name of the subnet inside `ex_virtual_network_name` the node would
                     be connected to
        :type        ex_subnet_name: `str`

        :keyword     ex_admin_username: Required.
                     The name of the default admin user on the node
        :type        ex_admin_username: `str`

        :keyword     ex_marketplace_image: Required.
                     The image from market place to be used for setting up the OS disk. For example:
                     ```
                     ubuntu_image = {
                         'sku': '14.04.5-LTS',
                         'publisher': 'canonical',
                         'offer': 'ubuntuserver',
                         'version': '14.04.201608091'
                     }
                     ```
        :type        ex_marketplace_image: `dict`

        :keyword     ex_os_disk_size: Optional.
                     The size of the OS disk to be attached in GB. Defaults to 30
        :type        ex_os_disk_size: `int`

        :keyword     ex_data_disk_size: Optional.
                     The size of the data disk to be attached in GB. Will not be created if passed nothing
        :type        ex_data_disk_size: `int`

        :keyword     ex_availability_set: Optional.
                     The availability set that the node lives in
        :type        ex_availability_set: `int`

        :keyword     ex_public_key: Optional.
                     The content of the SSH public key to be deployed on the box
        :type        ex_public_key: `str`
        """
        # Create the public IP address
        public_ip_address = self._create_public_ip_address(name, ex_resource_group_name, location.id)

        # Create the network interface card with that public IP address
        nic = self._create_network_interface(name, ex_resource_group_name, location.id,
                                             ex_virtual_network_name, ex_subnet_name,
                                             public_ip_address['name'])
        # Create the machine
        node_payload = {
            'name': name,
            'location': location.id,
        }

        os_disk_name = '%s-os-disk' % name

        node_payload['properties'] = {
            'hardwareProfile': {
                'vmSize': node_size.id
            },
            'storageProfile': {
                'imageReference': ex_marketplace_image,
                'osDisk': {
                    'name': os_disk_name,
                    'vhd': {
                        'uri': 'http://%s.blob.core.windows.net/vhds/%s.vhd' % (ex_storage_account_name, os_disk_name)
                    },
                    'caching': 'ReadWrite',
                    'createOption': 'fromImage',
                    'diskSizeGB': ex_os_disk_size
                }
            },
            'osProfile': {
                'computerName': name,
                'adminUsername': ex_admin_username,
                'linuxConfiguration': {
                    'disablePasswordAuthentication': True,
                    'ssh': {
                        'publicKeys': [
                            {
                                'path': '/home/%s/.ssh/authorized_keys' % ex_admin_username,
                                'keyData': ex_public_key
                            }
                        ]
                    }
               }
            },
            'networkProfile': {
                'networkInterfaces': [
                    {
                        'id': nic['id'],
                        'properties': {
                            'primary': True
                        }
                    }
                ]
            }
        }

        if ex_data_disk_size:
            data_disk_name = '%s-data-disk' % name
            # Attach an empty data disk if value this is given
            node_payload['properties']['storageProfile']['dataDisks'] = [
                {
                    'name': data_disk_name,
                    'diskSizeGB': ex_data_disk_size,
                    'lun': 0,
                    'vhd': {
                        'uri': 'http://%s.blob.core.windows.net/vhds/%s.vhd' % (ex_storage_account_name, data_disk_name)
                    },
                    'caching': 'ReadWrite',
                    'createOption': 'empty'
                }
            ]

        if ex_availability_set:
            availability_set_id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/availabilitySets/%s' % \
                               (self.subscription_id, ex_resource_group_name, ex_availability_set)
            node_payload['properties']['availabilitySet'] = {
                'id': availability_set_id
            }

        path = '%sresourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s' % \
               (self._default_path_prefix, ex_resource_group_name, name)

        output = self._perform_put(path, node_payload, api_version='2016-03-30')
        output = output.parse_body()

        if 'error' in output:
            raise Exception('Error encountered: %s' % output['error'])

        return Node(
            id=name,
            name=name,
            state=NodeState.PENDING,
            public_ips=[],
            private_ips=[],
            driver=self.connection.driver,
        )

    def _create_network_interface(self, node_name, resource_group_name, location,
                                  virtual_network_name, subnet_name,
                                  public_ip_address_name):
        nic_name = '%s-nic' % node_name
        payload = {
            'location': location,
            'properties': {
                'ipConfigurations': [{
                    'name': '%s-ip' % node_name,
                    'properties': {
                        'subnet': {
                            'id': '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualNetworks/%s/subnets/%s' %
                                  (self.subscription_id, resource_group_name, virtual_network_name, subnet_name)
                        },
                        'privateIPAllocationMethod': 'Dynamic',
                        'publicIPAddress': {
                            'id': '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/publicIPAddresses/%s' %
                                  (self.subscription_id, resource_group_name, public_ip_address_name)
                        }
                    }
                }]
            }
        }
        path = '%sresourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s' % \
               (self._default_path_prefix, resource_group_name, nic_name)
        output = self._perform_put(path, payload)
        return output.parse_body()

    def _create_public_ip_address(self, node_name, resource_group_name, location):
        public_ip_address_name = '%s-public-ip' % node_name
        payload = {
            'location': location,
            'properties': {
                'publicIPAllocationMethod': 'Dynamic',
                'publicIPAddressVersion': "IPv4",
                'idleTimeoutInMinutes': 5,
                "dnsSettings": {
                    "domainNameLabel": node_name
                }
            }
        }
        path = '%sresourceGroups/%s/providers/Microsoft.Network/publicIPAddresses/%s' % \
               (self._default_path_prefix, resource_group_name, public_ip_address_name)

        output = self._perform_put(path, payload)
        return output.parse_body()

    def _to_node(self, node_data):
        """
        Take the azure raw data and turn into a Node class
        """
        network_interfaces = node_data.get('properties', {}).get('networkProfile', {}).get('networkInterfaces', [])
        network_interface_urls = ['%s' % x.get('id') for x in network_interfaces if x.get('id')]
        public_ips = []
        private_ips = []
        for network_interface_url in network_interface_urls:
            _public_ips, _private_ips = self._get_public_and_private_ips(network_interface_url)
            public_ips.extend(_public_ips)
            private_ips.extend(_private_ips)

        provisioning_state = node_data.get('properties', {}).get('provisioningState')
        node_state = NodeState.RUNNING if provisioning_state == 'Succeeded' else NodeState.PENDING

        return Node(
            id=node_data.get('name'),
            name=node_data.get('name'),
            state=node_state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra={
                'provisioningState': node_data.get('properties', {}).get('provisioningState')
            }
        )

    def _get_public_and_private_ips(self, network_interace_url):
        """
        Get public and and private ips of the virtual machine by following the urls provided.
        :param network_interace_url:
        :return:
        """
        json_response = self._perform_get(network_interace_url)
        raw_data = json_response.parse_body()
        ip_configurations = raw_data.get('properties', {}).get('ipConfigurations', [])
        public_ips = []
        private_ips = []
        for ip_configuration in ip_configurations:
            private_ips.append(ip_configuration['properties']['privateIPAddress'])
            public_ips.append(self._get_public_ip(ip_configuration['properties']['publicIPAddress']['id']))
        return public_ips, private_ips

    def _get_public_ip(self, public_ip_url):
        """
        Using the public ip url we can query the azure api and get the public ip adrewss
        """
        json_response = self._perform_get(public_ip_url)
        raw_data = json_response.parse_body()
        return raw_data.get('properties', {}).get('ipAddress', None)

    def _to_location(self, location_data):
        """
        Convert the data from a Azure response object into a location. Commented out
        code is from the classic Azure driver, not sure if we need those fields.
        """
        return NodeLocation(
            id=location_data.get('name'),
            name=location_data.get('name'),
            country=location_data.get('display_name'),
            driver=self.connection.driver,
            # available_services=data.available_services,
            # virtual_machine_role_sizes=vm_role_sizes
        )

    def _to_size(self, size_data):
        """
        Convert the data from a Azure response object into a size

        Sample raw data:
        {
            'maxDataDiskCount': 32,
            'memoryInMB': 114688,
            'name': 'Standard_D14',
            'numberOfCores': 16,
            'osDiskSizeInMB': 1047552,
            'resourceDiskSizeInMB': 819200
        }
        """
        return NodeSize(
            id=size_data.get('name'),
            name=size_data.get('name'),
            ram=size_data.get('memoryInMB'),
            disk=size_data.get('osDiskSizeInMB'),
            driver=self,
            price=-1,
            bandwidth=-1,
            extra=size_data
        )

    @property
    def _default_path_prefix(self):
        """Everything starts with the subscription prefix"""
        return '/subscriptions/%s/' % self.subscription_id

    def _perform_put(self, path, body, api_version=None):
        request = AzureHTTPRequest()
        request.method = 'PUT'
        request.host = AZURE_RESOURCE_MANAGEMENT_HOST
        request.path = path
        request.body = ensure_string(self._get_request_body(body))
        request.path, request.query = self._update_request_uri_query(request, api_version)
        return self._perform_request(request)

    def _get_request_body(self, request_body):
        if request_body is None:
            return b''

        if isinstance(request_body, dict):
            return json.dumps(request_body)

        if isinstance(request_body, bytes):
            return request_body

        if isinstance(request_body, _unicode_type):
            return request_body.encode('utf-8')

        request_body = str(request_body)
        if isinstance(request_body, _unicode_type):
            return request_body.encode('utf-8')

        return request_body

    def _perform_get(self, path, api_version=None):
        request = AzureHTTPRequest()
        request.method = 'GET'
        request.host = AZURE_RESOURCE_MANAGEMENT_HOST
        request.path = path
        request.path, request.query = self._update_request_uri_query(request, api_version)
        return self._perform_request(request)

    def _update_request_uri_query(self, request, api_version=None):
        """
        pulls the query string out of the URI and moves it into
        the query portion of the request object.  If there are already
        query parameters on the request the parameters in the URI will
        appear after the existing parameters
        """
        if '?' in request.path:
            request.path, _, query_string = request.path.partition('?')
            if query_string:
                query_params = query_string.split('&')
                for query in query_params:
                    if '=' in query:
                        name, _, value = query.partition('=')
                        request.query.append((name, value))

        request.path = url_quote(request.path, '/()$=\',')

        # Add the API version
        if not api_version:
            api_version_query = ('api-version', DEFAULT_API_VERSION)
        else:
            api_version_query = ('api-version', api_version)

        if request.query:
            request.query.append(api_version_query)
        else:
            request.query = [api_version_query]

        # add encoded queries to request.path.
        request.path += '?'
        for name, value in request.query:
            if value is not None:
                request.path += '%s=%s%s' % (
                    name,
                    url_quote(value, '/()$=\','),
                    '&'
                )
        request.path = request.path[:-1]

        return request.path, request.query

    def _perform_request(self, request, retries=0):
        if retries > MAX_RETRIES:
            # We have retried more than enough, let's quit
            raise Exception('Maximum retries (%d) reached. Please try again later' % MAX_RETRIES)
        try:
            return self.connection.request(
                action=request.path,
                data=request.body,
                headers=request.headers,
                method=request.method
            )
        except AzureRedirectException:
            e = sys.exc_info()[1]
            parsed_url = urlparse.urlparse(e.location)
            request.host = parsed_url.netloc
            return self._perform_request(request)
        except RateLimitReachedError as e:
            if e.retry_after is not None:
                time.sleep(e.retry_after)
                # Redo the request but with retries value incremented
                return self._perform_request(request, retries=retries+1)
            else:
                raise e
        except Exception as e:
            raise e
