import json
import sys

from libcloud.common.azure import AzureResourceManagerConnection, AzureRedirectException
from libcloud.compute.base import NodeDriver
from libcloud.compute.drivers.azure import AzureHTTPRequest, AzureNodeLocation
from libcloud.compute.drivers.vcloud import urlparse
from libcloud.compute.types import Provider

from libcloud.utils.py3 import urlquote as url_quote

AZURE_RESOURCE_MANAGEMENT_HOST = 'management.azure.com'
API_VERSION = '2016-03-30'


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
        json_data = self._perform_get(path)
        raw_data = json.loads(json_data)

        return [self._to_location(l) for l in raw_data]

    def list_sizes(self, location):
        path = '%sproviders/Microsoft.Compute/locations/%s/vmSizes' % (self._default_path_prefix, location)
        return self._perform_get(path)
    # def list_nodes(self, resource_group)
    # def create_node(self, resource_group)

    def _to_location(self, location_data):
        """
            Convert the data from a Azure response object into a location
            """
        raw_data = location_data.get['value']
        # vm_role_sizes = data.compute_capabilities.virtual_machines_role_sizes

        return AzureNodeLocation(
            id=raw_data.get('name', None),
            name=raw_data.get('display_name', None),
            country=raw_data.get('display_name', None),
            driver=self.connection.driver,
            # available_services=data.available_services,
            # virtual_machine_role_sizes=vm_role_sizes
        )

    @property
    def _default_path_prefix(self):
        """Everything starts with the subscription prefix"""
        return '/subscription/%s/' % self.subscription_id

    def _perform_get(self, path):
        request = AzureHTTPRequest()
        request.method = 'GET'
        request.host = AZURE_RESOURCE_MANAGEMENT_HOST
        request.path = path
        request.path, request.query = self._update_request_uri_query(request)
        return self._perform_request(request)

    def _update_request_uri_query(self, request):
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
        api_version = ('api-version', API_VERSION)
        if request.query:
            request.query.append(api_version)
        else:
            request.query = [api_version]

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
