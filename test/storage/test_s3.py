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

import sys
import httplib
import unittest

from libcloud.common.types import InvalidCredsError
from libcloud.storage.base import Container, Object
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import InvalidContainerNameError
from libcloud.storage.drivers.s3 import S3StorageDriver, S3USWestStorageDriver
from libcloud.storage.drivers.s3 import S3EUWestStorageDriver
from libcloud.storage.drivers.s3 import S3APSEStorageDriver
from libcloud.storage.drivers.s3 import S3APNEStorageDriver

from test import MockHttp, MockRawResponse # pylint: disable-msg=E0611
from test.file_fixtures import StorageFileFixtures # pylint: disable-msg=E0611

class S3Tests(unittest.TestCase):
    def setUp(self):
        S3StorageDriver.connectionCls.conn_classes = (None, S3MockHttp)
        S3StorageDriver.connectionCls.rawResponseCls = S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3StorageDriver('dummy', 'dummy')

    def test_invalid_credts(self):
        S3MockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver.list_containers()
        except InvalidCredsError, e:
            self.assertEqual(True, isinstance(e, InvalidCredsError))
        else:
            self.fail('Exception was not thrown')

    def test_get_meta_data(self):
        try:
            self.driver.get_meta_data()
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_list_containers(self):
        S3MockHttp.type = 'list_containers_EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

        S3MockHttp.type = 'list_containers'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)

        self.assertTrue('creation_date' in containers[1].extra)

    def test_list_container_objects(self):
        S3MockHttp.type = 'EMPTY'
        container = Container(name='test_container', extra={},
                              driver=self.driver)
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

        S3MockHttp.type = None
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 1)

        obj = [o for o in objects if o.name == '1.zip'][0]
        self.assertEqual(obj.hash, '4397da7a7649e8085de9916c240e8166')
        self.assertEqual(obj.size, 1234567)
        self.assertEqual(obj.container.name, 'test_container')
        self.assertTrue('owner' in obj.meta_data)

    def test_get_container(self):
        S3MockHttp.type = 'list_containers'

        try:
            container = self.driver.get_container(container_name='container1')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

        container = self.driver.get_container(container_name='test1')
        self.assertTrue(container.name, 'test1')

    def test_get_object(self):
        # This method makes two requests which makes mocking the response a bit
        # trickier
        S3MockHttp.type = 'list_containers'

        try:
            obj = self.driver.get_object(container_name='test-inexistent',
                                         object_name='test')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

        obj = self.driver.get_object(container_name='test2',
                                     object_name='test')

        self.assertEqual(obj.name, 'test')
        self.assertEqual(obj.container.name, 'test2')
        self.assertEqual(obj.size, 12345)
        self.assertEqual(obj.hash, 'e31208wqsdoj329jd')

    def test_create_container(self):
        # invalid container name
        S3MockHttp.type = 'INVALID_NAME'
        try:
            self.driver.create_container(container_name='new_container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

        # container with this name already exists
        S3MockHttp.type = 'ALREADY_EXISTS'
        try:
            self.driver.create_container(container_name='new-container')
        except InvalidContainerNameError:
            pass
        else:
            self.fail('Exception was not thrown')

        # success
        S3MockHttp.type = None
        container = self.driver.create_container(container_name='new_container')
        self.assertEqual(container.name, 'new_container')

    def test_delete_container(self):
        container = Container(name='new_container', extra=None, driver=self)

        S3MockHttp.type = 'DOESNT_EXIST'
        # does not exist
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

        # container is not empty
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

class S3MockHttp(MockHttp):

    fixtures = StorageFileFixtures('s3')
    base_headers = {}

    def _UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED,
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

class S3MockRawResponse(MockRawResponse):

    fixtures = StorageFileFixtures('s3')

if __name__ == '__main__':
    sys.exit(unittest.main())
