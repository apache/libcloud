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

"""
Provides base classes for working with storage
"""

# Backward compatibility for Python 2.5
from __future__ import with_statement

from typing import Type

import os.path                          # pylint: disable-msg=W0404
import hashlib
from os.path import join as pjoin

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

import libcloud.utils.files
from libcloud.common.types import LibcloudError
from libcloud.common.base import Connection
from libcloud.common.base import ConnectionUserAndKey, BaseDriver
from libcloud.storage.types import ObjectDoesNotExistError

__all__ = [
    'Object',
    'Container',
    'StorageDriver',

    'CHUNK_SIZE',
    'DEFAULT_CONTENT_TYPE'
]

CHUNK_SIZE = 8096

# Default Content-Type which is sent when uploading an object if one is not
# supplied and can't be detected when using non-strict mode.
DEFAULT_CONTENT_TYPE = 'application/octet-stream'


class Object(object):
    """
    Represents an object (BLOB).
    """

    def __init__(self, name, size, hash, extra, meta_data, container,
                 driver):
        """
        :param name: Object name (must be unique per container).
        :type  name: ``str``

        :param size: Object size in bytes.
        :type  size: ``int``

        :param hash: Object hash.
        :type  hash: ``str``

        :param container: Object container.
        :type  container: :class:`Container`

        :param extra: Extra attributes.
        :type  extra: ``dict``

        :param meta_data: Optional object meta data.
        :type  meta_data: ``dict``

        :param driver: StorageDriver instance.
        :type  driver: :class:`StorageDriver`
        """

        self.name = name
        self.size = size
        self.hash = hash
        self.container = container
        self.extra = extra or {}
        self.meta_data = meta_data or {}
        self.driver = driver

    def get_cdn_url(self):
        return self.driver.get_object_cdn_url(obj=self)

    def enable_cdn(self, **kwargs):
        return self.driver.enable_object_cdn(obj=self, **kwargs)

    def download(self, destination_path, overwrite_existing=False,
                 delete_on_failure=True):
        return self.driver.download_object(self, destination_path,
                                           overwrite_existing,
                                           delete_on_failure)

    def as_stream(self, chunk_size=None):
        return self.driver.download_object_as_stream(self, chunk_size)

    def delete(self):
        return self.driver.delete_object(self)

    def __repr__(self):
        return ('<Object: name=%s, size=%s, hash=%s, provider=%s ...>' %
                (self.name, self.size, self.hash, self.driver.name))


class Container(object):
    """
    Represents a container (bucket) which can hold multiple objects.
    """

    def __init__(self, name, extra, driver):
        """
        :param name: Container name (must be unique).
        :type name: ``str``

        :param extra: Extra attributes.
        :type extra: ``dict``

        :param driver: StorageDriver instance.
        :type driver: :class:`StorageDriver`
        """

        self.name = name
        self.extra = extra or {}
        self.driver = driver

    def iterate_objects(self):
        return self.driver.iterate_container_objects(container=self)

    def list_objects(self):
        return self.driver.list_container_objects(container=self)

    def get_cdn_url(self):
        return self.driver.get_container_cdn_url(container=self)

    def enable_cdn(self, **kwargs):
        return self.driver.enable_container_cdn(container=self, **kwargs)

    def get_object(self, object_name):
        return self.driver.get_object(container_name=self.name,
                                      object_name=object_name)

    def upload_object(self, file_path, object_name, extra=None, **kwargs):
        return self.driver.upload_object(
            file_path, self, object_name, extra=extra, **kwargs)

    def upload_object_via_stream(self, iterator, object_name, extra=None,
                                 **kwargs):
        return self.driver.upload_object_via_stream(
            iterator, self, object_name, extra=extra, **kwargs)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        return self.driver.download_object(
            obj, destination_path, overwrite_existing=overwrite_existing,
            delete_on_failure=delete_on_failure)

    def download_object_as_stream(self, obj, chunk_size=None):
        return self.driver.download_object_as_stream(obj, chunk_size)

    def delete_object(self, obj):
        return self.driver.delete_object(obj)

    def delete(self):
        return self.driver.delete_container(self)

    def __repr__(self):
        return ('<Container: name=%s, provider=%s>'
                % (self.name, self.driver.name))


