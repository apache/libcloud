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
import httplib

try:
    import simplejson as json
except ImportError:
    import json

import time
from libcloud.utils.py3 import urlparse

from libcloud.common.base import (ConnectionUserAndKey,
                                  JsonResponse,
                                  RawResponse, Connection)
from libcloud.http import LibcloudConnection
from libcloud.utils.py3 import basestring, urlencode


class AzureBaseDriver(object):
    name = "Microsoft Azure Resource Management API"


class AzureJsonResponse(JsonResponse):
    def parse_error(self):
        b = self.parse_body()

        if isinstance(b, basestring):
            return b
        elif isinstance(b, dict) and "error" in b:
            return "[%s] %s" % (b["error"].get("code"),
                                b["error"].get("message"))
        else:
            return str(b)


class AzureAuthJsonResponse(JsonResponse):
    def parse_error(self):
        b = self.parse_body()

        if isinstance(b, basestring):
            return b
        elif isinstance(b, dict) and "error_description" in b:
            return b["error_description"]
        else:
            return str(b)


class AzureKeyCredential:
    keyId = None  # str
    startDate = None  # str|datetime
    endDate = None  # str|datetime
    type = None  # str
    usage = None  # str
    value = None  # str

    def __init__(self, key_id, key_type, usage, value, start_date, end_date):
        """
        https://docs.microsoft.com/en-us/rest/api/graphrbac/ServicePrincipals/Create#definitions_keycredential

        :param key_id:
        :type: key_id: `str`

        :param key_type: Acceptable values are 'AsymmetricX509Cert' and 'Symmetric'.
        :type: key_type: `str`

        :param usage: Acceptable values are 'Verify' and 'Sign'.
        :type: usage: `str`

        :param value: Key value
        :type: value: `str`

        :param start_date: Start date
        :type: start_date: `str`|`datetime`

        :param end_date: End date
        :type: end_date: `str`|`datetime`
        """
        self.keyId = key_id
        if key_type not in ('AsymmetricX509Cert', 'Symmetric'):
            raise ValueError('Invalid `key_type` argument to AzureKeyCredential')
        self.type = key_type
        if usage not in ('Verify', 'Sign'):
            raise ValueError('Invalid `usage` argument to AzureKeyCredential')
        self.usage = usage
        self.value = value
        self.startDate = start_date
        self.endDate = end_date


class AzurePasswordCredential:
    keyId = None  # str
    startDate = None  # str|datetime
    endDate = None  # str|datetime
    value = None  # str

    def __init__(self, key_id, value, start_date, end_date):
        """
        https://docs.microsoft.com/en-us/rest/api/graphrbac/ServicePrincipals/Create#definitions_passwordcredential

        :param key_id:
        :type: key_id: `str`

        :param value: Key value
        :type: value: `str`

        :param start_date: Start date
        :type: start_date: `str`|`datetime`

        :param end_date: End date
        :type: end_date: `str`|`datetime`
        """
        self.keyId = key_id
        self.value = value
        self.startDate = start_date
        self.endDate = end_date


