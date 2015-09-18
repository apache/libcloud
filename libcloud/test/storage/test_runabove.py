# -*- coding: utf-8 -*-
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
import unittest
from mock import patch

from libcloud.utils.py3 import httplib, StringIO

from libcloud.storage.base import Object
from libcloud.storage.types import ContainerDoesNotExistError, ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError
from libcloud.storage.drivers.runabove import RunAboveStorageDriver, RunAboveContainer

from libcloud.test import StorageMockHttp
from libcloud.test.secrets import RUNABOVE_PARAMS
from libcloud.test.file_fixtures import StorageFileFixtures
from libcloud.test.common.test_runabove import BaseRunAboveMockHttp


class RunAboveStorageMockHttp(BaseRunAboveMockHttp):
    fixtures = StorageFileFixtures('runabove')

    def _json_1_0_storage_get(self, method, url, body, headers):
        body = self.fixtures.load('storage.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_storage_post(self, method, url, body, headers):
        body = self.fixtures.load('storage_post.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_storage_foo_get(self, method, url, body, headers):
        body = self.fixtures.load('storage_foo.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_storage_not_found_get(self, method, url, body, headers):
        body = self.fixtures.load('storage_foo.json')
        return (httplib.NOT_FOUND, body, {}, httplib.responses[httplib.OK])

    def _json_1_0_token_get(self, method, url, body, headers):
        body = self.fixtures.load('token.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


class ContainerMockConnection(BaseRunAboveMockHttp, StorageMockHttp):
    fixtures = StorageFileFixtures('runabove')

    def _json_v1_AUTH_BAR_foo_delete(self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_not_found_delete(self, method, url, body, headers):
        return (httplib.NOT_FOUND, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_not_empty_delete(self, method, url, body, headers):
        return (httplib.CONFLICT, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_foo_foo_file_put(self, method, url, body, headers):
        return (httplib.CREATED, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_not_found_foo_file_put(self, method, url, body, headers):
        return (httplib.NOT_FOUND, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_foo_foo_file_delete(self, method, url, body, headers):
        return (httplib.NO_CONTENT, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_foo_not_found_delete(self, method, url, body, headers):
        return (httplib.NOT_FOUND, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_not_found_foo_file_delete(self, method, url, body, headers):
        return (httplib.NOT_FOUND, '', {}, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_foo_foo_file_head(self, method, url, body, headers):
        headers = {
            'content-length': '186',
            'accept-ranges': 'bytes',
            'last-modified': 'Sun, 20 Sep 2015 16:57:41 GMT',
            'connection': 'close',
            'etag': '6107a6bf44ce1427a9d25cb1c3af93ec',
            'x-timestamp': '1442768260.49150',
            'x-trans-id': '58B88003:DF53_A77230F0:01BB_560738A1_1B16A67:2421',
            'date': 'Sun, 27 Sep 2015 00:30:26 GMT',
            'content-type': 'application/octet-stream'
        }
        return (httplib.OK, '', headers, httplib.responses[httplib.OK])

    def _json_v1_AUTH_BAR_foo_not_found_head(self, method, url, body, headers):
        return (httplib.NOT_FOUND, '', {}, httplib.responses[httplib.OK])

    def success(self):
        return True


class RunAboveStorageTests(unittest.TestCase):
    def setUp(self):
        patch('libcloud.common.runabove.RunAboveConnection._timedelta', 42).start()
        RunAboveStorageDriver.connectionCls.conn_classes = (
            RunAboveStorageMockHttp, RunAboveStorageMockHttp)
        RunAboveStorageMockHttp.type = None
        RunAboveStorageDriver.containerConnectionCls.conn_classes = (
            ContainerMockConnection, ContainerMockConnection)
        self.driver = RunAboveStorageDriver(*RUNABOVE_PARAMS)

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 2)
        names = [c.name for c in containers]
        self.assertTrue('foo' in names)
        self.assertTrue('bar' in names)

    def test_list_container_objects(self):
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        objs = self.driver.list_container_objects(container)
        self.assertEqual(len(objs), 2)
        names = [o.name for o in objs]
        self.assertTrue('foo_file' in names)
        self.assertTrue('bar_file' in names)

    def test_list_container_objects_not_found(self):
        container = RunAboveContainer(name='not_found', extra={'region': 'BHS-1'}, driver=self.driver)
        try:
            self.driver.list_container_objects(container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_container(self):
        container = self.driver.get_container('foo', ex_location='BHS-1')
        self.assertEqual('foo', container.name)

    def test_get_container_not_found(self):
        try:
            self.driver.get_container('not_found', ex_location='BHS-1')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_object(self):
        obj = self.driver.get_object('foo', 'foo_file', ex_location='BHS-1')
        self.assertEqual('foo_file', obj.name)

    def test_get_object_not_found(self):
        try:
            self.driver.get_object('foo', 'not_found', ex_location='BHS-1')
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_object_but_container_not_found(self):
        try:
            self.driver.get_object('not_found', 'foo_file', ex_location='BHS-1')
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_container(self):
        container = self.driver.create_container('new_foo', ex_location='BHS-1')
        self.assertEqual('new_foo', container.name)

    def test_delete_container(self):
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        succeed = self.driver.delete_container(container)
        self.assertTrue(succeed)

    def test_delete_not_found_container(self):
        container = RunAboveContainer(name='not_found', extra={'region': 'BHS-1'}, driver=self.driver)
        try:
            self.driver.delete_container(container)
        except ContainerDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_not_empty_container(self):
        container = RunAboveContainer(name='not_empty', extra={'region': 'BHS-1'}, driver=self.driver)
        try:
            self.driver.delete_container(container)
        except ContainerIsNotEmptyError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_upload_object(self):
        test_file_path = '/tmp/foo'
        with open(test_file_path, 'w') as fd:
            fd.write('FOO')
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        self.driver.upload_object(test_file_path, container, 'foo_file')

    def test_upload_object_via_stream(self):
        test_file = StringIO('bar')
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        obj = self.driver.upload_object_via_stream(test_file, container, 'foo_file')
        self.assertEqual('foo_file', obj.name)

    # def test_download_object(self):
    #     container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
    #     obj = Object(name='foo_file', size=100, extra={'region': 'BHS-1'}, hash=None, meta_data={}, container=container, driver=self.driver)
    #     data = self.driver.download_object(obj, '/tmp/foo2')

    def test_delete_object(self):
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        obj = Object(name='foo_file', size=100, extra={'region': 'BHS-1'}, hash=None, meta_data={}, container=container, driver=self.driver)
        succeed = self.driver.delete_object(obj)
        self.assertTrue(succeed)

    def test_delete_object_not_found(self):
        container = RunAboveContainer(name='foo', extra={'region': 'BHS-1'}, driver=self.driver)
        obj = Object(name='not_found', size=100, extra={'region': 'BHS-1'}, hash=None, meta_data={}, container=container, driver=self.driver)
        try:
            self.driver.delete_object(obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_object_container_not_found(self):
        container = RunAboveContainer(name='not_found', extra={'region': 'BHS-1'}, driver=self.driver)
        obj = Object(name='foo_file', size=100, extra={'region': 'BHS-1'}, hash=None, meta_data={}, container=container, driver=self.driver)
        try:
            self.driver.delete_object(obj)
        except ObjectDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

if __name__ == '__main__':
    sys.exit(unittest.main())
