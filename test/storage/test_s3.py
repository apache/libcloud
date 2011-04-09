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

from libcloud.storage.base import Container, Object
from libcloud.storage.drivers.s3 import S3StorageDriver, S3USWestStorageDriver
from libcloud.storage.drivers.s3 import S3EUWestStorageDriver
from libcloud.storage.drivers.s3 import S3APSEStorageDriver
from libcloud.storage.drivers.s3 import S3APNEStorageDriver

from test import MockHttp, MockRawResponse # pylint: disable-msg=E0611
from test.file_fixtures import StorageFileFixtures # pylint: disable-msg=E0611

class S3Tests(unittest.TestCase):
    def setUp(self):
        S3StorageDriver.connectionCls.conn_classes = (
            None, S3MockHttp)
        S3StorageDriver.connectionCls.rawResponseCls = \
                                              S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3StorageDriver('dummy', 'dummy')

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

class S3USWestTests(S3Tests):
    def setUp(self):
        S3USWestStorageDriver.connectionCls.conn_classes = (
            None, S3MockHttp)
        S3USWestStorageDriver.connectionCls.rawResponseCls = \
                                              S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3USWestStorageDriver('dummy', 'dummy')

class S3EUWestTests(S3Tests):
    def setUp(self):
        S3EUWestStorageDriver.connectionCls.conn_classes = (
            None, S3MockHttp)
        S3EUWestStorageDriver.connectionCls.rawResponseCls = \
                                              S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3EUWestStorageDriver('dummy', 'dummy')

class S3APSETests(S3Tests):
    def setUp(self):
        S3APSEStorageDriver.connectionCls.conn_classes = (
            None, S3MockHttp)
        S3APSEStorageDriver.connectionCls.rawResponseCls = \
                                              S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3APSEStorageDriver('dummy', 'dummy')

class S3APNETests(S3Tests):
    def setUp(self):
        S3APNEStorageDriver.connectionCls.conn_classes = (
            None, S3MockHttp)
        S3APNEStorageDriver.connectionCls.rawResponseCls = \
                                              S3MockRawResponse
        S3MockHttp.type = None
        S3MockRawResponse.type = None
        self.driver = S3APNEStorageDriver('dummy', 'dummy')

class S3MockHttp(MockHttp):

    fixtures = StorageFileFixtures('s3')
    base_headers = {}

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

class S3MockRawResponse(MockRawResponse):

    fixtures = StorageFileFixtures('s3')

if __name__ == '__main__':
    sys.exit(unittest.main())
