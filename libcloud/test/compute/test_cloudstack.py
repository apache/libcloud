# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qsl

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver
from libcloud.compute.types import DeploymentError, LibcloudError
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation

from libcloud.test import unittest
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

    def test_create_node_default_location_success(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        default_location = self.driver.list_locations()[0]

        node = self.driver.create_node(name='fred',
                                       image=image,
                                       size=size)

        self.assertEqual(node.name, 'fred')
        self.assertEqual(node.public_ips, [])
        self.assertEqual(node.private_ips, ['1.1.1.2'])
        self.assertEqual(node.extra['zoneid'], default_location.id)

    def test_list_images_no_images_available(self):
        CloudStackMockHttp.fixture_tag = 'notemplates'

        images = self.driver.list_images()
        self.assertEquals(0, len(images))

    def test_list_images(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listTemplates_default.json')
        templates = fixture['listtemplatesresponse']['template']

        images = self.driver.list_images()
        for i, image in enumerate(images):
            # NodeImage expects id to be a string,
            # the CloudStack fixture has an int
            tid = str(templates[i]['id'])
            tname = templates[i]['name']
            self.assertIsInstance(image.driver, CloudStackNodeDriver)
            self.assertEquals(image.id, tid)
            self.assertEquals(image.name, tname)

    def test_ex_list_disk_offerings(self):
        diskOfferings = self.driver.ex_list_disk_offerings()
        self.assertEquals(1, len(diskOfferings))

        diskOffering, = diskOfferings

        self.assertEquals('Disk offer 1', diskOffering.name)
        self.assertEquals(10, diskOffering.size)

    def test_ex_list_networks(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listNetworks_default.json')
        fixture_networks = fixture['listnetworksresponse']['network']

        networks = self.driver.ex_list_networks()

        for i, network in enumerate(networks):
            self.assertEquals(network.id, fixture_networks[i]['id'])
            self.assertEquals(
                network.displaytext, fixture_networks[i]['displaytext'])
            self.assertEquals(network.name, fixture_networks[i]['name'])
            self.assertEquals(
                network.networkofferingid,
                fixture_networks[i]['networkofferingid'])
            self.assertEquals(network.zoneid, fixture_networks[i]['zoneid'])

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

    def test_list_nodes(self):
        node = self.driver.list_nodes()[0]
        self.assertEquals('test', node.name)

    def test_list_locations(self):
        location = self.driver.list_locations()[0]
        self.assertEquals('Sydney', location.name)

    def test_start_node(self):
        node = self.driver.list_nodes()[0]
        res = node.ex_start()
        self.assertEquals('Starting', res)

    def test_stop_node(self):
        node = self.driver.list_nodes()[0]
        res = node.ex_stop()
        self.assertEquals('Stopped', res)

    def test_list_keypairs(self):
        keypairs = self.driver.ex_list_keypairs()
        fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                      '00:00:00:00:00'

        self.assertEqual(keypairs[0]['name'], 'cs-keypair')
        self.assertEqual(keypairs[0]['fingerprint'], fingerprint)

    def test_create_keypair(self):
        self.assertRaises(
            LibcloudError,
            self.driver.ex_create_keypair,
            'cs-keypair')

    def test_delete_keypair(self):
        res = self.driver.ex_delete_keypair('cs-keypair')
        self.assertTrue(res)

    def test_list_security_groups(self):
        groups = self.driver.ex_list_security_groups()
        self.assertEqual(groups[0]['name'], 'default')

    def test_create_security_group(self):
        group = self.driver.ex_create_security_group(name='MySG')
        self.assertEqual(group['name'], 'MySG')

    def test_delete_security_group(self):
        res = self.driver.ex_delete_security_group(name='MySG')
        self.assertTrue(res)

    def test_authorize_security_group_ingress(self):
        res = self.driver.ex_authorize_security_group_ingress('MySG',
                                                              'TCP',
                                                              '22',
                                                              '22',
                                                              '0.0.0.0/0')
        self.assertTrue(res)


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
