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
import os

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qsl

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver
from libcloud.compute.types import LibcloudError, Provider
from libcloud.compute.providers import get_driver

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

    def test_user_must_provide_host_and_path(self):
        expected_msg = 'When instantiating CloudStack driver directly ' + \
                       'you also need to provide host and path argument'
        cls = get_driver(Provider.CLOUDSTACK)

        self.assertRaisesRegexp(Exception, expected_msg, cls,
                                'key', 'secret')

        try:
            cls('key', 'secret', True, 'localhost', '/path')
        except Exception:
            self.fail('host and path provided but driver raised an exception')

    def test_create_node_immediate_failure(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        CloudStackMockHttp.fixture_tag = 'deployfail'
        try:
            self.driver.create_node(name='node-name',
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
            self.driver.create_node(name='node-name',
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
        self.assertEqual(node.private_ips, ['192.168.1.2'])
        self.assertEqual(node.extra['zoneid'], default_location.id)

    def test_create_node_ex_security_groups(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        sg = [sg['name'] for sg in self.driver.ex_list_security_groups()]
        CloudStackMockHttp.fixture_tag = 'deploysecuritygroup'
        node = self.driver.create_node(name='test',
                                       location=location,
                                       image=image,
                                       size=size,
                                       ex_security_groups=sg)
        self.assertEqual(node.name, 'test')
        self.assertEqual(node.extra['securitygroup'], sg)
        self.assertEqual(node.id, 'fc4fd31a-16d3-49db-814a-56b39b9ef986')

    def test_create_node_ex_keyname(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        CloudStackMockHttp.fixture_tag = 'deploykeyname'
        node = self.driver.create_node(name='test',
                                       location=location,
                                       image=image,
                                       size=size,
                                       ex_keyname='foobar')
        self.assertEqual(node.name, 'test')
        self.assertEqual(node.extra['keyname'], 'foobar')

    def test_list_images_no_images_available(self):
        CloudStackMockHttp.fixture_tag = 'notemplates'

        images = self.driver.list_images()
        self.assertEqual(0, len(images))

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
            self.assertEqual(image.id, tid)
            self.assertEqual(image.name, tname)

    def test_ex_list_disk_offerings(self):
        diskOfferings = self.driver.ex_list_disk_offerings()
        self.assertEqual(1, len(diskOfferings))

        diskOffering, = diskOfferings

        self.assertEqual('Disk offer 1', diskOffering.name)
        self.assertEqual(10, diskOffering.size)

    def test_ex_list_networks(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listNetworks_default.json')
        fixture_networks = fixture['listnetworksresponse']['network']

        networks = self.driver.ex_list_networks()

        for i, network in enumerate(networks):
            self.assertEqual(network.id, fixture_networks[i]['id'])
            self.assertEqual(
                network.displaytext, fixture_networks[i]['displaytext'])
            self.assertEqual(network.name, fixture_networks[i]['name'])
            self.assertEqual(
                network.networkofferingid,
                fixture_networks[i]['networkofferingid'])
            self.assertEqual(network.zoneid, fixture_networks[i]['zoneid'])

    def test_create_volume(self):
        volumeName = 'vol-0'
        location = self.driver.list_locations()[0]

        volume = self.driver.create_volume(10, volumeName, location)

        self.assertEqual(volumeName, volume.name)
        self.assertEqual(10, volume.size)

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

        self.assertEqual(volumeName, volume.name)

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volumeName = 'vol-0'
        location = self.driver.list_locations()[0]

        volume = self.driver.create_volume(10, volumeName, location)
        attachReturnVal = self.driver.attach_volume(volume, node)

        self.assertTrue(attachReturnVal)

    def test_detach_volume(self):
        volumeName = 'gre-test-volume'
        location = self.driver.list_locations()[0]
        volume = self.driver.create_volume(10, volumeName, location)
        res = self.driver.detach_volume(volume)
        self.assertTrue(res)

    def test_destroy_volume(self):
        volumeName = 'gre-test-volume'
        location = self.driver.list_locations()[0]
        volume = self.driver.create_volume(10, volumeName, location)
        res = self.driver.destroy_volume(volume)
        self.assertTrue(res)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(1, len(volumes))
        self.assertEqual('ROOT-69942', volumes[0].name)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(2, len(nodes))
        self.assertEqual('test', nodes[0].name)
        self.assertEqual('2600', nodes[0].id)
        self.assertEqual([], nodes[0].extra['securitygroup'])
        self.assertEqual(None, nodes[0].extra['keyname'])

    def test_list_locations(self):
        location = self.driver.list_locations()[0]
        self.assertEqual('1', location.id)
        self.assertEqual('Sydney', location.name)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual('Compute Micro PRD', sizes[0].name)
        self.assertEqual('105', sizes[0].id)
        self.assertEqual(384, sizes[0].ram)
        self.assertEqual('Compute Large PRD', sizes[2].name)
        self.assertEqual('69', sizes[2].id)
        self.assertEqual(6964, sizes[2].ram)

    def test_ex_start_node(self):
        node = self.driver.list_nodes()[0]
        res = node.ex_start()
        self.assertEqual('Starting', res)

    def test_ex_stop_node(self):
        node = self.driver.list_nodes()[0]
        res = node.ex_stop()
        self.assertEqual('Stopped', res)

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        res = node.destroy()
        self.assertTrue(res)

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        res = node.reboot()
        self.assertTrue(res)

    def test_ex_list_keypairs(self):
        keypairs = self.driver.ex_list_keypairs()
        fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                      '00:00:00:00:00'

        self.assertEqual(keypairs[0]['name'], 'cs-keypair')
        self.assertEqual(keypairs[0]['fingerprint'], fingerprint)

    def test_ex_create_keypair(self):
        self.assertRaises(
            LibcloudError,
            self.driver.ex_create_keypair,
            'cs-keypair')

    def test_ex_delete_keypair(self):
        res = self.driver.ex_delete_keypair('cs-keypair')
        self.assertTrue(res)

    def test_ex_import_keypair(self):
        fingerprint = 'c4:a1:e5:d4:50:84:a9:4c:6b:22:ee:d6:57:02:b8:15'
        path = os.path.join(os.path.dirname(__file__), "fixtures",
                            "cloudstack",
                            "dummy_rsa.pub")

        res = self.driver.ex_import_keypair('foobar', path)
        self.assertEqual(res['keyName'], 'foobar')
        self.assertEqual(res['keyFingerprint'], fingerprint)

    def test_ex_import_keypair_from_string(self):
        fingerprint = 'c4:a1:e5:d4:50:84:a9:4c:6b:22:ee:d6:57:02:b8:15'
        path = os.path.join(os.path.dirname(__file__), "fixtures",
                            "cloudstack",
                            "dummy_rsa.pub")
        fh = open(path)
        res = self.driver.ex_import_keypair_from_string('foobar',
                                                        fh.read())
        fh.close()
        self.assertEqual(res['keyName'], 'foobar')
        self.assertEqual(res['keyFingerprint'], fingerprint)

    def test_ex_list_security_groups(self):
        groups = self.driver.ex_list_security_groups()
        self.assertEqual(2, len(groups))
        self.assertEqual(groups[0]['name'], 'default')
        self.assertEqual(groups[1]['name'], 'mongodb')

    def test_ex_create_security_group(self):
        group = self.driver.ex_create_security_group(name='MySG')
        self.assertEqual(group['name'], 'MySG')

    def test_ex_delete_security_group(self):
        res = self.driver.ex_delete_security_group(name='MySG')
        self.assertTrue(res)

    def test_ex_authorize_security_group_ingress(self):
        res = self.driver.ex_authorize_security_group_ingress('MySG',
                                                              'TCP',
                                                              '22',
                                                              '22',
                                                              '0.0.0.0/0')
        self.assertTrue(res)

    def test_ex_list_public_ips(self):
        ips = self.driver.ex_list_public_ips()
        self.assertEqual(ips[0].address, '1.1.1.116')

    def test_ex_allocate_public_ip(self):
        addr = self.driver.ex_allocate_public_ip()
        self.assertEqual(addr.address, '7.5.6.1')
        self.assertEqual(addr.id, '10987171-8cc9-4d0a-b98f-1698c09ddd2d')

    def test_ex_release_public_ip(self):
        addresses = self.driver.ex_list_public_ips()
        res = self.driver.ex_release_public_ip(addresses[0])
        self.assertTrue(res)

    def test_ex_create_port_forwarding_rule(self):
        node = self.driver.list_nodes()[0]
        address = self.driver.ex_list_public_ips()[0]
        private_port = 33
        private_end_port = 34
        public_port = 33
        public_end_port = 34
        openfirewall = True
        protocol = 'TCP'
        rule = self.driver.ex_create_port_forwarding_rule(address,
                                                          private_port,
                                                          public_port,
                                                          protocol,
                                                          node,
                                                          public_end_port,
                                                          private_end_port,
                                                          openfirewall)
        self.assertEqual(rule.address, address)
        self.assertEqual(rule.protocol, protocol)
        self.assertEqual(rule.public_port, public_port)
        self.assertEqual(rule.public_end_port, public_end_port)
        self.assertEqual(rule.private_port, private_port)
        self.assertEqual(rule.private_end_port, private_end_port)

    def test_ex_list_port_forwarding_rules(self):
        rules = self.driver.ex_list_port_forwarding_rules()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertTrue(rule.node)
        self.assertEqual(rule.protocol, 'tcp')
        self.assertEqual(rule.public_port, '33')
        self.assertEqual(rule.public_end_port, '34')
        self.assertEqual(rule.private_port, '33')
        self.assertEqual(rule.private_end_port, '34')
        self.assertEqual(rule.address.address, '1.1.1.116')

    def test_ex_delete_port_forwarding_rule(self):
        node = self.driver.list_nodes()[0]
        rule = self.driver.ex_list_port_forwarding_rules()[0]
        res = self.driver.ex_delete_port_forwarding_rule(node, rule)
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
