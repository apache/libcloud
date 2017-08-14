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
from libcloud.common.upcloud import UpcloudTimeoutException
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation, NodeAuthSSHKey
from libcloud.test import unittest


class TestUpcloudCreateNodeRequestBody(unittest.TestCase):

    def test_creating_node_from_template_image(self):
        image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                          name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                          driver='',
                          extra={'type': 'template'})
        location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver='')
        size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                        extra={'core_number': 1, 'storage_tier': 'maxiops'}, price=None, driver='')

        body = UpcloudCreateNodeRequestBody(user_id='somename', name='ts', image=image, location=location, size=size)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {'username': 'somename',
                               'create_password': 'yes'},
                'storage_devices': {
                    'storage_device': [{
                        'action': 'clone',
                        'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        'storage': '01000000-0000-4000-8000-000030060200'
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
        location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver='')
        size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                        extra={'core_number': 1, 'storage_tier': 'maxiops'}, price=None, driver='')

        body = UpcloudCreateNodeRequestBody(user_id='somename', name='ts', image=image, location=location, size=size)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {'username': 'somename',
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
        image = NodeImage(id='01000000-0000-4000-8000-000030060200',
                          name='Ubuntu Server 16.04 LTS (Xenial Xerus)',
                          driver='',
                          extra={'type': 'template'})
        location = NodeLocation(id='fi-hel1', name='Helsinki #1', country='FI', driver='')
        size = NodeSize(id='1xCPU-1GB', name='1xCPU-1GB', ram=1024, disk=30, bandwidth=2048,
                        extra={'core_number': 1, 'storage_tier': 'maxiops'}, price=None, driver='')
        auth = NodeAuthSSHKey('sshkey')

        body = UpcloudCreateNodeRequestBody(user_id='somename', name='ts', image=image, location=location, size=size, auth=auth)
        json_body = body.to_json()
        dict_body = json.loads(json_body)
        expected_body = {
            'server': {
                'title': 'ts',
                'hostname': 'localhost',
                'plan': '1xCPU-1GB',
                'zone': 'fi-hel1',
                'login_user': {
                    'username': 'somename',
                    'ssh_keys': {
                        'ssh_key': [
                            'sshkey'
                        ]
                    },
                },
                'storage_devices': {
                    'storage_device': [{
                        'action': 'clone',
                        'title': 'Ubuntu Server 16.04 LTS (Xenial Xerus)',
                        'storage': '01000000-0000-4000-8000-000030060200'
                    }]
                },
            }
        }
        self.assertDictEqual(expected_body, dict_body)


class TestUpcloudNodeDestroyer(unittest.TestCase):

    def setUp(self):
        self.mock_sleep = Mock()
        self.mock_operations = Mock(spec=UpcloudNodeOperations)
        self.destroyer = UpcloudNodeDestroyer(self.mock_operations, sleep_func=self.mock_sleep)

    def test_node_already_in_stopped_state(self):
        self.mock_operations.node_state.side_effect = ['stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_node_in_error_state(self):
        self.mock_operations.node_state.side_effect = ['error']

        self.assertFalse(self.destroyer.destroy_node(1))

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.assertTrue(self.mock_operations.destroy_node.call_count == 0)

    def test_node_in_started_state(self):
        self.mock_operations.node_state.side_effect = ['started', 'stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        self.mock_operations.stop_node.assert_called_once_with(1)
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_node_in_maintenace_state(self):
        self.mock_operations.node_state.side_effect = ['maintenance', 'maintenance', None]

        self.assertTrue(self.destroyer.destroy_node(1))

        self.mock_sleep.assert_has_calls([call(self.destroyer.WAIT_AMOUNT), call(self.destroyer.WAIT_AMOUNT)])

        self.assertTrue(self.mock_operations.stop_node.call_count == 0)
        self.assertTrue(self.mock_operations.destroy_node.call_count == 0)

    def test_node_statys_in_started_state_for_awhile(self):
        self.mock_operations.node_state.side_effect = ['started', 'started', 'stopped']

        self.assertTrue(self.destroyer.destroy_node(1))

        # Only one all for stop should be done
        self.mock_operations.stop_node.assert_called_once_with(1)
        self.mock_sleep.assert_has_calls([call(self.destroyer.WAIT_AMOUNT)])
        self.mock_operations.destroy_node.assert_called_once_with(1)

    def test_reuse(self):
        "Verify that internal flag self.destroyer._stop_node is handled properly"
        self.mock_operations.node_state.side_effect = ['started', 'stopped', 'started', 'stopped']
        self.assertTrue(self.destroyer.destroy_node(1))
        self.assertTrue(self.destroyer.destroy_node(1))

        self.assertEquals(self.mock_sleep.call_count, 0)
        self.assertEquals(self.mock_operations.stop_node.call_count, 2)

    def test_timeout(self):
        self.mock_operations.node_state.side_effect = ['maintenance'] * 50

        self.assertRaises(UpcloudTimeoutException, self.destroyer.destroy_node, 1)

    def test_timeout_reuse(self):
        "Verify sleep count is handled properly"
        self.mock_operations.node_state.side_effect = ['maintenance'] * 50
        self.assertRaises(UpcloudTimeoutException, self.destroyer.destroy_node, 1)

        self.mock_operations.node_state.side_effect = ['maintenance', None]
        self.assertTrue(self.destroyer.destroy_node(1))


if __name__ == '__main__':
    sys.exit(unittest.main())
