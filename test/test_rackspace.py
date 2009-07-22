import unittest

from libcloud.drivers.rackspace import RackspaceProvider
from libcloud.providers import connect
from libcloud.types import Provider

from secrets import RACKSPACE_USER, RACKSPACE_KEY

class RackspaceTests(unittest.TestCase):

  def setUp(self):
    self.conn = connect(Provider.RACKSPACE, RACKSPACE_USER, RACKSPACE_KEY)

  def test_list_nodes(self):
    ret = self.conn.list_nodes()
