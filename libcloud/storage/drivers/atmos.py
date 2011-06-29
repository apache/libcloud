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

import base64
import hashlib
import hmac
import httplib
import time
import urllib
import urlparse

from xml.etree import ElementTree

from libcloud import utils
from libcloud.common.base import ConnectionUserAndKey, Response

from libcloud.storage.base import Object, Container, StorageDriver, CHUNK_SIZE
from libcloud.storage.types import ContainerDoesNotExistError, \
                                   ObjectDoesNotExistError

def collapse(s):
    return ' '.join([x for x in s.split(' ') if x])

class AtmosError(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = int(code)

    def __repr__(self):
        return '<AtmosError code=' + self.code + ': ' + self.message + '>'

class AtmosResponse(Response):
    def success(self):
        return self.status in (httplib.OK, httplib.CREATED, httplib.NO_CONTENT,
                               httplib.PARTIAL_CONTENT)

    def parse_body(self):
        if not self.body:
            return None
        tree = ElementTree.fromstring(self.body)
        return tree

    def parse_error(self):
        if not self.body:
            return None
        tree = ElementTree.fromstring(self.body)
        code = tree.find('Code').text
        message = tree.find('Message').text
        raise AtmosError(message, code)

class AtmosConnection(ConnectionUserAndKey):
    responseCls = AtmosResponse

    def add_default_headers(self, headers):
        headers['x-emc-uid'] = self.user_id
        headers['Date'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                        time.gmtime())
        headers['x-emc-date'] = headers['Date']

        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/octet-stream'
        if 'Accept' not in headers:
            headers['Accept'] = '*/*'

        return headers

    def pre_connect_hook(self, params, headers):
        pathstring = self.action
        if pathstring.startswith(self.driver.path):
            pathstring = pathstring[len(self.driver.path):]
        if params:
            if type(params) is dict:
                params = params.items()
            pathstring += '?' + urllib.urlencode(params)
        pathstring = pathstring.lower()

        xhdrs = [(k, v) for k, v in headers.items() if k.startswith('x-emc-')]
        xhdrs.sort(key=lambda x: x[0])

        signature = [
            self.method,
            headers.get('Content-Type', ''),
            headers.get('Range', ''),
            headers.get('Date', ''),
            pathstring,
        ]
        signature.extend([k + ':' + collapse(v) for k, v in xhdrs])
        signature = '\n'.join(signature)
        key = base64.b64decode(self.key)
        signature = hmac.new(key, signature, hashlib.sha1).digest()
        headers['x-emc-signature'] = base64.b64encode(signature)

        return params, headers

class AtmosDriver(StorageDriver):
    connectionCls = AtmosConnection

    host = None
    path = None
    api_name = 'atmos'

    DEFAULT_CDN_TTL = 60 * 60 * 24 * 7 # 1 week

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        host = host or self.host
        super(AtmosDriver, self).__init__(key, secret, secure, host, port)

    def list_containers(self):
        result = self.connection.request(self._namespace_path(''))
        entries = self._list_objects(result.object)
        containers = []
        for entry in entries:
            if entry['type'] != 'directory':
                continue
            extra = {
                'object_id': entry['id']
            }
            containers.append(Container(entry['name'], extra, self))
        return containers

    def get_container(self, container_name):
        path = self._namespace_path(container_name + '/?metadata/system')
        result = self.connection.request(path)
        meta = self._emc_meta(result)
        extra = {
            'object_id': meta['objectid']
        }
        return Container(container_name, extra, self)

    def create_container(self, container_name):
        path = self._namespace_path(container_name + '/')
        result = self.connection.request(path, method='POST')
        meta = self._emc_meta(result)
        extra = {
            'object_id': meta['objectid']
        }
        return Container(container_name, extra, self)

    def delete_container(self, container):
        self.connection.request(self._namespace_path(container.name + '/'),
                                method='DELETE')
        return True

    def get_object(self, container_name, object_name):
        container = self.get_container(container_name)
        path = container_name + '/' + object_name
        path = self._namespace_path(path)

        try:
            result = self.connection.request(path + '?metadata/system')
            system_meta = self._emc_meta(result)

            result = self.connection.request(path + '?metadata/user')
            user_meta = self._emc_meta(result)
        except AtmosError, e:
            if e.code != 1003:
                raise
            raise ObjectDoesNotExistError(e, self, object_name)

        meta_data = {
            'object_id': system_meta['objectid']
        }
        hash = user_meta.get('md5', '')
        return Object(object_name, int(system_meta['size']), hash, {},
                      meta_data, container, self)

    def upload_object(self, file_path, container, object_name, extra=None,
                      verify_hash=True):
        upload_func = self._upload_file
        upload_func_kwargs = { 'file_path': file_path }
        method = 'PUT'

        extra = extra or {}
        request_path = container.name + '/' + object_name
        request_path = self._namespace_path(request_path)
        print repr(request_path)
        content_type = extra.get('content_type', None)

        try:
            self.connection.request(request_path + '?metadata/system')
        except AtmosError, e:
            if e.code != 1003:
                raise
            method = 'POST'

        result_dict = self._upload_object(object_name=object_name,
                                          content_type=content_type,
                                          upload_func=upload_func,
                                          upload_func_kwargs=upload_func_kwargs,
                                          request_path=request_path,
                                          request_method=method,
                                          headers={}, file_path=file_path)

        response = result_dict['response'].response
        bytes_transferred = result_dict['bytes_transferred']
        range_hdr = str(bytes_transferred) + '-' + str(bytes_transferred)

        self.connection.request(request_path + '?metadata/user', method='POST',
                                headers={
            'x-emc-meta': 'md5=' + result_dict['data_hash']
        })
        result = self.connection.request(request_path + '?metadata/system')
        meta = self._emc_meta(result)
        meta_data = {
            'object_id': meta['objectid']
        }

        return Object(object_name, bytes_transferred, result_dict['data_hash'],
                      {}, meta_data, container, self)

    def upload_object_via_stream(self, iterator, container, object_name,
                                 extra=None):
        if isinstance(iterator, file):
            iterator = iter(iterator)

        data_hash = hashlib.md5()

        def chunkify(source):
            data = ''
            empty = False

            while not empty or len(data) > 0:
                if empty or len(data) >= CHUNK_SIZE:
                    yield data[:CHUNK_SIZE]
                    data = data[CHUNK_SIZE:]
                else:
                    try:
                        data += source.next()
                    except StopIteration:
                        empty = True

        generator = chunkify(iterator)

        bytes_transferred = 0
        try:
            chunk = generator.next()
        except StopIteration:
            chunk = ''

        path = self._namespace_path(container.name + '/' + object_name)

        while True:
            end = bytes_transferred + len(chunk) - 1
            data_hash.update(chunk)
            headers = {
                'x-emc-meta': 'md5=' + data_hash.hexdigest(),
            }
            if len(chunk) > 0:
                headers['Range'] = 'Bytes=%d-%d' % (bytes_transferred, end)
            result = self.connection.request(path, method='PUT', data=chunk,
                                             headers=headers)
            bytes_transferred += len(chunk)

            try:
                chunk = generator.next()
            except StopIteration:
                break
            if len(chunk) == 0:
                break

        data_hash = data_hash.hexdigest()

        result = self.connection.request(path + '?metadata/system')

        meta = self._emc_meta(result)
        meta_data = {
            'object_id': meta['objectid']
        }

        return Object(object_name, bytes_transferred, data_hash, {}, meta_data,
                      container, self)

    def download_object(self, obj, destination_path, overwrite_existing=False,
                      delete_on_failure=True):
        path = self._namespace_path(obj.container.name + '/' + obj.name)
        response = self.connection.request(path, method='GET', raw=True)

        return self._get_object(obj=obj, callback=self._save_object,
                                response=response,
                                callback_kwargs={
                                    'obj': obj,
                                    'response': response.response,
                                    'destination_path': destination_path,
                                    'overwrite_existing': overwrite_existing,
                                    'delete_on_failure': delete_on_failure
                                },
                                success_status_code=httplib.OK)

    def download_object_as_stream(self, obj, chunk_size=None):
        path = self._namespace_path(obj.container.name + '/' + obj.name)
        response = self.connection.request(path, method='GET', raw=True)

        return self._get_object(obj=obj, callback=utils.read_in_chunks,
                                response=response,
                                callback_kwargs={
                                    'iterator': response.response,
                                    'chunk_size': chunk_size
                                },
                                success_status_code=httplib.OK)

    def delete_object(self, obj):
        path = self._namespace_path(obj.container.name + '/' + obj.name)
        try:
            self.connection.request(path, method='DELETE')
            return True
        except AtmosError:
            return False

    def list_container_objects(self, container):
        headers = {
            'x-emc-include-meta': '1',
            #'x-emc-system-tags': 'size',
        }
        path = self._namespace_path(container.name + '/')
        result = self.connection.request(path, headers=headers)
        print repr(result.headers)
        print result.body
        entries = self._list_objects(result.object)
        objects = []
        for entry in entries:
            if entry['type'] != 'regular':
                continue
            metadata = {
                'object_id': entry['id']
            }
            objects.append(Object(entry['name'], 0, '', {}, metadata, container,
                                  self))
        return objects

    def enable_object_cdn(self, obj):
        return True

    def get_object_cdn_url(self, obj, expiry=None, use_object=False):
        if use_object:
            path = '/rest/objects' + obj.meta_data['object_id']
        else:
            path = '/rest/namespace/' + obj.container.name + '/' + obj.name

        if self.secure:
            protocol = 'https'
        else:
            protocol = 'http'

        expiry = str(expiry or int(time.time()) + self.DEFAULT_CDN_TTL)
        params = [
            ('uid', self.key),
            ('expires', expiry),
        ]

        key = base64.b64decode(self.secret)
        signature = '\n'.join(['GET', path.lower(), self.key, expiry])
        signature = hmac.new(key, signature, hashlib.sha1).digest()
        params.append(('signature', base64.b64encode(signature)))

        params = urllib.urlencode(params)
        path = self.path + path
        return urlparse.urlunparse((protocol, self.host, path, '', params, ''))

    def _list_objects(self, tree):
        listing = tree.find(self._emc_tag('DirectoryList'))
        entries = []
        for entry in listing.findall(self._emc_tag('DirectoryEntry')):
            file_type = entry.find(self._emc_tag('FileType')).text
            entries.append({
                'id': entry.find(self._emc_tag('ObjectID')).text,
                'type': entry.find(self._emc_tag('FileType')).text,
                'name': entry.find(self._emc_tag('Filename')).text
            })
        return entries

    def _namespace_path(self, path):
        return self.path + '/rest/namespace/' + path

    def _object_path(self, object_id):
        return self.path + '/rest/objects/' + object_id

    @staticmethod
    def _emc_tag(self, tag):
        return '{http://www.emc.com/cos/}' + tag

    def _emc_meta(self, response):
        meta = response.headers.get('x-emc-meta', '')
        if len(meta) == 0:
            return {}
        meta = meta.split(', ')
        return dict([x.split('=', 1) for x in meta])
