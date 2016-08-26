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

import copy
import os
import time
import base64
import hmac

from hashlib import sha256

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b
from libcloud.utils.xml import fixxpath

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.common.types import InvalidCredsError
from libcloud.common.types import LibcloudError, MalformedResponseError
from libcloud.common.base import ConnectionUserAndKey, RawResponse, Connection, JsonResponse
from libcloud.common.base import CertificateConnection
from libcloud.common.base import XmlResponse

# Azure API version
API_VERSION = '2012-02-12'

# The time format for headers in Azure requests
AZURE_TIME_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


"""
Sizes must be hardcoded because Microsoft doesn't provide an API to fetch them
From http://msdn.microsoft.com/en-us/library/windowsazure/dn197896.aspx

Prices are for Linux instances in East US data center. To see what pricing will
actually be, visit:
http://azure.microsoft.com/en-gb/pricing/details/virtual-machines/
"""
AZURE_COMPUTE_INSTANCE_TYPES = {
    'A0': {
        'id': 'ExtraSmall',
        'name': 'Extra Small Instance',
        'ram': 768,
        'disk': 127,
        'bandwidth': None,
        'price': '0.0211',
        'max_data_disks': 1,
        'cores': 'Shared'
    },
    'A1': {
        'id': 'Small',
        'name': 'Small Instance',
        'ram': 1792,
        'disk': 127,
        'bandwidth': None,
        'price': '0.0633',
        'max_data_disks': 2,
        'cores': 1
    },
    'A2': {
        'id': 'Medium',
        'name': 'Medium Instance',
        'ram': 3584,
        'disk': 127,
        'bandwidth': None,
        'price': '0.1266',
        'max_data_disks': 4,
        'cores': 2
    },
    'A3': {
        'id': 'Large',
        'name': 'Large Instance',
        'ram': 7168,
        'disk': 127,
        'bandwidth': None,
        'price': '0.2531',
        'max_data_disks': 8,
        'cores': 4
    },
    'A4': {
        'id': 'ExtraLarge',
        'name': 'Extra Large Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.5062',
        'max_data_disks': 16,
        'cores': 8
    },
    'A5': {
        'id': 'A5',
        'name': 'Memory Intensive Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.2637',
        'max_data_disks': 4,
        'cores': 2
    },
    'A6': {
        'id': 'A6',
        'name': 'A6 Instance',
        'ram': 28672,
        'disk': 127,
        'bandwidth': None,
        'price': '0.5273',
        'max_data_disks': 8,
        'cores': 4
    },
    'A7': {
        'id': 'A7',
        'name': 'A7 Instance',
        'ram': 57344,
        'disk': 127,
        'bandwidth': None,
        'price': '1.0545',
        'max_data_disks': 16,
        'cores': 8
    },
    'A8': {
        'id': 'A8',
        'name': 'A8 Instance',
        'ram': 57344,
        'disk': 127,
        'bandwidth': None,
        'price': '2.0774',
        'max_data_disks': 16,
        'cores': 8
    },
    'A9': {
        'id': 'A9',
        'name': 'A9 Instance',
        'ram': 114688,
        'disk': 127,
        'bandwidth': None,
        'price': '4.7137',
        'max_data_disks': 16,
        'cores': 16
    },
    'A10': {
        'id': 'A10',
        'name': 'A10 Instance',
        'ram': 57344,
        'disk': 127,
        'bandwidth': None,
        'price': '1.2233',
        'max_data_disks': 16,
        'cores': 8
    },
    'A11': {
        'id': 'A11',
        'name': 'A11 Instance',
        'ram': 114688,
        'disk': 127,
        'bandwidth': None,
        'price': '2.1934',
        'max_data_disks': 16,
        'cores': 16
    },
    'D1': {
        'id': 'Standard_D1',
        'name': 'D1 Faster Compute Instance',
        'ram': 3584,
        'disk': 127,
        'bandwidth': None,
        'price': '0.0992',
        'max_data_disks': 2,
        'cores': 1
    },
    'D2': {
        'id': 'Standard_D2',
        'name': 'D2 Faster Compute Instance',
        'ram': 7168,
        'disk': 127,
        'bandwidth': None,
        'price': '0.1983',
        'max_data_disks': 4,
        'cores': 2
    },
    'D3': {
        'id': 'Standard_D3',
        'name': 'D3 Faster Compute Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.3965',
        'max_data_disks': 8,
        'cores': 4
    },
    'D4': {
        'id': 'Standard_D4',
        'name': 'D4 Faster Compute Instance',
        'ram': 28672,
        'disk': 127,
        'bandwidth': None,
        'price': '0.793',
        'max_data_disks': 16,
        'cores': 8
    },
    'D11': {
        'id': 'Standard_D11',
        'name': 'D11 Faster Compute Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.251',
        'max_data_disks': 4,
        'cores': 2
    },
    'D12': {
        'id': 'Standard_D12',
        'name': 'D12 Faster Compute Instance',
        'ram': 28672,
        'disk': 127,
        'bandwidth': None,
        'price': '0.502',
        'max_data_disks': 8,
        'cores': 4
    },
    'D13': {
        'id': 'Standard_D13',
        'name': 'D13 Faster Compute Instance',
        'ram': 57344,
        'disk': 127,
        'bandwidth': None,
        'price': '0.9038',
        'max_data_disks': 16,
        'cores': 8
    },
    'D14': {
        'id': 'Standard_D14',
        'name': 'D14 Faster Compute Instance',
        'ram': 114688,
        'disk': 127,
        'bandwidth': None,
        'price': '1.6261',
        'max_data_disks': 32,
        'cores': 16
    },
    'Standard_D2_v2': {
        'id': 'Standard_D2_v2',
        'name': 'D2 v2 Faster Compute Instance',
        'ram': 7168,
        'disk': 100,
        'bandwidth': None,
        'price': '0.16',
        'max_data_disks': 4,
        'cores': 2
    },
    'Standard_D3_v2': {
        'id': 'Standard_D3_v2',
        'name': 'D3 v2 Faster Compute Instance',
        'ram': 14336,
        'disk': 200,
        'bandwidth': None,
        'price': '0.319',
        'max_data_disks': 8,
        'cores': 4
    },
    'Standard_D4_v2': {
        'id': 'Standard_D4_v2',
        'name': 'D4 v2 Faster Compute Instance',
        'ram': 28672,
        'disk': 400,
        'bandwidth': None,
        'price': '0.672',
        'max_data_disks': 16,
        'cores': 8
    },
    'Standard_D5_v2': {
        'id': 'Standard_D5_v2',
        'name': 'D5 v2 Faster Compute Instance',
        'ram': 57344,
        'disk': 800,
        'bandwidth': None,
        'price': '1.277',
        'max_data_disks': 32,
        'cores': 16
    }
}


