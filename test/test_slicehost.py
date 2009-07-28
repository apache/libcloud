import unittest

from libcloud.providers import connect
from libcloud.types import Provider

from secrets import SLICEHOST_KEY

class SlicehostTests(unittest.TestCase):

  def setUp(self):
    self.conn = connect(Provider.SLICEHOST, SLICEHOST_KEY)

  def test_list_nodes(self):
    ret = self.conn.list_nodes()
