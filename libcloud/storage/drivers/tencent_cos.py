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

import os
import shutil
import tempfile

from qcloud_cos import (
    CosClient,
    DelFileRequest,
    DownloadFileRequest,
    DownloadObjectRequest,
    ListFolderRequest,
    StatFileRequest,
    StatFolderRequest,
    UploadFileRequest,
)

from libcloud.common.types import LibcloudError
from libcloud.storage.base import StorageDriver, Container, Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.utils.files import exhaust_iterator, read_in_chunks


class TencentCosDriver(StorageDriver):
    """
    Driver for Tencent Cloud Object Storage (COS).

    Can authenticate via API key & secret - requires App ID and region as well.

    Examples:

    API key, secret & app ID::

        driver = TencentCosDriver(key=api_key_id, secret=api_secret_key
                                  region=region, app_id=app_id)
    """
    name = 'Tencent COS'
    website = 'https://cloud.tencent.com/product/cos'
    hash_type = 'sha1'
    supports_chunked_encoding = False

    def __init__(self, key, secret=None, app_id=None, region=None, **kwargs):
        super(TencentCosDriver, self).__init__(key, secret, **kwargs)
        self.cos_client = CosClient(app_id, key, secret, region)

    @staticmethod
    def _is_ok(response):
        return response['code'] == 0

    def _to_containers(self, obj_list):
        for obj in obj_list:
            yield self._to_container(obj)

    def _to_container(self, obj):
        extra = {
            'creation_date': obj['ctime'],
            'modified_data': obj['mtime'],
        }
        return Container(obj['name'].rstrip('/'), extra, self)

    def _walk_container_folder(self, container, folder):
        exhausted = False
        context = ''
        while not exhausted:
            req = ListFolderRequest(container.name, folder, context=context)
            response = self.cos_client.list_folder(req)
            if not self._is_ok(response):
                return
            exhausted = response['data']['listover']
            context = response['data']['context']
            for obj in response['data']['infos']:
                if obj['name'].endswith('/'):
                    # need to recurse into folder
                    yield from self._walk_container_folder(
                        container, folder + obj['name'])
                else:
                    yield self._to_obj(obj, folder, container)

    def _to_obj(self, obj, folder, container):
        extra = {
            'creation_date': obj['ctime'],
            'modified_data': obj['mtime'],
            'access_url': obj['access_url'],
            'source_url': obj['source_url'],
        }
        meta_data = {}
        return Object(folder.lstrip('/') + obj['name'],
                      obj['filesize'], obj['sha'],
                      extra, meta_data, container, self)

    def iterate_containers(self):
        """
        Return a generator of containers for the given account

        :return: A generator of Container instances.
        :rtype: ``generator`` of :class:`Container`
        """
        exhausted = False
        context = ''
        while not exhausted:
            req = ListFolderRequest('', '/', context=context)
            response = self.cos_client.list_folder(req)
            if not self._is_ok(response):
                return
            exhausted = response['data']['listover']
            context = response['data']['context']
            yield from self._to_containers(response['data']['infos'])

    def iterate_container_objects(self, container):
        """
        Return a generator of objects for the given container.

        :param container: Container instance
        :type container: :class:`Container`

        :return: A generator of Object instances.
        :rtype: ``generator`` of :class:`Object`
        """
        return self._walk_container_folder(container, '/')

    def get_container(self, container_name):
        """
        Return a container instance.

        :param container_name: Container name.
        :type container_name: ``str``

        :return: :class:`Container` instance.
        :rtype: :class:`Container`
        """
        req = StatFolderRequest(container_name, '/')
        response = self.cos_client.stat_folder(req)
        if not self._is_ok(response):
            raise ContainerDoesNotExistError(value=None, driver=self,
                                             container_name=container_name)
        # "inject" the container name to the dictionary for `_to_container`
        response['data']['name'] = container_name
        return self._to_container(response['data'])

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
        req = StatFileRequest(container_name, '/' + object_name)
        response = self.cos_client.stat_file(req)
        if not self._is_ok(response):
            raise ObjectDoesNotExistError(value=None, driver=self,
                                          object_name=object_name)
        # "inject" the object name to the dictionary for `_to_obj`
        response['data']['name'] = object_name
        return self._to_obj(response['data'], '',
                            self.get_container(container_name))

    def get_object_cdn_url(self, obj):
        """
        Return an object CDN URL.

        :param obj: Object instance
        :type  obj: :class:`Object`

        :return: A CDN URL for this object.
        :rtype: ``str``
        """
        return obj.extra['access_url']

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
        if os.path.exists(destination_path) and not overwrite_existing:
            return False
        req = DownloadFileRequest(obj.container.name, '/' + obj.name,
                                  destination_path)
        response = self.cos_client.download_file(req)
        if self._is_ok(response):
            return True
        if delete_on_failure and os.path.exists(destination_path):
            os.remove(destination_path)
        return False

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        Return a generator which yields object data.

        :param obj: Object instance
        :type obj: :class:`Object`

        :param chunk_size: Optional chunk size (in bytes).
        :type chunk_size: ``int``
        """
        req = DownloadObjectRequest(obj.container.name, '/' + obj.name)
        response = self.cos_client.download_object(req)
        return read_in_chunks(response, chunk_size, yield_empty=True)

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
        if file_path and not os.path.exists(file_path):
            raise OSError('File %s does not exist' % (file_path))
        req = UploadFileRequest(container.name, '/' + object_name, file_path)

        def set_extra(field_name):
            if extra and field_name in extra:
                set_func = req.getattr('set_%s' % (field_name))
                set_func(extra[field_name])

        set_extra('authority')
        set_extra('biz_attr')
        set_extra('cache_control')
        set_extra('content_type')
        set_extra('content_language')
        set_extra('content_encoding')
        set_extra('x_cos_meta')
        response = self.cos_client.upload_file(req)
        if not self._is_ok(response):
            raise LibcloudError(
                'Error in uploading object: %s' % (response['message']),
                driver=self)
        obj = self.get_object(container.name, object_name)
        if verify_hash:
            hasher = self._get_hash_function()
            with open(file_path, 'rb') as src_file:
                hasher.update(src_file.read())
            data_hash = hasher.hexdigest()
            if data_hash != obj.hash:
                raise ObjectHashMismatchError(
                    value='SHA1 hash {0} checksum does not match {1}'.format(
                        obj.hash, data_hash),
                    object_name=object_name, driver=self)
        return obj

    def upload_object_via_stream(self, iterator, container, object_name,
                                 extra=None, headers=None):
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
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(exhaust_iterator(iterator))
        try:
            return self.upload_object(
                tmp_file.name, container, object_name, extra, headers)
        finally:
            os.remove(tmp_file.name)

    def delete_object(self, obj):
        """
        Delete an object.

        :param obj: Object instance.
        :type obj: :class:`Object`

        :return: ``bool`` True on success.
        :rtype: ``bool``
        """
        req = DelFileRequest(obj.container.name, '/' + obj.name)
        response = self.cos_client.del_file(req)
        return self._is_ok(response)
