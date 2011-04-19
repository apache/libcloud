import httplib
import os.path
import sys
import unittest

from libcloud.resource.lb.base import LB, LBNode
from libcloud.resource.lb.drivers.gogrid import GoGridLBDriver

from test import MockHttp, MockRawResponse
from test.file_fixtures import ResourceFileFixtures

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
                nodes=(LBNode(None, '10.1.0.10', 80),
                    LBNode(None, '10.1.0.11', 80))
                )

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '123')

    def test_destroy_balancer(self):
        balancer = self.driver.list_balancers()[0]

        ret = self.driver.destroy_balancer(balancer)
        self.assertTrue(ret)

    def test_balancer_detail(self):
        balancer = self.driver.balancer_detail(balancer_id='23530')

        self.assertEquals(balancer.name, 'test2')
        self.assertEquals(balancer.id, '23530')

    def test_balancer_list_nodes(self):
        balancer = self.driver.balancer_detail(balancer_id='23530')
        nodes = balancer.list_nodes()

        expected_nodes = set([u'10.0.0.78:80', u'10.0.0.77:80',
            u'10.0.0.76:80'])

        self.assertEquals(len(nodes), 3)
        self.assertEquals(expected_nodes,
                set(["%s:%s" % (node.ip, node.port) for node in nodes]))

    def test_balancer_attach_node(self):
        balancer = LB(23530, None, None, None, None, None)
        node = self.driver.balancer_attach_node(balancer,
                ip='10.0.0.75', port='80')

        self.assertEquals(node.ip, '10.0.0.75')
        self.assertEquals(node.port, 80)

    def test_balancer_detach_node(self):
        balancer = LB(23530, None, None, None, None, None)
        node = self.driver.balancer_list_nodes(balancer)[0]

        ret = self.driver.balancer_detach_node(balancer, node)

        self.assertTrue(ret)

class GoGridLBMockHttp(MockHttp):
    fixtures = ResourceFileFixtures(os.path.join('lb', 'gogrid'))

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
