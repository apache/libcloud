# -*- coding=utf-8 -*-
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
from __future__ import unicode_literals

import os
import sys
import unittest

try:
    import mock
except ImportError:
    from unittest import mock

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qs
from libcloud.utils.py3 import PY3
from libcloud.common.types import InvalidCredsError
from libcloud.common.types import MalformedResponseError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.drivers.oss import OSSConnection
from libcloud.storage.drivers.oss import OSSStorageDriver
from libcloud.storage.drivers.oss import CHUNK_SIZE
from libcloud.storage.drivers.dummy import DummyIterator
from libcloud.test import StorageMockHttp, MockRawResponse  # pylint: disable-msg=E0611
from libcloud.test import MockHttpTestCase  # pylint: disable-msg=E0611
from libcloud.test.file_fixtures import StorageFileFixtures  # pylint: disable-msg=E0611
from libcloud.test.secrets import STORAGE_OSS_PARAMS


class OSSConnectionTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = OSSConnection('44CF9590006BF252F707',
                                  'OtxrzxIsfpFjA7SwPzILwy8Bw21TLhquhboDYROV')

    def test_signature(self):
        expected = b('26NBxoKdsyly4EDv6inkoDft/yA=')
        headers = {
            'Content-MD5': 'ODBGOERFMDMzQTczRUY3NUE3NzA5QzdFNUYzMDQxNEM=',
            'Content-Type': 'text/html',
            'Expires': 'Thu, 17 Nov 2005 18:49:58 GMT',
            'X-OSS-Meta-Author': 'foo@bar.com',
            'X-OSS-Magic': 'abracadabra',
            'Host': 'oss-example.oss-cn-hangzhou.aliyuncs.com'
        }
        action = '/oss-example/nelson'
        actual = OSSConnection._get_auth_signature('PUT', headers, {},
                                                   headers['Expires'],
                                                   self.conn.key,
                                                   action,
                                                   'x-oss-')
        self.assertEqual(expected, actual)


class ObjectTestCase(unittest.TestCase):
    def test_object_with_chinese_name(self):
        driver = OSSStorageDriver(*STORAGE_OSS_PARAMS)
        obj = Object(name='中文', size=0, hash=None, extra=None,
                     meta_data=None, container=None, driver=driver)
        self.assertTrue(obj.__repr__() is not None)


