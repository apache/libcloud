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
import json
import os
from pprint import pprint
import shutil
import tempfile

import email.utils

from qcloud_cos import (
    DownloadFileRequest,
    DownloadObjectRequest,
    ListFolderRequest,
    StatFileRequest,
    StatFolderRequest,
    UploadFileRequest,
)

from libcloud.common.base import ConnectionAppIdAndUserAndKey
from libcloud.common.google import GoogleAuthType
from libcloud.common.google import GoogleOAuth2Credential
from libcloud.common.google import GoogleResponse
from libcloud.common.types import LibcloudError
from libcloud.common.types import ProviderError
from libcloud.storage.base import StorageDriver, Container, Object
from libcloud.storage.drivers.s3 import BaseS3Connection
from libcloud.storage.drivers.s3 import S3RawResponse
from libcloud.storage.drivers.s3 import S3Response
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.utils.files import exhaust_iterator, read_in_chunks
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlquote

# Docs are a lie. Actual namespace returned is different that the one listed
# in the docs.
SIGNATURE_IDENTIFIER = 'GOOG1'


def _clean_object_name(name):
    """
    Return the URL encoded name. name=None returns None. Useful for input
    checking without having to check for None first.

    :param name: The object name
    :type name: ``str`` or ``None``

    :return: The url-encoded object name or None if name=None.
    :rtype ``str`` or ``None``
    """
    return urlquote(name, safe='') if name else None


class ContainerPermissions(object):
    values = ['NONE', 'READER', 'WRITER', 'OWNER']
    NONE = 0
    READER = 1
    WRITER = 2
    OWNER = 3


class ObjectPermissions(object):
    values = ['NONE', 'READER', 'OWNER']
    NONE = 0
    READER = 1
    OWNER = 2


class TencentCosConnection(ConnectionAppIdAndUserAndKey):
    """
    Represents a single connection to the Tencent COS API endpoint.
    """

    host = 'storage.googleapis.com'
    responseCls = S3Response
    rawResponseCls = S3RawResponse
    PROJECT_ID_HEADER = 'x-goog-project-id'

    # def __init__(self, app_id, user_id, key, secure=True,
    #              credential_file=None, **kwargs):
    #     super(GoogleStorageConnection, self).__init__(user_id, key, secure,
    #                                                   **kwargs)

    def add_default_headers(self, headers):
        date = email.utils.formatdate(usegmt=True)
        headers['Date'] = date
        project = self.get_project()
        if project:
            headers[self.PROJECT_ID_HEADER] = project
        return headers

    def get_project(self):
        return getattr(self.driver, 'project', None)

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


class GCSResponse(GoogleResponse):
    pass


# class GoogleStorageJSONConnection(GoogleStorageConnection):
#     """
#     Represents a single connection to the Google storage JSON API endpoint.

#     This can either authenticate via the Google OAuth2 methods or via
#     the S3 HMAC interoperability method.
#     """
#     host = 'www.googleapis.com'
#     responseCls = GCSResponse
#     rawResponseCls = None

#     def add_default_headers(self, headers):
#         headers = super(GoogleStorageJSONConnection, self).add_default_headers(
#             headers)
#         headers['Content-Type'] = 'application/json'
#         return headers


