import unittest
import sys

from .driver.test import TestNodeDriver

from .api.data import NODES

class IntegrationTest(unittest.TestCase):
    def setUp(self):        
        self.instance = TestNodeDriver('apache', 'libcloud', secure=False,
                                       host='localhost', port=9898)

    def test_nodes(self):
        nodes = self.instance.list_nodes()

if __name__ == '__main__':
    sys.exit(unittest.main())
