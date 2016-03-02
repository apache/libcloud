import sys
import unittest

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_NSONE
from libcloud.dns.drivers.nsone import NsOneDNSDriver
from libcloud.utils.py3 import httplib


class NsOneTests(unittest.TestCase):
    def setUp(self):
        NsOneMockHttp.type = None
        NsOneDNSDriver.connectionCls.conn_classes = (None, NsOneMockHttp)
        self.driver = NsOneDNSDriver(*DNS_PARAMS_NSONE)

    def test_list_zones_empty(self):
        NsOneMockHttp.type = 'EMPTY_ZONES_LIST'
        zones = self.driver.list_zones()

        self.assertEqual(zones, [])


class NsOneMockHttp(MockHttp):
    fixtures = DNSFileFixtures('nsone')

    def _v1_zones_EMPTY_ZONES_LIST(self, method, url, body, headers):
        body = self.fixtures.load('empty_zones_list.json')

        return httplib.OK, body, {}, httplib.responses[httplib.OK]


if __name__ == '__main__':
    sys.exit(unittest.main())