class OSSMockHttp(StorageMockHttp, MockHttpTestCase):

    fixtures = StorageFileFixtures('oss')
    base_headers = {}

    def _unauthorized(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED,
                '',
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_containers_empty(self, method, url, body, headers):
        body = self.fixtures.load('list_containers_empty.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_containers(self, method, url, body, headers):
        body = self.fixtures.load('list_containers.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_container_objects_empty(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects_empty.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_container_objects(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_container_objects_chinese(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects_chinese.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_container_objects_prefix(self, method, url, body, headers):
        params = {'prefix': self.test.prefix}
        self.assertUrlContainsQueryParams(url, params)
        body = self.fixtures.load('list_container_objects_prefix.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _get_container(self, method, url, body, headers):
        return self._list_containers(method, url, body, headers)

    def _get_object(self, method, url, body, headers):
        return self._list_containers(method, url, body, headers)

    def _notexisted_get_object(self, method, url, body, headers):
        return (httplib.NOT_FOUND,
                body,
                self.base_headers,
                httplib.responses[httplib.NOT_FOUND])

    def _test_get_object(self, method, url, body, headers):
        self.base_headers.update(
            {'accept-ranges': 'bytes',
             'connection': 'keep-alive',
             'content-length': '0',
             'content-type': 'application/octet-stream',
             'date': 'Sat, 16 Jan 2016 15:38:14 GMT',
             'etag': '"D41D8CD98F00B204E9800998ECF8427E"',
             'last-modified': 'Fri, 15 Jan 2016 14:43:15 GMT',
             'server': 'AliyunOSS',
             'x-oss-object-type': 'Normal',
             'x-oss-request-id': '569A63E6257784731E3D877F',
             'x-oss-meta-rabbits': 'monkeys'})

        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _invalid_name(self, method, url, body, headers):
        # test_create_container_bad_request
        return (httplib.BAD_REQUEST,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _already_exists(self, method, url, body, headers):
        # test_create_container_already_existed
        return (httplib.CONFLICT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _create_container(self, method, url, body, headers):
        # test_create_container_success
        self.assertEqual('PUT', method)
        self.assertEqual('', body)
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _create_container_location(self, method, url, body, headers):
        # test_create_container_success
        self.assertEqual('PUT', method)
        location_constraint = ('<CreateBucketConfiguration>'
                               '<LocationConstraint>%s</LocationConstraint>'
                               '</CreateBucketConfiguration>' %
                               self.test.ex_location)
        self.assertEqual(location_constraint, body)
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _delete_container_doesnt_exist(self, method, url, body, headers):
        # test_delete_container_doesnt_exist
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _delete_container_not_empty(self, method, url, body, headers):
        # test_delete_container_not_empty
        return (httplib.CONFLICT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _delete_container(self, method, url, body, headers):
        return (httplib.NO_CONTENT,
                body,
                self.base_headers,
                httplib.responses[httplib.NO_CONTENT])

    def _foo_bar_object_not_found(self, method, url, body, headers):
        # test_delete_object_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_object(self, method, url, body, headers):
        # test_delete_object
        return (httplib.NO_CONTENT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_test_stream_data_multipart(self, method, url, body, headers):
        headers = {'etag': '"0cc175b9c0f1b6a831c399e269772661"'}
        TEST_UPLOAD_ID = '0004B9894A22E5B1888A1E29F8236E2D'

        query_string = urlparse.urlsplit(url).query
        query = parse_qs(query_string)

        if not query.get('uploadId', False):
            self.fail('Request doesnt contain uploadId query parameter')

        upload_id = query['uploadId'][0]
        if upload_id != TEST_UPLOAD_ID:
            self.fail('first uploadId doesnt match')

        if method == 'PUT':
            # PUT is used for uploading the part. part number is mandatory
            if not query.get('partNumber', False):
                self.fail('Request is missing partNumber query parameter')

            body = ''
            return (httplib.OK,
                    body,
                    headers,
                    httplib.responses[httplib.OK])

        elif method == 'DELETE':
            # DELETE is done for aborting the upload
            body = ''
            return (httplib.NO_CONTENT,
                    body,
                    headers,
                    httplib.responses[httplib.NO_CONTENT])

        else:
            commit = ET.fromstring(body)
            count = 0

            for part in commit.findall('Part'):
                count += 1
                part_no = part.find('PartNumber').text
                etag = part.find('ETag').text

                self.assertEqual(part_no, str(count))
                self.assertEqual(etag, headers['etag'])

            # Make sure that manifest contains at least one part
            self.assertTrue(count >= 1)

            body = self.fixtures.load('complete_multipart_upload.xml')
            return (httplib.OK,
                    body,
                    headers,
                    httplib.responses[httplib.OK])

    def _list_multipart(self, method, url, body, headers):
        query_string = urlparse.urlsplit(url).query
        query = parse_qs(query_string)

        if 'key-marker' not in query:
            body = self.fixtures.load('ex_iterate_multipart_uploads_p1.xml')
        else:
            body = self.fixtures.load('ex_iterate_multipart_uploads_p2.xml')

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])


class OSSMockRawResponse(MockRawResponse, MockHttpTestCase):

    fixtures = StorageFileFixtures('oss')

    def parse_body(self):
        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            if PY3:
                parser = ET.XMLParser(encoding='utf-8')
                body = ET.XML(self.body.encode('utf-8'), parser=parser)
            else:
                body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML",
                                         body=self.body,
                                         driver=self.connection.driver)
        return body

    def _foo_bar_object(self, method, url, body, headers):
        # test_download_object_success
        body = self._generate_random_data(1000)
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_object_invalid_size(self, method, url, body, headers):
        # test_upload_object_invalid_file_size
        body = ''
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_object_not_found(self, method, url, body, headers):
        # test_upload_object_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.NOT_FOUND])

    def _foo_test_upload_invalid_hash1(self, method, url, body, headers):
        body = ''
        headers = {}
        headers['etag'] = '"foobar"'
        # test_upload_object_invalid_hash1
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_test_upload(self, method, url, body, headers):
        # test_upload_object_success
        body = ''
        headers = {'etag': '"0CC175B9C0F1B6A831C399E269772661"'}
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_test_upload_acl(self, method, url, body, headers):
        # test_upload_object_with_acl
        body = ''
        headers = {'etag': '"0CC175B9C0F1B6A831C399E269772661"'}
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_test_stream_data(self, method, url, body, headers):
        # test_upload_object_via_stream
        body = ''
        headers = {'etag': '"0cc175b9c0f1b6a831c399e269772661"'}
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_test_stream_data_multipart(self, method, url, body, headers):
        headers = {}
        # POST is done for initiating multipart upload
        if method == 'POST':
            body = self.fixtures.load('initiate_multipart_upload.xml')
            return (httplib.OK,
                    body,
                    headers,
                    httplib.responses[httplib.OK])
        else:
            body = ''
            return (httplib.BAD_REQUEST,
                    body,
                    headers,
                    httplib.responses[httplib.BAD_REQUEST])


class OSSStorageDriverTestCase(unittest.TestCase):
    driver_type = OSSStorageDriver
    driver_args = STORAGE_OSS_PARAMS
    mock_response_klass = OSSMockHttp
    mock_raw_response_klass = OSSMockRawResponse

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args)

    def setUp(self):
        self.driver_type.connectionCls.conn_classes = (
            None, self.mock_response_klass)
        self.driver_type.connectionCls.rawResponseCls = \
            self.mock_raw_response_klass
        self.mock_response_klass.type = None
        self.mock_response_klass.test = self
        self.mock_raw_response_klass.type = None
        self.mock_raw_response_klass.test = self
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
        self.mock_response_klass.type = 'unauthorized'
        self.assertRaises(InvalidCredsError, self.driver.list_containers)

    def test_list_containers_empty(self):
        self.mock_response_klass.type = 'list_containers_empty'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

    def test_list_containers_success(self):
        self.mock_response_klass.type = 'list_containers'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)

        container = containers[0]
        self.assertEqual('xz02tphky6fjfiuc0', container.name)
        self.assertTrue('creation_date' in container.extra)
        self.assertEqual('2014-05-15T11:18:32.000Z',
                         container.extra['creation_date'])
        self.assertTrue('location' in container.extra)
        self.assertEqual('oss-cn-hangzhou-a', container.extra['location'])
        self.assertEqual(self.driver, container.driver)

    def test_list_container_objects_empty(self):
        self.mock_response_klass.type = 'list_container_objects_empty'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

    def test_list_container_objects_success(self):
        self.mock_response_klass.type = 'list_container_objects'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 2)

        obj = objects[0]
        self.assertEqual(obj.name, 'en/')
        self.assertEqual(obj.hash, 'D41D8CD98F00B204E9800998ECF8427E')
        self.assertEqual(obj.size, 0)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertEqual(
            obj.extra['last_modified'], '2016-01-15T14:43:15.000Z')
        self.assertTrue('owner' in obj.meta_data)

    def test_list_container_objects_with_chinese(self):
        self.mock_response_klass.type = 'list_container_objects_chinese'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 2)

        obj = [o for o in objects
               if o.name == 'WEB控制台.odp'][0]
        self.assertEqual(obj.hash, '281371EA1618CF0E645D6BB90A158276')
        self.assertEqual(obj.size, 1234567)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertEqual(
            obj.extra['last_modified'], '2016-01-15T14:43:06.000Z')
        self.assertTrue('owner' in obj.meta_data)

    def test_list_container_objects_with_prefix(self):
        self.mock_response_klass.type = 'list_container_objects_prefix'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        self.prefix = 'test_prefix'
        objects = self.driver.list_container_objects(container=container,
                                                     ex_prefix=self.prefix)
        self.assertEqual(len(objects), 2)

    def test_get_container_doesnt_exist(self):
        self.mock_response_klass.type = 'get_container'
        self.assertRaises(ContainerDoesNotExistError,
                          self.driver.get_container,
                          container_name='not-existed')

    def test_get_container_success(self):
        self.mock_response_klass.type = 'get_container'
        container = self.driver.get_container(
            container_name='xz02tphky6fjfiuc0')
        self.assertTrue(container.name, 'xz02tphky6fjfiuc0')

    def test_get_object_container_doesnt_exist(self):
        self.mock_response_klass.type = 'get_object'
        self.assertRaises(ObjectDoesNotExistError,
                          self.driver.get_object,
                          container_name='xz02tphky6fjfiuc0',
                          object_name='notexisted')

    def test_get_object_success(self):
        self.mock_response_klass.type = 'get_object'
        obj = self.driver.get_object(container_name='xz02tphky6fjfiuc0',
                                     object_name='test')

        self.assertEqual(obj.name, 'test')
        self.assertEqual(obj.container.name, 'xz02tphky6fjfiuc0')
        self.assertEqual(obj.size, 0)
        self.assertEqual(obj.hash, 'D41D8CD98F00B204E9800998ECF8427E')
        self.assertEqual(obj.extra['last_modified'],
                         'Fri, 15 Jan 2016 14:43:15 GMT')
        self.assertEqual(obj.extra['content_type'], 'application/octet-stream')
        self.assertEqual(obj.meta_data['rabbits'], 'monkeys')

    def test_create_container_bad_request(self):
        # invalid container name, returns a 400 bad request
        self.mock_response_klass.type = 'invalid_name'
        self.assertRaises(ContainerError,
                          self.driver.create_container,
                          container_name='invalid_name')

    def test_create_container_already_exists(self):
        # container with this name already exists
        self.mock_response_klass.type = 'already_exists'
        self.assertRaises(InvalidContainerNameError,
                          self.driver.create_container,
                          container_name='new-container')

    def test_create_container_success(self):
        # success
        self.mock_response_klass.type = 'create_container'
        name = 'new_container'
        container = self.driver.create_container(container_name=name)
        self.assertEqual(container.name, name)

    def test_create_container_with_ex_location(self):
        self.mock_response_klass.type = 'create_container_location'
        name = 'new_container'
        self.ex_location = 'oss-cn-beijing'
        container = self.driver.create_container(container_name=name,
                                                 ex_location=self.ex_location)
        self.assertEqual(container.name, name)
        self.assertTrue(container.extra['location'], self.ex_location)

    def test_delete_container_doesnt_exist(self):
        container = Container(name='new_container', extra=None,
                              driver=self.driver)
        self.mock_response_klass.type = 'delete_container_doesnt_exist'
        self.assertRaises(ContainerDoesNotExistError,
                          self.driver.delete_container,
                          container=container)

    def test_delete_container_not_empty(self):
        container = Container(name='new_container', extra=None,
                              driver=self.driver)
        self.mock_response_klass.type = 'delete_container_not_empty'
        self.assertRaises(ContainerIsNotEmptyError,
                          self.driver.delete_container,
                          container=container)

    def test_delete_container_success(self):
        self.mock_response_klass.type = 'delete_container'
        container = Container(name='new_container', extra=None,
                              driver=self.driver)
        self.assertTrue(self.driver.delete_container(container=container))

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
        self.mock_raw_response_klass.type = 'invalid_size'
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

    def test_download_object_not_found(self):
        self.mock_raw_response_klass.type = 'not_found'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)
        destination_path = os.path.abspath(__file__) + '.temp'
        self.assertRaises(ObjectDoesNotExistError,
                          self.driver.download_object,
                          obj=obj,
                          destination_path=destination_path,
                          overwrite_existing=False,
                          delete_on_failure=True)

    def test_download_object_as_stream_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=self.driver_type)

        stream = self.driver.download_object_as_stream(obj=obj,
                                                       chunk_size=None)
        self.assertTrue(hasattr(stream, '__iter__'))

    def test_upload_object_invalid_hash1(self):
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        self.mock_raw_response_klass.type = 'invalid_hash1'

        old_func = self.driver_type._upload_file
        try:
            self.driver_type._upload_file = upload_file
            file_path = os.path.abspath(__file__)
            container = Container(name='foo_bar_container', extra={},
                                  driver=self.driver)
            object_name = 'foo_test_upload'
            self.assertRaises(ObjectHashMismatchError,
                              self.driver.upload_object,
                              file_path=file_path,
                              container=container,
                              object_name=object_name,
                              verify_hash=True)
        finally:
            self.driver_type._upload_file = old_func

    def test_upload_object_success(self):
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, '0cc175b9c0f1b6a831c399e269772661', 1000

        old_func = self.driver_type._upload_file
        try:
            self.driver_type._upload_file = upload_file
            file_path = os.path.abspath(__file__)
            container = Container(name='foo_bar_container', extra={},
                                  driver=self.driver)
            object_name = 'foo_test_upload'
            extra = {'meta_data': {'some-value': 'foobar'}}
            obj = self.driver.upload_object(file_path=file_path,
                                            container=container,
                                            object_name=object_name,
                                            extra=extra,
                                            verify_hash=True)
            self.assertEqual(obj.name, 'foo_test_upload')
            self.assertEqual(obj.size, 1000)
            self.assertTrue('some-value' in obj.meta_data)
        finally:
            self.driver_type._upload_file = old_func

    def test_upload_object_with_acl(self):
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, '0cc175b9c0f1b6a831c399e269772661', 1000

        old_func = self.driver_type._upload_file
        try:
            self.driver_type._upload_file = upload_file
            self.mock_raw_response_klass.type = 'acl'
            file_path = os.path.abspath(__file__)
            container = Container(name='foo_bar_container', extra={},
                                  driver=self.driver)
            object_name = 'foo_test_upload'
            extra = {'acl': 'public-read'}
            obj = self.driver.upload_object(file_path=file_path,
                                            container=container,
                                            object_name=object_name,
                                            extra=extra,
                                            verify_hash=True)
            self.assertEqual(obj.name, 'foo_test_upload')
            self.assertEqual(obj.size, 1000)
            self.assertEqual(obj.extra['acl'], 'public-read')
        finally:
            self.driver_type._upload_file = old_func

    def test_upload_object_with_invalid_acl(self):
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_upload'
        extra = {'acl': 'invalid-acl'}
        self.assertRaises(AttributeError,
                          self.driver.upload_object,
                          file_path=file_path,
                          container=container,
                          object_name=object_name,
                          extra=extra,
                          verify_hash=True)

    def test_upload_empty_object_via_stream(self):
        if self.driver.supports_multipart_upload:
            self.mock_raw_response_klass.type = 'multipart'
            self.mock_response_klass.type = 'multipart'
        else:
            self.mock_raw_response_klass.type = None
            self.mock_response_klass.type = None

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_stream_data'
        iterator = DummyIterator(data=[''])
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, 0)

    def test_upload_small_object_via_stream(self):
        if self.driver.supports_multipart_upload:
            self.mock_raw_response_klass.type = 'multipart'
            self.mock_response_klass.type = 'multipart'
        else:
            self.mock_raw_response_klass.type = None
            self.mock_response_klass.type = None

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_stream_data'
        iterator = DummyIterator(data=['2', '3', '5'])
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, 3)

    def test_upload_big_object_via_stream(self):
        if self.driver.supports_multipart_upload:
            self.mock_raw_response_klass.type = 'multipart'
            self.mock_response_klass.type = 'multipart'
        else:
            self.mock_raw_response_klass.type = None
            self.mock_response_klass.type = None

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_stream_data'
        iterator = DummyIterator(
            data=['2' * CHUNK_SIZE, '3' * CHUNK_SIZE, '5'])
        extra = {'content_type': 'text/plain'}
        obj = self.driver.upload_object_via_stream(container=container,
                                                   object_name=object_name,
                                                   iterator=iterator,
                                                   extra=extra)

        self.assertEqual(obj.name, object_name)
        self.assertEqual(obj.size, CHUNK_SIZE * 2 + 1)

    def test_upload_object_via_stream_abort(self):
        if not self.driver.supports_multipart_upload:
            return

        self.mock_raw_response_klass.type = 'MULTIPART'
        self.mock_response_klass.type = 'MULTIPART'

        def _faulty_iterator():
            for i in range(0, 5):
                yield str(i)
            raise RuntimeError('Error in fetching data')

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        object_name = 'foo_test_stream_data'
        iterator = _faulty_iterator()
        extra = {'content_type': 'text/plain'}

        try:
            self.driver.upload_object_via_stream(container=container,
                                                 object_name=object_name,
                                                 iterator=iterator,
                                                 extra=extra)
        except Exception:
            pass

        return

    def test_ex_iterate_multipart_uploads(self):
        if not self.driver.supports_multipart_upload:
            return

        self.mock_response_klass.type = 'list_multipart'

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        for upload in self.driver.ex_iterate_multipart_uploads(container,
                                                               max_uploads=2):
            self.assertTrue(upload.key is not None)
            self.assertTrue(upload.id is not None)
            self.assertTrue(upload.initiated is not None)

    def test_ex_abort_all_multipart_uploads(self):
        if not self.driver.supports_multipart_upload:
            return

        self.mock_response_klass.type = 'list_multipart'

        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)

        with mock.patch('libcloud.storage.drivers.oss.OSSStorageDriver'
                        '._abort_multipart', autospec=True) as mock_abort:
            self.driver.ex_abort_all_multipart_uploads(container)

            self.assertEqual(3, mock_abort.call_count)

    def test_delete_object_not_found(self):
        self.mock_response_klass.type = 'not_found'
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)
        self.assertRaises(ObjectDoesNotExistError,
                          self.driver.delete_object,
                          obj=obj)

    def test_delete_object_success(self):
        container = Container(name='foo_bar_container', extra={},
                              driver=self.driver)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)

        result = self.driver.delete_object(obj=obj)
        self.assertTrue(result)


if __name__ == '__main__':
    sys.exit(unittest.main())
