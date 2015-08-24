import unittest
import sys

from libcloud.compute.base import Node
from libcloud.compute.drivers.onapp import OnAppNodeDriver
from libcloud.test import MockHttpTestCase, LibcloudTestCase
from libcloud.test.secrets import ONAPP_PARAMS
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.utils.py3 import httplib


class OnAppNodeTestCase(LibcloudTestCase):
    driver_klass = OnAppNodeDriver

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = \
            (None, OnAppMockHttp)

        self.driver = OnAppNodeDriver(*ONAPP_PARAMS)

    def test_create_node(self):
        node = self.driver.create_node(
            name='onapp-new-fred',
            ex_memory=512,
            ex_cpus=4,
            ex_cpu_shares=4,
            ex_hostname='onapp-new-fred',
            ex_template_id='template_id',
            ex_primary_disk_size=100,
            ex_swap_disk_size=1,
            ex_required_virtual_machine_build=0,
            ex_required_ip_address_assignment=0
        )

        extra = node.extra

        self.assertEqual('onapp-new-fred', node.name)
        self.assertEqual('456789', node.id)
        self.assertEqual('456789', node.id)

        self.assertEqual('delivered', node.state)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('8.8.8.8', extra['local_remote_access_ip_address'])

        self.assertEqual(['192.168.15.73'], node.private_ips)
        self.assertEqual([], node.public_ips)

    def test_destroy_node(self):
        node = Node('identABC', 'testnode',
                    ['123.123.123.123'], [],
                    {'state': 'test', 'template_id': 88}, None)
        res = self.driver.destroy_node(node=node)
        self.assertTrue(res)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        extra = nodes[0].extra
        private_ips = nodes[0].private_ips

        self.assertEqual(1, len(nodes))
        self.assertEqual('onapp-fred', nodes[0].name)
        self.assertEqual('123456', nodes[0].id)

        self.assertEqual(True, extra['booted'])
        self.assertEqual('passwd', extra['initial_root_password'])
        self.assertEqual('9.9.9.9', extra['local_remote_access_ip_address'])

        self.assertEqual(1, len(private_ips))
        self.assertEqual('192.168.15.72', private_ips[0])


class OnAppMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('onapp')

    def _virtual_machines_json(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('list_nodes.json')
        else:
            body = self.fixtures.load('create_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_identABC_json(self, method, url, body, headers):
        return (
            httplib.NO_CONTENT,
            '',
            {},
            httplib.responses[httplib.NO_CONTENT]
        )


if __name__ == '__main__':
    sys.exit(unittest.main())