class AzureServicePrincipal:
    tenant_id = None  # str

    def __init__(self, tenant_id):
        """
        AzureServicePrincipal

        :param tenant_id: tenant ID can be found with, e.g.: `az account list`
        :type: tenant_id: `str`
        """
        self.tenant_id = tenant_id

    # Copying from: https://docs.microsoft.com/en-us/rest/api/graphrbac/ServicePrincipals/Create
    def create(self, app_id, account_enabled, key_credentials, password_credentials):
        """
        Creates a service principal in the directory

        :param app_id: application Id
        :type: app_id: `str`

        :param account_enabled: Whether the account is enabled
        :type: account_enabled: `bool`

        :param key_credentials: A collection of KeyCredential objects.
        :type: key_credentials: `AzureKeyCredential[]`

        :param password_credentials: A collection of PasswordCredential objects
        :type: password_credentials: `AzurePasswordCredential[]`
        """
        # TODO: POST https://graph.windows.net/{tenantID}/servicePrincipals?api-version=1.6
        url = 'https://graph.windows.net/{tenantID}/servicePrincipals?api-version=1.6'.format(tenantID=self.tenant_id)

    # Copying from Azure CLI 2.0: `az ad app create --help`
    def create_application(self, display_name, homepage, identifier_uris, available_to_other_tenants=False,
                           start_date=None, end_date=None, key_type='AsymmetricX509Cert',
                           key_usage='Verify', key_value=None, password=None, reply_urls=None):
        """
        Create an application


        :param display_name: The display name of the application.
        :type: display_name: `str`

        :param homepage: The url where users can sign in and use your app.
        :type: homepage: `str`

        :param identifier_uris: Space separated unique URIs that Azure AD can use for this app.
        :type: identifier_uris: `str`

        :param available_to_other_tenants: The application can be used from any Azure AD tenants.
        :type: available_to_other_tenants: `bool`

        :param start_date: Date or datetime at which credentials become valid(e.g.
                                  '2017-01-01T01:00:00+00:00' or '2017-01-01'). Default value is
                                  current time.
        :type: start_date: `str`|`datetime`

        :param end_date: Date or datetime after which credentials expire(e.g.
                                  '2017-12-31T11:59:59+00:00' or '2017-12-31'). Default value is one
                                  year after current time.
        :type: end_date: `str`|`datetime`

        :param key_type: The type of the key credentials associated with the application.
                                  Allowed values: AsymmetricX509Cert, Password, Symmetric.  Default:
                                  AsymmetricX509Cert.
        :type: key_type: `str`

        :param key_usage: The usage of the key credentials associated with the application.
                                  Allowed values: Sign, Verify.  Default: Verify.
        :type: key_usage: `str`

        :param key_value: The value for the key credentials associated with the application.
        :type: key_value: `str`

        :param password:
        :type: password: `str`

        :param reply_urls: Space separated URIs to which Azure AD will redirect in response
                                  to an OAuth 2.0 request. The value does not need to be a physical
                                  endpoint, but must be a valid URI.
        :type: reply_urls: `str`
        """

    # Copying from Azure CLI 2.0: `az ad sp create --help`
    def create_service_principal(self, ident):
        """
        Create a service principal

        :param ident: Identifier uri, application id, or object id of the associated application
        :type: ident: `str`
        """

    # Copying from Azure CLI 2.0: `az role assignment create --help`
    def assign_role(self, assignee, role, resource_group=False, scope=None):
        """
        Create a new role assignment for a user, group, or service principal

        :param assignee: Represent a user, group, or service principal. supported format: object
                           id, user sign-in name, or service principal name.
        :type: assignee: `str`

        :param role: Role name or id
        :type: role: `str`

        :param resource_group: Use it only if the role or assignment was added at the level of a
                           resource group
        :type: resource_group: `bool`

        :param scope: Scope at which the role assignment or definition applies to, e.g.,
                           /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333,
                           /subscriptions/0b1f6471-1bf0-4dda-
                           aec3-111122223333/resourceGroups/myGroup, or
                           /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333/resourceGroups/myGrou
                           p/providers/Microsoft.Compute/virtualMachines/myVM.
        :type: scope: `str`
        """


class AzureResourceAccess:
    """
    The list of OAuth2.0 permission scopes and app roles that the application requires from the specified resource.

    https://docs.microsoft.com/en-us/rest/api/graphrbac/applications/create#resourceaccess
    """

    def __init__(self, id, type):
        """

        :param id: The unique identifier for one of the OAuth2Permission or AppRole instances
        that the resource application exposes.
        :type: id: `str`

        :param type: Specifies whether the id property references an OAuth2Permission or an AppRole.
        Possible values are "scope" or "role".
        :type: type: `str`
        """
        # Eww, these shadow builtin types :\
        self.id = id
        self.type = type


class AzureRequiredResourceAccess:
    """
    Specifies the set of OAuth 2.0 permission scopes and app roles under the specified resource that an application
     requires access to. The specified OAuth 2.0 permission scopes may be requested by client applications
     (through the requiredResourceAccess collection) when calling a resource application.
     The requiredResourceAccess property of the Application entity is a collection of ReqiredResourceAccess.

    https://docs.microsoft.com/en-us/rest/api/graphrbac/applications/create#requiredresourceaccess
    """

    def __init__(self, resourceAccess, resourceAppId):
        """

        :param resourceAccess: Specifies an OAuth 2.0 permission scope or an app role that an application requires.
        The resourceAccess property of the RequiredResourceAccess type is a collection of ResourceAccess.
        :type: resourceAccess: `AzureResourceAccess[]`

        :param resourceAppId: The unique identifier for the resource that the application requires access to.
        This should be equal to the appId declared on the target resource application.
        :type: resourceAppId: `str`

        """
        self.resourceAccess = resourceAccess
        self.resourceAppId = resourceAppId


