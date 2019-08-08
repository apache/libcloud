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
import tempfile

import mock
import json

from libcloud.storage.drivers.backblaze_b2 import BackblazeB2StorageDriver
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b
from libcloud.utils.files import exhaust_iterator
from libcloud.test import unittest
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import StorageFileFixtures


class MockAuthConn(mock.Mock):
    account_id = 'abcdefgh'


class BackblazeB2StorageDriverTestCase(unittest.TestCase):
    driver_klass = BackblazeB2StorageDriver
    driver_args = ('a', 'b')

    def setUp(self):
        self.driver_klass.connectionCls.authCls.conn_class = BackblazeB2MockHttp
        self.driver_klass.connectionCls.conn_class = \
            BackblazeB2MockHttp

        BackblazeB2MockHttp.type = None
        self.driver = self.driver_klass(*self.driver_args)

    def test_list_containers(self):
        containers = self.driver.list_containers()
        self.assertEqual(len(containers), 3)
        self.assertEqual(containers[0].name, 'test00001')
        self.assertEqual(containers[0].extra['id'], '481c37de2e1ab3bf5e150710')
        self.assertEqual(containers[0].extra['bucketType'], 'allPrivate')

    def test_list_container_objects(self):
        container = self.driver.list_containers()[0]
        objects = self.driver.list_container_objects(container=container)
        self.assertEqual(len(objects), 4)
        self.assertEqual(objects[0].name, '2.txt')
        self.assertEqual(objects[0].size, 2)
        self.assertEqual(objects[0].extra['fileId'], 'abcd')
        self.assertEqual(objects[0].extra['uploadTimestamp'], 1450545966000)

    def test_get_container(self):
        container = self.driver.get_container('test00001')
        self.assertEqual(container.name, 'test00001')
        self.assertEqual(container.extra['id'], '481c37de2e1ab3bf5e150710')
        self.assertEqual(container.extra['bucketType'], 'allPrivate')

    def test_get_object(self):
        obj = self.driver.get_object('test00001', '2.txt')
        self.assertEqual(obj.name, '2.txt')
        self.assertEqual(obj.size, 2)
        self.assertEqual(obj.extra['fileId'], 'abcd')
        self.assertEqual(obj.extra['uploadTimestamp'], 1450545966000)

    def test_create_container(self):
        container = self.driver.create_container(container_name='test0005')
        self.assertEqual(container.name, 'test0005')
        self.assertEqual(container.extra['id'], '681c87aebeaa530f5e250710')
        self.assertEqual(container.extra['bucketType'], 'allPrivate')

    def test_delete_container(self):
        container = self.driver.list_containers()[0]
        result = self.driver.delete_container(container=container)
        self.assertTrue(result)

    def test_download_object(self):
        container = self.driver.list_containers()[0]
        obj = self.driver.list_container_objects(container=container)[0]
        _, destination_path = tempfile.mkstemp()
        result = self.driver.download_object(obj=obj, destination_path=destination_path,
                                             overwrite_existing=True)
        self.assertTrue(result)

    def test_download_object_as_stream(self):
        container = self.driver.list_containers()[0]
        obj = self.driver.list_container_objects(container=container)[0]

        stream = self.driver.download_object_as_stream(obj=obj, chunk_size=1024)
        self.assertTrue(hasattr(stream, '__iter__'))
        self.assertEqual(exhaust_iterator(stream), b('ab'))

    def test_upload_object(self):
        file_path = os.path.abspath(__file__)
        container = self.driver.list_containers()[0]
        obj = self.driver.upload_object(file_path=file_path, container=container,
                                        object_name='test0007.txt')
        self.assertEqual(obj.name, 'test0007.txt')
        self.assertEqual(obj.size, 24)
        self.assertEqual(obj.extra['fileId'], 'abcde')

    def test_upload_object_via_stream(self):
        container = self.driver.list_containers()[0]
        file_path = os.path.abspath(__file__)

        with open(file_path, 'rb') as fp:
            iterator = iter(fp)

            obj = self.driver.upload_object_via_stream(iterator=iterator,
                                                       container=container,
                                                       object_name='test0007.txt')

        self.assertEqual(obj.name, 'test0007.txt')
        self.assertEqual(obj.size, 24)
        self.assertEqual(obj.extra['fileId'], 'abcde')

    def test_delete_object(self):
        container = self.driver.list_containers()[0]
        obj = self.driver.list_container_objects(container=container)[0]
        result = self.driver.delete_object(obj=obj)
        self.assertTrue(result)

    def test_ex_hide_object(self):
        container = self.driver.list_containers()[0]
        container_id = container.extra['id']
        obj = self.driver.ex_hide_object(container_id=container_id,
                                         object_name='2.txt')
        self.assertEqual(obj.name, '2.txt')

    def test_ex_list_object_versions(self):
        container = self.driver.list_containers()[0]
        container_id = container.extra['id']
        objects = self.driver.ex_list_object_versions(container_id=container_id)
        self.assertEqual(len(objects), 9)

    def test_ex_get_upload_data(self):
        container = self.driver.list_containers()[0]
        container_id = container.extra['id']
        data = self.driver.ex_get_upload_data(container_id=container_id)
        self.assertEqual(data['authorizationToken'], 'nope')
        self.assertEqual(data['bucketId'], '481c37de2e1ab3bf5e150710')
        self.assertEqual(data['uploadUrl'], 'https://podxxx.backblaze.com/b2api/v1/b2_upload_file/abcd/defg')

    def test_ex_get_upload_url(self):
        container = self.driver.list_containers()[0]
        container_id = container.extra['id']
        url = self.driver.ex_get_upload_url(container_id=container_id)
        self.assertEqual(url, 'https://podxxx.backblaze.com/b2api/v1/b2_upload_file/abcd/defg')


class BackblazeB2MockHttp(MockHttp):
    fixtures = StorageFileFixtures('backblaze_b2')

    def _b2api_v1_b2_authorize_account(self, method, url, body, headers):
        if method == 'GET':
            body = json.dumps({
                'accountId': 'test',
                'apiUrl': 'https://apiNNN.backblazeb2.com',
                'downloadUrl': 'https://f002.backblazeb2.com',
                'authorizationToken': 'test'
            })
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_list_buckets(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('b2_list_buckets.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_list_file_names(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('b2_list_file_names.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_create_bucket(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('b2_create_bucket.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_delete_bucket(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('b2_delete_bucket.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_delete_file_version(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('b2_delete_file_version.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_get_upload_url(self, method, url, body, headers):
        # test_upload_object
        if method == 'GET':
            body = self.fixtures.load('b2_get_upload_url.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_upload_file_abcd_defg(self, method, url, body, headers):
        # test_upload_object
        if method == 'POST':
            body = self.fixtures.load('b2_upload_file.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_list_file_versions(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('b2_list_file_versions.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _b2api_v1_b2_hide_file(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('b2_hide_file.json')
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _file_test00001_2_txt(self, method, url, body, headers):
        # test_download_object
        if method == 'GET':
            body = 'ab'
        else:
            raise AssertionError('Unsupported method')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
