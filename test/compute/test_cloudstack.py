import httplib
import sys
import unittest
import urlparse

try:
    import json
except:
    import simplejson as json

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver

from test import MockHttpTestCase
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures

class CloudStackNodeDriverTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        CloudStackNodeDriver.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)
        self.driver = CloudStackNodeDriver('apikey', 'secret')
        self.driver.path = '/test/path'
        self.driver.type = -1

class CloudStackMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('cloudstack')

    def _load_fixture(self, fixture):
        body = self.fixtures.load(fixture)
        return body, json.loads(body)

    def _test_path(self, method, url, body, headers):
        url = urlparse.urlparse(url)
        query = dict(urlparse.parse_qsl(url.query))

        self.assertTrue('apiKey' in query)
        self.assertTrue('command' in query)
        self.assertTrue('response' in query)
        self.assertTrue('signature' in query)

        self.assertTrue(query['response'] == 'json')

        del query['apiKey']
        del query['response']
        del query['signature']
        command = query.pop('command')

        if hasattr(self, '_cmd_' + command):
            return getattr(self, '_cmd_' + command)(**query)
        else:
            body, obj = self._load_fixture(command + '_default.json')
            return (httplib.OK, body, obj, httplib.responses[httplib.OK])

    def _cmd_queryAsyncJobResult(self, jobid):
        fixture = 'queryAsyncJobResult' + '_' + str(jobid) + '.json'
        body, obj = self._load_fixture(fixture)
        return (httplib.OK, body, obj, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
