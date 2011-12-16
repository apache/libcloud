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

import time
import copy
import base64
import hmac

from hashlib import sha1
from xml.etree.ElementTree import Element, SubElement, tostring

from libcloud.utils.py3 import PY3
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlquote
from libcloud.utils.py3 import b

from libcloud.utils.xml import fixxpath, findtext
from libcloud.utils.files import read_in_chunks
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.common.base import ConnectionUserAndKey, RawResponse
from libcloud.common.aws import AWSBaseResponse

from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.common.types import LazyList

# How long before the token expires
EXPIRATION_SECONDS = 15 * 60

S3_US_STANDARD_HOST = 's3.amazonaws.com'
S3_US_WEST_HOST = 's3-us-west-1.amazonaws.com'
S3_US_WEST_OREGON_HOST = 's3-us-west-2.amazonaws.com'
S3_EU_WEST_HOST = 's3-eu-west-1.amazonaws.com'
S3_AP_SOUTHEAST_HOST = 's3-ap-southeast-1.amazonaws.com'
S3_AP_NORTHEAST_HOST = 's3-ap-northeast-1.amazonaws.com'

API_VERSION = '2006-03-01'
NAMESPACE = 'http://s3.amazonaws.com/doc/%s/' % (API_VERSION)


class S3Response(AWSBaseResponse):

    valid_response_codes = [ httplib.NOT_FOUND, httplib.CONFLICT,
                             httplib.BAD_REQUEST ]

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299 or i in self.valid_response_codes

    def parse_error(self):
        if self.status  in [ httplib.UNAUTHORIZED, httplib.FORBIDDEN ]:
            raise InvalidCredsError(self.body)
        elif self.status == httplib.MOVED_PERMANENTLY:
            raise LibcloudError('This bucket is located in a different ' +
                                'region. Please use the correct driver.',
                                driver=S3StorageDriver)
        raise LibcloudError('Unknown error. Status code: %d' % (self.status),
                            driver=S3StorageDriver)

class S3RawResponse(S3Response, RawResponse):
    pass

class S3Connection(ConnectionUserAndKey):
    """
    Repersents a single connection to the EC2 Endpoint
    """

    host = 's3.amazonaws.com'
    responseCls = S3Response
    rawResponseCls = S3RawResponse

    def add_default_params(self, params):
        expires = str(int(time.time()) + EXPIRATION_SECONDS)
        params['AWSAccessKeyId'] = self.user_id
        params['Expires'] = expires
        return params

    def pre_connect_hook(self, params, headers):
        params['Signature'] = self._get_aws_auth_param(method=self.method,
                                                       headers=headers,
                                                       params=params,
                                                       expires=params['Expires'],
                                                       secret_key=self.key,
                                                       path=self.action)
        return params, headers

    def _get_aws_auth_param(self, method, headers, params, expires,
                            secret_key, path='/'):
        """
        Signature = URL-Encode( Base64( HMAC-SHA1( YourSecretAccessKeyID, UTF-8-Encoding-Of( StringToSign ) ) ) );

        StringToSign = HTTP-VERB + "\n" +
            Content-MD5 + "\n" +
            Content-Type + "\n" +
            Expires + "\n" +
            CanonicalizedAmzHeaders +
            CanonicalizedResource;
        """
        special_header_keys = [ 'content-md5', 'content-type', 'date' ]
        special_header_values = { 'date': '' }
        amz_header_values = {}

        headers_copy = copy.deepcopy(headers)
        for key, value in list(headers_copy.items()):
            if key.lower() in special_header_keys:
                special_header_values[key.lower()] = value.lower().strip()
            elif key.lower().startswith('x-amz-'):
                amz_header_values[key.lower()] = value.strip()

        if not 'content-md5' in special_header_values:
            special_header_values['content-md5'] = ''

        if not 'content-type' in special_header_values:
            special_header_values['content-type'] = ''

        if expires:
            special_header_values['date'] = str(expires)

        keys_sorted = list(special_header_values.keys())
        keys_sorted.sort()

        buf = [ method ]
        for key in keys_sorted:
            value = special_header_values[key]
            buf.append(value)
        string_to_sign = '\n'.join(buf)

        keys_sorted = list(amz_header_values.keys())
        keys_sorted.sort()

        amz_header_string = []
        for key in keys_sorted:
            value = amz_header_values[key]
            amz_header_string.append('%s:%s' % (key, value))
        amz_header_string = '\n'.join(amz_header_string)

        values_to_sign = []
        for value in [ string_to_sign, amz_header_string, path]:
            if value:
                values_to_sign.append(value)

        string_to_sign = '\n'.join(values_to_sign)
        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key), b(string_to_sign), digestmod=sha1).digest()
        )
        return b64_hmac

