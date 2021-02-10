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

from __future__ import with_statement

import os
import sys
import tempfile
from io import BytesIO

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qs
from libcloud.utils.py3 import b
from libcloud.utils.py3 import basestring

from libcloud.common.types import InvalidCredsError
from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.drivers.azure_blobs import AzureBlobsStorageDriver
from libcloud.storage.drivers.azure_blobs import AZURE_UPLOAD_CHUNK_SIZE

from libcloud.test import unittest
from libcloud.test import generate_random_data  # pylint: disable-msg=E0611
from libcloud.test.file_fixtures import StorageFileFixtures  # pylint: disable-msg=E0611
from libcloud.test.secrets import STORAGE_AZURE_BLOBS_PARAMS
from libcloud.test.secrets import STORAGE_AZURITE_BLOBS_PARAMS
from libcloud.test.storage.base import BaseRangeDownloadMockHttp


class AzureBlobsMockHttp(BaseRangeDownloadMockHttp, unittest.TestCase):

    fixtures = StorageFileFixtures('azure_blobs')
    base_headers = {}

    def _UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED,
                '',
                self.base_headers,
                httplib.responses[httplib.UNAUTHORIZED])

    def _list_containers_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_containers_empty.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_containers(self, method, url, body, headers):
        query_string = urlparse.urlsplit(url).query
        query = parse_qs(query_string)

        if 'marker' not in query:
            body = self.fixtures.load('list_containers_1.xml')
        else:
            body = self.fixtures.load('list_containers_2.xml')

        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _test_container_EMPTY(self, method, url, body, headers):
        if method == 'DELETE':
            body = u''
            return (httplib.ACCEPTED,
                    body,
                    self.base_headers,
                    httplib.responses[httplib.ACCEPTED])

        else:
            body = self.fixtures.load('list_objects_empty.xml')
            return (httplib.OK,
                    body,
                    self.base_headers,
                    httplib.responses[httplib.OK])

    def _new__container_INVALID_NAME(self, method, url, body, headers):
        return (httplib.BAD_REQUEST,
                body,
                self.base_headers,
                httplib.responses[httplib.BAD_REQUEST])

    def _test_container(self, method, url, body, headers):
        query_string = urlparse.urlsplit(url).query
        query = parse_qs(query_string)

        if 'marker' not in query:
            body = self.fixtures.load('list_objects_1.xml')
        else:
            body = self.fixtures.load('list_objects_2.xml')

        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _test_container100(self, method, url, body, headers):
        body = ''

        if method != 'HEAD':
            return (httplib.BAD_REQUEST,
                    body,
                    self.base_headers,
                    httplib.responses[httplib.BAD_REQUEST])

        return (httplib.NOT_FOUND,
                body,
                self.base_headers,
                httplib.responses[httplib.NOT_FOUND])

    def _test_container200(self, method, url, body, headers):
        body = ''

        if method != 'HEAD':
            return (httplib.BAD_REQUEST,
                    body,
                    self.base_headers,
                    httplib.responses[httplib.BAD_REQUEST])

        headers = {}

        headers['etag'] = '0x8CFB877BB56A6FB'
        headers['last-modified'] = 'Fri, 04 Jan 2013 09:48:06 GMT'
        headers['x-ms-lease-status'] = 'unlocked'
        headers['x-ms-lease-state'] = 'available'
        headers['x-ms-meta-meta1'] = 'value1'

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _test_container200_test(self, method, url, body, headers):
        body = ''

        if method != 'HEAD':
            return (httplib.BAD_REQUEST,
                    body,
                    self.base_headers,
                    httplib.responses[httplib.BAD_REQUEST])

        headers = {}

        headers['etag'] = '0x8CFB877BB56A6FB'
        headers['last-modified'] = 'Fri, 04 Jan 2013 09:48:06 GMT'
        headers['content-length'] = '12345'
        headers['content-type'] = 'application/zip'
        headers['x-ms-blob-type'] = 'Block'
        headers['x-ms-lease-status'] = 'unlocked'
        headers['x-ms-lease-state'] = 'available'
        headers['x-ms-meta-rabbits'] = 'monkeys'

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _test2_test_list_containers(self, method, url, body, headers):
        # test_get_object
        body = self.fixtures.load('list_containers.xml')
        headers = {'content-type': 'application/zip',
                   'etag': '"e31208wqsdoj329jd"',
                   'x-amz-meta-rabbits': 'monkeys',
                   'content-length': '12345',
                   'last-modified': 'Thu, 13 Sep 2012 07:13:22 GMT'
                   }

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container_ALREADY_EXISTS(self, method, url, body, headers):
        # test_create_container
        return (httplib.CONFLICT,
                body,
                headers,
                httplib.responses[httplib.CONFLICT])

    def _new_container(self, method, url, body, headers):
        # test_create_container, test_delete_container

        headers = {}

        if method == 'PUT':
            status = httplib.CREATED

            headers['etag'] = '0x8CFB877BB56A6FB'
            headers['last-modified'] = 'Fri, 04 Jan 2013 09:48:06 GMT'
            headers['x-ms-lease-status'] = 'unlocked'
            headers['x-ms-lease-state'] = 'available'
            headers['x-ms-meta-meta1'] = 'value1'

        elif method == 'DELETE':
            status = httplib.NO_CONTENT

        return (status,
                body,
                headers,
                httplib.responses[status])

    def _new_container_DOESNT_EXIST(self, method, url, body, headers):
        # test_delete_container
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.NOT_FOUND])

    def _foo_bar_container_NOT_FOUND(self, method, url, body, headers):
        # test_delete_container_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.NOT_FOUND])

    def _foo_bar_container_foo_bar_object_NOT_FOUND(self, method, url, body,
                                                    headers):
        # test_delete_object_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.NOT_FOUND])

    def _foo_bar_container_foo_bar_object_DELETE(self, method, url, body, headers):
        # test_delete_object
        return (httplib.ACCEPTED,
                body,
                headers,
                httplib.responses[httplib.ACCEPTED])

    def _foo_bar_container_foo_test_upload(self, method, url, body, headers):
        self._assert_content_length_header_is_string(headers=headers)

        query_string = urlparse.urlsplit(url).query
        query = parse_qs(query_string)
        comp = query.get('comp', [])

        headers = {}
        body = ''

        if 'blocklist' in comp or not comp:
            headers['etag'] = '"0x8CFB877BB56A6FB"'
            headers['content-md5'] = 'd4fe4c9829f7ca1cc89db7ad670d2bbd'
        elif 'block' in comp:
            headers['content-md5'] = 'lvcfx/bOJvndpRlrdKU1YQ=='
        else:
            raise NotImplementedError('Unknown request comp: {}'.format(comp))

        return (httplib.CREATED,
                body,
                headers,
                httplib.responses[httplib.CREATED])

    def _foo_bar_container_foo_test_upload_block(self, method, url,
                                                 body, headers):
        # test_upload_object_success
        self._assert_content_length_header_is_string(headers=headers)

        body = ''
        headers = {}
        headers['etag'] = '0x8CFB877BB56A6FB'
        return (httplib.CREATED,
                body,
                headers,
                httplib.responses[httplib.CREATED])

    def _foo_bar_container_foo_test_upload_blocklist(self, method, url,
                                                     body, headers):
        # test_upload_object_success
        self._assert_content_length_header_is_string(headers=headers)

        body = ''
        headers = {}
        headers['etag'] = '0x8CFB877BB56A6FB'
        headers['content-md5'] = 'd4fe4c9829f7ca1cc89db7ad670d2bbd'

        return (httplib.CREATED,
                body,
                headers,
                httplib.responses[httplib.CREATED])

    def _foo_bar_container_foo_test_upload_lease(self, method, url,
                                                 body, headers):
        # test_upload_object_success
        self._assert_content_length_header_is_string(headers=headers)

        action = headers['x-ms-lease-action']
        rheaders = {'x-ms-lease-id': 'someleaseid'}
        body = ''

        if action == 'acquire':
            return (httplib.CREATED,
                    body,
                    rheaders,
                    httplib.responses[httplib.CREATED])

        else:
            if headers.get('x-ms-lease-id', None) != 'someleaseid':
                return (httplib.BAD_REQUEST,
                        body,
                        rheaders,
                        httplib.responses[httplib.BAD_REQUEST])

            return (httplib.OK,
                    body,
                    headers,
                    httplib.responses[httplib.CREATED])

    def _foo_bar_container_foo_test_upload_INVALID_HASH(self, method, url,
                                                        body, headers):
        # test_upload_object_invalid_hash1
        self._assert_content_length_header_is_string(headers=headers)

        body = ''
        headers = {}
        headers['etag'] = '0x8CFB877BB56A6FB'
        headers['content-md5'] = 'd4fe4c9829f7ca1cc89db7ad670d2bbd'

        return (httplib.CREATED,
                body,
                headers,
                httplib.responses[httplib.CREATED])

    def _foo_bar_container_foo_bar_object(self, method, url, body, headers):
        # test_upload_object_invalid_file_size
        self._assert_content_length_header_is_string(headers=headers)

        body = generate_random_data(1000)
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_bar_object_range(self, method, url, body, headers):
        # test_download_object_range_success
        body = '0123456789123456789'

        self.assertTrue('x-ms-range' in headers)
        self.assertEqual(headers['x-ms-range'], 'bytes=5-6')

        start_bytes, end_bytes = self._get_start_and_end_bytes_from_range_str(headers['x-ms-range'], body)

        return (httplib.PARTIAL_CONTENT,
                body[start_bytes:end_bytes + 1],
                headers,
                httplib.responses[httplib.PARTIAL_CONTENT])

    def _foo_bar_container_foo_bar_object_range_stream(self, method, url, body, headers):
        # test_download_object_range_as_stream_success
        body = '0123456789123456789'

        self.assertTrue('x-ms-range' in headers)
        self.assertEqual(headers['x-ms-range'], 'bytes=4-5')

        start_bytes, end_bytes = self._get_start_and_end_bytes_from_range_str(headers['x-ms-range'], body)

        return (httplib.PARTIAL_CONTENT,
                body[start_bytes:end_bytes + 1],
                headers,
                httplib.responses[httplib.PARTIAL_CONTENT])

    def _foo_bar_container_foo_bar_object_INVALID_SIZE(self, method, url,
                                                       body, headers):
        # test_upload_object_invalid_file_size
        self._assert_content_length_header_is_string(headers=headers)

        body = ''
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _assert_content_length_header_is_string(self, headers):
        if 'Content-Length' in headers:
            self.assertTrue(isinstance(headers['Content-Length'], basestring))


