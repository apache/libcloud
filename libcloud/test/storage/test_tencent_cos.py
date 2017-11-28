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

import copy
import json
import mock
import re
import sys
import unittest

from io import BytesIO

import email.utils
import pytest

from libcloud.common.types import InvalidCredsError
from libcloud.storage.base import Container, Object
from libcloud.storage.drivers import tencent_cos
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ObjectDoesNotExistError


def _qcloud_access_url(path):
    return 'http://foobar.file.myqcloud.com/{}'.format(path)


def _qcloud_source_url(path):
    return 'http://foobar.cosgz.myqcloud.com/{}'.format(path)


_MOCK_CONTAINERS = [
    {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'request-id-1==',
        'data': {
            'context': 'public_read_1',
            'infos': [
                {
                    'authority': 'eWRPrivate',
                    'biz_attr': '',
                    'ctime': 1504236956,
                    'mtime': 1504236956,
                    'name': 'private_1/',
                },
                {
                    'authority': 'eWPrivateRPublic',
                    'biz_attr': '',
                    'ctime': 1482718269,
                    'mtime': 1482718269,
                    'name': 'public_read_1/',
                },
            ],
            'listover': False,
        },
    },
    {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'request-id-2==',
        'data': {
            'context': '',
            'infos': [
                {
                    'authority': 'eWRPrivate',
                    'biz_attr': '',
                    'ctime': 1503648523,
                    'mtime': 1503648523,
                    'name': 'private_2/',
                },
                {
                    'authority': 'eWPrivateRPublic',
                    'biz_attr': '',
                    'ctime': 1484183162,
                    'mtime': 1484183162,
                    'name': 'public_read_2/'
                },
            ],
            'listover': True,
        },
    },
]
_MOCK_OBJECTS = [
    {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'request-id-1==',
        'data': {
            'context': 'deep/tree/object/1',
            'infos': [
                {
                    'access_url': _qcloud_access_url('top-level-1'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511428772,
                    'filelen': 4328,
                    'filesize': 4328,
                    'mtime': 1511428772,
                    'name': 'top-level-1',
                    'sha': 'ec318800b567dde4f6cdd82aecd5b8385eef1f79',
                    'source_url': _qcloud_source_url('top-level-1'),
                },
                {
                    'access_url': _qcloud_access_url('top-level-2'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511428743,
                    'filelen': 282585,
                    'filesize': 282585,
                    'mtime': 1511428743,
                    'name': 'top-level-2',
                    'sha': 'afb21075914256cddfc9459535d679ae0a6c5731',
                    'source_url': _qcloud_source_url('top-level-2'),
                },
                {
                    'access_url': _qcloud_access_url('deep/tree/object/1'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511438556,
                    'filelen': 464364,
                    'filesize': 464364,
                    'mtime': 1511438556,
                    'name': 'deep/tree/object/1',
                    'sha': '7fa357010b6581b8f4cb0e06948fae352e1e8458',
                    'source_url': _qcloud_source_url('deep/tree/object/1'),
                },
            ],
            'listover': False,
        },
    },
    {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'request-id-2==',
        'data': {
            'context': '',
            'infos': [
                {
                    'access_url': _qcloud_access_url('deep/tree/object/2'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511428772,
                    'filelen': 4328,
                    'filesize': 4328,
                    'mtime': 1511428772,
                    'name': 'deep/tree/object/2',
                    'sha': 'ec318800b567dde4f6cdd82aecd5b8385eef1f79',
                    'source_url': _qcloud_source_url('deep/tree/object/2'),
                },
                {
                    'access_url': _qcloud_access_url('deep/tree/object/a'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511428743,
                    'filelen': 282585,
                    'filesize': 282585,
                    'mtime': 1511428743,
                    'name': 'deep/tree/object/a',
                    'sha': 'afb21075914256cddfc9459535d679ae0a6c5731',
                    'source_url': _qcloud_source_url('deep/tree/object/a'),
                },
                {
                    'access_url': _qcloud_access_url('deep/tree/object/b'),
                    'authority': 'eInvalid',
                    'biz_attr': '',
                    'ctime': 1511438556,
                    'filelen': 464364,
                    'filesize': 464364,
                    'mtime': 1511438556,
                    'name': 'deep/tree/object/b',
                    'sha': '7fa357010b6581b8f4cb0e06948fae352e1e8458',
                    'source_url': _qcloud_source_url('deep/tree/object/b'),
                },
            ],
            'listover': True,
        },
    },
]
_MOCK_STAT = {
    '/public_read_1/': {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'NWExZDJiYThfNTIyNWI2NF9hMDBlXzUzMmY5Nw==',
        'data': {
            'CORSConfiguration': {'CORSRule': [], 'NeedCORS': False},
            'authority': 'eWPrivateRPublic',
            'biz_attr': '',
            'blackrefers': [],
            'brower_exec': '0',
            'cnames': [],
            'ctime': 1504236956,
            'forbid': 0,
            'mtime': 1504236956,
            'refers': [],
        },
    },
    '/public_read_1/deep/tree/object/1': {
        'code': 0,
        'message': 'SUCCESS',
        'request_id': 'NWExZDJiYWFfNTIyNWI2NF9hMDA5XzUzOTFiMA==',
        'data': {
            'access_url': _qcloud_access_url('deep/tree/object/1'),
            'authority': 'eInvalid',
            'biz_attr': '',
            'ctime': 1511438556,
            'custom_headers': {},
            'filelen': 464364,
            'filesize': 464364,
            'forbid': 0,
            'mtime': 1511438556,
            'name': 'deep/tree/object/1',
            'sha': '7fa357010b6581b8f4cb0e06948fae352e1e8458',
            'slicesize': 464364,
            'source_url': _qcloud_source_url('deep/tree/object/1'),
        },
    },
}


class MockCosClient(object):

    def list_folder(self, req):
        cos_path = req.get_cos_path()
        bucket_name = req.get_bucket_name()
        context = req.get_context()
        if bucket_name == '':
            if context == '':
                return _MOCK_CONTAINERS[0]
            elif context == _MOCK_CONTAINERS[0]['data']['context']:
                return _MOCK_CONTAINERS[1]
            else:
                raise ValueError(
                    'Bad context for list containers: %s' % (context))
        elif bucket_name == 'public_read_1':
            if context == '':
                return _MOCK_OBJECTS[0]
            elif context == _MOCK_OBJECTS[0]['data']['context']:
                return _MOCK_OBJECTS[1]
            else:
                raise ValueError(
                    'Bad context for list container objects: %s' % (context))

    def stat_folder(self, req):
        return _MOCK_STAT['/{}/'.format(req.get_bucket_name())]

    def stat_file(self, req):
        return _MOCK_STAT['/{}{}'.format(
            req.get_bucket_name(), req.get_cos_path())]


class TencentStorageTests(unittest.TestCase):

    def _get_driver(self):
        return tencent_cos.TencentCosDriver(
            'api-key-id', 'api-secret-key', region='gz', app_id=1111111)

    @mock.patch('libcloud.storage.drivers.tencent_cos'
                '.TencentCosDriver._get_client')
    def test_create_driver(self, mock_get_client):
        mock_get_client.return_value = MockCosClient()
        driver = self._get_driver()
        mock_get_client.assert_called_with(
            1111111, 'api-key-id', 'api-secret-key', 'gz')

    @mock.patch('libcloud.storage.drivers.tencent_cos'
                '.TencentCosDriver._get_client')
    def test_list_containers(self, mock_get_client):
        mock_get_client.return_value = MockCosClient()
        driver = self._get_driver()
        containers = driver.list_containers()
        self.assertEqual(4, len(containers))
        self.assertTrue(
            all(isinstance(container, Container) for container in containers))
        self.assertSetEqual(
            set(('private_1', 'public_read_1', 'private_2', 'public_read_2')),
            set(container.name for container in containers))

    @mock.patch('libcloud.storage.drivers.tencent_cos'
                '.TencentCosDriver._get_client')
    def test_get_and_list_container_objects(self, mock_get_client):
        mock_get_client.return_value = MockCosClient()
        driver = self._get_driver()
        container = driver.get_container('public_read_1')
        self.assertIsInstance(container, Container)
        self.assertEqual('public_read_1', container.name)
        objects = container.list_objects()
        self.assertEqual(6, len(objects))
        self.assertTrue(
            all(isinstance(obj, Object) for obj in objects))
        self.assertSetEqual(
            set(('top-level-1', 'top-level-2',
                 'deep/tree/object/1', 'deep/tree/object/2',
                 'deep/tree/object/a', 'deep/tree/object/b')),
            set(obj.name for obj in objects))

    @mock.patch('libcloud.storage.drivers.tencent_cos'
                '.TencentCosDriver._get_client')
    def test_get_object_and_cdn_url(self, mock_get_client):
        mock_get_client.return_value = MockCosClient()
        driver = self._get_driver()
        obj = driver.get_object('public_read_1', 'deep/tree/object/1')
        exp_extra = {
            'creation_date': 1511438556,
            'modified_data': 1511438556,
            'access_url': 'http://foobar.file.myqcloud.com/deep/tree/object/1',
            'source_url': 'http://foobar.cosgz.myqcloud.com/deep/tree/object/1',
        }
        self.assertIsInstance(obj, Object)
        self.assertEqual('deep/tree/object/1', obj.name)
        self.assertEqual(464364, obj.size)
        self.assertEqual('7fa357010b6581b8f4cb0e06948fae352e1e8458', obj.hash)
        self.assertDictEqual(exp_extra, obj.extra)
        self.assertEqual('http://foobar.file.myqcloud.com/deep/tree/object/1',
                         obj.get_cdn_url())


if __name__ == '__main__':
    sys.exit(unittest.main())