class S3StorageDriver(StorageDriver):
    name = 'Amazon S3 (standard)'
    connectionCls = S3Connection
    hash_type = 'md5'
    supports_chunked_encoding = False
    ex_location_name = ''
    namespace = NAMESPACE

    def list_containers(self):
        response = self.connection.request('/')
        if response.status == httplib.OK:
            containers = self._to_containers(obj=response.object,
                                             xpath='Buckets/Bucket')
            return containers

        raise LibcloudError('Unexpected status code: %s' % (response.status),
                            driver=self)

    def list_container_objects(self, container):
        value_dict = { 'container': container }
        return LazyList(get_more=self._get_more, value_dict=value_dict)

    def get_container(self, container_name):
        # This is very inefficient, but afaik it's the only way to do it
        containers = self.list_containers()

        try:
            container = [ c for c in containers if c.name == container_name ][0]
        except IndexError:
            raise ContainerDoesNotExistError(value=None, driver=self,
                                             container_name=container_name)

        return container

    def get_object(self, container_name, object_name):
        # TODO: Figure out what is going on when the object or container does not exist
        # - it seems that Amazon just keeps the connection open and doesn't return a
        # response.
        container = self.get_container(container_name=container_name)
        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                           method='HEAD')
        if response.status == httplib.OK:
            obj = self._headers_to_object(object_name=object_name,
                                          container=container,
                                          headers=response.headers)
            return obj

        raise ObjectDoesNotExistError(value=None, driver=self,
                                      object_name=object_name)

    def create_container(self, container_name):
        if self.ex_location_name:
            root = Element('CreateBucketConfiguration')
            child = SubElement(root, 'LocationConstraint')
            child.text = self.ex_location_name

            if PY3:
                encoding = 'unicode'
            else:
                encoding = None
            data = tostring(root, encoding=encoding)
        else:
            data = ''

        response = self.connection.request('/%s' % (container_name),
                                           data=data,
                                           method='PUT')

        if response.status == httplib.OK:
            container = Container(name=container_name, extra=None, driver=self)
            return container
        elif response.status == httplib.CONFLICT:
            raise InvalidContainerNameError(value='Container with this name ' +
                                'already exists. The name must be unique among '
                                'all the containers in the system',
                                container_name=container_name, driver=self)
        elif response.status == httplib.BAD_REQUEST:
            raise InvalidContainerNameError(value='Container name contains ' +
                                            'invalid characters.',
                                            container_name=container_name,
                                            driver=self)

        raise LibcloudError('Unexpected status code: %s' % (response.status),
                            driver=self)

    def delete_container(self, container):
        # Note: All the objects in the container must be deleted first
        response = self.connection.request('/%s' % (container.name),
                                           method='DELETE')
        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.CONFLICT:
            raise ContainerIsNotEmptyError(value='Container must be empty' +
                                                  ' before it can be deleted.',
                                           container_name=container.name,
                                           driver=self)
        elif response.status == httplib.NOT_FOUND:
            raise ContainerDoesNotExistError(value=None,
                                             driver=self,
                                             container_name=container.name)

        return False

    def download_object(self, obj, destination_path, overwrite_existing=False,
                        delete_on_failure=True):
        container_name = self._clean_object_name(obj.container.name)
        object_name = self._clean_object_name(obj.name)

        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                           method='GET',
                                           raw=True)

        return self._get_object(obj=obj, callback=self._save_object,
                                response=response,
                                callback_kwargs={'obj': obj,
                                 'response': response.response,
                                 'destination_path': destination_path,
                                 'overwrite_existing': overwrite_existing,
                                 'delete_on_failure': delete_on_failure},
                                success_status_code=httplib.OK)

    def download_object_as_stream(self, obj, chunk_size=None):
        container_name = self._clean_object_name(obj.container.name)
        object_name = self._clean_object_name(obj.name)
        response = self.connection.request('/%s/%s' % (container_name,
                                                       object_name),
                                           method='GET', raw=True)

        return self._get_object(obj=obj, callback=read_in_chunks,
                                response=response,
                                callback_kwargs={ 'iterator': response.response,
                                                  'chunk_size': chunk_size},
                                success_status_code=httplib.OK)

    def upload_object(self, file_path, container, object_name, extra=None,
                      verify_hash=True, ex_storage_class=None):
        upload_func = self._upload_file
        upload_func_kwargs = { 'file_path': file_path }

        return self._put_object(container=container, object_name=object_name,
                                upload_func=upload_func,
                                upload_func_kwargs=upload_func_kwargs,
                                extra=extra, file_path=file_path,
                                verify_hash=verify_hash,
                                storage_class=ex_storage_class)

    def upload_object_via_stream(self, iterator, container, object_name,
                                 extra=None, ex_storage_class=None):
        # Amazon S3 does not support chunked transfer encoding so the whole data
        # is read into memory before uploading the object.
        upload_func = self._upload_data
        upload_func_kwargs = {}

        return self._put_object(container=container, object_name=object_name,
                                upload_func=upload_func,
                                upload_func_kwargs=upload_func_kwargs,
                                extra=extra, iterator=iterator,
                                verify_hash=False,
                                storage_class=ex_storage_class)

    def delete_object(self, obj):
        object_name = self._clean_object_name(name=obj.name)
        response = self.connection.request('/%s/%s' % (obj.container.name,
                                                       object_name),
                                           method='DELETE')
        if response.status == httplib.NO_CONTENT:
            return True
        elif response.status == httplib.NOT_FOUND:
            raise ObjectDoesNotExistError(value=None, driver=self,
                                         object_name=obj.name)

        return False

    def _clean_object_name(self, name):
        name = urlquote(name)
        return name

    def _get_more(self, last_key, value_dict):
        container = value_dict['container']
        params = {}

        if last_key:
            params['marker'] = last_key

        response = self.connection.request('/%s' % (container.name),
                                           params=params)

        if response.status == httplib.OK:
            objects = self._to_objs(obj=response.object,
                                       xpath='Contents', container=container)
            is_truncated = response.object.findtext(fixxpath(xpath='IsTruncated',
                                                   namespace=self.namespace)).lower()
            exhausted = (is_truncated == 'false')

            if (len(objects) > 0):
                last_key = objects[-1].name
            else:
                last_key = None
            return objects, last_key, exhausted

        raise LibcloudError('Unexpected status code: %s' % (response.status),
                            driver=self)

    def _put_object(self, container, object_name, upload_func,
                    upload_func_kwargs, extra=None, file_path=None,
                    iterator=None, verify_hash=True, storage_class=None):
        headers = {}
        extra = extra or {}
        storage_class = storage_class or 'standard'
        if storage_class not in ['standard', 'reduced_redundancy']:
            raise ValueError('Invalid storage class value: %s' % (storage_class))

        headers['x-amz-storage-class'] = storage_class.upper()

        container_name_cleaned = container.name
        object_name_cleaned = self._clean_object_name(object_name)
        content_type = extra.get('content_type', None)
        meta_data = extra.get('meta_data', None)

        if meta_data:
            for key, value in list(meta_data.items()):
                key = 'x-amz-meta-%s' % (key)
                headers[key] = value

        request_path = '/%s/%s' % (container_name_cleaned, object_name_cleaned)
        # TODO: Let the underlying exceptions bubble up and capture the SIGPIPE
        # here.
        # SIGPIPE is thrown if the provided container does not exist or the user
        # does not have correct permission
        result_dict = self._upload_object(object_name=object_name,
                                          content_type=content_type,
                                          upload_func=upload_func,
                                          upload_func_kwargs=upload_func_kwargs,
                                          request_path=request_path,
                                          request_method='PUT',
                                          headers=headers, file_path=file_path,
                                          iterator=iterator)

        response = result_dict['response']
        bytes_transferred = result_dict['bytes_transferred']
        headers = response.headers
        response = response.response
        server_hash = headers['etag'].replace('"', '')

        if (verify_hash and result_dict['data_hash'] != server_hash):
            raise ObjectHashMismatchError(
                value='MD5 hash checksum does not match',
                object_name=object_name, driver=self)
        elif response.status == httplib.OK:
            obj = Object(
                name=object_name, size=bytes_transferred, hash=server_hash,
                extra=None, meta_data=meta_data, container=container,
                driver=self)

            return obj
        else:
            raise LibcloudError('Unexpected status code, status_code=%s' % (response.status),
                                driver=self)

    def _to_containers(self, obj, xpath):
        return [ self._to_container(element) for element in \
                 obj.findall(fixxpath(xpath=xpath, namespace=self.namespace))]

    def _to_objs(self, obj, xpath, container):
        return [ self._to_obj(element, container) for element in \
                 obj.findall(fixxpath(xpath=xpath, namespace=self.namespace))]

    def _to_container(self, element):
        extra = {
            'creation_date': findtext(element=element, xpath='CreationDate',
                                      namespace=self.namespace)
        }

        container = Container(
                        name=findtext(element=element, xpath='Name',
                                      namespace=self.namespace),
                        extra=extra,
                        driver=self
                    )

        return container

    def _headers_to_object(self, object_name, container, headers):
        meta_data = { 'content_type': headers['content-type'] }
        hash = headers['etag'].replace('"', '')

        obj = Object(name=object_name, size=headers['content-length'],
                     hash=hash, extra=None,
                     meta_data=meta_data,
                     container=container,
                     driver=self)
        return obj

    def _to_obj(self, element, container):
        owner_id = findtext(element=element, xpath='Owner/ID',
                            namespace=self.namespace)
        owner_display_name = findtext(element=element,
                                      xpath='Owner/DisplayName',
                                      namespace=self.namespace)
        meta_data = { 'owner': { 'id': owner_id,
                                 'display_name':owner_display_name }}

        obj = Object(name=findtext(element=element, xpath='Key',
                                   namespace=self.namespace),
                     size=int(findtext(element=element, xpath='Size',
                                       namespace=self.namespace)),
                     hash=findtext(element=element, xpath='ETag',
                                   namespace=self.namespace).replace('"', ''),
                     extra=None,
                     meta_data=meta_data,
                     container=container,
                     driver=self
             )

        return obj

