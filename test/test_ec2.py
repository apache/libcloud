import unittest

from libcloud.providers import connect
from libcloud.types import Provider, Node

from secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase):

    def setUp(self):
        self.conn = connect(Provider.EC2, EC2_ACCESS_ID, EC2_SECRET)

    def test_list_nodes(self):
        ret = self.conn.list_nodes()

    def test_reboot_nodes(self):
        node = Node(None, None, None, None, None, 
                    attrs={'instanceId':'i-e1615d88'})
        ret = self.conn.reboot_node(node)
