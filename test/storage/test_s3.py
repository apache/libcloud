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
import sys
import httplib
import unittest

from libcloud.common.types import InvalidCredsError
from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.drivers.s3 import S3StorageDriver, S3USWestStorageDriver
from libcloud.storage.drivers.s3 import S3EUWestStorageDriver
from libcloud.storage.drivers.s3 import S3APSEStorageDriver
from libcloud.storage.drivers.s3 import S3APNEStorageDriver
from libcloud.storage.drivers.dummy import DummyIterator

from test import StorageMockHttp, MockRawResponse # pylint: disable-msg=E0611
from test.file_fixtures import StorageFileFixtures # pylint: disable-msg=E0611

class S3Tests(unittest.TestCase):

    def setUp(self):
        S3StorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3StorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3StorageDriver('dummy', 'dummy')

    def tearDown(self):
        self._remove_test_file()

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

    def test_invalid_credentials(self):
        S3MockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_containers()
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('Exception was not thrown')

    def test_bucket_is_located_in_different_region(self):
        S3MockHttp.type = 'DIFFERENT_REGION'
        try:
            self.driver.list_containers()
        except LibcloudError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_list_containers_empty(self):
        S3MockHttp.type = 'list_containers_EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

    def test_list_containers_success(self):
        S3MockHttp.type = 'list_containers'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)

        self.assertTrue('creation_date' in containers[1].extra)

    def test_list_container_objects_empty(self):
        S3MockHttp.type = 'EMPTY'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

    def test_list_container_objects_success(self):
        S3MockHttp.type = None
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 1)

        obj = [o for o in objects if o.name == '1.zip'][0]
        self.assertEqual(obj.hash, '4397da7a7649e8085de9916c240e8166')
        self.assertEqual(obj.size, 1234567)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertTrue('owner' in obj.meta_data)

    def test_get_container_doesnt_exist(self):
        S3MockHttp.type = 'list_containers'
        try:
            self.driver.get_container(container_name='container1')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_container_success(self):
        S3MockHttp.type = 'list_containers'
        container = self.driver.get_container(container_name='test1')
        self.assertTrue(container.name, 'test1')

    def test_get_object_container_doesnt_exist(self):
        # This method makes two requests which makes mocking the response a bit
        # trickier
        S3MockHttp.type = 'list_containers'
        try:
            self.driver.get_object(container_name='test-inexistent',
                                   object_name='test')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_object_success(self):
        # This method makes two requests which makes mocking the response a bit
        # trickier
        S3MockHttp.type = 'list_containers'
        obj = self.driver.get_object(container_name='test2',
                                     object_name='test')

        self.assertEqual(obj.name, 'test')
        self.assertEqual(obj.container.name, 'test2')
        self.assertEqual(obj.size, 12345)
        self.assertEqual(obj.hash, 'e31208wqsdoj329jd')

    def test_create_container_invalid_name(self):
        # invalid container name
        S3MockHttp.type = 'INVALID_NAME'
        try:
            self.driver.create_container(container_name='new_container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_already_exists(self):
        # container with this name already exists
        S3MockHttp.type = 'ALREADY_EXISTS'
        try:
            self.driver.create_container(container_name='new-container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_success(self):
        # success
        S3MockHttp.type = None
        container = self.driver.create_container(container_name='new_container')
        self.assertEqual(container.name, 'new_container')

    def test_delete_container_doesnt_exist(self):
        container = Container(name='new_container', extra=None, driver=self)
        S3MockHttp.type = 'DOESNT_EXIST'
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_container_not_empty(self):
        container = Container(name='new_container', extra=None, driver=self)
        S3MockHttp.type = 'NOT_EMPTY'
        try:
            self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Exception was not thrown')

        # success
        S3MockHttp.type = None
        self.assertTrue(self.driver.delete_container(container=container))

    def test_delete_container_not_found(self):
        S3MockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Container does not exist but an exception was not thrown')

    def test_delete_container_success(self):
        S3MockHttp.type = None
        container = Container(name='new_container', extra=None, driver=self)
        self.assertTrue(self.driver.delete_container(container=container))

    def test_download_object_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=S3StorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertTrue(result)

    def test_download_object_invalid_file_size(self):
        S3MockRawResponse.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=S3StorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertFalse(result)

    def test_download_object_invalid_file_already_exists(self):
        S3MockRawResponse.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=S3StorageDriver)
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
        container = Container(name='foo_bar_container', extra={}, driver=self)

        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=S3StorageDriver)

        stream = self.driver.download_object_as_stream(obj=obj, chunk_size=None)
        self.assertTrue(hasattr(stream, '__iter__'))

    def test_upload_object_invalid_ex_storage_class(self):
        # Invalid hash is detected on the amazon side and BAD_REQUEST is
        # returned
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      verify_hash=True,
                                      ex_storage_class='invalid-class')
        except ValueError, e:
            self.assertTrue(str(e).lower().find('invalid storage class') != -1)
            pass
        else:
           self.fail('Exception was not thrown')

    def test_upload_object_invalid_hash1(self):
        # Invalid hash is detected on the amazon side and BAD_REQUEST is
        # returned
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        S3MockRawResponse.type = 'INVALID_HASH1'

        old_func = S3StorageDriver._upload_file
        S3StorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      verify_hash=True)
        except ObjectHashMismatchError:
            pass
        else:
            self.fail(
                'Invalid hash was returned but an exception was not thrown')
        finally:
            S3StorageDriver._upload_file = old_func

    def test_upload_object_invalid_hash2(self):
        # Invalid hash is detected when comparing hash provided in the response
        # ETag header
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, '0cc175b9c0f1b6a831c399e269772661', 1000

        S3MockRawResponse.type = 'INVALID_HASH2'

        old_func = S3StorageDriver._upload_file
        S3StorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      verify_hash=True)
        except ObjectHashMismatchError:
            pass
        else:
            self.fail(
                'Invalid hash was returned but an exception was not thrown')
        finally:
            S3StorageDriver._upload_file = old_func

    def test_upload_object_success(self):
        def upload_file(self, response, file_path, chunked=False,
                        calculate_hash=True):
            return True, '0cc175b9c0f1b6a831c399e269772661', 1000

        old_func = S3StorageDriver._upload_file
        S3StorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        extra = {'meta_data': { 'some-value': 'foobar'}}
        obj = self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      extra=extra,
                                      verify_hash=True)
        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, 1000)
        self.assertTrue('some-value' in obj.meta_data)
        S3StorageDriver._upload_file = old_func

    def test_upload_object_via_stream(self):
        try:
            container = Container(name='foo_bar_container', extra={}, driver=self)
            object_name = 'foo_test_stream_data'
            iterator = DummyIterator(data=['2', '3', '5'])
            self.driver.upload_object_via_stream(container=container,
                                                 object_name=object_name,
                                                 iterator=iterator)
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_object_not_found(self):
        S3MockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)
        try:
            self.driver.delete_object(obj=obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_object_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1234, hash=None, extra=None,
                     meta_data=None, container=container, driver=self.driver)

        result = self.driver.delete_object(obj=obj)
        self.assertTrue(result)

