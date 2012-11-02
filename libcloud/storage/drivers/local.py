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
Provides storage driver for working with local filesystem
"""

import os
import shutil

from lockfile import mkdirlockfile
from pwd import getpwuid
from libcloud.utils.py3 import next
from libcloud.common.base import Connection
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.common.types import LibcloudError, LazyList
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import InvalidContainerNameError

CHUNK_SIZE = 16384
IGNORE_FOLDERS = ['.lock', '.hash']

class LockLocalStorage:
    """
    A class to help in locking a local path before being updated
    """
    def __init__(self, path):
        self.path = path
        self.lock = mkdirlockfile.MkdirLockFile(self.path, threaded=True)

    def __enter__(self):
        try:
            self.lock.acquire(timeout=0.1)
        except lockfile.LockTimeout:
            raise LibcloudError('Lock timeout')

    def __exit__(self, type, value, traceback):
        if self.lock.is_locked():
            self.lock.release()

        if value is not None:
            raise value

class LocalStorageDriver(StorageDriver):
    """
    Implementation of local file-system based storage. This is helpful
    where the user would want to use the same code (using libcloud) and
    switch between cloud storage and local storage
    """

    connectionCls = Connection
    name = 'Local Storage'

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 **kwargs):

        # Use the key as the path to the storage
        self.base_path = key[0]

        if not os.path.isdir(self.base_path):
            raise LibcloudError('The base path is not a directory')

        super(StorageDriver, self).__init__(key=key, secret=secret,
                                            secure=secure, host=host,
                                            port=port, **kwargs)

    def _make_path(self, path, ignore_existing=True):
        """
        Create a path by checking if it already exists
        """

        try:
            os.makedirs(path)
        except OSError, exp:
            if exp.errno == 17 and not ignore_existing:
                raise exp

    def _make_container(self, container_name):
        """
        Create a container instance

        @param container_name: Container name.
        @type container_name: C{str}

        @return: Container instance.
        @rtype: L{Container}
        """

        if '/' in container_name:
            raise InvalidContainerNameError(value=None, driver=self,
                                            container_name=container_name)

        full_path = os.path.join(self.base_path, container_name)

        try:
            stat = os.stat(full_path)
            if not os.path.isdir(full_path):
                raise ValueError
        except Exception:
            raise ContainerDoesNotExistError(value=None, driver=self,
                                             container_name=container_name)

        extra = {}
        extra['creation_time'] = stat.st_ctime
        extra['access_time'] = stat.st_atime
        extra['modify_time'] = stat.st_mtime
        extra['owner'] = getpwuid(stat.st_uid).pw_name

        return Container(name=container_name, extra=extra, driver=self)

    def _make_object(self, container, object_name):
        """
        Create an object instance

        @param container: Container.
        @type container: L{Container}

        @param object_name: Object name.
        @type object_name: C{str}

        @return: Object instance.
        @rtype: L{Object}
        """

        full_path = os.path.join(self.base_path, container.name, object_name)

        if os.path.isdir(full_path):
            raise ObjectError(value=None, driver=self, object_name=object_name)

        try:
            stat = os.stat(full_path)
        except Exception:
            raise ObjectDoesNotExistError(value=None, driver=self,
                                          object_name=object_name)

        extra = {}
        extra['creation_time'] = stat.st_ctime
        extra['access_time'] = stat.st_atime
        extra['modify_time'] = stat.st_mtime

        meta_data = {}
        meta_data['owner'] = getpwuid(stat.st_uid).pw_name

        return Object(name=object_name, size=stat.st_size, extra=extra,
                      driver=self, container=container, hash=None,
                      meta_data=meta_data)

    def list_containers(self):
        """
        Return a list of containers.

        @return: A list of Container instances.
        @rtype: C{list} of L{Container}
        """

        containers = []

        for container_name in os.listdir(self.base_path):
            full_path = os.path.join(self.base_path, container_name)
            if not os.path.isdir(full_path):
                continue
            containers.append(self._make_container(container_name))

        return containers

    def _get_objects(self, container):
        """
        Recursively iterate through the file-system and return the object names
        """

        cpath = self.get_container_cdn_url(container, check=True)

        for folder, subfolders, files in os.walk(cpath, topdown=True):
            # Remove unwanted subfolders
            for subf in IGNORE_FOLDERS:
                if subf in subfolders:
                    subfolders.remove(subf)

            for name in files:
                full_path = os.path.join(folder, name)
                object_name = os.path.relpath(full_path, start=cpath)
                yield self._make_object(container, object_name)

    def _get_more(self, last_key, value_dict):
        """
        A handler for using with LazyList
        """
        container = value_dict['container']
        objects = [obj for obj in self._get_objects(container)]

        return (objects, None, True)

    def list_container_objects(self, container):
        """
        Return a list of objects for the given container.

        @param container: Container instance
        @type container: L{Container}

        @return: A list of Object instances.
        @rtype: C{list} of L{Object}
        """

        value_dict = {'container': container}
        return LazyList(get_more=self._get_more, value_dict=value_dict)

    def get_container(self, container_name):
        """
        Return a container instance.

        @param container_name: Container name.
        @type container_name: C{str}

        @return: L{Container} instance.
        @rtype: L{Container}
        """
        return self._make_container(container_name)

    def get_container_cdn_url(self, container, check=False):
        """
        Return a container CDN URL.

        @param container: Container instance
        @type  container: L{Container}

        @return: A CDN URL for this container.
        @rtype: C{str}
        """
        path = os.path.join(self.base_path, container.name)

        if check and not os.path.isdir(path):
            raise ContainerDoesNotExistError(value=None, driver=self,
                                             container_name=container.name)

        return path

    def get_object(self, container_name, object_name):
        """
        Return an object instance.

        @param container_name: Container name.
        @type  container_name: C{str}

        @param object_name: Object name.
        @type  object_name: C{str}

        @return: L{Object} instance.
        @rtype: L{Object}
        """
        container = self._make_container(container_name)
        return self._make_object(container, object_name)

    def get_object_cdn_url(self, obj):
        """
        Return a object CDN URL.

        @param obj: Object instance
        @type  obj: L{Object}

        @return: A CDN URL for this object.
        @rtype: C{str}
        """
        return os.path.join(self.base_path, obj.container.name, obj.name)

    def enable_container_cdn(self, container):
        """
        Enable container CDN.

        @param container: Container instance
        @type  container: L{Container}

        @rtype: C{bool}
        """

        path = self.get_container_cdn_url(container)
        lock = lockfile.MkdirFileLock(path, threaded=True)

        with LockLocalStorage(path) as lock:
            self._make_path(path)

        return True

    def enable_object_cdn(self, obj):
        """
        Enable object CDN.

        @param obj: Object instance
        @type  obj: L{Object}

        @rtype: C{bool}
        """
        path = self.get_object_cdn_url(obj)

        with LockLocalStorage(path) as lock:
            if os.path.exists(path):
                return False
            try:
                obj_file = open(path, 'w')
                obj_file.close()
            except:
                return False

        return True

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        """
        Download an object to the specified destination path.

        @param obj: Object instance.
        @type obj: L{Object}

        @param destination_path: Full path to a file or a directory where the
                                incoming file will be saved.
        @type destination_path: C{str}

        @param overwrite_existing: True to overwrite an existing file,
            defaults to False.
        @type overwrite_existing: C{bool}

        @param delete_on_failure: True to delete a partially downloaded file if
        the download was not successful (hash mismatch / file size).
        @type delete_on_failure: C{bool}

        @return: True if an object has been successfully downloaded, False
        otherwise.
        @rtype: C{bool}
        """

        obj_path = self.get_object_cdn_url(obj)
        base_name = os.path.basename(destination_path)

        if not base_name and not os.path.exists(destination_path):
            raise LibcloudError(
                value='Path %s does not exist' % (destination_path),
                driver=self)

        if not base_name:
            file_path = os.path.join(destination_path, obj.name)
        else:
            file_path = destination_path

        if os.path.exists(file_path) and not overwrite_existing:
            raise LibcloudError(
                value='File %s already exists, but ' % (file_path) +
                'overwrite_existing=False',
                driver=self)

        try:
            shutil.copy(obj_path, file_path)
        except Exception:
            if delete_on_failure:
                try:
                    os.unlink(file_path)
                except Exception:
                    pass
            return False

        return True

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        Return a generator which yields object data.

        @param obj: Object instance
        @type obj: L{Object}

        @param chunk_size: Optional chunk size (in bytes).
        @type chunk_size: C{int}

        @rtype: C{object}
        """

        path = self.get_object_cdn_url(obj)
        obj_file = open(path)

        if chunk_size is None:
            chunk_size = CHUNK_SIZE

        data = obj_file.read(chunk_size)

        while data:
            yield data
            data = obj_file.read(chunk_size)

        obj_file.close()

    def upload_object(self, file_path, container, object_name, extra=None,
                      verify_hash=True):
        """
        Upload an object currently located on a disk.

        @param file_path: Path to the object on disk.
        @type file_path: C{str}

        @param container: Destination container.
        @type container: L{Container}

        @param object_name: Object name.
        @type object_name: C{str}

        @param verify_hash: Verify hast
        @type verify_hash: C{bool}

        @param extra: (optional) Extra attributes (driver specific).
        @type extra: C{dict}

        @rtype: C{object}
        """

        path = self.get_container_cdn_url(container, check=True)
        obj_path = os.path.join(path, object_name)
        base_path = os.path.dirname(obj_path)

        self._make_path(base_path)

        with LockLocalStorage(obj_path) as lock:
            shutil.copy(file_path, obj_path)

        os.chmod(obj_path, 0664)

        return self._make_object(container, object_name)

    def upload_object_via_stream(self, iterator, container,
                                 object_name,
                                 extra=None):
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

        @type iterator: C{object}
        @param iterator: An object which implements the iterator interface.

        @type container: L{Container}
        @param container: Destination container.

        @type object_name: C{str}
        @param object_name: Object name.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific). Note:
            This dictionary must contain a 'content_type' key which represents
            a content type of the stored object.

        @rtype: C{object}
        """

        path = self.get_container_cdn_url(container, check=True)
        obj_path = os.path.join(path, object_name)
        base_path = os.path.dirname(obj_path)

        self._make_path(base_path)

        with LockLocalStorage(obj_path) as lock:
            obj_file = open(obj_path, 'w')
            for data in iterator:
                obj_file.write(data)

            obj_file.close()

        os.chmod(obj_path, 0664)

        return self._make_object(container, object_name)

    def delete_object(self, obj):
        """
        Delete an object.

        @type obj: L{Object}
        @param obj: Object instance.

        @return: C{bool} True on success.
        @rtype: C{bool}
        """

        path = self.get_object_cdn_url(obj)

        with LockLocalStorage(path) as lock:
            try:
                os.unlink(path)
            except Exception, exp:
                return False

        # Check and delete the folder if required
        path = os.path.dirname(path)

        try:
            if path != obj.container.get_cdn_url():
                os.rmdir(path)
        except Exception, exp:
            pass

        return True

    def create_container(self, container_name):
        """
        Create a new container.

        @type container_name: C{str}
        @param container_name: Container name.

        @return: C{Container} instance on success.
        @rtype: L{Container}
        """

        if '/' in container_name:
            raise InvalidContainerNameError(value=None, driver=self,
                                            container_name=container_name)

        path = os.path.join(self.base_path, container_name)

        try:
            self._make_path(path, ignore_existing=False)
        except OSError, exp:
            if exp.errno == 17:
                raise ContainerAlreadyExistsError(
                    value='Container with this name already exists. The name '
                          'must be unique among all the containers in the '
                          'system',
                    container_name=container_name, driver=self)
            else:
                raise LibcloudError(
                    'Error creating container %s' % container_name, driver=self)
        except Exception, exp:
            raise LibcloudError(
                'Error creating container %s' % container_name, driver=self)

        return self._make_container(container_name)

    def delete_container(self, container):
        """
        Delete a container.

        @type container: L{Container}
        @param container: Container instance

        @return: True on success, False otherwise.
        @rtype: C{bool}
        """

        # Check if there are any objects inside this
        for obj in self._get_objects(container):
            raise ContainerIsNotEmptyError(value='Container is not empty',
                                container_name=container.name, driver=self)

        path = self.get_container_cdn_url(container, check=True)

        with LockLocalStorage(path) as lock:
            try:
                shutil.rmtree(path)
            except Exception, exp:
                return False

        return True
