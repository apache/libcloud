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
import urlparse
import os.path
import urllib

try:
    import json
except:
    import simplejson as json

from libcloud import utils
from libcloud.common.types import MalformedResponseError, LibcloudError
from libcloud.common.types import InvalidCredsError
from libcloud.common.base import ConnectionUserAndKey, Response

from libcloud.storage.providers import Provider
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.types import InvalidContainerNameError

from libcloud.common.rackspace import AUTH_HOST_US, AUTH_HOST_UK, RackspaceBaseConnection

API_VERSION = 'v1.0'

class CloudFilesResponse(Response):

    valid_response_codes = [ httplib.NOT_FOUND, httplib.CONFLICT ]

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299 or i in self.valid_response_codes

    def parse_body(self):
        if not self.body:
            return None

        if 'content-type' in self.headers:
            key = 'content-type'
        elif 'Content-Type' in self.headers:
            key = 'Content-Type'
        else:
            raise LibcloudError('Missing content-type header')

        content_type = self.headers[key]
        if content_type.find(';') != -1:
            content_type = content_type.split(';')[0]

        if content_type == 'application/json':
            try:
                data = json.loads(self.body)
            except:
                raise MalformedResponseError('Failed to parse JSON',
                                             body=self.body,
                                             driver=CloudFilesStorageDriver)
        elif content_type == 'text/plain':
            data = self.body
        else:
            data = self.body

        return data


