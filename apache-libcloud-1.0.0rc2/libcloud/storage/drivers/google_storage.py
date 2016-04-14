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

import email.utils

from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.google import GoogleAuthType
from libcloud.common.google import GoogleOAuth2Credential
from libcloud.storage.drivers.s3 import BaseS3Connection
from libcloud.storage.drivers.s3 import BaseS3StorageDriver
from libcloud.storage.drivers.s3 import S3RawResponse
from libcloud.storage.drivers.s3 import S3Response

# Docs are a lie. Actual namespace returned is different that the one listed
# in the docs.
SIGNATURE_IDENTIFIER = 'GOOG1'
API_VERSION = '2006-03-01'
NAMESPACE = 'http://doc.s3.amazonaws.com/%s' % (API_VERSION)


class GoogleStorageConnection(ConnectionUserAndKey):
    """
    Represents a single connection to the Google storage API endpoint.

    This can either authenticate via the Google OAuth2 methods or via
    the S3 HMAC interoperability method.
    """

    host = 'storage.googleapis.com'
    responseCls = S3Response
    rawResponseCls = S3RawResponse
    PROJECT_ID_HEADER = 'x-goog-project-id'

    def __init__(self, user_id, key, secure, auth_type=None,
                 credential_file=None, **kwargs):
        self.auth_type = auth_type or GoogleAuthType.guess_type(user_id)
        if GoogleAuthType.is_oauth2(self.auth_type):
            self.oauth2_credential = GoogleOAuth2Credential(
                user_id, key, self.auth_type, credential_file, **kwargs)
        else:
            self.oauth2_credential = None
        super(GoogleStorageConnection, self).__init__(user_id, key, secure,
                                                      **kwargs)

    def add_default_headers(self, headers):
        date = email.utils.formatdate(usegmt=True)
        headers['Date'] = date
        project = self.get_project()
        if project:
            headers[self.PROJECT_ID_HEADER] = project
        return headers

    def get_project(self):
        return getattr(self.driver, 'project')

    def pre_connect_hook(self, params, headers):
        if self.auth_type == GoogleAuthType.GCS_S3:
            signature = self._get_s3_auth_signature(params, headers)
            headers['Authorization'] = '%s %s:%s' % (SIGNATURE_IDENTIFIER,
                                                     self.user_id, signature)
        else:
            headers['Authorization'] = ('Bearer ' +
                                        self.oauth2_credential.access_token)
        return params, headers

    def _get_s3_auth_signature(self, params, headers):
        """Hacky wrapper to work with S3's get_auth_signature."""
        headers_copy = {}
        params_copy = copy.deepcopy(params)

        # Lowercase all headers except 'date' and Google header values
        for k, v in headers.items():
            k_lower = k.lower()
            if (k_lower == 'date' or k_lower.startswith(
                    GoogleStorageDriver.http_vendor_prefix) or
                    not isinstance(v, str)):
                headers_copy[k_lower] = v
            else:
                headers_copy[k_lower] = v.lower()

        return BaseS3Connection.get_auth_signature(
            method=self.method,
            headers=headers_copy,
            params=params_copy,
            expires=None,
            secret_key=self.key,
            path=self.action,
            vendor_prefix=GoogleStorageDriver.http_vendor_prefix)


class GoogleStorageDriver(BaseS3StorageDriver):
    """
    Driver for Google Cloud Storage.

    Can authenticate via standard Google Cloud methods (Service Accounts,
    Installed App credentials, and GCE instance service accounts)

    Examples:

    Service Accounts::

        driver = GoogleStorageDriver(key=client_email, secret=private_key, ...)

    Installed Application::

        driver = GoogleStorageDriver(key=client_id, secret=client_secret, ...)

    From GCE instance::

        driver = GoogleStorageDriver(key=foo , secret=bar, ...)

    Can also authenticate via Google Cloud Storage's S3 HMAC interoperability
    API. S3 user keys are 20 alphanumeric characters, starting with GOOG.

    Example::

        driver = GoogleStorageDriver(key='GOOG0123456789ABCXYZ',
                                     secret=key_secret)
    """
    name = 'Google Storage'
    website = 'http://cloud.google.com/'
    connectionCls = GoogleStorageConnection
    hash_type = 'md5'
    namespace = NAMESPACE
    supports_chunked_encoding = False
    supports_s3_multipart_upload = False
    http_vendor_prefix = 'x-goog'

    def __init__(self, key, secret=None, project=None, **kwargs):
        self.project = project
        super(GoogleStorageDriver, self).__init__(key, secret, **kwargs)
