import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse

try:
    import simplejson as json
except ImportError:
    import json

try:
    parse_qsl = urlparse.parse_qsl
except AttributeError:
    import cgi
    parse_qsl = cgi.parse_qsl

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver
from libcloud.compute.types import DeploymentError, LibcloudError

from libcloud.test import MockHttpTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

class CloudStackNodeDriverTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        CloudStackNodeDriver.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)
        self.driver = CloudStackNodeDriver('apikey', 'secret',
                                           path='/test/path',
                                           host='api.dummy.com')
        self.driver.path = '/test/path'
        self.driver.type = -1
        CloudStackMockHttp.fixture_tag = 'default'
        self.driver.connection.poll_interval = 0.0

    def test_create_node_immediate_failure(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        CloudStackMockHttp.fixture_tag = 'deployfail'
        try:
            node = self.driver.create_node(name='node-name',
                                           image=image,
                                           size=size)
        except:
            return
        self.assertTrue(False)

    def test_create_node_delayed_failure(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        CloudStackMockHttp.fixture_tag = 'deployfail2'
        try:
            node = self.driver.create_node(name='node-name',
                                           image=image,
                                           size=size)
        except:
            return
        self.assertTrue(False)

    def test_list_images_no_images_available(self):
        CloudStackMockHttp.fixture_tag = 'notemplates'

        images = self.driver.list_images()
        self.assertEquals(0, len(images))

    def test_ex_list_disk_offerings(self):
        diskOfferings = self.driver.ex_list_disk_offerings()
        self.assertEquals(1, len(diskOfferings))

        diskOffering, = diskOfferings

        self.assertEquals('Disk offer 1', diskOffering.name)
        self.assertEquals(10, diskOffering.size)

    def test_create_volume(self):
        volumeName = 'vol-0'
        location = self.driver.list_locations()[0]

        volume = self.driver.create_volume(10, volumeName, location)

        self.assertEquals(volumeName, volume.name)
        self.assertEquals(10, volume.size)

    def test_create_volume_no_noncustomized_offering_with_size(self):
        """If the sizes of disk offerings are not configurable and there
        are no disk offerings with the requested size, an exception should
        be thrown."""

        location = self.driver.list_locations()[0]

        self.assertRaises(
                LibcloudError,
                self.driver.create_volume,
                    'vol-0', location, 11)

    def test_create_volume_with_custom_disk_size_offering(self):
        CloudStackMockHttp.fixture_tag = 'withcustomdisksize'

        volumeName = 'vol-0'
        location = self.driver.list_locations()[0]

        volume = self.driver.create_volume(10, volumeName, location)

        self.assertEquals(volumeName, volume.name)

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volumeName = 'vol-0'
        location = self.driver.list_locations()[0]

        volume = self.driver.create_volume(10, volumeName, location)
        attachReturnVal = self.driver.attach_volume(volume, node)

        self.assertTrue(attachReturnVal)


class CloudStackMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('cloudstack')
    fixture_tag = 'default'

    def _load_fixture(self, fixture):
        body = self.fixtures.load(fixture)
        return body, json.loads(body)

    def _test_path(self, method, url, body, headers):
        url = urlparse.urlparse(url)
        query = dict(parse_qsl(url.query))

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
            fixture = command + '_' + self.fixture_tag + '.json'
            body, obj = self._load_fixture(fixture)
            return (httplib.OK, body, obj, httplib.responses[httplib.OK])

    def _cmd_queryAsyncJobResult(self, jobid):
        fixture = 'queryAsyncJobResult' + '_' + str(jobid) + '.json'
        body, obj = self._load_fixture(fixture)
        return (httplib.OK, body, obj, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
