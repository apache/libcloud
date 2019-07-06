import unittest
import sys

from integration.driver.test import TestNodeDriver

from integration.api.data import NODES, REPORT_DATA


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.instance = TestNodeDriver('apache', 'libcloud', secure=False,
                                       host='localhost', port=9898)

    def test_nodes(self):
        """
        Test that you can list nodes and that the responding objects
        match basic values, list (ip), and dict (extra).
        """
        nodes = self.instance.list_nodes()
        for node in NODES:
            match = [n for n in nodes if n.id == node['id']]
            self.assertTrue(len(match) == 1)
            match = match[0]
            self.assertEqual(match.id, node['id'])
            self.assertEqual(match.name, node['name'])
            self.assertEqual(match.private_ips, node['private_ips'])
            self.assertEqual(match.public_ips, node['public_ips'])
            self.assertEqual(match.extra, node['extra'])

    def test_ex_report_data(self):
        """
        Test that a raw request can correctly return the data
        """
        data = self.instance.ex_report_data()
        self.assertEqual(data, REPORT_DATA)


if __name__ == '__main__':
    import libcloud
    with open('/tmp/testing.log', 'w') as f:
        libcloud.enable_debug(f)
        sys.exit(unittest.main())