class StorageDriver(BaseDriver):
    """
    A base StorageDriver to derive from.
    """

    connectionCls = ConnectionUserAndKey  # type: Type[Connection]
    name = None  # type: str
    hash_type = 'md5'  # type: str
    supports_chunked_encoding = False  # type: bool

    # When strict mode is used, exception will be thrown if no content type is
    # provided and none can be detected when uploading an object
    strict_mode = False  # type: bool

    def iterate_containers(self):
        """
        Return a generator of containers for the given account

        :return: A generator of Container instances.
        :rtype: ``generator`` of :class:`Container`
        """
        raise NotImplementedError(
            'iterate_containers not implemented for this driver')

    def list_containers(self):
        """
        Return a list of containers.

        :return: A list of Container instances.
        :rtype: ``list`` of :class:`Container`
        """
        return list(self.iterate_containers())

    def iterate_container_objects(self, container):
        """
        Return a generator of objects for the given container.

        :param container: Container instance
        :type container: :class:`Container`

        :return: A generator of Object instances.
        :rtype: ``generator`` of :class:`Object`
        """
        raise NotImplementedError(
            'iterate_container_objects not implemented for this driver')

    def list_container_objects(self, container, ex_prefix=None):
        """
        Return a list of objects for the given container.

        :param container: Container instance.
        :type container: :class:`Container`

        :param ex_prefix: Filter objects starting with a prefix.
        :type  ex_prefix: ``str``

        :return: A list of Object instances.
        :rtype: ``list`` of :class:`Object`
        """
        return list(self.iterate_container_objects(container))

    def get_container(self, container_name):
        """
        Return a container instance.

        :param container_name: Container name.
        :type container_name: ``str``

        :return: :class:`Container` instance.
        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'get_object not implemented for this driver')

    def get_container_cdn_url(self, container):
        """
        Return a container CDN URL.

        :param container: Container instance
        :type  container: :class:`Container`

        :return: A CDN URL for this container.
        :rtype: ``str``
        """
        raise NotImplementedError(
            'get_container_cdn_url not implemented for this driver')

    def get_object(self, container_name, object_name):
        """
        Return an object instance.

        :param container_name: Container name.
        :type  container_name: ``str``

        :param object_name: Object name.
        :type  object_name: ``str``

        :return: :class:`Object` instance.
        :rtype: :class:`Object`
        """
        raise NotImplementedError(
            'get_object not implemented for this driver')

    def get_object_cdn_url(self, obj):
        """
        Return an object CDN URL.

        :param obj: Object instance
        :type  obj: :class:`Object`

        :return: A CDN URL for this object.
        :rtype: ``str``
        """
        raise NotImplementedError(
            'get_object_cdn_url not implemented for this driver')

    def enable_container_cdn(self, container):
        """
        Enable container CDN.

        :param container: Container instance
        :type  container: :class:`Container`

        :rtype: ``bool``
        """
        raise NotImplementedError(
            'enable_container_cdn not implemented for this driver')

    def enable_object_cdn(self, obj):
        """
        Enable object CDN.

        :param obj: Object instance
        :type  obj: :class:`Object`

        :rtype: ``bool``
        """
        raise NotImplementedError(
            'enable_object_cdn not implemented for this driver')

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        """
        Download an object to the specified destination path.

        :param obj: Object instance.
        :type obj: :class:`Object`

        :param destination_path: Full path to a file or a directory where the
                                 incoming file will be saved.
        :type destination_path: ``str``

        :param overwrite_existing: True to overwrite an existing file,
                                   defaults to False.
        :type overwrite_existing: ``bool``

        :param delete_on_failure: True to delete a partially downloaded file if
                                   the download was not successful (hash
                                   mismatch / file size).
        :type delete_on_failure: ``bool``

        :return: True if an object has been successfully downloaded, False
                 otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'download_object not implemented for this driver')

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        Return a generator which yields object data.

        :param obj: Object instance
        :type obj: :class:`Object`

        :param chunk_size: Optional chunk size (in bytes).
        :type chunk_size: ``int``
        """
        raise NotImplementedError(
            'download_object_as_stream not implemented for this driver')

    def upload_object(self, file_path, container, object_name, extra=None,
                      verify_hash=True, headers=None):
        """
        Upload an object currently located on a disk.

        :param file_path: Path to the object on disk.
        :type file_path: ``str``

        :param container: Destination container.
        :type container: :class:`Container`

        :param object_name: Object name.
        :type object_name: ``str``

        :param verify_hash: Verify hash
        :type verify_hash: ``bool``

        :param extra: Extra attributes (driver specific). (optional)
        :type extra: ``dict``

        :param headers: (optional) Additional request headers,
            such as CORS headers. For example:
            headers = {'Access-Control-Allow-Origin': 'http://mozilla.com'}
        :type headers: ``dict``

        :rtype: :class:`Object`
        """
        raise NotImplementedError(
            'upload_object not implemented for this driver')

    def upload_object_via_stream(self, iterator, container,
                                 object_name,
                                 extra=None,
                                 headers=None):
        """
        Upload an object using an iterator.

        If a provider supports it, chunked transfer encoding is used and you
        don't need to know in advance the amount of data to be uploaded.

        Otherwise if a provider doesn't support it, iterator will be exhausted
        so a total size for data to be uploaded can be determined.

        Note: Exhausting the iterator means that the whole data must be
        buffered in memory which might result in memory exhausting when
        uploading a very large object.

        If a file is located on a disk you are advised to use upload_object
        function which uses fs.stat function to determine the file size and it
        doesn't need to buffer whole object in the memory.

        :param iterator: An object which implements the iterator interface.
        :type iterator: :class:`object`

        :param container: Destination container.
        :type container: :class:`Container`

        :param object_name: Object name.
        :type object_name: ``str``

        :param extra: (optional) Extra attributes (driver specific). Note:
            This dictionary must contain a 'content_type' key which represents
            a content type of the stored object.
        :type extra: ``dict``

        :param headers: (optional) Additional request headers,
            such as CORS headers. For example:
            headers = {'Access-Control-Allow-Origin': 'http://mozilla.com'}
        :type headers: ``dict``

        :rtype: ``object``
        """
        raise NotImplementedError(
            'upload_object_via_stream not implemented for this driver')

    def delete_object(self, obj):
        """
        Delete an object.

        :param obj: Object instance.
        :type obj: :class:`Object`

        :return: ``bool`` True on success.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'delete_object not implemented for this driver')

    def create_container(self, container_name):
        """
        Create a new container.

        :param container_name: Container name.
        :type container_name: ``str``

        :return: Container instance on success.
        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'create_container not implemented for this driver')

    def delete_container(self, container):
        """
        Delete a container.

        :param container: Container instance
        :type container: :class:`Container`

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'delete_container not implemented for this driver')

    def _get_object(self, obj, callback, callback_kwargs, response,
                    success_status_code=None):
        """
        Call passed callback and start transfer of the object'

        :param obj: Object instance.
        :type obj: :class:`Object`

        :param callback: Function which is called with the passed
            callback_kwargs
        :type callback: :class:`function`

        :param callback_kwargs: Keyword arguments which are passed to the
             callback.
        :type callback_kwargs: ``dict``

        :param response: Response instance.
        :type response: :class:`Response`

        :param success_status_code: Status code which represents a successful
                                    transfer (defaults to httplib.OK)
        :type success_status_code: ``int``

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """
        success_status_code = success_status_code or httplib.OK

        if response.status == success_status_code:
            return callback(**callback_kwargs)
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(object_name=obj.name,
                                          value='', driver=self)

        raise LibcloudError(value='Unexpected status code: %s' %
                                  (response.status),
                            driver=self)

    def _save_object(self, response, obj, destination_path,
                     overwrite_existing=False, delete_on_failure=True,
                     chunk_size=None):
        """
        Save object to the provided path.

        :param response: RawResponse instance.
        :type response: :class:`RawResponse`

        :param obj: Object instance.
        :type obj: :class:`Object`

        :param destination_path: Destination directory.
        :type destination_path: ``str``

        :param delete_on_failure: True to delete partially downloaded object if
                                  the download fails.
        :type delete_on_failure: ``bool``

        :param overwrite_existing: True to overwrite a local path if it already
                                   exists.
        :type overwrite_existing: ``bool``

        :param chunk_size: Optional chunk size
            (defaults to ``libcloud.storage.base.CHUNK_SIZE``, 8kb)
        :type chunk_size: ``int``

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """

        chunk_size = chunk_size or CHUNK_SIZE

        base_name = os.path.basename(destination_path)

        if not base_name and not os.path.exists(destination_path):
            raise LibcloudError(
                value='Path %s does not exist' % (destination_path),
                driver=self)

        if not base_name:
            file_path = pjoin(destination_path, obj.name)
        else:
            file_path = destination_path

        if os.path.exists(file_path) and not overwrite_existing:
            raise LibcloudError(
                value='File %s already exists, but ' % (file_path) +
                'overwrite_existing=False',
                driver=self)

        bytes_transferred = 0

        with open(file_path, 'wb') as file_handle:
            for chunk in response._response.iter_content(chunk_size):
                file_handle.write(b(chunk))
                bytes_transferred += len(chunk)

        if int(obj.size) != int(bytes_transferred):
            # Transfer failed, support retry?
            if delete_on_failure:
                try:
                    os.unlink(file_path)
                except Exception:
                    pass

            return False

        return True

    def _upload_object(self, object_name, content_type, request_path,
                       request_method='PUT',
                       headers=None, file_path=None, stream=None,
                       upload_func=None, upload_func_kwargs=None,
                       chunked=False, multipart=False):
        """
        Helper function for setting common request headers and calling the
        passed in callback which uploads an object.
        """
        headers = headers or {}

        if file_path and not os.path.exists(file_path):
            raise OSError('File %s does not exist' % (file_path))

        if stream is not None and not hasattr(stream, 'next') and not \
                hasattr(stream, '__next__'):
            raise AttributeError('iterator object must implement next() ' +
                                 'method.')

        if not content_type:
            if file_path:
                name = file_path
            else:
                name = object_name
            content_type, _ = libcloud.utils.files.guess_file_mime_type(name)

            if not content_type:
                if self.strict_mode:
                    raise AttributeError('File content-type could not be '
                                         'guessed and no content_type value '
                                         'is provided')
                else:
                    # Fallback to a content-type
                    content_type = DEFAULT_CONTENT_TYPE

        headers['Content-Type'] = content_type
        if stream:
            response = self.connection.request(
                request_path,
                method=request_method, data=stream,
                headers=headers, raw=True)
            stream_hash, stream_length = self._hash_buffered_stream(
                stream,
                self._get_hash_function())
        else:
            with open(file_path, 'rb') as file_stream:
                response = self.connection.request(
                    request_path,
                    method=request_method, data=file_stream,
                    headers=headers, raw=True)
            with open(file_path, 'rb') as file_stream:
                stream_hash, stream_length = self._hash_buffered_stream(
                    file_stream,
                    self._get_hash_function())

        if not response.success():
            response.parse_error()

        if upload_func:
            upload_func(**upload_func_kwargs)

        return {'response': response,
                'bytes_transferred': stream_length,
                'data_hash': stream_hash}

    def _hash_buffered_stream(self, stream, hasher, blocksize=65536):
        total_len = 0

        if hasattr(stream, '__next__') or hasattr(stream, 'next'):
            # Ensure we start from the begining of a stream in case stream is
            # not at the beginning
            if hasattr(stream, 'seek'):
                stream.seek(0)

            for chunk in libcloud.utils.files.read_in_chunks(iterator=stream):
                hasher.update(b(chunk))
                total_len += len(chunk)

            return (hasher.hexdigest(), total_len)

        if not hasattr(stream, '__exit__'):
            for s in stream:
                hasher.update(s)
                total_len = total_len + len(s)
            return (hasher.hexdigest(), total_len)

        with stream:
            buf = stream.read(blocksize)
            while len(buf) > 0:
                total_len = total_len + len(buf)
                hasher.update(buf)
                buf = stream.read(blocksize)

        return (hasher.hexdigest(), total_len)

    def _get_hash_function(self):
        """
        Return instantiated hash function for the hash type supported by
        the provider.
        """
        try:
            func = getattr(hashlib, self.hash_type)()
        except AttributeError:
            raise RuntimeError('Invalid or unsupported hash type: %s' %
                               (self.hash_type))

        return func