class S3USWestConnection(S3Connection):
    host = S3_US_WEST_HOST

class S3USWestStorageDriver(S3StorageDriver):
    name = 'Amazon S3 (us-west-1)'
    connectionCls = S3USWestConnection
    ex_location_name = 'us-west-1'

class S3USWestOregonConnection(S3Connection):
    host = S3_US_WEST_OREGON_HOST

class S3USWestOregonStorageDriver(S3StorageDriver):
    name = 'Amazon S3 (us-west-2)'
    connectionCls = S3USWestOregonConnection
    ex_location_name = 'us-west-2'

class S3EUWestConnection(S3Connection):
    host = S3_EU_WEST_HOST

class S3EUWestStorageDriver(S3StorageDriver):
    name = 'Amazon S3 (eu-west-1)'
    connectionCls = S3EUWestConnection
    ex_location_name = 'EU'

class S3APSEConnection(S3Connection):
    host = S3_AP_SOUTHEAST_HOST

class S3APSEStorageDriver(S3StorageDriver):
    name = 'Amazon S3 (ap-southeast-1)'
    connectionCls = S3APSEConnection
    ex_location_name = 'ap-southeast-1'

class S3APNEConnection(S3Connection):
    host = S3_AP_NORTHEAST_HOST

class S3APNEStorageDriver(S3StorageDriver):
    name = 'Amazon S3 (ap-northeast-1)'
    connectionCls = S3APNEConnection
    ex_location_name = 'ap-northeast-1'