class AzureRedirectException(Exception):

    def __init__(self, response):
        self.location = response.headers['location']


class AzureResponse(XmlResponse):

    valid_response_codes = [
        httplib.NOT_FOUND,
        httplib.CONFLICT,
        httplib.BAD_REQUEST,
        httplib.TEMPORARY_REDIRECT
        # added TEMPORARY_REDIRECT as this can sometimes be
        # sent by azure instead of a success or fail response
    ]

    def success(self):
        i = int(self.status)
        return 200 <= i <= 299 or i in self.valid_response_codes

    def parse_error(self, msg=None):
        error_msg = 'Unknown error'

        try:
            # Azure does give some meaningful errors, but is inconsistent
            # Some APIs respond with an XML error. Others just dump HTML
            body = self.parse_body()

            # pylint: disable=no-member
            if type(body) == ET.Element:
                code = body.findtext(fixxpath(xpath='Code'))
                message = body.findtext(fixxpath(xpath='Message'))
                message = message.split('\n')[0]
                error_msg = '%s: %s' % (code, message)

        except MalformedResponseError:
            pass

        if msg:
            error_msg = '%s - %s' % (msg, error_msg)

        if self.status in [httplib.UNAUTHORIZED, httplib.FORBIDDEN]:
            raise InvalidCredsError(error_msg)

        raise LibcloudError(
            '%s Status code: %d.' % (error_msg, self.status),
            driver=self
        )

    def parse_body(self):
        is_redirect = int(self.status) == httplib.TEMPORARY_REDIRECT

        if is_redirect and self.connection.driver.follow_redirects:
            raise AzureRedirectException(self)
        else:
            return super(AzureResponse, self).parse_body()


class AzureRawResponse(RawResponse):
    pass


