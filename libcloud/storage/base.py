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

# Backward compatibility for Python 2.5
from __future__ import with_statement

import os
import os.path
import hashlib
from os.path import join as pjoin

from libcloud import utils
from libcloud.common.types import LibcloudError
from libcloud.common.base import ConnectionKey

CHUNK_SIZE = 8096

class Object(object):
    """
    Represents an object (BLOB).
    """

    def __init__(self, name, size, hash, extra, meta_data, container,
                 driver):
        """
        @type name: C{str}
        @param name: Object name (must be unique per container).

        @type size: C{int}
        @param size: Object size in bytes.

        @type hash: C{string}
        @param hash Object hash.

        @type container: C{Container}
        @param container: Object container.

        @type extra: C{dict}
        @param extra: Extra attributes.

        @type meta_data: C{dict}
        @param meta_data: Optional object meta data.

        @type driver: C{StorageDriver}
        @param driver: StorageDriver instance.
        """

        self.name = name
        self.size = size
        self.hash = hash
        self.container = container
        self.extra = extra or {}
        self.meta_data = meta_data or {}
        self.driver = driver

    def download(self, destination_path, overwrite_existing=False,
                 delete_on_failure=True):
        return self.driver.download_object(self, destination_path,
                                           overwrite_existing,
                                           delete_on_failure)

    def as_stream(self, chunk_size=None):
        return self.driver.object_as_stream(self, chunk_size)

    def delete(self):
        return self.driver.delete_object(self)

    def __repr__(self):
        return '<Object: name=%s, size=%s, hash=%s, provider=%s ...>' % \
        (self.name, self.size, self.hash, self.driver.name)

class Container(object):
    """
    Represents a container (bucket) which can hold multiple objects.
    """

    def __init__(self, name, extra, driver):
        """
        @type name: C{str}
        @param name: Container name (must be unique).

        @type extra: C{dict}
        @param extra: Extra attributes.

        @type driver: C{StorageDriver}
        @param driver: StorageDriver instance.
        """

        self.name = name
        self.extra = extra or {}
        self.driver = driver

    def list_objects(self):
        return self.driver.list_container_objects(self)

    def get_object(self, object_name):
        return self.driver.get_object(container_name=self.name,
                                      object_name=object_name)

    def upload_object(self, file_path, object_name, extra=None, file_hash=None):
        return self.driver.upload_object(file_path, self, object_name, extra, file_hash)

    def stream_object_data(self, iterator, object_name, extra=None):
        return self.driver.stream_object_data(iterator, self, object_name, extra)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        return self.driver.download_object(obj, destination_path)

    def object_as_stream(self, obj, chunk_size=None):
        return self.driver.object_as_stream(obj, chunk_size)

    def delete_object(self, obj):
        return self.driver.delete_object(obj)

    def delete(self):
        return self.driver.delete_container(self)

    def __repr__(self):
        return '<Container: name=%s, provider=%s>' % (self.name, self.driver.name)

