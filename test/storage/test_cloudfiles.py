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
import os.path                          # pylint: disable-msg=W0404
import random
import sys
import copy
import unittest
import httplib

import libcloud.utils

from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.types import ObjectHashMismatchError
from libcloud.storage.drivers.cloudfiles import CloudFilesStorageDriver
from libcloud.storage.drivers.dummy import DummyIterator

from test import MockHttp, MockRawResponse # pylint: disable-msg=E0611
from test.file_fixtures import StorageFileFixtures # pylint: disable-msg=E0611

class CloudFilesTests(unittest.TestCase):

    def setUp(self):
        CloudFilesStorageDriver.connectionCls.conn_classes = (
            None, CloudFilesMockHttp)
        CloudFilesStorageDriver.connectionCls.rawResponseCls = \
                                              CloudFilesMockRawResponse
        CloudFilesMockHttp.type = None
        CloudFilesMockRawResponse.type = None
        self.driver = CloudFilesStorageDriver('dummy', 'dummy')
        self._remove_test_file()

    def tearDown(self):
        self._remove_test_file()

    def test_get_meta_data(self):
        self.driver.get_meta_data()

    def test_list_containers(self):
        CloudFilesMockHttp.type = 'EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

        CloudFilesMockHttp.type = None
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 3)

        container = [c for c in containers if c.name == 'container2'][0]
        self.assertEqual(container.extra['object_count'], 120)
        self.assertEqual(container.extra['size'], 340084450)

    def test_list_container_objects(self):
        CloudFilesMockHttp.type = 'EMPTY'
        container = Container(
            name='test_container', extra={}, driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

        CloudFilesMockHttp.type = None
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 4)

        obj = [o for o in objects if o.name == 'foo test 1'][0]
        self.assertEqual(obj.hash, '16265549b5bda64ecdaa5156de4c97cc')
        self.assertEqual(obj.size, 1160520)
        self.assertEqual(obj.container.name, 'test_container')

    def test_get_container(self):
        container = self.driver.get_container(container_name='test_container')
        self.assertEqual(container.name, 'test_container')
        self.assertEqual(container.extra['object_count'], 800)
        self.assertEqual(container.extra['size'], 1234568)

    def test_get_object(self):
        obj = self.driver.get_object(container_name='test_container',
                                     object_name='test_object')
        self.assertEqual(obj.container.name, 'test_container')
        self.assertEqual(obj.size, 555)
        self.assertEqual(obj.extra['content_type'], 'application/zip')
        self.assertEqual(obj.extra['etag'], '6b21c4a111ac178feacf9ec9d0c71f17')
        self.assertEqual(
            obj.extra['last_modified'], 'Tue, 25 Jan 2011 22:01:49 GMT')
        self.assertEqual(obj.meta_data['foo-bar'], 'test 1')
        self.assertEqual(obj.meta_data['bar-foo'], 'test 2')

    def test_create_container_success(self):
        container = self.driver.create_container(
            container_name='test_create_container')
        self.assertTrue(isinstance(container, Container))
        self.assertEqual(container.name, 'test_create_container')
        self.assertEqual(container.extra['object_count'], 0)

    def test_create_container_already_exists(self):
        CloudFilesMockHttp.type = 'ALREADY_EXISTS'

        try:
            self.driver.create_container(
                container_name='test_create_container')
        except ContainerAlreadyExistsError:
            pass
        else:
            self.fail(
                'Container already exists but an exception was not thrown')

    def test_create_container_invalid_name(self):
        name = ''.join([ 'x' for x in range(0, 257)])
        try:
            self.driver.create_container(container_name=name)
        except:
            pass
        else:
            self.fail(
                'Invalid name was provided (name is too long)'
                ', but exception was not thrown')

    def test_delete_container_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        result = self.driver.delete_container(container=container)
        self.assertTrue(result)

    def test_delete_container_not_found(self):
        CloudFilesMockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail(
                'Container does not exist but an exception was not thrown')

    def test_delete_container_not_empty(self):
        CloudFilesMockHttp.type = 'NOT_EMPTY'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Container is not empty but an exception was not thrown')

    def test_download_object_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertTrue(result)

    def test_download_object_invalid_file_size(self):
        CloudFilesMockRawResponse.type = 'INVALID_SIZE'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        result = self.driver.download_object(obj=obj,
                                             destination_path=destination_path,
                                             overwrite_existing=False,
                                             delete_on_failure=True)
        self.assertFalse(result)

    def test_download_object_success_not_found(self):
        #CloudFilesMockHttp.type = 'NOT_FOUND'
        CloudFilesMockRawResponse.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)

        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container,
                     meta_data=None,
                     driver=CloudFilesStorageDriver)
        destination_path = os.path.abspath(__file__) + '.temp'
        try:
            self.driver.download_object(
                obj=obj,
                destination_path=destination_path,
                overwrite_existing=False,
                delete_on_failure=True)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Object does not exist but an exception was not thrown')

    def object_as_stream(self):
        pass

    def test_upload_object_success(self):
        def upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        old_func = CloudFilesStorageDriver._upload_file
        CloudFilesStorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        obj = self.driver.upload_object(
            file_path=file_path, container=container,
                                        object_name=object_name)
        self.assertEqual(obj.name, 'foo_test_upload')
        self.assertEqual(obj.size, 1000)
        CloudFilesStorageDriver._upload_file = old_func

    def test_upload_object_invalid_hash(self):
        def upload_file(self, response, file_path, chunked=False,
                     calculate_hash=True):
            return True, 'hash343hhash89h932439jsaa89', 1000

        CloudFilesMockRawResponse.type = 'INVALID_HASH'

        old_func = CloudFilesStorageDriver._upload_file
        CloudFilesStorageDriver._upload_file = upload_file
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name,
                                      file_hash='footest123')
        except ObjectHashMismatchError:
            pass
        else:
            self.fail(
                'Invalid hash was returned but an exception was not thrown')
        finally:
            CloudFilesStorageDriver._upload_file = old_func

    def test_upload_object_no_content_type(self):
        def no_content_type(name):
            return None, None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = no_content_type
        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(file_path=file_path, container=container,
                                      object_name=object_name)
        except AttributeError:
            pass
        else:
            self.fail(
                'File content type not provided'
                ' but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_upload_object_error(self):
        def dummy_content_type(name):
            return 'application/zip', None

        def send(instance):
            raise Exception('')

        old_func1 = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type
        old_func2 = CloudFilesMockHttp.send
        CloudFilesMockHttp.send = send

        file_path = os.path.abspath(__file__)
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(
                file_path=file_path,
                container=container,
                object_name=object_name)
        except LibcloudError:
            pass
        else:
            self.fail('Timeout while uploading but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func1
            CloudFilesMockHttp.send = old_func2

    def test_upload_object_inexistent_file(self):
        def dummy_content_type(name):
            return 'application/zip', None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type

        file_path = os.path.abspath(__file__ + '.inexistent')
        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_upload'
        try:
            self.driver.upload_object(
                file_path=file_path,
                container=container,
                object_name=object_name)
        except OSError:
            pass
        else:
            self.fail('Inesitent but an exception was not thrown')
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_upload_object_via_stream(self):
        def dummy_content_type(name):
            return 'application/zip', None

        old_func = libcloud.utils.guess_file_mime_type
        libcloud.utils.guess_file_mime_type = dummy_content_type

        container = Container(name='foo_bar_container', extra={}, driver=self)
        object_name = 'foo_test_stream_data'
        iterator = DummyIterator(data=['2', '3', '5'])
        try:
            self.driver.upload_object_via_stream(container=container,
                                                 object_name=object_name,
                                                 iterator=iterator)
        finally:
            libcloud.utils.guess_file_mime_type = old_func

    def test_delete_object_success(self):
        CloudFilesMockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        obj = Object(name='foo_bar_object', size=1000, hash=None, extra={},
                     container=container, meta_data=None,
                     driver=CloudFilesStorageDriver)
        try:
            self.driver.delete_object(obj=obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Object does not exist but an exception was not thrown')

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

class CloudFilesMockHttp(MockHttp):

    fixtures = StorageFileFixtures('cloudfiles')
    base_headers = { 'content-type': 'application/json; charset=UTF-8'}

    def putrequest(self, method, action):
        pass

    def putheader(self, key, value):
        pass

    def endheaders(self):
        pass

    def send(self, data):
        pass

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = copy.deepcopy(self.base_headers)
        headers.update({ 'x-server-management-url':
                             'https://servers.api.rackspacecloud.com/v1.0/slug',
                         'x-auth-token': 'FE011C19',
                         'x-cdn-management-url':
                             'https://cdn.clouddrive.com/v1/MossoCloudFS',
                         'x-storage-token': 'FE011C19',
                         'x-storage-url':
                            'https://storage4.clouddrive.com/v1/MossoCloudFS'})
        return (httplib.NO_CONTENT,
                "",
                headers,
                httplib.responses[httplib.NO_CONTENT])

    def _v1_MossoCloudFS_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_containers_empty.json')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS(self, method, url, body, headers):
        if method == 'GET':
            # list_containers
            body = self.fixtures.load('list_containers.json')
            status_code = httplib.OK
            headers = copy.deepcopy(self.base_headers)
        elif method == 'HEAD':
            # get_meta_data
            body = self.fixtures.load('meta_data.json')
            status_code = httplib.NO_CONTENT
            headers = copy.deepcopy(self.base_headers)
            headers.update({ 'x-account-container-count': 10,
                             'x-account-object-count': 400,
                             'x-account-bytes-used': 1234567
                           })
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_container_objects_empty.json')
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container(self, method, url, body, headers):
        if method == 'GET':
            # list_container_objects
            body = self.fixtures.load('list_container_objects.json')
            status_code = httplib.OK
            headers = copy.deepcopy(self.base_headers)
        elif method == 'HEAD':
            # get_container
            body = self.fixtures.load('list_container_objects_empty.json')
            status_code = httplib.NO_CONTENT
            headers = copy.deepcopy(self.base_headers)
            headers.update({ 'x-container-object-count': 800,
                             'x-container-bytes-used': 1234568
                           })
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_container_test_object(
        self, method, url, body, headers):

        if method == 'HEAD':
            # get_object
            body = self.fixtures.load('list_container_objects_empty.json')
            status_code = httplib.NO_CONTENT
            headers = self.base_headers
            headers.update({ 'content-length': 555,
                             'last-modified': 'Tue, 25 Jan 2011 22:01:49 GMT',
                             'etag': '6b21c4a111ac178feacf9ec9d0c71f17',
                             'x-object-meta-foo-bar': 'test 1',
                             'x-object-meta-bar-foo': 'test 2',
                             'content-type': 'application/zip'})
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_create_container(
        self, method, url, body, headers):

        # test_create_container_success
        body = self.fixtures.load('list_container_objects_empty.json')
        headers = self.base_headers
        headers.update({ 'content-length': 18,
                         'date': 'Mon, 28 Feb 2011 07:52:57 GMT'
                       })
        status_code = httplib.CREATED
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_test_create_container_ALREADY_EXISTS(
        self, method, url, body, headers):

        # test_create_container_already_exists
        body = self.fixtures.load('list_container_objects_empty.json')
        headers = self.base_headers
        headers.update({ 'content-type': 'text/plain' })
        status_code = httplib.ACCEPTED
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container(self, method, url, body, headers):
        if method == 'DELETE':
            # test_delete_container_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NO_CONTENT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_NOT_FOUND(
        self, method, url, body, headers):

        if method == 'DELETE':
            # test_delete_container_not_found
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NOT_FOUND
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_NOT_EMPTY(
        self, method, url, body, headers):

        if method == 'DELETE':
            # test_delete_container_not_empty
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.CONFLICT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object(
        self, method, url, body, headers):

        if method == 'DELETE':
            # test_delete_object_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NO_CONTENT
        return (status_code, body, headers, httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object_NOT_FOUND(
        self, method, url, body, headers):

        if method == 'DELETE':
            # test_delete_object_success
            body = self.fixtures.load('list_container_objects_empty.json')
            headers = self.base_headers
            status_code = httplib.NOT_FOUND

        return (status_code, body, headers, httplib.responses[httplib.OK])

class CloudFilesMockRawResponse(MockRawResponse):

    fixtures = StorageFileFixtures('cloudfiles')
    base_headers = { 'content-type': 'application/json; charset=UTF-8'}

    def __init__(self, *args, **kwargs):
        super(CloudFilesMockRawResponse, self).__init__(*args, **kwargs)
        self._data = []
        self._current_item = 0

    def next(self):
        if self._current_item == len(self._data):
            raise StopIteration

        value = self._data[self._current_item]
        self._current_item += 1
        return value

    def _generate_random_data(self, size):
        data = []
        current_size = 0
        while current_size < size:
            value = str(random.randint(0, 9))
            value_size = len(value)
            data.append(value)
            current_size += value_size

        return data

    def  _v1_MossoCloudFS_foo_bar_container_foo_test_upload(
        self, method, url, body, headers):
        # test_object_upload_success

        body = ''
        headers = copy.deepcopy(self.base_headers)
        headers.update(headers)
        return (httplib.CREATED, body, headers, httplib.responses[httplib.OK])

    def  _v1_MossoCloudFS_foo_bar_container_foo_test_upload_INVALID_HASH(
        self, method, url, body, headers):

        # test_object_upload_invalid_hash
        body = ''
        headers = self.base_headers
        return (httplib.UNPROCESSABLE_ENTITY, body, headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object(
        self, method, url, body, headers):

        # test_download_object_success
        body = 'test'
        self._data = self._generate_random_data(1000)
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object_INVALID_SIZE(
        self, method, url, body, headers):

        # test_download_object_invalid_file_size
        body = 'test'
        self._data = self._generate_random_data(100)
        return (httplib.OK, body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_bar_object_NOT_FOUND(
        self, method, url, body, headers):

        body = ''
        return (httplib.NOT_FOUND, body,
                self.base_headers,
                httplib.responses[httplib.OK])

    def _v1_MossoCloudFS_foo_bar_container_foo_test_stream_data(
        self, method, url, body, headers):

        # test_upload_object_via_stream_success
        body = 'test'
        return (httplib.OK,
                body,
                self.base_headers,
                httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
