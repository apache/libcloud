import httplib
import os.path
import sys
import unittest

from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.drivers.gogrid import GoGridLBDriver

from test import MockHttp, MockRawResponse
from test.file_fixtures import LoadBalancerFileFixtures

class GoGridTests(unittest.TestCase):

    def setUp(self):
        GoGridLBDriver.connectionCls.conn_classes = (None,
                GoGridLBMockHttp)
        GoGridLBMockHttp.type = None
        self.driver = GoGridLBDriver('user', 'key')

    def test_list_balancers(self):
        balancers = self.driver.list_balancers()

        self.assertEquals(len(balancers), 2)
        self.assertEquals(balancers[0].name, "foo")
        self.assertEquals(balancers[0].id, "23517")
        self.assertEquals(balancers[1].name, "bar")
        self.assertEquals(balancers[1].id, "23526")

    def test_create_balancer(self):
        balancer = self.driver.create_balancer(name='test2',
                port=80,
                algorithm=Algorithm.ROUND_ROBIN,
                members=(Member(None, '10.1.0.10', 80),
                         Member(None, '10.1.0.11', 80))
                )

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '123')

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]

        ret = self.driver.destroy_balancer(balancer)
        self.assertTrue(ret)

    def test_get_balancer(self):
        balancer = self.driver.get_balancer(balancer_id='23530')

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '23530')

    def test_balancer_list_members(self):
        balancer = self.driver.get_balancer(balancer_id='23530')
        members = balancer.list_members()

        expected_members = set([u'10.0.0.78:80', u'10.0.0.77:80',
            u'10.0.0.76:80'])

        self.assertEquals(len(members), 3)
        self.assertEquals(expected_members,
                set(["%s:%s" % (member.ip, member.port) for member in members]))

    def test_balancer_attach_member(self):
        balancer = LoadBalancer(23530, None, None, None, None, None)
        member = self.driver.balancer_attach_member(balancer,
                    Member(None, ip='10.0.0.75', port='80'))

        self.assertEquals(member.ip, '10.0.0.75')
        self.assertEquals(member.port, 80)

    def test_balancer_detach_member(self):
        balancer = LoadBalancer(23530, None, None, None, None, None)
        member = self.driver.balancer_list_members(balancer)[0]

        ret = self.driver.balancer_detach_member(balancer, member)

        self.assertTrue(ret)

class GoGridLBMockHttp(MockHttp):
    fixtures = LoadBalancerFileFixtures('gogrid')

    def _api_grid_loadbalancer_list(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_ip_list(self, method, url, body, headers):
        body = self.fixtures.load('ip_list.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_add(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_delete(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_add.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_get(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_get.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _api_grid_loadbalancer_edit(self, method, url, body, headers):
        body = self.fixtures.load('loadbalancer_edit.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
