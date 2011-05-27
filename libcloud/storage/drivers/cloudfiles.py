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
import urllib

try:
    import json
except:
    import simplejson as json

from libcloud.utils import read_in_chunks
from libcloud.common.types import MalformedResponseError, LibcloudError
from libcloud.common.base import Response, RawResponse

from libcloud.storage.providers import Provider
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.types import InvalidContainerNameError

from libcloud.common.rackspace import (
    AUTH_HOST_US, AUTH_HOST_UK, RackspaceBaseConnection)

from libcloud.storage.drivers.swift import SwiftConnection, SwiftStorageDriver, SwiftResponse

CDN_HOST = 'cdn.clouddrive.com'
API_VERSION = 'v1.0'


class CloudFilesResponse(SwiftResponse):
    pass

class CloudFilesRawResponse(CloudFilesResponse, RawResponse):
    pass

class CloudFilesConnection(SwiftConnection):
    """
    Base connection class for the Cloudfiles driver.
    """

    responseCls = CloudFilesResponse
    rawResponseCls = CloudFilesRawResponse
    auth_host = None
    _url_key = "storage_url"
    auth_headers_keys = {
        'storage_url' :'x-storage-url',
        'server_url':'x-server-management-url',
        'cdn_management_url':'x-cdn-management-url'
    }

    def __init__(self, user_id, key, secure=True):
        super(CloudFilesConnection, self).__init__(user_id, key, secure=secure)
        self.api_version = API_VERSION
        self.accept_format = 'application/json'

    def request(self, action, params=None, data='', headers=None, method='GET',
                raw=False, cdn_request=False):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if cdn_request:
            host = self._get_host(url_key='cdn_management_url')
        else:
            host = None

        # Due to first-run authentication request, we may not have a path
        if self.request_path:
            action = self.request_path + action
            params['format'] = 'json'
        if method in [ 'POST', 'PUT' ]:
            headers.update({'Content-Type': 'application/json; charset=UTF-8'})

        return super(CloudFilesConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers,
            raw=raw, host=host
        )


class CloudFilesUSConnection(CloudFilesConnection):
    """
    Connection class for the Cloudfiles US endpoint.
    """

    auth_host = AUTH_HOST_US


class CloudFilesUKConnection(CloudFilesConnection):
    """
    Connection class for the Cloudfiles UK endpoint.
    """

    auth_host = AUTH_HOST_UK


class CloudFilesStorageDriver(SwiftStorageDriver):
    """
    Base CloudFiles driver.

    You should never create an instance of this class directly but use US/US
    class.
    """
    name = 'CloudFiles'
    connectionCls = CloudFilesConnection
    hash_type = 'md5'

    def get_container_cdn_url(self, container):
        container_name = container.name
        response = self.connection.request('/%s' % (container_name),
                                           method='HEAD',
                                           cdn_request=True)

        if response.status == httplib.NO_CONTENT:
            cdn_url = response.headers['x-cdn-uri']
            return cdn_url
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(value='',
                                             container_name=container_name,
                                             driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_object_cdn_url(self, obj):
        container_cdn_url = self.get_container_cdn_url(container=obj.container)
        return '%s/%s' % (container_cdn_url, obj.name)

    def enable_container_cdn(self, container):
        container_name = container.name
        response = self.connection.request('/%s' % (container_name),
                                           method='PUT',
                                           cdn_request=True)

        if response.status in [ httplib.CREATED, httplib.ACCEPTED ]:
            return True

        return False


class CloudFilesUSStorageDriver(CloudFilesStorageDriver):
    """
    Cloudfiles storage driver for the US endpoint.
    """

    type = Provider.CLOUDFILES_US
    name = 'CloudFiles (US)'
    connectionCls = CloudFilesUSConnection

class CloudFilesUKStorageDriver(CloudFilesStorageDriver):
    """
    Cloudfiles storage driver for the UK endpoint.
    """

    type = Provider.CLOUDFILES_UK
    name = 'CloudFiles (UK)'
    connectionCls = CloudFilesUKConnection
