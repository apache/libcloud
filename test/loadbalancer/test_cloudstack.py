import sys
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse

try:
    parse_qsl = urlparse.parse_qsl
except AttributeError:
    import cgi
    parse_qsl = cgi.parse_qsl

from libcloud.common.types import LibcloudError
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.cloudstack import CloudStackLBDriver

from test import MockHttpTestCase
from test.file_fixtures import LoadBalancerFileFixtures

class CloudStackLBTests(unittest.TestCase):
    def setUp(self):
        CloudStackLBDriver.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)
        self.driver = CloudStackLBDriver('apikey', 'secret')
        self.driver.path = '/test/path'
        self.driver.type = -1
        self.driver.name = 'CloudStack'
        CloudStackMockHttp.fixture_tag = 'default'
        self.driver.connection.poll_interval = 0.0

    def test_list_supported_algorithms(self):
        algorithms = self.driver.list_supported_algorithms()

        self.assertTrue(Algorithm.ROUND_ROBIN in algorithms)
        self.assertTrue(Algorithm.LEAST_CONNECTIONS in algorithms)

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()
        for balancer in balancers:
            self.assertTrue(isinstance(balancer, LoadBalancer))

    def test_create_balancer(self):
        members = [Member(1, '1.1.1.1', 80), Member(2, '1.1.1.2', 80)]
        balancer = self.driver.create_balancer('fake', members)
        self.assertTrue(isinstance(balancer, LoadBalancer))

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]
        self.driver.destroy_balancer(balancer)

    def test_balancer_attach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = Member(id=1234, ip='1.1.1.1', port=80)
        balancer.attach_member(member)

    def test_balancer_detach_member(self):
        balancer = self.driver.list_balancers()[0]
        member = balancer.list_members()[0]
        balancer.detach_member(member)

    def test_balancer_list_members(self):
        balancer = self.driver.list_balancers()[0]
        members = balancer.list_members()
        for member in members:
            self.assertTrue(isinstance(member, Member))

class CloudStackMockHttp(MockHttpTestCase):
    fixtures = LoadBalancerFileFixtures('cloudstack')
    fixture_tag = 'default'

    def _load_fixture(self, fixture):
        body = self.fixtures.load(fixture)
        return body, json.loads(body)

    def _test_path(self, method, url, body, headers):
        url = urlparse.urlparse(url)
        query = dict(parse_qsl(url.query))

        self.assertTrue('apiKey' in query)
        self.assertTrue('command' in query)
        self.assertTrue('response' in query)
        self.assertTrue('signature' in query)

        self.assertTrue(query['response'] == 'json')

        del query['apiKey']
        del query['response']
        del query['signature']
        command = query.pop('command')

        if hasattr(self, '_cmd_' + command):
            return getattr(self, '_cmd_' + command)(**query)
        else:
            fixture = command + '_' + self.fixture_tag + '.json'
            body, obj = self._load_fixture(fixture)
            return (httplib.OK, body, obj, httplib.responses[httplib.OK])

    def _cmd_queryAsyncJobResult(self, jobid):
        fixture = 'queryAsyncJobResult' + '_' + str(jobid) + '.json'
        body, obj = self._load_fixture(fixture)
        return (httplib.OK, body, obj, httplib.responses[httplib.OK])

if __name__ == "__main__":
    sys.exit(unittest.main())