class TencentCosDriver(StorageDriver):
    """
    Driver for Tencent Cloud Object Storage (COS).

    Can authenticate via standard Google Cloud methods (Service Accounts,
    Installed App credentials, and GCE instance service accounts)

    Examples:

    Service Accounts::

        driver = TencentCosDriver(key=client_email, secret=private_key, ...)

    Installed Application::

        driver = TencentCosDriver(key=client_id, secret=client_secret, ...)

    From GCE instance::

        driver = TencentCosDriver(key=foo, secret=bar, ...)

    Can also authenticate via Google Cloud Storage's S3 HMAC interoperability
    API. S3 user keys are 20 alphanumeric characters, starting with GOOG.

    Example::

        driver = TencentCosDriver(key='GOOG0123456789ABCXYZ',
                                     secret=key_secret)
    """
    name = 'Tencent COS'
    website = 'https://cloud.tencent.com/product/cos'
    # connectionCls = GoogleStorageConnection
    # jsonConnectionCls = GoogleStorageJSONConnection
    hash_type = 'sha1'
    supports_chunked_encoding = False
    supports_s3_multipart_upload = False

    def __init__(self, key, secret=None, app_id=None, region=None, **kwargs):
        super(TencentCosDriver, self).__init__(key, secret, **kwargs)
        from qcloud_cos import CosClient
        self.cos_client = CosClient(app_id, key, secret, region)

        # self.json_connection = GoogleStorageJSONConnection(
        #     key, secret, **kwargs)

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
        return read_in_chunks(response, chunk_size)

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
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(exhaust_iterator(iterator))
            return self.upload_object(
                tmp_file.name, container, object_name, extra, headers)

    # def _get_container_permissions(self, container_name):
    #     """
    #     Return the container permissions for the current authenticated user.

    #     :param container_name:  The container name.
    #     :param container_name: ``str``

    #     :return: The permissions on the container.
    #     :rtype: ``int`` from ContainerPermissions
    #     """
    #     # Try OWNER permissions first: try listing the bucket ACL.
    #     # FORBIDDEN -> exists, but not an OWNER.
    #     # NOT_FOUND -> bucket DNE, return NONE.
    #     try:
    #         self.json_connection.request(
    #             '/storage/v1/b/%s/acl' % container_name)
    #         return ContainerPermissions.OWNER
    #     except ProviderError as e:
    #         if e.http_code == httplib.FORBIDDEN:
    #             pass
    #         elif e.http_code == httplib.NOT_FOUND:
    #             return ContainerPermissions.NONE
    #         else:
    #             raise

    #     # Try WRITER permissions with a noop request: try delete with an
    #     # impossible precondition. Authorization is checked before file
    #     # existence or preconditions. So, if we get a NOT_FOUND or a
    #     # PRECONDITION_FAILED, then we must be authorized.
    #     try:
    #         self.json_connection.request(
    #             '/storage/v1/b/%s/o/writecheck' % container_name,
    #             headers={'x-goog-if-generation-match': '0'}, method='DELETE')
    #     except ProviderError as e:
    #         if e.http_code in [httplib.NOT_FOUND, httplib.PRECONDITION_FAILED]:
    #             return ContainerPermissions.WRITER
    #         elif e.http_code != httplib.FORBIDDEN:
    #             raise

    #     # Last, try READER permissions: try getting container metadata.
    #     try:
    #         self.json_connection.request('/storage/v1/b/%s' % container_name)
    #         return ContainerPermissions.READER
    #     except ProviderError as e:
    #         if e.http_code not in [httplib.FORBIDDEN, httplib.NOT_FOUND]:
    #             raise

    #     return ContainerPermissions.NONE

    # def _get_user(self):
    #     """Gets this drivers' authenticated user, if any."""
    #     oauth2_creds = getattr(self.connection, 'oauth2_credential')
    #     if oauth2_creds:
    #         return oauth2_creds.user_id
    #     else:
    #         return None

    # def _get_object_permissions(self, container_name, object_name):
    #     """
    #     Return the object permissions for the current authenticated user.
    #     If the object does not exist, or no object_name is given, return the
    #     default object permissions.

    #     :param container_name: The container name.
    #     :type container_name: ``str``

    #     :param object_name: The object name.
    #     :type object_name: ``str``

    #     :return: The permissions on the object or default object permissions.
    #     :rtype: ``int`` from ObjectPermissions
    #     """
    #     # Try OWNER permissions first: try listing the object ACL.
    #     try:
    #         self.json_connection.request(
    #             '/storage/v1/b/%s/o/%s/acl' % (container_name, object_name))
    #         return ObjectPermissions.OWNER
    #     except ProviderError as e:
    #         if e.http_code not in [httplib.FORBIDDEN, httplib.NOT_FOUND]:
    #             raise

    #     # Try READER permissions: try getting the object.
    #     try:
    #         self.json_connection.request(
    #             '/storage/v1/b/%s/o/%s' % (container_name, object_name))
    #         return ObjectPermissions.READER
    #     except ProviderError as e:
    #         if e.http_code not in [httplib.FORBIDDEN, httplib.NOT_FOUND]:
    #             raise

    #     return ObjectPermissions.NONE

    # def ex_delete_permissions(self, container_name, object_name=None,
    #                           entity=None):
    #     """
    #     Delete permissions for an ACL entity on a container or object.

    #     :param container_name: The container name.
    #     :type container_name: ``str``

    #     :param object_name: The object name. Optional. Not providing an object
    #         will delete a container permission.
    #     :type object_name: ``str``

    #     :param entity: The entity to whose permission will be deleted.
    #         Optional. If not provided, the role will be applied to the
    #         authenticated user, if using an OAuth2 authentication scheme.
    #     :type entity: ``str`` or ``None``
    #     """
    #     object_name = _clean_object_name(object_name)
    #     if not entity:
    #         user_id = self._get_user()
    #         if not user_id:
    #             raise ValueError(
    #                 'Must provide an entity. Driver is not using an '
    #                 'authenticated user.')
    #         else:
    #             entity = 'user-%s' % user_id

    #     if object_name:
    #         url = ('/storage/v1/b/%s/o/%s/acl/%s' %
    #                (container_name, object_name, entity))
    #     else:
    #         url = '/storage/v1/b/%s/acl/%s' % (container_name, entity)

    #     self.json_connection.request(url, method='DELETE')

    # def ex_get_permissions(self, container_name, object_name=None):
    #     """
    #     Return the permissions for the currently authenticated user.

    #     :param container_name: The container name.
    #     :type container_name: ``str``

    #     :param object_name: The object name. Optional. Not providing an object
    #         will return only container permissions.
    #     :type object_name: ``str`` or ``None``

    #     :return: A tuple of container and object permissions.
    #     :rtype: ``tuple`` of (``int``, ``int`` or ``None``) from
    #         ContainerPermissions and ObjectPermissions, respectively.
    #     """
    #     object_name = _clean_object_name(object_name)
    #     obj_perms = self._get_object_permissions(
    #         container_name, object_name) if object_name else None
    #     return self._get_container_permissions(container_name), obj_perms

    # def ex_set_permissions(self, container_name, object_name=None,
    #                        entity=None, role=None):
    #     """
    #     Set the permissions for an ACL entity on a container or an object.

    #     :param container_name: The container name.
    #     :type container_name: ``str``

    #     :param object_name: The object name. Optional. Not providing an object
    #         will apply the acl to the container.
    #     :type object_name: ``str``

    #     :param entity: The entity to which apply the role. Optional. If not
    #         provided, the role will be applied to the authenticated user, if
    #         using an OAuth2 authentication scheme.
    #     :type entity: ``str``

    #     :param role: The permission/role to set on the entity.
    #     :type role: ``int`` from ContainerPermissions or ObjectPermissions
    #         or ``str``.

    #     :raises ValueError: If no entity was given, but was required. Or if
    #         the role isn't valid for the bucket or object.
    #     """
    #     object_name = _clean_object_name(object_name)
    #     if isinstance(role, int):
    #         perms = ObjectPermissions if object_name else ContainerPermissions
    #         try:
    #             role = perms.values[role]
    #         except IndexError:
    #             raise ValueError(
    #                 '%s is not a valid role level for container=%s object=%s' %
    #                 (role, container_name, object_name))
    #     elif not isinstance(role, str):
    #         raise ValueError('%s is not a valid permission.' % role)

    #     if not entity:
    #         user_id = self._get_user()
    #         if not user_id:
    #             raise ValueError(
    #                 'Must provide an entity. Driver is not using an '
    #                 'authenticated user.')
    #         else:
    #             entity = 'user-%s' % user_id

    #     if object_name:
    #         url = '/storage/v1/b/%s/o/%s/acl' % (container_name, object_name)
    #     else:
    #         url = '/storage/v1/b/%s/acl' % container_name

    #     self.json_connection.request(
    #         url, method='POST',
    #         data=json.dumps({'role': role, 'entity': entity}))