class StorageDriver(object):
    """
    A base StorageDriver to derive from.
    """

    connectionCls = ConnectionKey
    name = None
    hash_type = 'md5'

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        self.key = key
        self.secret = secret
        self.secure = secure
        args = [self.key]

        if self.secret != None:
            args.append(self.secret)

        args.append(secure)

        if host != None:
            args.append(host)

        if port != None:
            args.append(port)

        self.connection = self.connectionCls(*args)

        self.connection.driver = self
        self.connection.connect()

    def get_meta_data(self):
        """
        Return account meta data - total number of containers, objects and
        number of bytes currently used.

        @return A C{dict} with account meta data.
        """
        raise NotImplementedError, \
            'get_account_meta_data not implemented for this driver'

    def list_containters(self):
        raise NotImplementedError, \
            'list_containers not implemented for this driver'

    def list_container_objects(self, container):
        """
        Return a list of objects for the given container.

        @type container: C{Container}
        @param container: Container instance

        @return A list of Object instances.
        """
        raise NotImplementedError, \
            'list_objects not implemented for this driver'

    def get_container(self, container_name):
        """
        Return a container instance.

        @type container_name: C{str}
        @param container_name: Container name.

        @return: C{Container} instance.
        """
        raise NotImplementedError, \
            'get_object not implemented for this driver'

    def get_object(self, container_name, object_name):
        """
        Return an object instance.

        @type container_name: C{str}
        @param container_name: Container name.

        @type object_name: C{str}
        @param object_name: Object name.

        @return: C{Object} instance.
        """
        raise NotImplementedError, \
            'get_object not implemented for this driver'

    def download_object(self, obj, destination_path, delete_on_failure=True):
        """
        Download an object to the specified destination path.

        @type obj; C{Object}
        @param obj: Object instance.

        @type destination_path: C{str}
        @type destination_path: Full path to a file or a directory where the
                                incoming file will be saved.

        @type overwrite_existing: C{bool}
        @type overwrite_existing: True to overwrite an existing file.

        @type delete_on_failure: C{bool}
        @param delete_on_failure: True to delete a partially downloaded file if
        the download was not successful (hash mismatch / file size).

        @return C{bool} True if an object has been successfully downloaded, False
        otherwise.
        """
        raise NotImplementedError, \
            'download_object not implemented for this driver'

    def object_as_stream(self, obj, chunk_size=None):
        """
        Return a generator which yields object data.

        @type obj: C{Object}
        @param obj: Object instance

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (in bytes).
        """
        raise NotImplementedError, \
            'object_as_stream not implemented for this driver'

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        Upload an object.

        @type file_path: C{str}
        @param file_path: Path to the object on disk.

        @type container: C{Container}
        @param container: Destination container.

        @type object_name: C{str}
        @param object_name: Object name.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).

        @type file_hash: C{str}
        @param file_hash: (optional) File hash. If provided object hash is
                          on upload and if it doesn't match the one provided an
                          exception is thrown.
        """
        raise NotImplementedError, \
            'upload_object not implemented for this driver'

    def stream_object_data(self, iterator, container, object_name, extra=None):
        """
        @type iterator: C{object}
        @param iterator: An object which implements the iterator interface.

        @type container: C{Container}
        @param container: Destination container.

        @type object_name: C{str}
        @param object_name: Object name.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).
        """
        raise NotImplementedError, \
            'stream_object_data not implemented for this driver'

    def delete_object(self, obj):
        """
        Delete an object.

        @type obj: C{Object}
        @param obj: Object instance.

        @return: C{bool} True on success.
        """
        raise NotImplementedError, \
            'delete_object not implemented for this driver'

    def create_container(self, container_name):
        """
        Create a new container.

        @type container_name: C{str}
        @param container_name: Container name.

        @return C{Container} instance on success.
        """
        raise NotImplementedError, \
            'create_container not implemented for this driver'

    def delete_container(self, container):
        """
        Delete a container.

        @type container: C{Container}
        @param container: Container instance

        @return C{bool} True on success, False otherwise.
        """
        raise NotImplementedError, \
            'delete_container not implemented for this driver'

    def _save_object(self, response, obj, destination_path,
                     overwrite_existing=False, delete_on_failure=True,
                     chunk_size=None):
        """
        Save object to the provided path.

        @type response: C{RawResponse}
        @param response: RawResponse instance.

        @type obj: C{Object}
        @param obj: Object instance.

        @type destination_path: C{Str}
        @param destination_path: Destination directory.

        @type delete_on_failure: C{bool}
        @param delete_on_failure: True to delete partially downloaded object if
                                  the download fails.
        @type overwrite_existing: C{bool}
        @param overwrite_existing: True to overwrite a local path if it already
                                   exists.

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)

        @return C{bool} True on success, False otherwise.
        """

        chunk_size = chunk_size or CHUNK_SIZE

        base_name = os.path.basename(destination_path)

        if not base_name and not os.path.exists(destination_path):
            raise LibcloudError(value='Path %s does not exist' % (destination_path),
                                driver=self)

        if not base_name:
            file_path = pjoin(destination_path, obj.name)
        else:
            file_path = destination_path

        if os.path.exists(file_path) and not overwrite_existing:
            raise LibcloudError(value='File %s already exists, but ' % (file_path) +
                                'overwrite_existing=False',
                                driver=self)

        stream = utils.read_in_chunks(response, chunk_size)

        try:
            data_read = stream.next()
        except StopIteration:
            # Empty response?
            return False

        bytes_transferred = 0

        with open(file_path, 'wb') as file_handle:
            while len(data_read) > 0:
                file_handle.write(data_read)
                bytes_transferred += len(data_read)

                try:
                    data_read = stream.next()
                except StopIteration:
                    data_read = ''

        if obj.size != bytes_transferred:
            # Transfer failed, support retry?
            if delete_on_failure:
                try:
                    os.unlink(file_path)
                except Exception:
                    pass

            return False

        return True

    def _stream_data(self, response, iterator, chunked=False,
                     calculate_hash=True, chunk_size=None):
        """
        Stream a data over an http connection.

        @type response: C{RawResponse}
        @param response: RawResponse object.

        @type iterator: C{}
        @param response: An object which implements an iterator interface
                         or a File like object with read method.

        @type chunk_size: C{int}
        @param chunk_size: Optional chunk size (defaults to CHUNK_SIZE)

        @return C{tuple} First item is a boolean indicator of success, second
                         one is the uploaded data MD5 hash and the third one
                         is the number of transferred bytes.
        """

        chunk_size = chunk_size or CHUNK_SIZE

        data_hash = None
        if calculate_hash:
            data_hash = hashlib.md5()

        generator = utils.read_in_chunks(iterator, chunk_size)

        bytes_transferred = 0
        try:
            chunk = generator.next()
        except StopIteration:
            # No data?
            return False, None, None

        while len(chunk) > 0:
            if calculate_hash:
                try:
                    if chunked:
                        response.connection.connection.send('%X\r\n' %
                                                           (len(chunk)))
                        response.connection.connection.send(chunk)
                        response.connection.connection.send('\r\n')
                    else:
                        response.connection.connection.send(chunk)
                except Exception, e:
                    # Timeout, etc.
                    return False, None, bytes_transferred

                bytes_transferred += len(chunk)
                if calculate_hash:
                    data_hash.update(chunk)

                try:
                    chunk = generator.next()
                except StopIteration:
                    chunk = ''

        if chunked:
                response.connection.connection.send('0\r\n\r\n')

        if calculate_hash:
            data_hash = data_hash.hexdigest()

        return True, data_hash, bytes_transferred

    def _upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
        """
        Upload a file to the server.

        @type response: C{RawResponse}
        @param response: RawResponse object.

        @type file_path: C{str}
        @param file_path: Path to a local file.

        @type iterator: C{}
        @param response: An object which implements an iterator interface (File
                         object, etc.)

        @return C{tuple} First item is a boolean indicator of success, second
                         one is the uploaded data MD5 hash and the third one
                         is the number of transferred bytes.
        """
        with open (file_path, 'rb') as file_handle:
            success, data_hash, bytes_transferred = \
                     self._stream_data(response=response,
                                       iterator=iter(file_handle),
                                       chunked=chunked,
                                       calculate_hash=calculate_hash)

        return success, data_hash, bytes_transferred