class AzureApplication:
    """
    Active Directory application information.

    https://docs.microsoft.com/en-us/rest/api/graphrbac/applications/create#application
    """

    def __init__(self, appId, appPermissions, availableToOtherTenants, deletionTimestamp,
                 displayName, homepage, identifierUris, oauth2AllowImplicitFlow, objectId,
                 objectType, replyUrls):
        """
        :param appId: The application ID.
        :type: appId: `str`

        :param appPermissions: The application permissions.
        :type: appPermissions: `str[]`

        :param availableToOtherTenants: Whether the application is available to other tenants.
        :type: availableToOtherTenants: `bool`

        :param deletionTimestamp: The time at which the directory object was deleted.
        :type: deletionTimestamp: `str`

        :param displayName: The display name of the application.
        :type: displayName: `str`

        :param homepage: The home page of the application.
        :type: homepage: `str`

        :param objectId: The object ID.
        :type: objectId: `str`

        :param objectType: The object type.
        :type: objectType: `str`

        :param identifierUris: A collection of URIs for the application.
        :type: identifierUris: `str[]`

        :param replyUrls: A collection of reply URLs for the application.
        :type: replyUrls: `str[]`

        :param oauth2AllowImplicitFlow: Whether to allow implicit grant flow for OAuth2
        :type: oauth2AllowImplicitFlow: `AzureRequiredResourceAccess[]`
        """
        self.appId = appId
        self.appPermissions = appPermissions
        self.availableToOtherTenants = availableToOtherTenants
        self.deletionTimestamp = deletionTimestamp
        self.displayName = displayName
        self.homepage = homepage
        self.identifierUris = identifierUris
        self.oauth2AllowImplicitFlow = oauth2AllowImplicitFlow
        self.objectId = objectId
        self.objectType = objectType
        self.replyUrls = replyUrls


class AzureGraphError(Exception):
    """
    Active Directory error information.

    https://docs.microsoft.com/en-us/rest/api/graphrbac/applications/create#grapherror
    """

    def __init__(self, code, value):
        """

        :param code: Error code.
        :type: `str`

        :param value: Error message value.
        :type: `str`
        """
        if not isinstance(code, basestring):
            code = code['error']['code']
        if not isinstance(value, basestring):
            value = value['error']['message']['value']
        self.code = code
        self.value = value


