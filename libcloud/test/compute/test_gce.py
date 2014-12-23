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
"""
Tests for Google Compute Engine Driver
"""
import sys
import unittest
import datetime

from mock import Mock

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.gce import (GCENodeDriver, API_VERSION,
                                          timestamp_to_datetime,
                                          GCEAddress, GCEHealthCheck,
                                          GCEFirewall, GCEForwardingRule,
                                          GCENetwork,
                                          GCEZone,
                                          GCENodeImage,
                                          GCERoute)
from libcloud.common.google import (GoogleBaseAuthConnection,
                                    GoogleInstalledAppAuthConnection,
                                    GoogleBaseConnection,
                                    ResourceNotFoundError, ResourceExistsError)
from libcloud.test.common.test_google import GoogleAuthMockHttp
from libcloud.compute.base import Node, StorageVolume

from libcloud.test import MockHttpTestCase, LibcloudTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.secrets import GCE_PARAMS, GCE_KEYWORD_PARAMS


class GCENodeDriverTest(LibcloudTestCase, TestCaseMixin):

    """
    Google Compute Engine Test Class.
    """
    # Mock out a few specific calls that interact with the user, system or
    # environment.
    GoogleBaseConnection._get_token_info_from_file = lambda x: None
    GoogleBaseConnection._write_token_info_to_file = lambda x: None
    GoogleInstalledAppAuthConnection.get_code = lambda x: '1234'
    GCEZone._now = lambda x: datetime.datetime(2013, 6, 26, 19, 0, 0)
    datacenter = 'us-central1-a'

    def setUp(self):
        GCEMockHttp.test = self
        GCENodeDriver.connectionCls.conn_classes = (GCEMockHttp, GCEMockHttp)
        GoogleBaseAuthConnection.conn_classes = (GoogleAuthMockHttp,
                                                 GoogleAuthMockHttp)
        GCEMockHttp.type = None
        kwargs = GCE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        kwargs['datacenter'] = self.datacenter
        self.driver = GCENodeDriver(*GCE_PARAMS, **kwargs)

    def test_default_scopes(self):
        self.assertEqual(self.driver.scopes, None)

    def test_timestamp_to_datetime(self):
        timestamp1 = '2013-06-26T10:05:19.340-07:00'
        datetime1 = datetime.datetime(2013, 6, 26, 17, 5, 19)
        self.assertEqual(timestamp_to_datetime(timestamp1), datetime1)
        timestamp2 = '2013-06-26T17:43:15.000-00:00'
        datetime2 = datetime.datetime(2013, 6, 26, 17, 43, 15)
        self.assertEqual(timestamp_to_datetime(timestamp2), datetime2)

    def test_get_object_by_kind(self):
        obj = self.driver._get_object_by_kind(None)
        self.assertIsNone(obj)
        obj = self.driver._get_object_by_kind('')
        self.assertIsNone(obj)
        obj = self.driver._get_object_by_kind(
            'https://www.googleapis.com/compute/v1/projects/project_name/'
            'global/targetHttpProxies/web-proxy')
        self.assertEquals(obj.name, 'web-proxy')

    def test_get_region_from_zone(self):
        zone1 = self.driver.ex_get_zone('us-central1-a')
        expected_region1 = 'us-central1'
        region1 = self.driver._get_region_from_zone(zone1)
        self.assertEqual(region1.name, expected_region1)
        zone2 = self.driver.ex_get_zone('europe-west1-b')
        expected_region2 = 'europe-west1'
        region2 = self.driver._get_region_from_zone(zone2)
        self.assertEqual(region2.name, expected_region2)

    def test_find_zone_or_region(self):
        zone1 = self.driver._find_zone_or_region('libcloud-demo-np-node',
                                                 'instances')
        self.assertEqual(zone1.name, 'us-central2-a')
        zone2 = self.driver._find_zone_or_region(
            'libcloud-demo-europe-np-node', 'instances')
        self.assertEqual(zone2.name, 'europe-west1-a')
        region = self.driver._find_zone_or_region('libcloud-demo-address',
                                                  'addresses', region=True)
        self.assertEqual(region.name, 'us-central1')

    def test_match_images(self):
        project = 'debian-cloud'
        image = self.driver._match_images(project, 'debian-7')
        self.assertEqual(image.name, 'debian-7-wheezy-v20131120')
        image = self.driver._match_images(project, 'backports')
        self.assertEqual(image.name, 'backports-debian-7-wheezy-v20131127')

    def test_ex_list_addresses(self):
        address_list = self.driver.ex_list_addresses()
        address_list_all = self.driver.ex_list_addresses('all')
        address_list_uc1 = self.driver.ex_list_addresses('us-central1')
        address_list_global = self.driver.ex_list_addresses('global')
        self.assertEqual(len(address_list), 2)
        self.assertEqual(len(address_list_all), 5)
        self.assertEqual(len(address_list_global), 1)
        self.assertEqual(address_list[0].name, 'libcloud-demo-address')
        self.assertEqual(address_list_uc1[0].name, 'libcloud-demo-address')
        self.assertEqual(address_list_global[0].name, 'lcaddressglobal')
        names = [a.name for a in address_list_all]
        self.assertTrue('libcloud-demo-address' in names)

    def test_ex_list_backend_services(self):
        self.backend_services_mock = 'empty'
        backend_services_list = self.driver.ex_list_backend_services()
        self.assertListEqual(backend_services_list, [])

        self.backend_services_mock = 'web-service'
        backend_services_list = self.driver.ex_list_backend_services()
        web_service = backend_services_list[0]
        self.assertEqual(web_service.name, 'web-service')
        self.assertEqual(len(web_service.healthchecks), 1)
        self.assertEqual(len(web_service.backends), 2)

    def test_ex_list_healthchecks(self):
        healthchecks = self.driver.ex_list_healthchecks()
        self.assertEqual(len(healthchecks), 3)
        self.assertEqual(healthchecks[0].name, 'basic-check')

    def test_ex_list_firewalls(self):
        firewalls = self.driver.ex_list_firewalls()
        self.assertEqual(len(firewalls), 5)
        self.assertEqual(firewalls[0].name, 'default-allow-internal')

    def test_ex_list_forwarding_rules(self):
        forwarding_rules = self.driver.ex_list_forwarding_rules()
        forwarding_rules_all = self.driver.ex_list_forwarding_rules('all')
        forwarding_rules_uc1 = self.driver.ex_list_forwarding_rules(
            'us-central1')
        self.assertEqual(len(forwarding_rules), 2)
        self.assertEqual(len(forwarding_rules_all), 2)
        self.assertEqual(forwarding_rules[0].name, 'lcforwardingrule')
        self.assertEqual(forwarding_rules_uc1[0].name, 'lcforwardingrule')
        names = [f.name for f in forwarding_rules_all]
        self.assertTrue('lcforwardingrule' in names)

    def test_ex_list_forwarding_rules_global(self):
        forwarding_rules = self.driver.ex_list_forwarding_rules(global_rules=True)
        self.assertEqual(len(forwarding_rules), 2)
        self.assertEqual(forwarding_rules[0].name, 'http-rule')
        names = [f.name for f in forwarding_rules]
        self.assertListEqual(names, ['http-rule', 'http-rule2'])

    def test_list_images(self):
        local_images = self.driver.list_images()
        debian_images = self.driver.list_images(ex_project='debian-cloud')
        local_plus_deb = self.driver.list_images(['debian-cloud', 'project_name'])
        self.assertEqual(len(local_images), 3)
        self.assertEqual(len(debian_images), 19)
        self.assertEqual(len(local_plus_deb), 22)
        self.assertEqual(local_images[0].name, 'debian-7-wheezy-v20130617')
        self.assertEqual(local_images[1].name, 'centos-6-v20131118')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 5)
        self.assertEqual(locations[0].name, 'europe-west1-a')

    def test_ex_list_routes(self):
        routes = self.driver.ex_list_routes()
        self.assertEqual(len(routes), 3)
        self.assertTrue('lcdemoroute' in [route.name for route in routes])

    def test_ex_list_networks(self):
        networks = self.driver.ex_list_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[0].name, 'default')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        nodes_all = self.driver.list_nodes(ex_zone='all')
        nodes_uc1a = self.driver.list_nodes(ex_zone='us-central1-a')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(nodes_all), 8)
        self.assertEqual(len(nodes_uc1a), 1)
        self.assertEqual(nodes[0].name, 'node-name')
        self.assertEqual(nodes_uc1a[0].name, 'node-name')
        names = [n.name for n in nodes_all]
        self.assertTrue('node-name' in names)

    def test_ex_list_regions(self):
        regions = self.driver.ex_list_regions()
        self.assertEqual(len(regions), 3)
        self.assertEqual(regions[0].name, 'europe-west1')

    def test_ex_list_snapshots(self):
        snapshots = self.driver.ex_list_snapshots()
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].name, 'lcsnapshot')

    def test_ex_list_targetinstances(self):
        target_instances = self.driver.ex_list_targetinstances()
        target_instances_all = self.driver.ex_list_targetinstances('all')
        target_instances_uc1 = self.driver.ex_list_targetinstances('us-central1-a')
        self.assertEqual(len(target_instances), 2)
        self.assertEqual(len(target_instances_all), 2)
        self.assertEqual(len(target_instances_uc1), 2)
        self.assertEqual(target_instances[0].name, 'hello')
        self.assertEqual(target_instances_uc1[0].name, 'hello')
        names = [t.name for t in target_instances_all]
        self.assertTrue('lctargetinstance' in names)

    def test_ex_list_targetpools(self):
        target_pools = self.driver.ex_list_targetpools()
        target_pools_all = self.driver.ex_list_targetpools('all')
        target_pools_uc1 = self.driver.ex_list_targetpools('us-central1')
        self.assertEqual(len(target_pools), 4)
        self.assertEqual(len(target_pools_all), 5)
        self.assertEqual(len(target_pools_uc1), 4)
        self.assertEqual(target_pools[0].name, 'lctargetpool')
        self.assertEqual(target_pools_uc1[0].name, 'lctargetpool')
        names = [t.name for t in target_pools_all]
        self.assertTrue('www-pool' in names)

    def test_ex_list_target_http_proxies(self):
        target_proxies = self.driver.ex_list_target_http_proxies()
        self.assertEqual(len(target_proxies), 2)
        self.assertEqual(target_proxies[0].name, 'web-proxy')
        names = [t.name for t in target_proxies]
        self.assertListEqual(names, ['web-proxy', 'web-proxy2'])

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        sizes_all = self.driver.list_sizes('all')
        self.assertEqual(len(sizes), 22)
        self.assertEqual(len(sizes_all), 100)
        self.assertEqual(sizes[0].name, 'f1-micro')
        self.assertEqual(sizes[0].extra['zone'].name, 'us-central1-a')
        names = [s.name for s in sizes_all]
        self.assertEqual(names.count('n1-standard-1'), 5)

    def test_ex_get_license(self):
        license = self.driver.ex_get_license('suse-cloud', 'sles-12')
        self.assertTrue(license.name, 'sles-12')
        self.assertTrue(license.charges_use_fee)

    def test_list_disktypes(self):
        disktypes = self.driver.ex_list_disktypes()
        disktypes_all = self.driver.ex_list_disktypes('all')
        disktypes_uc1a = self.driver.ex_list_disktypes('us-central1-a')
        self.assertEqual(len(disktypes), 2)
        self.assertEqual(len(disktypes_all), 9)
        self.assertEqual(len(disktypes_uc1a), 2)
        self.assertEqual(disktypes[0].name, 'pd-ssd')
        self.assertEqual(disktypes_uc1a[0].name, 'pd-ssd')
        names = [v.name for v in disktypes_all]
        self.assertTrue('pd-standard' in names)
        self.assertTrue('local-ssd' in names)

    def test_ex_list_url_maps(self):
        url_maps_list = self.driver.ex_list_url_maps()
        web_map = url_maps_list[0]
        self.assertEqual(web_map.name, 'web-map')
        self.assertEqual(len(web_map.host_rules), 0)
        self.assertEqual(len(web_map.path_matchers), 0)
        self.assertEqual(len(web_map.tests), 0)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        volumes_all = self.driver.list_volumes('all')
        volumes_uc1a = self.driver.list_volumes('us-central1-a')
        self.assertEqual(len(volumes), 2)
        self.assertEqual(len(volumes_all), 10)
        self.assertEqual(len(volumes_uc1a), 2)
        self.assertEqual(volumes[0].name, 'lcdisk')
        self.assertEqual(volumes_uc1a[0].name, 'lcdisk')
        names = [v.name for v in volumes_all]
        self.assertTrue('libcloud-demo-europe-boot-disk' in names)

    def test_ex_list_zones(self):
        zones = self.driver.ex_list_zones()
        self.assertEqual(len(zones), 5)
        self.assertEqual(zones[0].name, 'europe-west1-a')

    def test_ex_create_address_global(self):
        address_name = 'lcaddressglobal'
        address = self.driver.ex_create_address(address_name, 'global')
        self.assertTrue(isinstance(address, GCEAddress))
        self.assertEqual(address.name, address_name)
        self.assertEqual(address.region, 'global')

    def test_ex_create_address(self):
        address_name = 'lcaddress'
        address = self.driver.ex_create_address(address_name)
        self.assertTrue(isinstance(address, GCEAddress))
        self.assertEqual(address.name, address_name)

    def test_ex_create_healthcheck(self):
        healthcheck_name = 'lchealthcheck'
        kwargs = {'host': 'lchost',
                  'path': '/lc',
                  'port': 8000,
                  'interval': 10,
                  'timeout': 10,
                  'unhealthy_threshold': 4,
                  'healthy_threshold': 3,
                  'description': 'test healthcheck'}
        hc = self.driver.ex_create_healthcheck(healthcheck_name, **kwargs)
        self.assertTrue(isinstance(hc, GCEHealthCheck))
        self.assertEqual(hc.name, healthcheck_name)
        self.assertEqual(hc.path, '/lc')
        self.assertEqual(hc.port, 8000)
        self.assertEqual(hc.interval, 10)
        self.assertEqual(hc.extra['host'], 'lchost')
        self.assertEqual(hc.extra['description'], 'test healthcheck')

    def test_ex_create_image(self):
        volume = self.driver.ex_get_volume('lcdisk')
        image = self.driver.ex_create_image('coreos', volume)
        self.assertTrue(isinstance(image, GCENodeImage))
        self.assertEqual(image.name, 'coreos')
        self.assertEqual(image.extra['description'], 'CoreOS test image')

    def test_ex_create_firewall(self):
        firewall_name = 'lcfirewall'
        allowed = [{'IPProtocol': 'tcp', 'ports': ['4567']}]
        source_tags = ['libcloud']
        firewall = self.driver.ex_create_firewall(firewall_name, allowed,
                                                  source_tags=source_tags)
        self.assertTrue(isinstance(firewall, GCEFirewall))
        self.assertEqual(firewall.name, firewall_name)

    def test_ex_create_forwarding_rule(self):
        fwr_name = 'lcforwardingrule'
        targetpool = 'lctargetpool'
        region = 'us-central1'
        port_range = '8000-8500'
        description = 'test forwarding rule'
        fwr = self.driver.ex_create_forwarding_rule(fwr_name, targetpool,
                                                    region=region,
                                                    port_range=port_range,
                                                    description=description)
        self.assertTrue(isinstance(fwr, GCEForwardingRule))
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.region.name, region)
        self.assertEqual(fwr.protocol, 'TCP')
        self.assertEqual(fwr.extra['portRange'], port_range)
        self.assertEqual(fwr.extra['description'], description)

    def test_ex_create_route(self):
        route_name = 'lcdemoroute'
        dest_range = '192.168.25.0/24'
        priority = 1000
        route = self.driver.ex_create_route(route_name, dest_range)
        self.assertTrue(isinstance(route, GCERoute))
        self.assertEqual(route.name, route_name)
        self.assertEqual(route.priority, priority)
        self.assertTrue("tag1" in route.tags)
        self.assertTrue(route.extra['nextHopInstance'].endswith('libcloud-100'))
        self.assertEqual(route.dest_range, dest_range)

    def test_ex_create_network(self):
        network_name = 'lcnetwork'
        cidr = '10.11.0.0/16'
        network = self.driver.ex_create_network(network_name, cidr)
        self.assertTrue(isinstance(network, GCENetwork))
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, cidr)

    def test_create_node_req(self):
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        location = self.driver.zone
        network = self.driver.ex_get_network('default')
        tags = ['libcloud']
        metadata = [{'key': 'test_key', 'value': 'test_value'}]
        boot_disk = self.driver.ex_get_volume('lcdisk')
        node_request, node_data = self.driver._create_node_req('lcnode', size,
                                                               image, location,
                                                               network, tags,
                                                               metadata,
                                                               boot_disk)
        self.assertEqual(node_request, '/zones/%s/instances' % location.name)
        self.assertEqual(node_data['metadata'][0]['key'], 'test_key')
        self.assertEqual(node_data['tags']['items'][0], 'libcloud')
        self.assertEqual(node_data['name'], 'lcnode')
        self.assertTrue(node_data['disks'][0]['boot'])
        self.assertIsInstance(node_data['serviceAccounts'], list)
        self.assertIsInstance(node_data['serviceAccounts'][0], dict)
        self.assertTrue(node_data['serviceAccounts'][0]['email'], 'default')
        self.assertIsInstance(node_data['serviceAccounts'][0]['scopes'], list)
        self.assertTrue(len(node_data['serviceAccounts'][0]['scopes']), 1)

    def test_create_node(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        node = self.driver.create_node(node_name, size, image)
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.name, node_name)

    def test_create_node_req_with_serviceaccounts(self):
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        location = self.driver.zone
        network = self.driver.ex_get_network('default')
        # ex_service_accounts with specific scopes, default 'email'
        ex_sa = [{'scopes': ['compute-ro', 'pubsub', 'storage-ro']}]
        node_request, node_data = self.driver._create_node_req('lcnode', size,
                                                               image, location,
                                                               network,
                                                               ex_service_accounts=ex_sa)
        self.assertIsInstance(node_data['serviceAccounts'], list)
        self.assertIsInstance(node_data['serviceAccounts'][0], dict)
        self.assertTrue(node_data['serviceAccounts'][0]['email'], 'default')
        self.assertIsInstance(node_data['serviceAccounts'][0]['scopes'], list)
        self.assertTrue(len(node_data['serviceAccounts'][0]['scopes']), 3)
        self.assertTrue('https://www.googleapis.com/auth/devstorage.read_only'
                        in node_data['serviceAccounts'][0]['scopes'])
        self.assertTrue('https://www.googleapis.com/auth/compute.readonly'
                        in node_data['serviceAccounts'][0]['scopes'])

    def test_create_node_with_metadata(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')

        self.driver._create_node_req = Mock()
        self.driver._create_node_req.return_value = (None, None)
        self.driver.connection.async_request = Mock()
        self.driver.ex_get_node = Mock()

        # ex_metadata doesn't contain "items" key
        ex_metadata = {'key1': 'value1', 'key2': 'value2'}
        self.driver.create_node(node_name, size, image,
                                ex_metadata=ex_metadata)

        actual = self.driver._create_node_req.call_args[0][6]
        self.assertTrue('items' in actual)
        self.assertEqual(len(actual['items']), 2)

        # ex_metadata contains "items" key
        ex_metadata = {'items': [{'key0': 'value0'}]}
        self.driver.create_node(node_name, size, image,
                                ex_metadata=ex_metadata)
        actual = self.driver._create_node_req.call_args[0][6]
        self.assertTrue('items' in actual)
        self.assertEqual(len(actual['items']), 1)
        self.assertEqual(actual['items'][0], {'key0': 'value0'})

    def test_create_node_existing(self):
        node_name = 'libcloud-demo-europe-np-node'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1', zone='europe-west1-a')
        self.assertRaises(ResourceExistsError, self.driver.create_node,
                          node_name, size, image, location='europe-west1-a')

    def test_ex_create_multiple_nodes(self):
        base_name = 'lcnode'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        number = 2
        nodes = self.driver.ex_create_multiple_nodes(base_name, size, image,
                                                     number)
        self.assertEqual(len(nodes), 2)
        self.assertTrue(isinstance(nodes[0], Node))
        self.assertTrue(isinstance(nodes[1], Node))
        self.assertEqual(nodes[0].name, '%s-000' % base_name)
        self.assertEqual(nodes[1].name, '%s-001' % base_name)

    def test_ex_create_targetinstance(self):
        targetinstance_name = 'lctargetinstance'
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('node-name', zone)
        targetinstance = self.driver.ex_create_targetinstance(
            targetinstance_name, zone=zone, node=node)
        self.assertEqual(targetinstance.name, targetinstance_name)
        self.assertEqual(targetinstance.zone.name, zone)

    def test_ex_create_targetpool(self):
        targetpool_name = 'lctargetpool'
        region = 'us-central1'
        healthchecks = ['libcloud-lb-demo-healthcheck']
        node1 = self.driver.ex_get_node('libcloud-lb-demo-www-000',
                                        'us-central1-b')
        node2 = self.driver.ex_get_node('libcloud-lb-demo-www-001',
                                        'us-central1-b')
        nodes = [node1, node2]
        targetpool = self.driver.ex_create_targetpool(
            targetpool_name, region=region, healthchecks=healthchecks,
            nodes=nodes)
        self.assertEqual(targetpool.name, targetpool_name)
        self.assertEqual(len(targetpool.nodes), len(nodes))
        self.assertEqual(targetpool.region.name, region)

    def test_ex_create_targetpool_session_affinity(self):
        targetpool_name = 'lctargetpool-sticky'
        region = 'us-central1'
        session_affinity = 'CLIENT_IP_PROTO'
        targetpool = self.driver.ex_create_targetpool(
            targetpool_name, region=region,
            session_affinity=session_affinity)
        self.assertEqual(targetpool.name, targetpool_name)
        self.assertEqual(targetpool.extra.get('sessionAffinity'),
                         session_affinity)

    def test_ex_create_volume_snapshot(self):
        snapshot_name = 'lcsnapshot'
        volume = self.driver.ex_get_volume('lcdisk')
        snapshot = volume.snapshot(snapshot_name)
        self.assertEqual(snapshot.name, snapshot_name)
        self.assertEqual(snapshot.size, '10')

    def test_create_volume_ssd(self):
        volume_name = 'lcdisk'
        size = 10
        volume = self.driver.create_volume(size, volume_name,
                                           ex_disk_type='pd-ssd')
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.extra['type'], 'pd-ssd')

    def test_create_volume(self):
        volume_name = 'lcdisk'
        size = 10
        volume = self.driver.create_volume(size, volume_name)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

    def test_ex_update_healthcheck(self):
        healthcheck_name = 'lchealthcheck'
        healthcheck = self.driver.ex_get_healthcheck(healthcheck_name)
        healthcheck.port = 9000
        healthcheck2 = self.driver.ex_update_healthcheck(healthcheck)
        self.assertTrue(isinstance(healthcheck2, GCEHealthCheck))

    def test_ex_update_firewall(self):
        firewall_name = 'lcfirewall'
        firewall = self.driver.ex_get_firewall(firewall_name)
        firewall.source_ranges = ['10.0.0.0/16']
        firewall.source_tags = ['libcloud', 'test']
        firewall2 = self.driver.ex_update_firewall(firewall)
        self.assertTrue(isinstance(firewall2, GCEFirewall))

    def test_ex_targetpool_gethealth(self):
        targetpool = self.driver.ex_get_targetpool('lb-pool')
        health = targetpool.get_health('libcloud-lb-demo-www-000')
        self.assertEqual(len(health), 1)
        self.assertTrue('node' in health[0])
        self.assertTrue('health' in health[0])
        self.assertEqual(health[0]['health'], 'UNHEALTHY')

    def test_ex_targetpool_with_backup_pool(self):
        targetpool = self.driver.ex_get_targetpool('lb-pool')
        self.assertTrue('backupPool' in targetpool.extra)
        self.assertTrue('failoverRatio' in targetpool.extra)

    def test_ex_targetpool_setbackup(self):
        targetpool = self.driver.ex_get_targetpool('lb-pool')
        backup_targetpool = self.driver.ex_get_targetpool('backup-pool')
        self.assertTrue(targetpool.set_backup_targetpool(backup_targetpool,
                                                         0.1))

    def test_ex_targetpool_remove_add_node(self):
        targetpool = self.driver.ex_get_targetpool('lctargetpool')
        node = self.driver.ex_get_node('libcloud-lb-demo-www-001',
                                       'us-central1-b')
        remove_node = self.driver.ex_targetpool_remove_node(targetpool, node)
        self.assertTrue(remove_node)
        self.assertEqual(len(targetpool.nodes), 1)

        add_node = self.driver.ex_targetpool_add_node(targetpool, node.extra['selfLink'])
        self.assertTrue(add_node)
        self.assertEqual(len(targetpool.nodes), 2)

        remove_node = self.driver.ex_targetpool_remove_node(targetpool, node.extra['selfLink'])
        self.assertTrue(remove_node)
        self.assertEqual(len(targetpool.nodes), 1)

        add_node = self.driver.ex_targetpool_add_node(targetpool, node)
        self.assertTrue(add_node)
        self.assertEqual(len(targetpool.nodes), 2)

        # check that duplicates are filtered
        add_node = self.driver.ex_targetpool_add_node(targetpool, node.extra['selfLink'])
        self.assertTrue(add_node)
        self.assertEqual(len(targetpool.nodes), 2)

    def test_ex_targetpool_remove_add_healthcheck(self):
        targetpool = self.driver.ex_get_targetpool('lctargetpool')
        healthcheck = self.driver.ex_get_healthcheck(
            'libcloud-lb-demo-healthcheck')
        remove_healthcheck = self.driver.ex_targetpool_remove_healthcheck(
            targetpool, healthcheck)
        self.assertTrue(remove_healthcheck)
        self.assertEqual(len(targetpool.healthchecks), 0)

        add_healthcheck = self.driver.ex_targetpool_add_healthcheck(
            targetpool, healthcheck)
        self.assertTrue(add_healthcheck)
        self.assertEqual(len(targetpool.healthchecks), 1)

    def test_reboot_node(self):
        node = self.driver.ex_get_node('node-name')
        reboot = self.driver.reboot_node(node)
        self.assertTrue(reboot)

    def test_ex_set_node_tags(self):
        new_tags = ['libcloud']
        node = self.driver.ex_get_node('node-name')
        set_tags = self.driver.ex_set_node_tags(node, new_tags)
        self.assertTrue(set_tags)

    def test_attach_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        node = self.driver.ex_get_node('node-name')
        attach = volume.attach(node)
        self.assertTrue(attach)

    def test_detach_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        node = self.driver.ex_get_node('node-name')
        # This fails since the node is required
        detach = volume.detach()
        self.assertFalse(detach)
        # This should pass
        detach = self.driver.detach_volume(volume, node)
        self.assertTrue(detach)

    def test_ex_destroy_address_global(self):
        address = self.driver.ex_get_address('lcaddressglobal', 'global')
        self.assertTrue(address.name, 'lcaddressglobal')
        self.assertTrue(address.region, 'global')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_address(self):
        address = self.driver.ex_get_address('lcaddress')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_healthcheck(self):
        hc = self.driver.ex_get_healthcheck('lchealthcheck')
        destroyed = hc.destroy()
        self.assertTrue(destroyed)

    def test_ex_delete_image(self):
        image = self.driver.ex_get_image('debian-7')
        deleted = self.driver.ex_delete_image(image)
        self.assertTrue(deleted)

    def test_ex_deprecate_image(self):
        dep_ts = '2064-03-11T20:18:36.194-07:00'
        obs_ts = '2074-03-11T20:18:36.194-07:00'
        del_ts = '2084-03-11T20:18:36.194-07:00'
        image = self.driver.ex_get_image('debian-6-squeeze-v20130926')
        deprecated = image.deprecate('debian-7', 'DEPRECATED',
                                     deprecated=dep_ts,
                                     obsolete=obs_ts,
                                     deleted=del_ts)
        self.assertTrue(deprecated)
        self.assertTrue(image.extra['deprecated']['deprecated'], dep_ts)
        self.assertTrue(image.extra['deprecated']['obsolete'], obs_ts)
        self.assertTrue(image.extra['deprecated']['deleted'], del_ts)

    def test_ex_destroy_firewall(self):
        firewall = self.driver.ex_get_firewall('lcfirewall')
        destroyed = firewall.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_forwarding_rule(self):
        fwr = self.driver.ex_get_forwarding_rule('lcforwardingrule')
        destroyed = fwr.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_route(self):
        route = self.driver.ex_get_route('lcdemoroute')
        destroyed = route.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_network(self):
        network = self.driver.ex_get_network('lcnetwork')
        destroyed = network.destroy()
        self.assertTrue(destroyed)

    def test_destroy_node(self):
        node = self.driver.ex_get_node('node-name')
        destroyed = node.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_multiple_nodes(self):
        nodes = []
        nodes.append(self.driver.ex_get_node('lcnode-000'))
        nodes.append(self.driver.ex_get_node('lcnode-001'))
        destroyed = self.driver.ex_destroy_multiple_nodes(nodes)
        for d in destroyed:
            self.assertTrue(d)

    def test_destroy_targetinstance(self):
        targetinstance = self.driver.ex_get_targetinstance('lctargetinstance')
        self.assertEqual(targetinstance.name, 'lctargetinstance')
        destroyed = targetinstance.destroy()
        self.assertTrue(destroyed)

    def test_destroy_targetpool(self):
        targetpool = self.driver.ex_get_targetpool('lctargetpool')
        destroyed = targetpool.destroy()
        self.assertTrue(destroyed)

    def test_destroy_volume(self):
        disk = self.driver.ex_get_volume('lcdisk')
        destroyed = disk.destroy()
        self.assertTrue(destroyed)

    def test_ex_set_volume_auto_delete(self):
        node = self.driver.ex_get_node('node-name')
        volume = node.extra['boot_disk']
        auto_delete = self.driver.ex_set_volume_auto_delete(
            volume, node)
        self.assertTrue(auto_delete)

    def test_destroy_volume_snapshot(self):
        snapshot = self.driver.ex_get_snapshot('lcsnapshot')
        destroyed = snapshot.destroy()
        self.assertTrue(destroyed)

    def test_ex_get_address_global(self):
        address_name = 'lcaddressglobal'
        address = self.driver.ex_get_address(address_name, 'global')
        self.assertEqual(address.name, address_name)
        self.assertEqual(address.address, '173.99.99.99')
        self.assertEqual(address.region, 'global')
        self.assertEqual(address.extra['status'], 'RESERVED')

    def test_ex_get_address(self):
        address_name = 'lcaddress'
        address = self.driver.ex_get_address(address_name)
        self.assertEqual(address.name, address_name)
        self.assertEqual(address.address, '173.255.113.20')
        self.assertEqual(address.region.name, 'us-central1')
        self.assertEqual(address.extra['status'], 'RESERVED')

    def test_ex_get_backend_service(self):
        web_service = self.driver.ex_get_backend_service('web-service')
        self.assertEqual(web_service.name, 'web-service')
        self.assertEqual(web_service.protocol, 'HTTP')
        self.assertEqual(web_service.port, 80)
        self.assertEqual(web_service.timeout, 30)
        self.assertEqual(web_service.healthchecks[0].name, 'basic-check')
        self.assertEqual(len(web_service.healthchecks), 1)
        backends = web_service.backends
        self.assertEqual(len(backends), 2)
        self.assertEqual(backends[0]['balancingMode'], 'RATE')
        self.assertEqual(backends[0]['maxRate'], 100)
        self.assertEqual(backends[0]['capacityScaler'], 1.0)

        web_service = self.driver.ex_get_backend_service('no-backends')
        self.assertEqual(web_service.name, 'web-service')
        self.assertEqual(web_service.healthchecks[0].name, 'basic-check')
        self.assertEqual(len(web_service.healthchecks), 1)
        self.assertEqual(len(web_service.backends), 0)

    def test_ex_get_healthcheck(self):
        healthcheck_name = 'lchealthcheck'
        healthcheck = self.driver.ex_get_healthcheck(healthcheck_name)
        self.assertEqual(healthcheck.name, healthcheck_name)
        self.assertEqual(healthcheck.port, 8000)
        self.assertEqual(healthcheck.path, '/lc')

    def test_ex_get_firewall(self):
        firewall_name = 'lcfirewall'
        firewall = self.driver.ex_get_firewall(firewall_name)
        self.assertEqual(firewall.name, firewall_name)
        self.assertEqual(firewall.network.name, 'default')
        self.assertEqual(firewall.source_tags, ['libcloud'])

    def test_ex_get_forwarding_rule(self):
        fwr_name = 'lcforwardingrule'
        fwr = self.driver.ex_get_forwarding_rule(fwr_name)
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.extra['portRange'], '8000-8500')
        self.assertEqual(fwr.targetpool.name, 'lctargetpool')
        self.assertEqual(fwr.protocol, 'TCP')

    def test_ex_get_forwarding_rule_global(self):
        fwr_name = 'http-rule'
        fwr = self.driver.ex_get_forwarding_rule(fwr_name, global_rules=True)
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.extra['portRange'], '80-80')
        self.assertEqual(fwr.targetpool.name, 'web-proxy')
        self.assertEqual(fwr.protocol, 'TCP')
        self.assertEqual(fwr.address, '192.0.2.1')
        self.assertEqual(fwr.targetpool.name, 'web-proxy')

    def test_ex_get_image_license(self):
        image = self.driver.ex_get_image('sles-12-v20141023')
        self.assertTrue('licenses' in image.extra)
        self.assertTrue(image.extra['licenses'][0].name, 'sles-12')
        self.assertTrue(image.extra['licenses'][0].charges_use_fee)

    def test_ex_get_image(self):
        partial_name = 'debian-7'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-7-wheezy-v20130617')
        # A 'debian-7' image exists in the local project
        self.assertTrue(image.extra['description'].startswith('Local'))

        partial_name = 'debian-6'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-6-squeeze-v20130926')
        self.assertTrue(image.extra['description'].startswith('Debian'))

        partial_name = 'debian-7'
        image = self.driver.ex_get_image(partial_name, ['debian-cloud'])
        self.assertEqual(image.name, 'debian-7-wheezy-v20131120')

    def test_ex_copy_image(self):
        name = 'coreos'
        url = 'gs://storage.core-os.net/coreos/amd64-generic/247.0.0/coreos_production_gce.tar.gz'
        description = 'CoreOS test image'
        image = self.driver.ex_copy_image(name, url, description)
        self.assertEqual(image.name, name)
        self.assertEqual(image.extra['description'], description)

    def test_ex_get_route(self):
        route_name = 'lcdemoroute'
        route = self.driver.ex_get_route(route_name)
        self.assertEqual(route.name, route_name)
        self.assertEqual(route.dest_range, '192.168.25.0/24')
        self.assertEqual(route.priority, 1000)

    def test_ex_get_network(self):
        network_name = 'lcnetwork'
        network = self.driver.ex_get_network(network_name)
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, '10.11.0.0/16')
        self.assertEqual(network.extra['gatewayIPv4'], '10.11.0.1')
        self.assertEqual(network.extra['description'], 'A custom network')

    def test_ex_get_node(self):
        node_name = 'node-name'
        zone = 'us-central1-a'
        node = self.driver.ex_get_node(node_name, zone)
        self.assertEqual(node.name, node_name)
        self.assertEqual(node.size, 'n1-standard-1')
        removed_node = 'libcloud-lb-demo-www-002'
        self.assertRaises(ResourceNotFoundError, self.driver.ex_get_node,
                          removed_node, 'us-central1-b')
        missing_node = 'dummy-node'
        self.assertRaises(ResourceNotFoundError, self.driver.ex_get_node,
                          missing_node, 'all')

    def test_ex_get_project(self):
        project = self.driver.ex_get_project()
        self.assertEqual(project.name, 'project_name')
        networks_quota = project.quotas[1]
        self.assertEqual(networks_quota['usage'], 3)
        self.assertEqual(networks_quota['limit'], 5)
        self.assertEqual(networks_quota['metric'], 'NETWORKS')
        self.assertTrue('fingerprint' in project.extra['commonInstanceMetadata'])
        self.assertTrue('items' in project.extra['commonInstanceMetadata'])
        self.assertTrue('usageExportLocation' in project.extra)
        self.assertTrue('bucketName' in project.extra['usageExportLocation'])
        self.assertTrue(project.extra['usageExportLocation']['bucketName'], 'gs://graphite-usage-reports')

    def test_ex_set_usage_export_bucket(self):
        self.assertRaises(ValueError,
                          self.driver.ex_set_usage_export_bucket, 'foo')
        bucket_name = 'gs://foo'
        self.driver.ex_set_usage_export_bucket(bucket_name)

        bucket_name = 'https://www.googleapis.com/foo'
        self.driver.ex_set_usage_export_bucket(bucket_name)

    def test__set_project_metadata(self):
        self.assertEqual(len(self.driver._set_project_metadata(None, False, "")), 0)

        # 'delete' metadata, but retain current sshKeys
        md = self.driver._set_project_metadata(None, False, "this is a test")
        self.assertEqual(len(md), 1)
        self.assertEqual(md[0]['key'], 'sshKeys')
        self.assertEqual(md[0]['value'], 'this is a test')

        # 'delete' metadata *and* any existing sshKeys
        md = self.driver._set_project_metadata(None, True, "this is a test")
        self.assertEqual(len(md), 0)

        # add new metadata, keep existing sshKeys, since the new value also
        # has 'sshKeys', we want the final struct to only have one ke/value
        # of sshKeys and it should be the "current_keys"
        gce_md = {'items': [{'key': 'foo', 'value': 'one'},
                            {'key': 'sshKeys', 'value': 'another test'}]}
        md = self.driver._set_project_metadata(gce_md, False, "this is a test")
        self.assertEqual(len(md), 2, str(md))
        sshKeys = ""
        count = 0
        for d in md:
            if d['key'] == 'sshKeys':
                count += 1
                sshKeys = d['value']
        self.assertEqual(sshKeys, 'this is a test')
        self.assertEqual(count, 1)

        # add new metadata, overwrite existing sshKeys, in this case, the
        # existing 'sshKeys' value should be replaced
        gce_md = {'items': [{'key': 'foo', 'value': 'one'},
                            {'key': 'sshKeys', 'value': 'another test'}]}
        md = self.driver._set_project_metadata(gce_md, True, "this is a test")
        self.assertEqual(len(md), 2, str(md))
        sshKeys = ""
        count = 0
        for d in md:
            if d['key'] == 'sshKeys':
                count += 1
                sshKeys = d['value']
        self.assertEqual(sshKeys, 'another test')
        self.assertEqual(count, 1)

        # add new metadata, remove existing sshKeys. in this case, we had an
        # 'sshKeys' entry, but it will be removed entirely
        gce_md = {'items': [{'key': 'foo', 'value': 'one'},
                            {'key': 'nokeys', 'value': 'two'}]}
        md = self.driver._set_project_metadata(gce_md, True, "this is a test")
        self.assertEqual(len(md), 2, str(md))
        sshKeys = ""
        count = 0
        for d in md:
            if d['key'] == 'sshKeys':
                count += 1
                sshKeys = d['value']
        self.assertEqual(sshKeys, '')
        self.assertEqual(count, 0)

    def test_ex_set_common_instance_metadata(self):
        # test non-dict
        self.assertRaises(ValueError,
                          self.driver.ex_set_common_instance_metadata,
                          ['bad', 'type'])
        # test standard python dict
        pydict = {'foo': 'pydict', 'one': 1}
        self.driver.ex_set_common_instance_metadata(pydict)
        # test GCE badly formatted dict
        bad_gcedict = {'items': 'foo'}
        self.assertRaises(ValueError,
                          self.driver.ex_set_common_instance_metadata,
                          bad_gcedict)
        # test gce formatted dict
        gcedict = {'items': [{'key': 'gcedict', 'value': 'v1'},
                             {'key': 'gcedict', 'value': 'v2'}]}
        self.driver.ex_set_common_instance_metadata(gcedict)

    def test_ex_get_region(self):
        region_name = 'us-central1'
        region = self.driver.ex_get_region(region_name)
        self.assertEqual(region.name, region_name)
        self.assertEqual(region.status, 'UP')
        self.assertEqual(region.zones[0].name, 'us-central1-a')

    def test_ex_get_size(self):
        size_name = 'n1-standard-1'
        size = self.driver.ex_get_size(size_name)
        self.assertEqual(size.name, size_name)
        self.assertEqual(size.extra['zone'].name, 'us-central1-a')
        self.assertEqual(size.disk, 10)
        self.assertEqual(size.ram, 3840)
        self.assertEqual(size.extra['guestCpus'], 1)

    def test_ex_get_targetinstance(self):
        targetinstance_name = 'lctargetinstance'
        targetinstance = self.driver.ex_get_targetinstance(targetinstance_name)
        self.assertEqual(targetinstance.name, targetinstance_name)
        self.assertEqual(targetinstance.zone.name, 'us-central1-a')

    def test_ex_get_targetpool(self):
        targetpool_name = 'lctargetpool'
        targetpool = self.driver.ex_get_targetpool(targetpool_name)
        self.assertEqual(targetpool.name, targetpool_name)
        self.assertEqual(len(targetpool.nodes), 2)
        self.assertEqual(targetpool.region.name, 'us-central1')

    def test_ex_get_snapshot(self):
        snapshot_name = 'lcsnapshot'
        snapshot = self.driver.ex_get_snapshot(snapshot_name)
        self.assertEqual(snapshot.name, snapshot_name)
        self.assertEqual(snapshot.size, '10')
        self.assertEqual(snapshot.status, 'READY')

    def test_ex_get_target_http_proxy(self):
        target_http_proxy_name = 'web-proxy'
        target_http_proxy = self.driver.ex_get_target_http_proxy(
            target_http_proxy_name)
        self.assertEqual(target_http_proxy.name, target_http_proxy_name)
        self.assertEqual(target_http_proxy.url_map.name, 'web-map')

    def test_ex_get_url_map(self):
        url_map_name = 'web-map'
        url_map = self.driver.ex_get_url_map(url_map_name)
        self.assertEqual(url_map.name, url_map_name)
        self.assertEqual(url_map.default_service.name, 'web-service')

    def test_ex_get_volume(self):
        volume_name = 'lcdisk'
        volume = self.driver.ex_get_volume(volume_name)
        self.assertEqual(volume.name, volume_name)
        self.assertEqual(volume.size, '10')
        self.assertEqual(volume.extra['status'], 'READY')
        self.assertEqual(volume.extra['type'], 'pd-ssd')

    def test_ex_get_disktype(self):
        disktype_name = 'pd-ssd'
        disktype_zone = 'us-central1-a'
        disktype = self.driver.ex_get_disktype(disktype_name, disktype_zone)
        self.assertEqual(disktype.name, disktype_name)
        self.assertEqual(disktype.zone.name, disktype_zone)
        self.assertEqual(disktype.extra['description'], 'SSD Persistent Disk')
        self.assertEqual(disktype.extra['valid_disk_size'], '10GB-10240GB')
        self.assertEqual(disktype.extra['default_disk_size_gb'], '100')

    def test_ex_get_zone(self):
        zone_name = 'us-central1-b'
        zone = self.driver.ex_get_zone(zone_name)
        self.assertEqual(zone.name, zone_name)
        self.assertFalse(zone.time_until_mw)
        self.assertFalse(zone.next_mw_duration)

        zone_no_mw = self.driver.ex_get_zone('us-central1-a')
        self.assertEqual(zone_no_mw.time_until_mw, None)


class GCEMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('gce')
    json_hdr = {'content-type': 'application/json; charset=UTF-8'}

    def _get_method_name(self, type, use_param, qs, path):
        api_path = '/compute/%s' % API_VERSION
        project_path = '/projects/%s' % GCE_KEYWORD_PARAMS['project']
        path = path.replace(api_path, '')
        # This replace is separate, since there is a call with a different
        # project name
        path = path.replace(project_path, '')
        # The path to get project information is the base path, so use a fake
        # '/project' path instead
        if not path:
            path = '/project'
        method_name = super(GCEMockHttp, self)._get_method_name(type,
                                                                use_param,
                                                                qs, path)
        return method_name

    def _setUsageExportBucket(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('setUsageExportBucket_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _setCommonInstanceMetadata(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('setCommonInstanceMetadata_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_addresses(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_diskTypes(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_disktypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_disks(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_disks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_forwardingRules(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_forwardingRules.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_instances(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_machineTypes(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_machineTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_targetInstances(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_targetInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_targetPools(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_targetPools.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_backendServices(self, method, url, body, headers):
        body = self.fixtures.load('global_backendServices-%s.json' %
                                  self.test.backend_services_mock)
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_backendServices_no_backends(self, method, url, body, headers):
        body = self.fixtures.load('global_backendServices_no_backends.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_backendServices_web_service(self, method, url, body, headers):
        body = self.fixtures.load('global_backendServices_web_service.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_forwardingRules(self, method, url, body, headers):
        body = self.fixtures.load('global_forwardingRules.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_forwardingRules_http_rule(self, method, url, body, headers):
        body = self.fixtures.load('global_forwardingRules_http_rule.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_httpHealthChecks_post.json')
        else:
            body = self.fixtures.load('global_httpHealthChecks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks_default_health_check(self, method, url, body, headers):
        body = self.fixtures.load('global_httpHealthChecks_basic-check.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks_basic_check(self, method, url, body, headers):
        body = self.fixtures.load('global_httpHealthChecks_basic-check.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks_libcloud_lb_demo_healthcheck(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'global_httpHealthChecks_libcloud-lb-demo-healthcheck.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks_lchealthcheck(self, method, url, body,
                                               headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_httpHealthChecks_lchealthcheck_delete.json')
        elif method == 'PUT':
            body = self.fixtures.load(
                'global_httpHealthChecks_lchealthcheck_put.json')
        else:
            body = self.fixtures.load(
                'global_httpHealthChecks_lchealthcheck.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_firewalls(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_firewalls_post.json')
        else:
            body = self.fixtures.load('global_firewalls.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_firewalls_lcfirewall(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_firewalls_lcfirewall_delete.json')
        elif method == 'PUT':
            body = self.fixtures.load('global_firewalls_lcfirewall_put.json')
        else:
            body = self.fixtures.load('global_firewalls_lcfirewall.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_images_post.json')
        else:
            body = self.fixtures.load('global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images_debian_7_wheezy_v20130617(
            self, method, url, body, headers):
        body = self.fixtures.load('global_images_debian_7_wheezy_v20130617_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images_debian_6_squeeze_v20130926_deprecate(
            self, method, url, body, headers):
        body = self.fixtures.load('global_images_debian_6_squeeze_v20130926_deprecate.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_routes(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_routes_post.json')
        else:
            body = self.fixtures.load('global_routes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_networks_post.json')
        else:
            body = self.fixtures.load('global_networks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_default(self, method, url, body, headers):
        body = self.fixtures.load('global_networks_default.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_libcloud_demo_network(self, method, url, body,
                                               headers):
        body = self.fixtures.load('global_networks_libcloud-demo-network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_libcloud_demo_europe_network(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'global_networks_libcloud-demo-europe-network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_routes_lcdemoroute(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('global_routes_lcdemoroute_delete.json')
        else:
            body = self.fixtures.load('global_routes_lcdemoroute.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_lcnetwork(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('global_networks_lcnetwork_delete.json')
        else:
            body = self.fixtures.load('global_networks_lcnetwork.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_snapshots(self, method, url, body, headers):
        body = self.fixtures.load('global_snapshots.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_snapshots_lcsnapshot(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_snapshots_lcsnapshot_delete.json')
        else:
            body = self.fixtures.load('global_snapshots_lcsnapshot.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_setUsageExportBucket(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_setUsageExportBucket.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_setCommonInstanceMetadata(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_setCommonInstanceMetadata.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_httpHealthChecks_lchealthcheck_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_httpHealthChecks_lchealthcheck_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_images_debian7_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_images_debian7_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_httpHealthChecks_lchealthcheck_put(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_httpHealthChecks_lchealthcheck_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_httpHealthChecks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_httpHealthChecks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_lcfirewall_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_lcfirewall_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_lcfirewall_put(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_lcfirewall_put.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_routes_lcdemoroute_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_routes_lcdemoroute_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_networks_lcnetwork_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_networks_lcnetwork_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_routes_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_routes_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_networks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_networks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_snapshots_lcsnapshot_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_snapshots_lcsnapshot_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_image_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_image_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_addresses_lcaddressglobal_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_addresses_lcaddressglobal_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_targetHttpProxies(self, method, url, body, headers):
        body = self.fixtures.load('global_targetHttpProxies.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_targetHttpProxies_web_proxy(self, method, url, body, headers):
        body = self.fixtures.load('global_targetHttpProxies_web_proxy.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_urlMaps(self, method, url, body, headers):
        body = self.fixtures.load('global_urlMaps.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_urlMaps_web_map(self, method, url, body, headers):
        body = self.fixtures.load('global_urlMaps_web_map.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_lcaddress_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_lcaddress_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_addresses_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_addresses_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_forwardingRules_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_forwardingRules_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_forwardingRules_lcforwardingrule_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_forwardingRules_lcforwardingrule_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_targetInstances_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_targetInstances_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_targetInstances_lctargetinstance_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_targetInstances_lctargetinstance_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lctargetpool_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lctargetpool_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lctargetpool_removeHealthCheck_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lctargetpool_removeHealthCheck_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lctargetpool_addHealthCheck_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lctargetpool_addHealthCheck_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lctargetpool_removeInstance_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lctargetpool_removeInstance_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lb_pool_setBackup_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lb_pool_setBackup_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_targetPools_lctargetpool_addInstance_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_targetPools_lctargetpool_addInstance_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_lcdisk_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_lcdisk_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setDiskAutoDelete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_node_name_setDiskAutoDelete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_volume_auto_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us_central1_a_operations_operation_volume_auto_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_lcdisk_createSnapshot_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_lcdisk_createSnapshot_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_lcnode_000_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_lcnode-000_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_lcnode_001_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_lcnode-001_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_attachDisk_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_attachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_detachDisk_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_detachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_setTags_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_setTags_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_reset_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_reset_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_operations_operation_zones_europe_west1_a_instances_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_europe-west1-a_instances_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _project(self, method, url, body, headers):
        body = self.fixtures.load('project.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_licenses_sles_11(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-cloud_global_licenses_sles_11.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_licenses_sles_12(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-cloud_global_licenses_sles_12.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_debian_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_debian-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions(self, method, url, body, headers):
        body = self.fixtures.load(
            'regions.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_addresses(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'global_addresses_post.json')
        else:
            body = self.fixtures.load('global_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_addresses(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_addresses_post.json')
        else:
            body = self.fixtures.load('regions_us-central1_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_addresses_lcaddressglobal(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_addresses_lcaddressglobal_delete.json')
        else:
            body = self.fixtures.load('global_addresses_lcaddressglobal.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_addresses_lcaddress(self, method, url, body,
                                                 headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'regions_us-central1_addresses_lcaddress_delete.json')
        else:
            body = self.fixtures.load(
                'regions_us-central1_addresses_lcaddress.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_forwardingRules(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_forwardingRules_post.json')
        else:
            body = self.fixtures.load(
                'regions_us-central1_forwardingRules.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_forwardingRules_libcloud_lb_demo_lb(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_forwardingRules_libcloud-lb-demo-lb.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_forwardingRules_lcforwardingrule(
            self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'regions_us-central1_forwardingRules_lcforwardingrule_delete.json')
        else:
            body = self.fixtures.load(
                'regions_us-central1_forwardingRules_lcforwardingrule.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_targetInstances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_targetInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_targetPools_post.json')
        else:
            body = self.fixtures.load('regions_us-central1_targetPools.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_targetInstances_lctargetinstance(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances_lctargetinstance_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances_lctargetinstance.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lb_pool_getHealth(self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lb_pool_getHealth.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lb_pool(self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lb_pool.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool(self, method, url,
                                                      body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'regions_us-central1_targetPools_lctargetpool_delete.json')
        else:
            body = self.fixtures.load(
                'regions_us-central1_targetPools_lctargetpool.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool_sticky(self, method, url,
                                                             body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lctargetpool_sticky.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_backup_pool(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_backup_pool.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_libcloud_lb_demo_lb_tp(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_libcloud-lb-demo-lb-tp.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool_removeHealthCheck(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lctargetpool_removeHealthCheck_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool_addHealthCheck(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lctargetpool_addHealthCheck_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool_removeInstance(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lctargetpool_removeInstance_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lb_pool_setBackup(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lb_pool_setBackup_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool_addInstance(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lctargetpool_addInstance_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones(self, method, url, body, headers):
        body = self.fixtures.load('zones.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_diskTypes(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('zones_us-central1-a_diskTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_diskTypes_pd_ssd(self, method, url, body, headers):
        if method == 'GET':
            body = self.fixtures.load('zones_us-central1-a_diskTypes_pd_ssd.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('zones_us-central1-a_disks_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_disks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcdisk(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_disks_lcdisk_delete.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_disks_lcdisk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcdisk_createSnapshot(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_disks_lcdisk_createSnapshot_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_node_name(self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcnode_000(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcnode_001(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_000(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_001(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_002(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_boot_disk(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_np_node(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_multiple_nodes_000(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_multiple_nodes_001(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_disks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('zones_us-central1-a_disks_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_disks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_disks_libcloud_demo_europe_np_node(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_disks_libcloud_demo_europe_boot_disk(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_disks_libcloud_demo_europe_multiple_nodes_000(
            self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_instances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_europe-west1-a_instances_post.json')
        else:
            body = self.fixtures.load('zones_europe-west1-a_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name(self, method, url, body,
                                                 headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_node-name_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_node-name.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_attachDisk(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_attachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_detachDisk(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_detachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setTags(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_setTags_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_reset(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_reset_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_lcnode_000(self, method, url, body,
                                                  headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-000_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-000.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_lcnode_001(self, method, url, body,
                                                  headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-001_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-001.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_instances_libcloud_lb_demo_www_000(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instances_libcloud-lb-demo-www-000.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_instances_libcloud_lb_demo_www_001(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instances_libcloud-lb-demo-www-001.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_instances_libcloud_lb_demo_www_002(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instances_libcloud-lb-demo-www-002.json')
        return (httplib.NOT_FOUND, body, self.json_hdr,
                httplib.responses[httplib.NOT_FOUND])

    def _zones_us_central1_a(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-central1-a.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_machineTypes(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-central1-a_machineTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_machineTypes_n1_standard_1(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'zones_europe-west1-a_machineTypes_n1-standard-1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_machineTypes_n1_standard_1(self, method, url,
                                                        body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_machineTypes_n1-standard-1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
