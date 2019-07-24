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
import json

from mock import Mock, call

from libcloud.common.upcloud import UpcloudCreateNodeRequestBody, UpcloudNodeDestroyer, UpcloudNodeOperations
from libcloud.common.upcloud import _StorageDevice
from libcloud.common.upcloud import UpcloudTimeoutException
from libcloud.common.upcloud import PlanPrice
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, NodeAuthSSHKey
from libcloud.test import unittest


class TestUpcloudCreateNodeRequestBody(unittest.TestCase):

    def setUp(self):
        self.image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                               name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                               driver='',
                               extra={'type': 'template'})
        self.location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver='')
        self.size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                             extra={'core_number': 1, 'storage_tier': 'maxiops'}, price=None, driver='')

    def test_creating_node_from_template_image(self):
        body = UpcloudCreateNodeRequestBody(name='ts', image=self.image, location=self.location, size=self.size)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {'username': 'root',
                               'create_password': 'yes'},
                'storage_devices': {
                    'storage_device': [{
                        'action': 'clone',
                        'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        'storage': '01000000-0000-4000-8000-000030060200',
                        'size': 30,
                        'tier': 'maxiops',
                    }]
                },
            }
        }
        self.assertDictEqual(expected_body, dict_body)

    def test_creating_node_from_cdrom_image(self):
        image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                          name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                          driver='',
                          extra={'type': 'cdrom'})
        body = UpcloudCreateNodeRequestBody(name='ts', image=image, location=self.location, size=self.size)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {'username': 'root',
                               'create_password': 'yes'},
                'storage_devices': {
                    'storage_device': [
                        {
                            'action': 'create',
                            'size': 30,
                            'tier': 'maxiops',
                            'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        },
                        {
                            'action': 'attach',
                            'storage': '01000000-0000-4000-8000-000030060200',
                            'type': 'cdrom'
                        }
                    ]
                }
            }
        }
        self.assertDictEqual(expected_body, dict_body)

    def test_creating_node_using_ssh_keys(self):
        auth = NodeAuthSSHKey('sshkey')

        body = UpcloudCreateNodeRequestBody(name='ts', image=self.image, location=self.location, size=self.size, auth=auth)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {
                    'username': 'root',
                    'ssh_keys': {
                        'ssh_key': [
                            'sshkey'
                        ]
                    },
                },
                'storage_devices': {
                    'storage_device': [{
                        'action': 'clone',
                        'size': 30,
                        'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        'tier': 'maxiops',
                        'storage': '01000000-0000-4000-8000-000030060200'
                    }]
                },
            }
        }
        self.assertDictEqual(expected_body, dict_body)

    def test_creating_node_using_hostname(self):
        body = UpcloudCreateNodeRequestBody(name='ts', image=self.image, location=self.location, size=self.size,
                                            ex_hostname='myhost.upcloud.com')
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'myhost.upcloud.com',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {'username': 'root',
                               'create_password': 'yes'},
                'storage_devices': {
                    'storage_device': [{
                        'action': 'clone',
                        'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        'storage': '01000000-0000-4000-8000-000030060200',
                        'tier': 'maxiops',
                        'size': 30
                    }]
                },
            }
        }
        self.assertDictEqual(expected_body, dict_body)

    def test_creating_node_with_non_default_username(self):
        body = UpcloudCreateNodeRequestBody(name='ts', image=self.image, location=self.location, size=self.size,
                                            ex_username='someone')
        json_body = body.to_json()
        dict_body = json.loads(json_body)

        login_user = dict_body['server']['login_user']
        self.assertDictEqual({'username': 'someone', 'create_password': 'yes'}, login_user)


