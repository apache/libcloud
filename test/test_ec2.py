import unittest

from libcloud.drivers.ec2 import EC2Provider
from libcloud.providers import connect
from libcloud.types import Provider

from secrets import EC2_ACCESS_ID, EC2_SECRET

class EC2Tests(unittest.TestCase):

  def setUp(self):
    self.conn = connect(Provider.EC2, EC2_ACCESS_ID, EC2_SECRET)

  def test_list_nodes(self):
    ret = self.conn.list_nodes()
