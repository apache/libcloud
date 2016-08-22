import json
import sys

from libcloud.common.azure import AzureResourceManagerConnection, AzureRedirectException
from libcloud.compute.base import NodeDriver, NodeLocation, NodeSize, Node
from libcloud.compute.drivers.azure import AzureHTTPRequest
from libcloud.compute.drivers.vcloud import urlparse
from libcloud.compute.types import Provider, NodeState

from libcloud.utils.py3 import urlquote as url_quote, ensure_string

AZURE_RESOURCE_MANAGEMENT_HOST = 'management.azure.com'
DEFAULT_API_VERSION = '2016-07-01'

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

    def create_node(self, name, location, node_size, disk_size,
                    ex_resource_group_name,
                    ex_storage_account_name,
                    ex_virtual_network_name,
                    ex_subnet_name,
                    ex_admin_username,
                    ex_marketplace_image,
                    ex_public_key=None):

        # Create the public IP address
        public_ip_address = self._create_public_ip_address(name, ex_resource_group_name, location.id)

        # Create the network interface card with that public IP address
        nic = self._create_network_interface(name, ex_resource_group_name, location.id,
                                             ex_virtual_network_name, ex_subnet_name,
                                             public_ip_address['name'])
        # Create the machine
        # - name
        # - location
        # - "plan": Marketplace image reference
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
                    'createOption': 'fromImage',
                    'diskSizeGB': disk_size
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
        path = '%sresourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s' % \
               (self._default_path_prefix, ex_resource_group_name, name)

        output = self._perform_put(path, node_payload, api_version='2016-03-30')
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
                'idleTimeoutInMinutes': 5
            }
        }
        path = '%sresourceGroups/%s/providers/Microsoft.Network/publicIPAddresses/%s' % \
               (self._default_path_prefix, resource_group_name, public_ip_address_name)

        output = self._perform_put(path, payload)
        return output.parse_body()

    def _to_node(self, node_data):
        network_interface_urls = node_data.get('properties', {}).get('networkProfile', {}).get('networkInterfaces', [])
        public_ips = []
        private_ips = []
        for network_interface_url in network_interface_urls:
            public_ip, private_ip = self._get_public_and_private_ips(network_interface_url)
            public_ips.append(public_ip)
            private_ips.append(private_ip)

        return Node(
            id=node_data.get('name'),
            name=node_data.get('name'),
            state=NodeState.UKNOWN,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self.connection.driver,
            extra={
                'provisioningState': node_data.get('properties', {}).get('provisioningState')
            }
        )

    def _get_public_and_private_ips(self, network_interace_url):
        json_response = self._perform_get(network_interace_url)
        raw_data = json_response.parse_body()
        public_ip = raw_data['properties']['ipConfigurations']['publicIPAddress']
        private_ip = raw_data['properties']['ipConfigurations']['privateIPAddress']
        return public_ip, private_ip

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

    def _perform_request(self, request):
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
        except Exception as e:
            raise e