class AzuriteBlobsMockHttp(AzureBlobsMockHttp):
    fixtures = StorageFileFixtures('azurite_blobs')

    def _get_method_name(self, *args, **kwargs):
        method_name = super(AzuriteBlobsMockHttp, self).\
            _get_method_name(*args, **kwargs)

        if method_name.startswith('_account'):
            method_name = method_name[8:]

        return method_name


class AzureBlobsTests(unittest.TestCase):
    driver_type = AzureBlobsStorageDriver
    driver_args = STORAGE_AZURE_BLOBS_PARAMS
    mock_response_klass = AzureBlobsMockHttp

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args)

    def setUp(self):
        self.driver_type.connectionCls.conn_class = self.mock_response_klass
        self.mock_response_klass.type = None
        self.driver = self.create_driver()

    def tearDown(self):
        self._remove_test_file()

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

    def test_invalid_credentials(self):
        self.mock_response_klass.type = 'UNAUTHORIZED'
        try:
            self.driver.list_containers()
        except InvalidCredsError as e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('Exception was not thrown')

    def test_list_containers_empty(self):
        self.mock_response_klass.type = 'list_containers_EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

    def test_list_containers_success(self):
        self.mock_response_klass.type = 'list_containers'
        AzureBlobsStorageDriver.RESPONSES_PER_REQUEST = 2
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 4)

        self.assertTrue('last_modified' in containers[1].extra)
        self.assertTrue('url' in containers[1].extra)
        self.assertTrue('etag' in containers[1].extra)
        self.assertTrue('lease' in containers[1].extra)
        self.assertTrue('meta_data' in containers[1].extra)

    def test_list_container_objects_empty(self):
        self.mock_response_klass.type = 'EMPTY'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

    def test_list_container_objects_success(self):
        self.mock_response_klass.type = None
        AzureBlobsStorageDriver.RESPONSES_PER_REQUEST = 2

        container = Container(name='test_container', extra={},
                              driver=self.driver)

        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 4)

        obj = objects[1]
        self.assertEqual(obj.name, 'object2.txt')
        self.assertEqual(obj.hash, '0x8CFB90F1BA8CD8F')
        self.assertEqual(obj.size, 1048576)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertTrue('meta1' in obj.meta_data)
        self.assertTrue('meta2' in obj.meta_data)
        self.assertTrue('last_modified' in obj.extra)
        self.assertTrue('content_type' in obj.extra)
        self.assertTrue('content_encoding' in obj.extra)
        self.assertTrue('content_language' in obj.extra)

    def test_list_container_objects_with_prefix(self):
        self.mock_response_klass.type = None
        AzureBlobsStorageDriver.RESPONSES_PER_REQUEST = 2

        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container,
                                                     prefix='test_prefix')
        self.assertEqual(len(objects), 4)

        obj = objects[1]
        self.assertEqual(obj.name, 'object2.txt')
        self.assertEqual(obj.hash, '0x8CFB90F1BA8CD8F')
        self.assertEqual(obj.size, 1048576)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertTrue('meta1' in obj.meta_data)
        self.assertTrue('meta2' in obj.meta_data)
        self.assertTrue('last_modified' in obj.extra)
        self.assertTrue('content_type' in obj.extra)
        self.assertTrue('content_encoding' in obj.extra)
        self.assertTrue('content_language' in obj.extra)

    def test_get_container_doesnt_exist(self):
        self.mock_response_klass.type = None
        try:
            self.driver.get_container(container_name='test_container100')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_container_success(self):
        self.mock_response_klass.type = None
        container = self.driver.get_container(
            container_name='test_container200')

        self.assertTrue(container.name, 'test_container200')
        self.assertTrue(container.extra['etag'], '0x8CFB877BB56A6FB')
        self.assertTrue(container.extra['last_modified'],
                        'Fri, 04 Jan 2013 09:48:06 GMT')
        self.assertTrue(container.extra['lease']['status'], 'unlocked')
        self.assertTrue(container.extra['lease']['state'], 'available')
        self.assertTrue(container.extra['meta_data']['meta1'], 'value1')

    def test_get_object_cdn_url(self):
        obj = self.driver.get_object(container_name='test_container200',
                                     object_name='test')

        url = urlparse.urlparse(self.driver.get_object_cdn_url(obj))
        query = urlparse.parse_qs(url.query)

        self.assertEqual(len(query['sig']), 1)
        self.assertGreater(len(query['sig'][0]), 0)

    def test_get_object_container_doesnt_exist(self):
        # This method makes two requests which makes mocking the response a bit
        # trickier
        self.mock_response_klass.type = None
        try:
            self.driver.get_object(container_name='test_container100',
                                   object_name='test')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_object_success(self):
        # This method makes two requests which makes mocking the response a bit
        # trickier
        self.mock_response_klass.type = None
        obj = self.driver.get_object(container_name='test_container200',
                                     object_name='test')

        self.assertEqual(obj.name, 'test')
        self.assertEqual(obj.container.name, 'test_container200')
        self.assertEqual(obj.size, 12345)
        self.assertEqual(obj.hash, '0x8CFB877BB56A6FB')
        self.assertEqual(obj.extra['last_modified'],
                         'Fri, 04 Jan 2013 09:48:06 GMT')
        self.assertEqual(obj.extra['content_type'], 'application/zip')
        self.assertEqual(obj.meta_data['rabbits'], 'monkeys')

    def test_create_container_invalid_name(self):
        # invalid container name
        self.mock_response_klass.type = 'INVALID_NAME'
        try:
            self.driver.create_container(container_name='new--container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_already_exists(self):
        # container with this name already exists
        self.mock_response_klass.type = 'ALREADY_EXISTS'
        try:
            self.driver.create_container(container_name='new-container')
        except ContainerAlreadyExistsError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_success(self):
        # success
        self.mock_response_klass.type = None
        name = 'new-container'
        container = self.driver.create_container(container_name=name)
        self.assertEqual(container.name, name)

    def test_delete_container_doesnt_exist(self):
        container = Container(name='new_container', extra=None,
                              driver=self.driver)
        self.mock_response_klass.type = 'DOESNT_EXIST'
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_container_not_empty(self):
        self.mock_response_klass.type = None
        AzureBlobsStorageDriver.RESPONSES_PER_REQUEST = 2

        container = Container(name='test_container', extra={},
                              driver=self.driver)

        try:
            self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_container_success(self):
        self.mock_response_klass.type = 'EMPTY'
        AzureBlobsStorageDriver.RESPONSES_PER_REQUEST = 2

        container = Container(name='test_container', extra={},
                              driver=self.driver)

        self.assertTrue(self.driver.delete_container(container=container))

    def test_delete_container_not_found(self):
        self.mock_response_klass.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Container does not exist but an exception was not' +
                      'thrown')

    def test_download_object_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertTrue(result)

    def test_download_object_invalid_file_size(self):
        self.mock_response_klass.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertFalse(result)

    def test_download_object_invalid_file_already_exists(self):
        self.mock_response_klass.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = os.path.abspath(__file__)
        try:
            self.driver.download_object(obj=obj,
                                        destination_path=destination_path,
                                        overwrite_existing=False,
                                        delete_on_failure=True)
        except LibcloudError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_download_object_as_stream_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)

        stream = self.driver.download_object_as_stream(obj=obj,
                                                       chunk_size=None)

        consumed_stream = ''.join(chunk.decode('utf-8') for chunk in stream)
        self.assertEqual(len(consumed_stream), obj.size)

    def test_download_object_range_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object_range', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object_range(obj=obj,
                                                   start_bytes=5,
                                                   end_bytes=7,
                                                   destination_path=destination_path,
                                                   overwrite_existing=False,
                                                   delete_on_failure=True)
        self.assertTrue(result)

        with open(destination_path, 'r') as fp:
            content = fp.read()

        self.assertEqual(content, '56')

    def test_download_object_range_as_stream_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        obj = Object(name='foo_bar_object_range_stream', size=2, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)

        stream = self.driver.download_object_range_as_stream(obj=obj,
                                                             start_bytes=4,
                                                             end_bytes=6,
                                                             chunk_size=None)

        consumed_stream = ''.join(chunk.decode('utf-8') for chunk in stream)
        self.assertEqual(consumed_stream, '45')
        self.assertEqual(len(consumed_stream), obj.size)

    def test_upload_object_invalid_md5(self):
        # Invalid md5 is returned by azure
        self.mock_response_klass.type = 'INVALID_HASH'

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        file_path = os.path.abspath(__file__)
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      verify_hash=True)
        except ObjectHashMismatchError:
            pass
        else:
            self.fail(
                'Invalid hash was returned but an exception was not thrown')

    def test_upload_small_block_object_success(self):
        file_path = os.path.abspath(__file__)
        file_size = os.stat(file_path).st_size

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        extra = {'meta_data': {'some-value': 'foobar'}}
        obj = self.driver.upload_object(file_path=file_path,
                                        container=container,
                                        object_name=object_name,
                                        extra=extra,
                                        verify_hash=False)

        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, file_size)
        self.assertTrue('some-value' in obj.meta_data)

    def test_upload_big_block_object_success(self):
        _, file_path = tempfile.mkstemp(suffix='.jpg')
        file_size = AZURE_UPLOAD_CHUNK_SIZE + 1

        with open(file_path, 'w') as file_hdl:
            file_hdl.write('0' * file_size)

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        extra = {'meta_data': {'some-value': 'foobar'}}
        obj = self.driver.upload_object(file_path=file_path,
                                        container=container,
                                        object_name=object_name,
                                        extra=extra,
                                        verify_hash=False)

        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, file_size)
        self.assertTrue('some-value' in obj.meta_data)

        os.remove(file_path)

    def test_upload_small_block_object_success_with_lease(self):
        self.mock_response_klass.use_param = 'comp'
        file_path = os.path.abspath(__file__)
        file_size = os.stat(file_path).st_size

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        extra = {'meta_data': {'some-value': 'foobar'}}
        obj = self.driver.upload_object(file_path=file_path,
                                        container=container,
                                        object_name=object_name,
                                        extra=extra,
                                        verify_hash=False,
                                        ex_use_lease=True)

        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, file_size)
        self.assertTrue('some-value' in obj.meta_data)
        self.mock_response_klass.use_param = None

    def test_upload_big_block_object_success_with_lease(self):
        self.mock_response_klass.use_param = 'comp'
        _, file_path = tempfile.mkstemp(suffix='.jpg')
        file_size = AZURE_UPLOAD_CHUNK_SIZE * 2

        with open(file_path, 'w') as file_hdl:
            file_hdl.write('0' * file_size)

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        extra = {'meta_data': {'some-value': 'foobar'}}
        obj = self.driver.upload_object(file_path=file_path,
                                        container=container,
                                        object_name=object_name,
                                        extra=extra,
                                        verify_hash=False,
                                        ex_use_lease=False)

        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, file_size)
        self.assertTrue('some-value' in obj.meta_data)

        os.remove(file_path)
        self.mock_response_klass.use_param = None

    def test_upload_blob_object_via_stream(self):
        self.mock_response_klass.use_param = 'comp'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        object_name = 'foo_test_upload'
        iterator = BytesIO(b('345'))
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, 3)
        self.mock_response_klass.use_param = None

    def test_upload_blob_object_via_stream_from_iterable(self):
        self.mock_response_klass.use_param = 'comp'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        object_name = 'foo_test_upload'
        iterator = iter([b('34'), b('5')])
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, 3)
        self.mock_response_klass.use_param = None

    def test_upload_blob_object_via_stream_with_lease(self):
        self.mock_response_klass.use_param = 'comp'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        object_name = 'foo_test_upload'
        iterator = BytesIO(b('345'))
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra,
                                                   ex_use_lease=True)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, 3)
        self.mock_response_klass.use_param = None

    def test_delete_object_not_found(self):
        self.mock_response_klass.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)
        try:
            self.driver.delete_object(obj=obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_object_success(self):
        self.mock_response_klass.type = 'DELETE'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)

        result = self.driver.delete_object(obj=obj)
        self.assertTrue(result)

    def test_storage_driver_host(self):
        # Non regression tests for issue LIBCLOUD-399 dealing with the bad
        # management of the connectionCls.host class attribute
        driver1 = self.driver_type('fakeaccount1', 'deadbeafcafebabe==')
        driver2 = self.driver_type('fakeaccount2', 'deadbeafcafebabe==')
        driver3 = self.driver_type('fakeaccount3', 'deadbeafcafebabe==',
                                   host='test.foo.bar.com')

        host1 = driver1.connection.host
        host2 = driver2.connection.host
        host3 = driver3.connection.host

        self.assertEqual(host1, 'fakeaccount1.blob.core.windows.net')
        self.assertEqual(host2, 'fakeaccount2.blob.core.windows.net')
        self.assertEqual(host3, 'test.foo.bar.com')

    def test_normalize_http_headers(self):
        driver = self.driver_type('fakeaccount1', 'deadbeafcafebabe==')

        headers = driver._fix_headers({
            # should be normalized to include x-ms-blob prefix
            'Content-Encoding': 'gzip',
            'content-language': 'en-us',
            # should be passed through
            'x-foo': 'bar',
        })

        self.assertEqual(headers, {
            'x-ms-blob-content-encoding': 'gzip',
            'x-ms-blob-content-language': 'en-us',
            'x-foo': 'bar',
        })

    def test_storage_driver_host_govcloud(self):
        driver1 = self.driver_type(
            'fakeaccount1', 'deadbeafcafebabe==',
            host='blob.core.usgovcloudapi.net')
        driver2 = self.driver_type(
            'fakeaccount2', 'deadbeafcafebabe==',
            host='fakeaccount2.blob.core.usgovcloudapi.net')

        host1 = driver1.connection.host
        host2 = driver2.connection.host
        account_prefix_1 = driver1.connection.account_prefix
        account_prefix_2 = driver2.connection.account_prefix

        self.assertEqual(host1, 'fakeaccount1.blob.core.usgovcloudapi.net')
        self.assertEqual(host2, 'fakeaccount2.blob.core.usgovcloudapi.net')
        self.assertIsNone(account_prefix_1)
        self.assertIsNone(account_prefix_2)

    def test_storage_driver_host_azurite(self):
        driver = self.driver_type(
            'fakeaccount1', 'deadbeafcafebabe==',
            host='localhost', port=10000, secure=False)

        host = driver.connection.host
        account_prefix = driver.connection.account_prefix

        self.assertEqual(host, 'localhost')
        self.assertEqual(account_prefix, 'fakeaccount1')


class AzuriteBlobsTests(AzureBlobsTests):
    driver_args = STORAGE_AZURITE_BLOBS_PARAMS
    mock_response_klass = AzuriteBlobsMockHttp


if __name__ == '__main__':
    sys.exit(unittest.main())