class S3USWestTests(S3Tests):
    def setUp(self):
        S3USWestStorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3USWestStorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3USWestStorageDriver('dummy', 'dummy')

class S3EUWestTests(S3Tests):
    def setUp(self):
        S3EUWestStorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3EUWestStorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3EUWestStorageDriver('dummy', 'dummy')

class S3APSETests(S3Tests):
    def setUp(self):
        S3APSEStorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3APSEStorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3APSEStorageDriver('dummy', 'dummy')

class S3APNETests(S3Tests):
    def setUp(self):
        S3APNEStorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3APNEStorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3APNEStorageDriver('dummy', 'dummy')

class S3MockHttp(StorageMockHttp):

    fixtures = StorageFileFixtures('s3')
    base_headers = {}

    def _UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED,
                '',
                self.base_headers,
                httplib.responses[httplib.OK])

    def _DIFFERENT_REGION(self, method, url, body, headers):
        return (httplib.MOVED_PERMANENTLY,
                '',
                self.base_headers,
                httplib.responses[httplib.OK])

    def _list_containers_EMPTY(self, method, url, body, headers):
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

    def _test_container_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects_empty.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _test_container(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects.xml')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _test2_test_list_containers(self, method, url, body, headers):
        # test_get_object
        body = self.fixtures.load('list_containers.xml')
        headers = { 'content-type': 'application/zip',
                    'etag': '"e31208wqsdoj329jd"',
                    'content-length': 12345,
                    }

        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container_INVALID_NAME(self, method, url, body, headers):
        # test_create_container
        return (httplib.BAD_REQUEST,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container_ALREADY_EXISTS(self, method, url, body, headers):
        # test_create_container
        return (httplib.CONFLICT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container(self, method, url, body, headers):
        # test_create_container, test_delete_container

        if method == 'PUT':
            status = httplib.OK
        elif method == 'DELETE':
            status = httplib.NO_CONTENT

        return (status,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container_DOESNT_EXIST(self, method, url, body, headers):
        # test_delete_container
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _new_container_NOT_EMPTY(self, method, url, body, headers):
        # test_delete_container
        return (httplib.CONFLICT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container(self, method, url, body, headers):
        # test_delete_container
        return (httplib.NO_CONTENT,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_NOT_FOUND(self, method, url, body, headers):
        # test_delete_container_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_bar_object_NOT_FOUND(self, method, url, body, headers):
        # test_delete_object_not_found
        return (httplib.NOT_FOUND,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_bar_object(self, method, url, body, headers):
        # test_delete_object
        return (httplib.NO_CONTENT,
                body,
                headers,
                httplib.responses[httplib.OK])

class S3MockRawResponse(MockRawResponse):

    fixtures = StorageFileFixtures('s3')

    def _foo_bar_container_foo_bar_object(self, method, url, body, headers):
        # test_download_object_success
        body = ''
        self._data = self._generate_random_data(1000)
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_test_upload_INVALID_HASH1(self, method, url, body, headers):
        body = ''
        headers = {}
        headers['etag'] = '"foobar"'
        # test_upload_object_invalid_hash1
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_test_upload_INVALID_HASH2(self, method, url, body, headers):
        # test_upload_object_invalid_hash2
        body = ''
        headers = { 'etag': '"hash343hhash89h932439jsaa89"'}
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_test_upload(self, method, url, body, headers):
        # test_upload_object_success
        body = ''
        headers = { 'etag': '"0cc175b9c0f1b6a831c399e269772661"'}
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

    def _foo_bar_container_foo_bar_object_INVALID_SIZE(self, method, url, body, headers):
        # test_upload_object_invalid_file_size
        body = ''
        return (httplib.OK,
                body,
                headers,
                httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
