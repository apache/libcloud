import unittest

from libcloud.drivers.gogrid import GoGridProvider
from libcloud.providers import connect
from libcloud.types import Provider

from secrets import GOGRID_API_KEY, GOGRID_SECRET 

class GoGridTests(unittest.TestCase):

  def setUp(self):
    self.conn = connect(Provider.GOGRID, GOGRID_API_KEY, GOGRID_SECRET)

  def test_list_nodes(self):
    ret = self.conn.list_nodes()
    print ret
