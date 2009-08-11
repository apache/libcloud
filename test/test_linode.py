import unittest
from libcloud.drivers.linode import LinodeNodeDriver
from test import MockHttp
import httplib

class LinodeTest(unittest.TestCase):

    def setUp(self):
        LinodeNodeDriver.connectionCls.conn_classes = (None, LinodeMockHttp)
        LinodeMockHttp.use_param = 'api_action'
        self.driver = LinodeNodeDriver('foo')

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, 8098)
        self.assertEqual(node.name, 'api-node3')
        self.assertEqual(node.public_ip, '75.127.96.245')
        self.assertEqual(node.private_ip, None)
        
        
class LinodeMockHttp(MockHttp):

    def _linode_list(self, method, url, body, headers):
        body = """{
   "ERRORARRAY":[],
   "ACTION":"linode.list",
   "DATA":[
      {
         "TOTALXFER":200,
         "BACKUPSENABLED":1,
         "WATCHDOG":1,
         "LPM_DISPLAYGROUP":"",
         "ALERT_BWQUOTA_ENABLED":1,
         "STATUS":2,
         "TOTALRAM":540,
         "ALERT_DISKIO_THRESHOLD":200,
         "BACKUPWINDOW":1,
         "ALERT_BWOUT_ENABLED":1,
         "ALERT_BWOUT_THRESHOLD":5,
         "LABEL":"api-node3",
         "ALERT_CPU_ENABLED":1,
         "ALERT_BWQUOTA_THRESHOLD":81,
         "ALERT_BWIN_THRESHOLD":5,
         "BACKUPWEEKLYDAY":0,
         "DATACENTERID":5,
         "ALERT_CPU_THRESHOLD":10,
         "TOTALHD":100,
         "ALERT_DISKIO_ENABLED":1,
         "ALERT_BWIN_ENABLED":1,
         "LINODEID":8098
      }
   ]
}"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _linode_ip_list(self, method, url, body, headers):
        body = """{
   "ERRORARRAY":[],
   "ACTION":"linode.ip.list",
   "DATA":[
      {
         "LINODEID":8098,
         "ISPUBLIC":1,
         "IPADDRESS":"75.127.96.54",
         "RDNS_NAME":"li22-54.members.linode.com",
         "IPADDRESSID":5384
      },
      {
         "LINODEID":8098,
         "ISPUBLIC":1,
         "IPADDRESS":"75.127.96.245",
         "RDNS_NAME":"li22-245.members.linode.com",
         "IPADDRESSID":5575
      }
   ]
}"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