class TestStorageDevice(unittest.TestCase):

    def setUp(self):
        self.image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                               name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                               driver='',
                               extra={'type': 'template'})
        self.size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                             extra={'core_number': 1}, price=None, driver='')

    def test_storage_tier_default_value(self):
        storagedevice = _StorageDevice(self.image, self.size)
        d = storagedevice.to_dict()

        self.assertEqual(d['storage_device'][0]['tier'], 'maxiops')

    def test_storage_tier_given(self):
        self.size.extra['storage_tier'] = 'hdd'
        storagedevice = _StorageDevice(self.image, self.size)
        d = storagedevice.to_dict()

        self.assertEqual(d['storage_device'][0]['tier'], 'hdd')


class TestUpcloudNodeDestroyer(unittest.TestCase):

    def setUp(self):
        self.mock_sleep = Mock()
        self.mock_operations = Mock(spec=UpcloudNodeOperations)
        self.destroyer = UpcloudNodeDestroyer(self.mock_operations, sleep_func=self.mock_sleep)

    def test_node_already_in_stopped_state(self):
        self.mock_operations.get_node_state.side_effect = ['stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_node_in_error_state(self):
        self.mock_operations.get_node_state.side_effect = ['error']

        self.assertFalse(self.destroyer.destroy_node(1))

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.assertTrue(self.mock_operations.destroy_node.call_count == 0)

    def test_node_in_started_state(self):
        self.mock_operations.get_node_state.side_effect = ['started', 'stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        self.mock_operations.stop_node.assert_called_once_with(1)
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_node_in_maintenace_state(self):
        self.mock_operations.get_node_state.side_effect = ['maintenance', 'maintenance', None]

        self.assertTrue(self.destroyer.destroy_node(1))

        self.mock_sleep.assert_has_calls([call(self.destroyer.WAIT_AMOUNT), call(self.destroyer.WAIT_AMOUNT)])

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.assertTrue(self.mock_operations.destroy_node.call_count == 0)

    def test_node_statys_in_started_state_for_awhile(self):
        self.mock_operations.get_node_state.side_effect = ['started', 'started', 'stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        # Only one all for stop should be done
        self.mock_operations.stop_node.assert_called_once_with(1)
        self.mock_sleep.assert_has_calls([call(self.destroyer.WAIT_AMOUNT)])
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_reuse(self):
        """Verify that internal flag self.destroyer._stop_node is handled properly"""
        self.mock_operations.get_node_state.side_effect = ['started', 'stopped', 'started', 'stopped']
        self.assertTrue(self.destroyer.destroy_node(1))
        self.assertTrue(self.destroyer.destroy_node(1))

        self.assertEqual(self.mock_sleep.call_count, 0)
        self.assertEqual(self.mock_operations.stop_node.call_count, 2)

    def test_timeout(self):
        self.mock_operations.get_node_state.side_effect = ['maintenance'] * 50

        self.assertRaises(UpcloudTimeoutException, self.destroyer.destroy_node, 1)

    def test_timeout_reuse(self):
        """Verify sleep count is handled properly"""
        self.mock_operations.get_node_state.side_effect = ['maintenance'] * 50
        self.assertRaises(UpcloudTimeoutException, self.destroyer.destroy_node, 1)

        self.mock_operations.get_node_state.side_effect = ['maintenance', None]
        self.assertTrue(self.destroyer.destroy_node(1))


class TestPlanPrice(unittest.TestCase):

    def setUp(self):
        prices = [{'name': 'uk-lon1', 'server_plan_1xCPU-1GB': {'amount': 1, 'price': 1.488}},
                  {'name': 'fi-hel1', 'server_plan_1xCPU-1GB': {'amount': 1, 'price': 1.588}}]
        self.pp = PlanPrice(prices)

    def test_zone_prices(self):
        location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver=None)
        self.assertEqual(self.pp.get_price('1xCPU-1GB', location), 1.588)

    def test_plan_not_found_in_zone(self):
        location = NodeLocation(id='no_such_location', name='', country='', driver=None)
        self.assertIsNone(self.pp.get_price('1xCPU-1GB', location))

    def test_no_location_given(self):
        self.assertIsNone(self.pp.get_price('1xCPU-1GB'))


if __name__ == '__main__':
    sys.exit(unittest.main())
