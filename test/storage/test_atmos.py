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
import httplib
import os.path
import sys
import unittest
import urlparse

from xml.etree import ElementTree

from libcloud.storage.base import Container
from libcloud.storage.types import ContainerAlreadyExistsError, \
                                   ContainerDoesNotExistError, \
                                   ContainerIsNotEmptyError, \
                                   ObjectDoesNotExistError
from libcloud.storage.drivers.atmos import AtmosDriver

from test import StorageMockHttp, MockRawResponse
from test.file_fixtures import StorageFileFixtures

class AtmosTests(unittest.TestCase):
    def setUp(self):
        AtmosDriver.connectionCls.conn_classes = (None, AtmosMockHttp)
        AtmosDriver.connectionCls.rawResponseCls = AtmosMockRawResponse
        AtmosDriver.path = ''
        AtmosMockHttp.type = None
        AtmosMockRawResponse.type = None
        self.driver = AtmosDriver('dummy', base64.b64encode('dummy'))
        self._remove_test_file()

    def tearDown(self):
        self._remove_test_file()

    def _remove_test_file(self):
        file_path = os.path.abspath(__file__) + '.temp'

        try:
            os.unlink(file_path)
        except OSError:
            pass

    def test_list_containers(self):
        AtmosMockHttp.type = 'EMPTY'
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 0)

        AtmosMockHttp.type = None
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 6)

    def test_list_container_objects(self):
        container = Container(name='test_container', extra={},
                              driver=self.driver)

        AtmosMockHttp.type = 'EMPTY'
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 0)

        AtmosMockHttp.type = None
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 2)

        obj = [o for o in objects if o.name == 'not-a-container1'][0]
        self.assertEqual(obj.meta_data['object_id'],
                         '651eae32634bf84529c74eabd555fda48c7cead6')
        self.assertEqual(obj.container.name, 'test_container')

    def test_get_container(self):
        container = self.driver.get_container(container_name='test_container')
        self.assertEqual(container.name, 'test_container')
        self.assertEqual(container.extra['object_id'],
                         'b21cb59a2ba339d1afdd4810010b0a5aba2ab6b9')

    def test_get_container_not_found(self):
        try:
            self.driver.get_container(container_name='not_found')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container_success(self):
        container = self.driver.create_container(
            container_name='test_create_container')
        self.assertTrue(isinstance(container, Container))
        self.assertEqual(container.name, 'test_create_container')
        self.assertEqual(container.extra['object_id'],
                         '31a27b593629a3fe59f887fd973fd953e80062ce')

    def test_create_container_already_exists(self):
        AtmosMockHttp.type = 'ALREADY_EXISTS'

        try:
            self.driver.create_container(
                container_name='test_create_container')
        except ContainerAlreadyExistsError:
            pass
        else:
            self.fail(
                'Container already exists but an exception was not thrown')

    def test_delete_container_success(self):
        container = Container(name='foo_bar_container', extra={}, driver=self)
        result = self.driver.delete_container(container=container)
        self.assertTrue(result)

    def test_delete_container_not_found(self):
        AtmosMockHttp.type = 'NOT_FOUND'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            self.driver.delete_container(container=container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail(
                'Container does not exist but an exception was not thrown')

    def test_delete_container_not_empty(self):
        AtmosMockHttp.type = 'NOT_EMPTY'
        container = Container(name='foo_bar_container', extra={}, driver=self)
        try:
            self.driver.delete_container(container=container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Container is not empty but an exception was not thrown')

    def test_get_object_success(self):
        obj = self.driver.get_object(container_name='test_container',
                                     object_name='test_object')
        self.assertEqual(obj.container.name, 'test_container')
        self.assertEqual(obj.size, 555)
        self.assertEqual(obj.hash, '6b21c4a111ac178feacf9ec9d0c71f17')
        self.assertEqual(obj.extra['object_id'],
                         '322dce3763aadc41acc55ef47867b8d74e45c31d6643')
        self.assertEqual(
            obj.extra['last_modified'], 'Tue, 25 Jan 2011 22:01:49 GMT')
        self.assertEqual(obj.meta_data['foo-bar'], 'test 1')
        self.assertEqual(obj.meta_data['bar-foo'], 'test 2')


    def test_get_object_not_found(self):
        try:
            self.driver.get_object(container_name='test_container',
                                   object_name='not_found')
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

class AtmosMockHttp(StorageMockHttp):
    fixtures = StorageFileFixtures('atmos')

    def request(self, method, url, body=None, headers=None, raw=False):
        headers = headers or {}
        parsed = urlparse.urlparse(url)
        if parsed.query.startswith('metadata/'):
            parsed = list(parsed)
            parsed[2] = parsed[2] + '/' + parsed[4]
            parsed[4] = ''
            url = urlparse.urlunparse(parsed)
        return super(AtmosMockHttp, self).request(method, url, body, headers,
                                                  raw)

    def _rest_namespace_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('empty_directory_listing.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_namespace(self, method, url, body, headers):
        body = self.fixtures.load('list_containers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_namespace_test_container_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('empty_directory_listing.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_namespace_test_container(self, method, url, body, headers):
        body = self.fixtures.load('list_containers.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _rest_namespace_test_container__metadata_system(self, method, url, body,
                                                        headers):
        headers = {
            'x-emc-meta': 'objectid=b21cb59a2ba339d1afdd4810010b0a5aba2ab6b9'
        }
        return (httplib.OK, '', headers, httplib.responses[httplib.OK])

    def _rest_namespace_not_found__metadata_system(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('not_found.xml')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _rest_namespace_test_create_container(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _rest_namespace_test_create_container__metadata_system(self, method,
                                                               url, body,
                                                               headers):
        headers = {
            'x-emc-meta': 'objectid=31a27b593629a3fe59f887fd973fd953e80062ce'
        }
        return (httplib.OK, '', headers, httplib.responses[httplib.OK])

    def _rest_namespace_test_create_container_ALREADY_EXISTS(self, method, url,
                                                             body, headers):
        body = self.fixtures.load('already_exists.xml')
        return (httplib.BAD_REQUEST, body, {},
                httplib.responses[httplib.BAD_REQUEST])

    def _rest_namespace_foo_bar_container(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _rest_namespace_foo_bar_container_NOT_FOUND(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('not_found.xml')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _rest_namespace_foo_bar_container_NOT_EMPTY(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('not_empty.xml')
        return (httplib.BAD_REQUEST, body, {},
                httplib.responses[httplib.BAD_REQUEST])

    def _rest_namespace_test_container_test_object_metadata_system(self, method,
                                                                   url, body,
                                                                   headers):
        meta = {
            'objectid': '322dce3763aadc41acc55ef47867b8d74e45c31d6643',
            'size': '555',
            'mtime': '2011-01-25T22:01:49Z'
        }
        headers = {
            'x-emc-meta': ', '.join([k + '=' + v for k, v in meta.items()])
        }
        return (httplib.OK, '', headers, httplib.responses[httplib.OK])

    def _rest_namespace_test_container_test_object_metadata_user(self, method,
                                                                 url, body,
                                                                 headers):
        meta = {
            'md5': '6b21c4a111ac178feacf9ec9d0c71f17',
            'foo-bar': 'test 1',
            'bar-foo': 'test 2',
        }
        headers = {
            'x-emc-meta': ', '.join([k + '=' + v for k, v in meta.items()])
        }
        return (httplib.OK, '', headers, httplib.responses[httplib.OK])

    def _rest_namespace_test_container_not_found_metadata_system(self, method,
                                                                 url, body,
                                                                 headers):
        body = self.fixtures.load('not_found.xml')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

class AtmosMockRawResponse(MockRawResponse):
    pass

if __name__ == '__main__':
    sys.exit(unittest.main())
