import unittest

from libcloud.drivers.vpsnet import VPSNetProvider
from libcloud.providers import connect
from libcloud.types import Provider

from secrets import VPSNET_USER, VPSNET_KEY

class VPSNetTests(unittest.TestCase):

  def setUp(self):
    self.conn = connect(Provider.VPSNET, VPSNET_USER, VPSNET_KEY)

  def test_list_nodes(self):
    ret = self.conn.list_nodes()
    print ret