# Based on
# https://github.com/Azure/azure-xplat-cli/blob/master/lib/util/profile/environment.js
publicEnvironments = {
    "default": {
        'name': 'default',
        'portalUrl': 'http://go.microsoft.com/fwlink/?LinkId=254433',
        'publishingProfileUrl':
            'http://go.microsoft.com/fwlink/?LinkId=254432',
        'managementEndpointUrl': 'https://management.core.windows.net',
        'resourceManagerEndpointUrl':
            'https://management.azure.com/',
        'sqlManagementEndpointUrl':
            'https://management.core.windows.net:8443/',
        'sqlServerHostnameSuffix': '.database.windows.net',
        'galleryEndpointUrl': 'https://gallery.azure.com/',
        'activeDirectoryEndpointUrl': 'https://login.microsoftonline.com',
        'activeDirectoryResourceId': 'https://management.core.windows.net/',
        'activeDirectoryGraphResourceId': 'https://graph.windows.net/',
        'activeDirectoryGraphApiVersion': '2013-04-05',
        'activeDirectoryGraphApiNumber': 1.6,
        'storageEndpointSuffix': '.core.windows.net',
        'keyVaultDnsSuffix': '.vault.azure.net',
        'azureDataLakeStoreFileSystemEndpointSuffix': 'azuredatalakestore.net',
        'azureDataLakeAnalyticsCatalogAndJobEndpointSuffix':
            'azuredatalakeanalytics.net'
    },
    "AzureChinaCloud": {
        'name': 'AzureChinaCloud',
        'portalUrl': 'http://go.microsoft.com/fwlink/?LinkId=301902',
        'publishingProfileUrl':
            'http://go.microsoft.com/fwlink/?LinkID=301774',
        'managementEndpointUrl': 'https://management.core.chinacloudapi.cn',
        'resourceManagerEndpointUrl': 'https://management.chinacloudapi.cn',
        'sqlManagementEndpointUrl':
            'https://management.core.chinacloudapi.cn:8443/',
        'sqlServerHostnameSuffix': '.database.chinacloudapi.cn',
        'galleryEndpointUrl': 'https://gallery.chinacloudapi.cn/',
        'activeDirectoryEndpointUrl': 'https://login.chinacloudapi.cn',
        'activeDirectoryResourceId':
            'https://management.core.chinacloudapi.cn/',
        'activeDirectoryGraphResourceId': 'https://graph.chinacloudapi.cn/',
        'activeDirectoryGraphApiVersion': '2013-04-05',
        'storageEndpointSuffix': '.core.chinacloudapi.cn',
        'keyVaultDnsSuffix': '.vault.azure.cn',
        'azureDataLakeStoreFileSystemEndpointSuffix': 'N/A',
        'azureDataLakeAnalyticsCatalogAndJobEndpointSuffix': 'N/A'
    },
    "AzureUSGovernment": {
        'name': 'AzureUSGovernment',
        'portalUrl': 'https://manage.windowsazure.us',
        'publishingProfileUrl':
            'https://manage.windowsazure.us/publishsettings/index',
        'managementEndpointUrl': 'https://management.core.usgovcloudapi.net',
        'resourceManagerEndpointUrl': 'https://management.usgovcloudapi.net',
        'sqlManagementEndpointUrl':
            'https://management.core.usgovcloudapi.net:8443/',
        'sqlServerHostnameSuffix': '.database.usgovcloudapi.net',
        'galleryEndpointUrl': 'https://gallery.usgovcloudapi.net/',
        'activeDirectoryEndpointUrl': 'https://login-us.microsoftonline.com',
        'activeDirectoryResourceId':
            'https://management.core.usgovcloudapi.net/',
        'activeDirectoryGraphResourceId': 'https://graph.windows.net/',
        'activeDirectoryGraphApiVersion': '2013-04-05',
        'storageEndpointSuffix': '.core.usgovcloudapi.net',
        'keyVaultDnsSuffix': '.vault.usgovcloudapi.net',
        'azureDataLakeStoreFileSystemEndpointSuffix': 'N/A',
        'azureDataLakeAnalyticsCatalogAndJobEndpointSuffix': 'N/A'
    },
    "AzureGermanCloud": {
        'name': 'AzureGermanCloud',
        'portalUrl': 'http://portal.microsoftazure.de/',
        'publishingProfileUrl':
            'https://manage.microsoftazure.de/publishsettings/index',
        'managementEndpointUrl': 'https://management.core.cloudapi.de',
        'resourceManagerEndpointUrl': 'https://management.microsoftazure.de',
        'sqlManagementEndpointUrl':
            'https://management.core.cloudapi.de:8443/',
        'sqlServerHostnameSuffix': '.database.cloudapi.de',
        'galleryEndpointUrl': 'https://gallery.cloudapi.de/',
        'activeDirectoryEndpointUrl': 'https://login.microsoftonline.de',
        'activeDirectoryResourceId': 'https://management.core.cloudapi.de/',
        'activeDirectoryGraphResourceId': 'https://graph.cloudapi.de/',
        'activeDirectoryGraphApiVersion': '2013-04-05',
        'storageEndpointSuffix': '.core.cloudapi.de',
        'keyVaultDnsSuffix': '.vault.microsoftazure.de',
        'azureDataLakeStoreFileSystemEndpointSuffix': 'N/A',
        'azureDataLakeAnalyticsCatalogAndJobEndpointSuffix': 'N/A'
    }
}


class AzureResourceManagementConnection(ConnectionUserAndKey):
    """
    Represents a single connection to Azure
    """

    conn_class = LibcloudConnection
    driver = AzureBaseDriver
    name = 'Azure AD Auth'
    responseCls = AzureJsonResponse
    rawResponseCls = RawResponse

    def __init__(self, key, secret, secure=True, tenant_id=None,
                 subscription_id=None, cloud_environment=None, **kwargs):
        super(AzureResourceManagementConnection, self) \
            .__init__(key, secret, **kwargs)
        if not cloud_environment:
            cloud_environment = "default"
        if isinstance(cloud_environment, basestring):
            cloud_environment = publicEnvironments[cloud_environment]
        if not isinstance(cloud_environment, dict):
            raise Exception("cloud_environment must be one of '%s' or a dict "
                            "containing keys 'resourceManagerEndpointUrl', "
                            "'activeDirectoryEndpointUrl', "
                            "'activeDirectoryResourceId', "
                            "'storageEndpointSuffix'" % (
                                "', '".join(publicEnvironments.keys())))
        self.host = urlparse.urlparse(
            cloud_environment['resourceManagerEndpointUrl']).hostname
        self.login_host = urlparse.urlparse(
            cloud_environment['activeDirectoryEndpointUrl']).hostname
        self.login_resource = cloud_environment['activeDirectoryResourceId']
        self.storage_suffix = cloud_environment['storageEndpointSuffix']
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    def add_default_headers(self, headers):
        headers['Content-Type'] = "application/json"
        headers['Authorization'] = "Bearer %s" % self.access_token
        return headers

    def encode_data(self, data):
        """Encode data to JSON"""
        return json.dumps(data)

    def get_token_from_credentials(self):
        """
        Log in and get bearer token used to authorize API requests.
        """

        conn = self.conn_class(self.login_host, 443, timeout=self.timeout)
        conn.connect()
        params = urlencode({
            "grant_type": "client_credentials",
            "client_id": self.user_id,
            "client_secret": self.key,
            "resource": self.login_resource
        })
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/%s/oauth2/token" % self.tenant_id,
                     params, headers)
        js = AzureAuthJsonResponse(conn.getresponse(), conn)
        self.access_token = js.object["access_token"]
        self.expires_on = js.object["expires_on"]

    def connect(self, **kwargs):
        self.get_token_from_credentials()
        return super(AzureResourceManagementConnection, self).connect(**kwargs)

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False):

        # Log in again if the token has expired or is going to expire soon
        # (next 5 minutes).
        if (time.time() + 300) >= int(self.expires_on):
            self.get_token_from_credentials()

        return super(AzureResourceManagementConnection, self) \
            .request(action, params=params,
                     data=data, headers=headers,
                     method=method, raw=raw)


