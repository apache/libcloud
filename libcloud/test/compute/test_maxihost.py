import sys
import unittest
from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.maxihost import MaxihostNodeDriver
from libcloud.compute.base import Node, KeyPair
from libcloud.compute.types import NodeState

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class MaxihostTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        MaxihostNodeDriver.connectionCls.conn_class = MaxihostMockHttp
        self.driver = MaxihostNodeDriver('foo')


    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 1)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 3)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image.id, 'ubuntu_18_04_x64_lts')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.name, 'tester')

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(len(keys), 1)
        key = keys[0]
        self.assertEqual(key.name, 'test_key')
        self.assertEqual(key.fingerprint, '77:08:a7:a5:f9:8c:e1:ab:7b:c3:d8:0c:cd:ac:8b:dd')


class MaxihostMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('maxihost')

    def _plans(self, method, url, body, headers):
        body = self.fixtures.load('plans.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _regions(self, method, url, body, headers):
        body = self.fixtures.load('regions.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _plans_operating_systems(self, method, url, body, headers):
        body = self.fixtures.load('images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _devices(self, method, url, body, headers):
        body = self.fixtures.load('nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _devices_1319_actions(self, method, url, body, headers):
        body = self.fixtures.load('node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _account_keys(self, method, url, body, headers):
        body = self.fixtures.load('keys.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
