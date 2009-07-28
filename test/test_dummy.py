import unittest

from libcloud.providers import connect
from libcloud.types import Provider, Node

class DummyTests(unittest.TestCase):

    def setUp(self):
        self.conn = connect(Provider.DUMMY, 'foo')

    def test_list_nodes(self):
        ret = self.conn.list_nodes()

    def test_reboot_node(self):
        node = Node(None, None, None, None, None, attrs={})
        ret = self.conn.reboot_node(node)

    def test_create_node(self):
        node = Node(None, None, None, None, None, attrs={})
        ret = self.conn.create_node(node)