class AzureConnection(ConnectionUserAndKey):
    """
    Represents a single connection to Azure
    """

    responseCls = AzureResponse
    rawResponseCls = AzureRawResponse

    def add_default_params(self, params):
        return params

    def pre_connect_hook(self, params, headers):
        headers = copy.deepcopy(headers)

        # We have to add a date header in GMT
        headers['x-ms-date'] = time.strftime(AZURE_TIME_FORMAT, time.gmtime())
        headers['x-ms-version'] = API_VERSION

        # Add the authorization header
        headers['Authorization'] = self._get_azure_auth_signature(
            method=self.method,
            headers=headers,
            params=params,
            account=self.user_id,
            secret_key=self.key,
            path=self.action
        )

        # Azure cribs about this in 'raw' connections
        headers.pop('Host', None)

        return params, headers

    def _get_azure_auth_signature(self,
                                  method,
                                  headers,
                                  params,
                                  account,
                                  secret_key,
                                  path='/'):
        """
        Signature = Base64( HMAC-SHA1( YourSecretAccessKeyID,
                            UTF-8-Encoding-Of( StringToSign ) ) ) );

        StringToSign = HTTP-VERB + "\n" +
            Content-Encoding + "\n" +
            Content-Language + "\n" +
            Content-Length + "\n" +
            Content-MD5 + "\n" +
            Content-Type + "\n" +
            Date + "\n" +
            If-Modified-Since + "\n" +
            If-Match + "\n" +
            If-None-Match + "\n" +
            If-Unmodified-Since + "\n" +
            Range + "\n" +
            CanonicalizedHeaders +
            CanonicalizedResource;
        """
        special_header_values = []
        xms_header_values = []
        param_list = []
        special_header_keys = [
            'content-encoding',
            'content-language',
            'content-length',
            'content-md5',
            'content-type',
            'date',
            'if-modified-since',
            'if-match',
            'if-none-match',
            'if-unmodified-since',
            'range'
        ]

        # Split the x-ms headers and normal headers and make everything
        # lower case
        headers_copy = {}
        for header, value in headers.items():
            header = header.lower()
            value = str(value).strip()
            if header.startswith('x-ms-'):
                xms_header_values.append((header, value))
            else:
                headers_copy[header] = value

        # Get the values for the headers in the specific order
        for header in special_header_keys:
            header = header.lower()  # Just for safety
            if header in headers_copy:
                special_header_values.append(headers_copy[header])
            else:
                special_header_values.append('')

        # Prepare the first section of the string to be signed
        values_to_sign = [method] + special_header_values
        # string_to_sign = '\n'.join([method] + special_header_values)

        # The x-ms-* headers have to be in lower case and sorted
        xms_header_values.sort()

        for header, value in xms_header_values:
            values_to_sign.append('%s:%s' % (header, value))

        # Add the canonicalized path
        values_to_sign.append('/%s%s' % (account, path))

        # URL query parameters (sorted and lower case)
        for key, value in params.items():
            param_list.append((key.lower(), str(value).strip()))

        param_list.sort()

        for key, value in param_list:
            values_to_sign.append('%s:%s' % (key, value))

        string_to_sign = b('\n'.join(values_to_sign))
        secret_key = b(secret_key)
        b64_hmac = base64.b64encode(
            hmac.new(secret_key, string_to_sign, digestmod=sha256).digest()
        )

        return 'SharedKey %s:%s' % (self.user_id, b64_hmac.decode('utf-8'))


class AzureBaseDriver(object):
    name = "Microsoft Azure Service Management API"


class AzureServiceManagementConnection(CertificateConnection):
    # This needs the following approach -
    # 1. Make request using LibcloudHTTPSConnection which is a overloaded
    # class which takes in a client certificate
    # 2. Depending on the type of operation use a PollingConnection
    # when the response id is returned
    # 3. The Response can be used in an AzureServiceManagementResponse

    """
    Authentication class for "Service Account" authentication.
    """

    driver = AzureBaseDriver
    responseCls = AzureResponse
    rawResponseCls = AzureRawResponse
    name = 'Azure Service Management API Connection'
    host = 'management.core.windows.net'
    keyfile = ""

    def __init__(self, subscription_id, key_file, *args, **kwargs):
        """
        Check to see if PyCrypto is available, and convert key file path into a
        key string if the key is in a file.

        :param  subscription_id: Azure subscription ID.
        :type   subscription_id: ``str``

        :param  key_file: The PEM file used to authenticate with the service.
        :type   key_file: ``str``
        """

        super(AzureServiceManagementConnection, self).__init__(
            key_file,
            *args,
            **kwargs
        )

        self.subscription_id = subscription_id

        keypath = os.path.expanduser(key_file)
        self.keyfile = keypath
        is_file_path = os.path.exists(keypath) and os.path.isfile(keypath)
        if not is_file_path:
            raise InvalidCredsError(
                'You need an certificate PEM file to authenticate with '
                'Microsoft Azure. This can be found in the portal.'
            )
        self.key_file = key_file

    def add_default_headers(self, headers):
        """
        @inherits: :class:`Connection.add_default_headers`
        TODO: move to constant..
        """
        headers['x-ms-version'] = "2014-05-01"
        headers['x-ms-date'] = time.strftime(AZURE_TIME_FORMAT, time.gmtime())
        #  headers['host'] = self.host
        return headers


class AzureARMResponse(JsonResponse):

    valid_response_codes = [
        httplib.NOT_FOUND,
        httplib.CONFLICT,
        httplib.BAD_REQUEST,
        httplib.TEMPORARY_REDIRECT
        # added TEMPORARY_REDIRECT as this can sometimes be
        # sent by azure instead of a success or fail response
    ]

    def success(self):
        i = int(self.status)
        return 200 <= i <= 299 or i in self.valid_response_codes


class AzureResourceManagerConnection(Connection):
    driver = AzureBaseDriver
    responseCls = AzureARMResponse
    rawResponseCls = AzureRawResponse
    name = 'Azure Resource Manager API Connection'
    host = 'management.azure.com'
    token = ''

    def __init__(self, subscription_id, token, *args, **kwargs):
        """
        :param  subscription_id: Azure subscription ID.
        :type   subscription_id: ``str``

        :param  token: JSON web token to authenticate with Azure Active Directory
        :type   token: ``str``
        """

        super(AzureResourceManagerConnection, self).__init__(
            *args,
            **kwargs
        )
        self.subscription_id = subscription_id
        self.token = token

    def add_default_headers(self, headers):
        """
        @inherits: :class:`Connection.add_default_headers`
        """
        headers['Content-Type'] = 'application/json'
        headers['Authorization'] = 'Bearer %s' % self.token
        return headers
