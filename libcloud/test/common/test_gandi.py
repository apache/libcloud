import sys
import unittest

from xml.etree import ElementTree as ET

from libcloud.utils.py3 import xmlrpclib


class MockGandiTransport(xmlrpclib.Transport):

    def request(self, host, handler, request_body, verbose=0):
        self.verbose = 0
        method = ET.XML(request_body).find('methodName').text
        mock = self.mockCls(host, 80)
        mock.request('POST', '%s/%s' % (handler, method))
        resp = mock.getresponse()

        if sys.version[0] == '2' and sys.version[2] == '7':
            response = self.parse_response(resp)
        else:
            response = self.parse_response(resp.body)
        return response


class BaseGandiTests(unittest.TestCase):

    def setUp(self):
        d = self.driverCls
        t = self.transportCls
        t.mockCls.type = None
        d.connectionCls.proxyCls.transportCls = \
            [t, t]
        self.driver = d(*self.params)
