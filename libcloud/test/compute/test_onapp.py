import unittest
import sys
import json

from mock import call, MagicMock

from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.drivers.onapp import OnAppNodeDriver, OnAppNode, OnAppIpAddress
from libcloud.test import LibcloudTestCase
from libcloud.test.secrets import ONAPP_PARAMS


class OnAppNodeTestCase(LibcloudTestCase):
    def setUp(self):
        def _request(*args, **kwargs):
            fixtures = ComputeFileFixtures('onapp')
            response = MagicMock()
            method = kwargs.get('method', "GET")

            if method is 'GET' and args[0] == '/virtual_machines.json':
                response.object = json.loads(fixtures.load(
                    'list_nodes.json'))
            if method is 'POST' and args[0] == '/virtual_machines.json':
                response.object = json.loads(fixtures.load('create_node.json'))
            if method is 'DELETE' and args[0] == '/virtual_machines.json':
                response.status = 204

            return response

        self.connection_mock = MagicMock()
        self.connection_mock.return_value.request.side_effect = _request
        OnAppNodeDriver.connectionCls = self.connection_mock
        self.driver = OnAppNodeDriver(*ONAPP_PARAMS)

    def test_create_node(self):
        node = self.driver.create_node(
            label='onapp-new-fred',
            memory=512,
            cpus=4,
            cpu_shares=4,
            hostname='onapp-new-fred',
            template_id='template_id',
            primary_disk_size=100,
            swap_disk_size=1,
            required_virtual_machine_build=0,
            required_ip_address_assignment=0
        )

        req_mock = self.connection_mock.return_value.request
        self.assertEqual('/virtual_machines.json', req_mock.call_args[0][0])
        self.assertEqual({'Content-type': 'application/json'},
                         req_mock.call_args[1]['headers'])
        self.assertEqual(json.loads(
            '{"virtual_machine": {'
            '"swap_disk_size": 1, "required_ip_address_assignment": 0, '
            '"hostname": "onapp-new-fred", "cpus": 4, "label": '
            '"onapp-new-fred", "primary_disk_size": 100, "memory": 512, '
            '"required_virtual_machine_build": 0, "template_id": '
            '"template_id", "cpu_shares": 4, "rate_limit": null}}'),
            json.loads(req_mock.call_args[1]['data']))
        self.assertEqual('POST', req_mock.call_args[1]['method'])

        extra = node.extra
        addresses = node.ip_addresses

        self.assertEqual('onapp-new-fred', node.label)
        self.assertEqual('onapp-new-fred', node.name)
        self.assertEqual('456789', node.identifier)
        self.assertEqual('456789', node.id)

        self.assertEqual('delivered', node.state)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('8.8.8.8', extra['local_remote_access_ip_address'])

        self.assertEqual(1, len(addresses))
        self.assertEqual('192.168.15.73', addresses[0].address)
        self.assertEqual('192.168.15.255', addresses[0].broadcast)
        self.assertEqual('255.255.255.0', addresses[0].netmask)

        self.assertEqual(['192.168.15.73'], node.private_ips)
        self.assertEqual([], node.public_ips)

    def test_destroy_node(self):
        node = OnAppNode('identABC', 'testnode',
                         [OnAppIpAddress('123.123.123.123')],
                         {'state': 'test', 'template_id': 88}, None)
        self.driver.destroy_node(node=node)
        self.assertEqual(call(
            '/virtual_machines/identABC.json',
            params={'destroy_all_backups': 0, 'convert_last_backup': 0},
            method='DELETE'),
                         self.connection_mock.return_value.request.call_args)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        extra = nodes[0].extra
        addresses = nodes[0].ip_addresses

        self.assertEqual(1, len(nodes))
        self.assertEqual('onapp-fred', nodes[0].label)
        self.assertEqual('123456', nodes[0].identifier)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('9.9.9.9', extra['local_remote_access_ip_address'])

        self.assertEqual(1, len(addresses))
        self.assertEqual('192.168.15.72', addresses[0].address)
        self.assertEqual('192.168.15.255', addresses[0].broadcast)
        self.assertEqual('255.255.255.0', addresses[0].netmask)

        self.assertEqual(call('/virtual_machines.json'),
                         self.connection_mock.return_value.request.call_args)


if __name__ == '__main__':
    sys.exit(unittest.main())