class AzurePrep(Connection):
    """
    Represents a single connection to Azure (Graph API)

    Used just for setup, expected to be used in the first 3 lines of creating within Azure (e.g.: new subscription)
    """

    def __init__(self, tenant_id):
        """
        Instantiate AzurePrep

        :param tenant_id: Acceptable values are 'Verify' and 'Sign'.
        :type: tenant_id: `str`

        (you can find this from `az account list`)
        """
        super(AzurePrep, self).__init__(
            host=publicEnvironments['default']['activeDirectoryGraphResourceId']
        )
        self.add_default_headers({'Content-Type': 'application/json'})
        self.add_default_params({'api-version': publicEnvironments['default']['activeDirectoryGraphApiNumber']})

    def create_app(self, availableToOtherTenants, displayName, identifierUris, homepage=None,
                   replyUrls=None, keyCredentials=None, passwordCredentials=None, oauth2AllowImplicitFlow=None,
                   requiredResourceAccess=None):
        """

        https://docs.microsoft.com/en-us/rest/api/graphrbac/applications/create

        :param availableToOtherTenants: Whether the application is available to other tenants.
        :type: availableToOtherTenants: `bool`

        :param displayName: The display name of the application.
        :type: displayName: `str`

        :param homepage: The home page of the application.
        :type: homepage: `str`

        :param identifierUris: A collection of URIs for the application.
        :type: identifierUris: `str[]`

        :param replyUrls: A collection of reply URLs for the application.
        :type: replyUrls: `str[]`

        :param keyCredentials: Active Directory Key Credential information.
        :type: keyCredentials: `AzureKeyCredential[]`

        :param passwordCredentials: Active Directory Password Credential information.
        :type: passwordCredentials: `AzurePasswordCredential[]`

        :param oauth2AllowImplicitFlow: Whether to allow implicit grant flow for OAuth2
        :type: oauth2AllowImplicitFlow: `AzureRequiredResourceAccess[]`

        :param requiredResourceAccess: Specifies the set of OAuth 2.0 permission scopes and app roles under the
        specified resource that an application requires access to. The specified OAuth 2.0 permission scopes may be
        requested by client applications (through the requiredResourceAccess collection) when calling a
        resource application. The requiredResourceAccess property of the Application entity is a
        collection of ReqiredResourceAccess.
        :type: requiredResourceAccess: `str`

        :return Azure Application
        :rtype: :class:`AzureApplication`
        """
        if passwordCredentials is None and keyCredentials is None:
            raise TypeError('Must set some credentials!')

        resp = self.request(method='POST', action='/applications', data={
            k: locals()[k]
            for k in ('availableToOtherTenants', 'displayName', 'identifierUris', 'homepage',
                      'replyUrls', 'keyCredentials', 'passwordCredentials', 'oauth2AllowImplicitFlow',
                      'requiredResourceAccess')
            if locals()[k] is not None
        })

        resp_content = json.loads(resp.read())
        if resp.status == httplib.CREATED:
            return AzureApplication(**resp_content)

        raise AzureGraphError(**resp_content)

    def create_service_principal(self):
        pass

    def create_role_assignment(self):
        pass