class CloudFilesConnection(RackspaceBaseConnection):
    """
    Base connection class for the Cloudfiles driver.
    """

    responseCls = CloudFilesResponse
    auth_host = None
    _url_key = "storage_url"

    def __init__(self, user_id, key, secure=True):
        super(CloudFilesConnection, self).__init__(user_id, key, secure=secure)
        self.api_version = API_VERSION
        self.accept_format = 'application/json'

    def request(self, action, params=None, data='', headers=None, method='GET',
                raw=False):
        if not headers:
            headers = {}
        if not params:
            params = {}
        # Due to first-run authentication request, we may not have a path
        if self.request_path:
            action = self.request_path + action
            params['format'] = 'json'
        if method in [ 'POST', 'PUT' ]:
            headers = {'Content-Type': 'application/json; charset=UTF-8'}

        return super(CloudFilesConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers,
            raw=raw
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


class CloudFilesStorageDriver(StorageDriver):
    """
    Base CloudFiles driver.

    You should never create an instance of this class directly but use US/US
    class.
    """
    name = 'CloudFiles'
    connectionCls = CloudFilesConnection
    hash_type = 'md5'

    def get_meta_data(self):
        response = self.connection.request('', method='HEAD')

        if response.status == httplib.NO_CONTENT:
            container_count = response.headers.get('x-account-container-count', 'unknown')
            object_count = response.headers.get('x-account-object-count', 'unknown')
            bytes_used = response.headers.get('x-account-bytes-used', 'unknown')

            return { 'container_count': int(container_count),
                      'object_count': int(object_count),
                      'bytes_used': int(bytes_used) }

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def list_containers(self):
        response = self.connection.request('')

        if response.status == httplib.NO_CONTENT:
            return []
        elif response.status == httplib.OK:
            return self._to_container_list(json.loads(response.body))

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def list_container_objects(self, container):
        response = self.connection.request('/%s' % (container.name))

        if response.status == httplib.NO_CONTENT:
            # Empty or inexistent container
            return []
        elif response.status == httplib.OK:
            return self._to_object_list(json.loads(response.body), container)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_container(self, container_name):
        response = self.connection.request('/%s' % (container_name),
                                                    method='HEAD')

        if response.status == httplib.NO_CONTENT:
            container = self._headers_to_container(container_name, response.headers)
            return container
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(None, self, container_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def get_object(self, container_name, object_name):
        container = self.get_container(container_name)
        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                                       method='HEAD')

        if response.status in [ httplib.OK, httplib.NO_CONTENT ]:
            obj = self._headers_to_object(object_name, container, response.headers)
            return obj
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(None, self, object_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def create_container(self, container_name):
        container_name = self._clean_container_name(container_name)
        response = self.connection.request('/%s' % (container_name), method='PUT')

        if response.status == httplib.CREATED:
            # Accepted mean that container is not yet created but it will be
            # eventually
            extra = { 'object_count': 0 }
            container = Container(name=container_name, extra=extra, driver=self)

            return container
        elif response.status == httplib.ACCEPTED:
            error = ContainerAlreadyExistsError(None, self, container_name)
            raise error

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def delete_container(self, container):
        name = self._clean_container_name(container.name)

        # Only empty container can be deleted
        response = self.connection.request('/%s' % (name), method='DELETE')

        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(value='',
                                             container_name=name, driver=self)
        elif response.status == httplib.CONFLICT:
            # @TODO: Add "delete_all_objects" parameter?
            raise ContainerIsNotEmptyError(value='',
                                           container_name=name, driver=self)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        return self._get_object(obj, self._save_object,
                                {'obj': obj,
                                 'destination_path': destination_path,
                                 'overwrite_existing': overwrite_existing,
                                 'delete_on_failure': delete_on_failure})

    def download_object_as_stream(self, obj, chunk_size=None):
        return self._get_object(obj, self._get_object_as_stream,
                                {'chunk_size': chunk_size})

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        Upload an object.

        Note: This will override file with a same name if it already exists.
        """
        upload_func = self._upload_file
        upload_func_args = { 'file_path': file_path }

        return self._put_object(container=container, file_path=file_path,
                                object_name=object_name, extra=extra,
                                upload_func=upload_func,
                                upload_func_args=upload_func_args)

    def upload_object_via_stream(self, iterator, container, object_name, extra=None):
        if isinstance(iterator, file):
            iterator = iter(iterator)

        upload_func = self._stream_data
        upload_func_args = { 'iterator': iterator }

        return self._put_object(container=container, iterator=iterator,
                                object_name=object_name, extra=extra,
                                upload_func=upload_func,
                                upload_func_args=upload_func_args)

    def delete_object(self, obj):
        container_name = self._clean_container_name(obj.container.name)
        object_name = self._clean_object_name(obj.name)

        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name), method='DELETE')

        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(value='', object_name=object_name,
                                          driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def _get_object(self, obj, callback, callback_args):
        container_name = obj.container.name
        object_name = obj.name

        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                           raw=True)

        callback_args['response'] = response.response

        if response.status == httplib.OK:
            return callback(**callback_args)
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(name=object_name)

        raise LibcloudError('Unexpected status code: %s' % (response.status))

    def _put_object(self, upload_func, upload_func_args, container, object_name,
                    extra=None, file_path=None, iterator=None, file_hash=None):
        container_name_cleaned = self._clean_container_name(container.name)
        object_name_cleaned = self._clean_object_name(object_name)

        extra = extra or {}
        content_type = extra.get('content_type', None)
        meta_data = extra.get('meta_data', None)

        if not content_type:
            if file_path:
                name = file_path
            else:
                name = object_name
            content_type, _ = utils.guess_file_mime_type(name)

            if not content_type:
                raise AttributeError('File content-type could not be guessed and' +
                                     ' no content_type value provided')

        headers = {}
        if iterator:
            headers['Transfer-Encoding'] = 'chunked'
            upload_func_args['chunked'] = True
        else:
            file_size = os.path.getsize(file_path)
            headers['Content-Length'] = file_size
            upload_func_args['chunked'] = False

            if file_hash:
                headers['ETag'] = file_hash

        headers['Content-Type'] = content_type

        if meta_data:
            for key, value in meta_data.iteritems():
                key = 'X-Object-Meta-%s' % (key)
                headers[key] = value

        response = self.connection.request('/%s/%s' % (container_name_cleaned,
                                                       object_name_cleaned),
                                           method='PUT', data=None,
                                           headers=headers, raw=True)

        upload_func_args['response'] = response
        success, data_hash, bytes_transferred = upload_func(**upload_func_args)

        if not success:
            raise LibcloudError('Object upload failed, Perhaps a timeout?')

        response = response.response

        if response.status == httplib.EXPECTATION_FAILED:
            raise LibcloudError('Missing content-type header')
        elif response.status == httplib.UNPROCESSABLE_ENTITY:
            raise ObjectHashMismatchError(value='MD5 hash checksum does not match',
                                          object_name=object_name, driver=self)
        elif response.status == httplib.CREATED:
            obj = Object(name=object_name, size=bytes_transferred, hash=file_hash,
                         extra=None, meta_data=meta_data, container=container,
                         driver=self)

            return obj

    def _clean_container_name(self, name):
        """
        Clean container name.
        """
        if name.startswith('/'):
            name = name[1:]
        name = urllib.quote(name)

        if name.find('/') != -1:
            raise InvalidContainerNameError(value='Container name cannot'
                                                  ' contain slashes',
                                            container_name=name, driver=self)

        if len(name) > 256:
            raise InvalidContainerNameError(value='Container name cannot be'
                                                   ' longer than 256 bytes',
                                            container_name=name, driver=self)


        return name

    def _clean_object_name(self, name):
        name = urllib.quote(name)
        return name

    def _to_container_list(self, response):
        # @TODO: Handle more then 10k containers - use "lazy list"?
        containers = []

        for container in response:
            extra = { 'object_count': int(container['count']),
                      'size': int(container['bytes'])}
            containers.append(Container(name=container['name'], extra=extra,
                                        driver=self))

        return containers

    def _to_object_list(self, response, container):
        objects = []

        for obj in response:
            name = obj['name']
            size = int(obj['bytes'])
            hash = obj['hash']
            extra = { 'content_type': obj['content_type'],
                      'last_modified': obj['last_modified'] }
            objects.append(Object(name=name, size=size, hash=hash, extra=extra,
                                  meta_data=None, container=container, driver=self))

        return objects

    def _headers_to_container(self, name, headers):
        size = int(headers.get('x-container-bytes-used', 0))
        object_count = int(headers.get('x-container-object-count', 0))

        extra = { 'object_count': object_count,
                  'size': size }
        container = Container(name=name, extra=extra, driver=self)
        return container

    def _headers_to_object(self, name, container, headers):
        size = int(headers.pop('content-length', 0))
        last_modified = headers.pop('last-modified', None)
        etag = headers.pop('etag', None)
        content_type = headers.pop('content-type', None)

        meta_data = {}
        for key, value in headers.iteritems():
            if key.find('x-object-meta-') != -1:
                key = key.replace('x-object-meta-', '')
                meta_data[key] = value

        extra = { 'content_type': content_type, 'last_modified': last_modified,
                  'etag': etag }

        obj = Object(name=name, size=size, hash=None, extra=extra,
                     meta_data=meta_data, container=container, driver=self)
        return obj

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
