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

import datetime
import mock
import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.gce import (
    GCENodeDriver, API_VERSION, timestamp_to_datetime, GCEAddress, GCEBackend,
    GCEBackendService, GCEFirewall, GCEForwardingRule, GCEHealthCheck,
    GCENetwork, GCENodeImage, GCERoute, GCERegion, GCETargetHttpProxy,
    GCEUrlMap, GCEZone, GCESubnetwork, GCEProject)
from libcloud.common.google import (GoogleBaseAuthConnection,
                                    ResourceNotFoundError, ResourceExistsError,
                                    GoogleBaseError)
from libcloud.test.common.test_google import GoogleAuthMockHttp, GoogleTestCase
from libcloud.compute.base import Node, StorageVolume
from libcloud.compute.types import NodeState

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.secrets import GCE_PARAMS, GCE_KEYWORD_PARAMS


class GCENodeDriverTest(GoogleTestCase, TestCaseMixin):
    """
    Google Compute Engine Test Class.
    """
    # Mock out a few specific calls that interact with the user, system or
    # environment.
    GCEZone._now = lambda x: datetime.datetime(2013, 6, 26, 19, 0, 0)
    datacenter = 'us-central1-a'

    def setUp(self):
        GCEMockHttp.test = self
        GCENodeDriver.connectionCls.conn_class = GCEMockHttp
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        GCEMockHttp.type = None
        kwargs = GCE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        kwargs['datacenter'] = self.datacenter
        self.driver = GCENodeDriver(*GCE_PARAMS, **kwargs)

    def test_default_scopes(self):
        self.assertIsNone(self.driver.scopes)

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
        self.assertEqual(obj.name, 'web-proxy')

    def test_get_region_from_zone(self):
        zone1 = self.driver.ex_get_zone('us-central1-a')
        expected_region1 = 'us-central1'
        region1 = self.driver._get_region_from_zone(zone1)
        self.assertEqual(region1.name, expected_region1)
        zone2 = self.driver.ex_get_zone('europe-west1-b')
        expected_region2 = 'europe-west1'
        region2 = self.driver._get_region_from_zone(zone2)
        self.assertEqual(region2.name, expected_region2)

    def test_get_volume(self):
        volume_name = 'lcdisk'
        volume = self.driver.ex_get_volume(volume_name)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

    def test_get_volume_location(self):
        volume_name = 'lcdisk'
        location = self.driver.zone
        volume = self.driver.ex_get_volume(volume_name, zone=location)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

    def test_get_volume_location_name(self):
        volume_name = 'lcdisk'
        location = self.driver.zone
        volume = self.driver.ex_get_volume(volume_name, zone=location.name)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

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

    def test_build_disk_gce_struct(self):
        device_name = 'disk_name'
        disk_name = None
        source = self.driver.ex_get_volume('lcdisk')
        is_boot = True
        # source as input
        d = self.driver._build_disk_gce_struct(
            device_name=device_name, source=source, disk_name=disk_name,
            is_boot=is_boot)
        self.assertEqual(source.extra['selfLink'], d['source'])
        self.assertTrue(d['boot'])
        self.assertTrue(d['autoDelete'])
        self.assertEqual('READ_WRITE', d['mode'])
        self.assertFalse('initializeParams' in d)

        # image as input
        device_name = 'disk_name'
        disk_type = self.driver.ex_get_disktype('pd-ssd', 'us-central1-a')
        image = self.driver.ex_get_image('debian-7')
        source = None
        is_boot = True
        d = self.driver._build_disk_gce_struct(device_name=device_name,
                                               disk_type=disk_type,
                                               image=image, is_boot=is_boot)
        self.assertEqual('READ_WRITE', d['mode'])
        self.assertEqual('PERSISTENT', d['type'])
        self.assertTrue('initializeParams' in d and
                        isinstance(d['initializeParams'], dict))
        self.assertTrue(
            all(k in d['initializeParams']
                for k in ['sourceImage', 'diskType', 'diskName']))
        self.assertTrue(d['initializeParams']['sourceImage'].startswith(
            'https://'))
        self.assertTrue(d['autoDelete'])
        self.assertTrue(d['boot'])

    def test_build_network_gce_struct(self):
        network = self.driver.ex_get_network('lcnetwork')
        address = self.driver.ex_get_address('lcaddress')
        internalip = self.driver.ex_get_address('testaddress')
        subnetwork_name = 'cf-972cf02e6ad49112'
        subnetwork = self.driver.ex_get_subnetwork(subnetwork_name)
        d = self.driver._build_network_gce_struct(network, subnetwork, address)
        self.assertTrue('network' in d)
        self.assertTrue('subnetwork' in d)
        self.assertTrue('kind' in d and
                        d['kind'] == 'compute#instanceNetworkInterface')
        self.assertEqual(d['accessConfigs'][0]['natIP'], address.address)
        # test with internal IP
        d = self.driver._build_network_gce_struct(network, subnetwork, address,
                                                  internal_ip=internalip)
        self.assertTrue('network' in d)
        self.assertTrue('subnetwork' in d)
        self.assertTrue('kind' in d and
                        d['kind'] == 'compute#instanceNetworkInterface')
        self.assertEqual(d['accessConfigs'][0]['natIP'], address.address)
        self.assertEqual(d['networkIP'], internalip)
        network = self.driver.ex_get_network('default')
        d = self.driver._build_network_gce_struct(network)
        self.assertTrue('network' in d)
        self.assertFalse('subnetwork' in d)
        self.assertTrue('kind' in d and
                        d['kind'] == 'compute#instanceNetworkInterface')

    def test_build_scheduling_gce_struct(self):
        self.assertFalse(
            self.driver._build_scheduling_gce_struct(None, None, None))
        # on_host_maintenance bad value should raise a Valueerror
        self.assertRaises(ValueError,
                          self.driver._build_service_account_gce_struct,
                          'on_host_maintenance="foobar"')
        # on_host_maintenance is 'MIGRATE' and prempt is True
        self.assertRaises(ValueError,
                          self.driver._build_service_account_gce_struct,
                          'on_host_maintenance="MIGRATE"', 'preemptible=True')
        # automatic_restart is True and prempt is  True
        self.assertRaises(ValueError,
                          self.driver._build_service_account_gce_struct,
                          'automatic_restart="True"', 'preemptible=True')

        actual = self.driver._build_scheduling_gce_struct('TERMINATE', True,
                                                          False)
        self.assertTrue('automaticRestart' in actual and
                        actual['automaticRestart'] is True)
        self.assertTrue('onHostMaintenance' in actual and
                        actual['onHostMaintenance'] == 'TERMINATE')
        self.assertTrue('preemptible' in actual)
        self.assertFalse(actual['preemptible'])

    def test_build_service_account_gce_struct(self):
        self.assertRaises(ValueError,
                          self.driver._build_service_account_gce_struct, None)
        input = {'scopes': ['compute-ro']}
        actual = self.driver._build_service_account_gce_struct(input)
        self.assertTrue('email' in actual)
        self.assertTrue('scopes' in actual)

        input = {'scopes': ['compute-ro'], 'email': 'test@test.com'}
        actual = self.driver._build_service_account_gce_struct(input)
        self.assertTrue('email' in actual)
        self.assertEqual(actual['email'], 'test@test.com')
        self.assertTrue('scopes' in actual)

    def test_build_service_account_gce_list(self):
        # ensure we have a list
        self.assertRaises(ValueError,
                          self.driver._build_service_accounts_gce_list, 'foo')
        # no input
        actual = self.driver._build_service_accounts_gce_list()
        self.assertTrue(len(actual) == 1)
        self.assertTrue('email' in actual[0])
        self.assertTrue('scopes' in actual[0])

    def test_get_selflink_or_name(self):
        network = self.driver.ex_get_network('lcnetwork')

        # object as input
        actual = self.driver._get_selflink_or_name(network, False, 'network')
        self.assertEqual('lcnetwork', actual)
        actual = self.driver._get_selflink_or_name(network, True, 'network')
        self.assertTrue(actual.startswith('https://'))

        # name-only as input
        actual = self.driver._get_selflink_or_name('lcnetwork', True,
                                                   'network')
        self.assertTrue(actual.startswith('https://'))

        actual = self.driver._get_selflink_or_name('lcnetwork', False,
                                                   'network')
        self.assertTrue('lcnetwork', actual)

        # if selflinks is true, we need objname
        self.assertRaises(ValueError, self.driver._get_selflink_or_name,
                          'lcnetwork', True)

    def test_ex_get_serial_output(self):
        self.assertRaises(ValueError, self.driver.ex_get_serial_output, 'foo')
        node = self.driver.ex_get_node('node-name', 'us-central1-a')
        self.assertTrue(
            self.driver.ex_get_serial_output(node),
            'This is some serial\r\noutput for you.')

    def test_ex_list(self):
        d = self.driver
        # Test the default case for all list methods
        # (except list_volume_snapshots, which requires an arg)
        for list_fn in (d.ex_list_addresses, d.ex_list_backendservices,
                        d.ex_list_disktypes, d.ex_list_firewalls,
                        d.ex_list_forwarding_rules, d.ex_list_healthchecks,
                        d.ex_list_networks, d.ex_list_subnetworks,
                        d.ex_list_project_images, d.ex_list_regions,
                        d.ex_list_routes, d.ex_list_snapshots,
                        d.ex_list_targethttpproxies, d.ex_list_targetinstances,
                        d.ex_list_targetpools, d.ex_list_urlmaps,
                        d.ex_list_zones, d.list_images, d.list_locations,
                        d.list_nodes, d.list_sizes, d.list_volumes):
            full_list = [item.name for item in list_fn()]
            li = d.ex_list(list_fn)
            iter_list = [item.name for sublist in li for item in sublist]
            self.assertEqual(full_list, iter_list)

        # Test paging & filtering with a single list function as they require
        # additional test fixtures
        list_fn = d.ex_list_regions
        for count, sublist in zip((2, 1), d.ex_list(list_fn).page(2)):
            self.assertTrue(len(sublist) == count)
        for sublist in d.ex_list(list_fn).filter('name eq us-central1'):
            self.assertTrue(len(sublist) == 1)
            self.assertEqual(sublist[0].name, 'us-central1')

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

    def test_ex_list_backendservices(self):
        self.backendservices_mock = 'empty'
        backendservices_list = self.driver.ex_list_backendservices()
        self.assertListEqual(backendservices_list, [])

        self.backendservices_mock = 'web-service'
        backendservices_list = self.driver.ex_list_backendservices()
        web_service = backendservices_list[0]
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
        forwarding_rules = self.driver.ex_list_forwarding_rules(
            global_rules=True)
        self.assertEqual(len(forwarding_rules), 2)
        self.assertEqual(forwarding_rules[0].name, 'http-rule')
        names = [f.name for f in forwarding_rules]
        self.assertListEqual(names, ['http-rule', 'http-rule2'])

    def test_list_images(self):
        local_images = self.driver.list_images()
        all_deprecated_images = self.driver.list_images(
            ex_include_deprecated=True)
        debian_images = self.driver.list_images(ex_project='debian-cloud')
        local_plus_deb = self.driver.list_images(
            ['debian-cloud', 'project_name'])
        self.assertEqual(len(local_images), 50)
        self.assertEqual(len(all_deprecated_images), 178)
        self.assertEqual(len(debian_images), 2)
        self.assertEqual(len(local_plus_deb), 4)
        self.assertEqual(local_images[0].name, 'custom-image')
        self.assertEqual(debian_images[1].name, 'debian-7-wheezy-v20131120')

    def test_ex_destroy_instancegroup(self):
        name = 'myname'
        zone = 'us-central1-a'
        uig = self.driver.ex_get_instancegroup(name, zone)
        self.assertTrue(self.driver.ex_destroy_instancegroup(uig))

    def test_ex_get_instancegroup(self):
        name = 'myname'
        loc = 'us-central1-a'
        actual = self.driver.ex_get_instancegroup(name, loc)
        self.assertEqual(actual.name, name)
        self.assertEqual(actual.zone.name, loc)

    def test_ex_create_instancegroup(self):
        name = 'myname'
        loc = 'us-central1-a'
        actual = self.driver.ex_create_instancegroup(name, loc)
        self.assertEqual(actual.name, name)
        self.assertEqual(actual.zone.name, loc)

    def test_ex_list_instancegroups(self):
        loc = 'us-central1-a'
        actual = self.driver.ex_list_instancegroups(loc)
        self.assertTrue(len(actual) == 2)
        self.assertEqual(actual[0].name, 'myname')
        self.assertEqual(actual[1].name, 'myname2')

    def test_ex_instancegroup_list_instances(self):
        name = 'myname'
        loc = 'us-central1-a'
        gceobj = self.driver.ex_get_instancegroup(name, loc)
        actual = self.driver.ex_instancegroup_list_instances(gceobj)
        self.assertTrue(len(actual) == 2)
        for node in actual:
            self.assertTrue(isinstance(node, Node))
            self.assertEqual(loc, node.extra['zone'].name)

    def test_ex_instancegroup_add_instances(self):
        name = 'myname'
        loc = 'us-central1-a'
        gceobj = self.driver.ex_get_instancegroup(name, loc)
        node_name = self.driver.ex_get_node('node-name', loc)
        lcnode = self.driver.ex_get_node('lcnode-001', loc)
        node_list = [node_name, lcnode]
        self.assertTrue(
            self.driver.ex_instancegroup_add_instances(gceobj, node_list))

    def test_ex_instancegroup_remove_instances(self):
        name = 'myname'
        loc = 'us-central1-a'
        gceobj = self.driver.ex_get_instancegroup(name, loc)
        node_name = self.driver.ex_get_node('node-name', loc)
        lcnode = self.driver.ex_get_node('lcnode-001', loc)
        node_list = [node_name, lcnode]
        self.assertTrue(
            self.driver.ex_instancegroup_remove_instances(gceobj, node_list))

    def test_ex_instancegroup_set_named_ports(self):
        name = 'myname'
        loc = 'us-central1-a'
        gceobj = self.driver.ex_get_instancegroup(name, loc)
        named_ports = [{'name': 'foo', 'port': 4444}]
        # base case
        self.assertTrue(
            self.driver.ex_instancegroup_set_named_ports(gceobj, named_ports))
        # specify nothing, default is empty list
        self.assertTrue(self.driver.ex_instancegroup_set_named_ports(gceobj))
        # specify empty list
        self.assertTrue(
            self.driver.ex_instancegroup_set_named_ports(gceobj, []))
        # raise valueerror if string is passed in
        self.assertRaises(ValueError,
                          self.driver.ex_instancegroup_set_named_ports, gceobj,
                          'foobar')
        # raise valueerror if dictionary is passed in
        self.assertRaises(ValueError,
                          self.driver.ex_instancegroup_set_named_ports, gceobj,
                          {'name': 'foo',
                           'port': 4444})

    def test_ex_instancegroupmanager_set_autohealing_policies(self):
        kwargs = {'host': 'lchost',
                  'path': '/lc',
                  'port': 8000,
                  'interval': 10,
                  'timeout': 10,
                  'unhealthy_threshold': 4,
                  'healthy_threshold': 3,
                  'description': 'test healthcheck'}
        healthcheck_name = 'lchealthcheck'
        hc = self.driver.ex_create_healthcheck(healthcheck_name, **kwargs)

        ig_name = 'myinstancegroup'
        ig_zone = 'us-central1-a'
        manager = self.driver.ex_get_instancegroupmanager(ig_name, ig_zone)

        res = self.driver.ex_instancegroupmanager_set_autohealingpolicies(
            manager=manager, healthcheck=hc, initialdelaysec=2)
        self.assertTrue(res)

        res = manager.set_autohealingpolicies(healthcheck=hc, initialdelaysec=2)
        self.assertTrue(res)

    def test_ex_create_instancegroupmanager(self):
        name = 'myinstancegroup'
        zone = 'us-central1-a'
        size = 4
        template_name = 'my-instance-template1'
        template = self.driver.ex_get_instancetemplate(template_name)
        mig = self.driver.ex_create_instancegroupmanager(
            name, zone, template, size, base_instance_name='base-foo')

        self.assertEqual(mig.name, name)
        self.assertEqual(mig.size, size)
        self.assertEqual(mig.zone.name, zone)

    def test_ex_create_instancegroupmanager_shared_network(self):
        name = 'myinstancegroup-shared-network'
        zone = 'us-central1-a'
        size = 4
        template_name = 'my-instance-template-shared-network'
        template = self.driver.ex_get_instancetemplate(template_name)
        mig = self.driver.ex_create_instancegroupmanager(
            name, zone, template, size, base_instance_name='base-foo')

        self.assertEqual(mig.name, name)
        self.assertEqual(mig.size, size)
        self.assertEqual(mig.zone.name, zone)

    def test_ex_create_instancetemplate(self):
        name = 'my-instance-template1'
        actual = self.driver.ex_create_instancetemplate(
            name, size='n1-standard-1', image='debian-7', network='default')
        self.assertEqual(actual.name, name)
        self.assertEqual(actual.extra['properties']['machineType'],
                         'n1-standard-1')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 6)
        self.assertEqual(locations[0].name, 'asia-east1-a')

    def test_ex_list_routes(self):
        routes = self.driver.ex_list_routes()
        self.assertEqual(len(routes), 3)
        self.assertTrue('lcdemoroute' in [route.name for route in routes])

    def test_ex_list_sslcertificate(self):
        ssl_name = 'example'
        certs = self.driver.ex_list_sslcertificates()
        self.assertEqual(certs[0].name, ssl_name)
        self.assertTrue(len(certs) == 1)

    def test_ex_list_subnetworks(self):
        subnetworks = self.driver.ex_list_subnetworks()
        self.assertEqual(len(subnetworks), 1)
        self.assertEqual(subnetworks[0].name, 'cf-972cf02e6ad49112')
        self.assertEqual(subnetworks[0].cidr, '10.128.0.0/20')
        subnetworks = self.driver.ex_list_subnetworks('all')
        self.assertEqual(len(subnetworks), 4)

    def test_ex_create_sslcertificate(self):
        ssl_name = 'example'
        private_key = '-----BEGIN RSA PRIVATE KEY-----\nfoobar==\n-----END RSA PRIVATE KEY-----\n'
        certificate = '-----BEGIN CERTIFICATE-----\nfoobar==\n-----END CERTIFICATE-----\n'
        ssl = self.driver.ex_create_sslcertificate(
            ssl_name, certificate=certificate, private_key=private_key)
        self.assertEqual(ssl_name, ssl.name)
        self.assertEqual(certificate, ssl.certificate)

    def test_ex_create_subnetwork(self):
        name = 'cf-972cf02e6ad49112'
        cidr = '10.128.0.0/20'
        network_name = 'cf'
        network = self.driver.ex_get_network(network_name)
        region_name = 'us-central1'
        region = self.driver.ex_get_region(region_name)
        description = 'LCTestSubnet'
        privateipgoogleaccess = True
        secondaryipranges = [{"rangeName": "secondary", "ipCidrRange": "192.168.168.0/24"}]
        # test by network/region name
        subnet = self.driver.ex_create_subnetwork(
            name, cidr, network_name, region_name, description=description,
            privateipgoogleaccess=privateipgoogleaccess, secondaryipranges=secondaryipranges)
        self.assertTrue(isinstance(subnet, GCESubnetwork))
        self.assertTrue(isinstance(subnet.region, GCERegion))
        self.assertTrue(isinstance(subnet.network, GCENetwork))
        self.assertEqual(subnet.name, name)
        self.assertEqual(subnet.cidr, cidr)
        self.assertEqual(subnet.extra['privateIpGoogleAccess'], privateipgoogleaccess)
        self.assertEqual(subnet.extra['secondaryIpRanges'], secondaryipranges)
        # test by network/region object
        subnet = self.driver.ex_create_subnetwork(name, cidr, network, region)
        self.assertTrue(isinstance(subnet, GCESubnetwork))
        self.assertTrue(isinstance(subnet.region, GCERegion))
        self.assertTrue(isinstance(subnet.network, GCENetwork))
        self.assertEqual(subnet.name, name)
        self.assertEqual(subnet.cidr, cidr)
        self.assertEqual(subnet.extra['privateIpGoogleAccess'], privateipgoogleaccess)
        self.assertEqual(subnet.extra['secondaryIpRanges'], secondaryipranges)

    def test_ex_destroy_subnetwork(self):
        name = 'cf-972cf02e6ad49112'
        region_name = 'us-central1'
        region = self.driver.ex_get_region(region_name)
        # delete with no region
        self.assertTrue(self.driver.ex_destroy_subnetwork(name))
        # delete with region name
        self.assertTrue(self.driver.ex_destroy_subnetwork(name, region_name))
        # delete with region object
        self.assertTrue(self.driver.ex_destroy_subnetwork(name, region))

    def test_ex_get_sslcertificate(self):
        ssl_name = 'example'
        ssl = self.driver.ex_get_sslcertificate(ssl_name)
        self.assertEqual(ssl.name, ssl_name)
        self.assertTrue(hasattr(ssl, 'certificate'))
        self.assertTrue(len(ssl.certificate))

    def test_ex_get_accelerator_type(self):
        name = 'nvidia-tesla-k80'
        zone = self.driver.ex_get_zone('us-central1-a')
        accelerator_type = self.driver.ex_get_accelerator_type(name, zone)
        self.assertEqual(accelerator_type.name, name)
        self.assertEqual(accelerator_type.zone, zone)

    def test_ex_get_subnetwork(self):
        name = 'cf-972cf02e6ad49112'
        region_name = 'us-central1'
        region = self.driver.ex_get_region(region_name)
        # fetch by no region
        subnetwork = self.driver.ex_get_subnetwork(name)
        self.assertEqual(subnetwork.name, name)
        # fetch by region name
        subnetwork = self.driver.ex_get_subnetwork(name, region_name)
        self.assertEqual(subnetwork.name, name)
        # fetch by region object
        subnetwork = self.driver.ex_get_subnetwork(name, region)
        self.assertEqual(subnetwork.name, name)
        # do the same but this time by resource URL
        url = 'https://www.googleapis.com/compute/v1/projects/project_name/regions/us-central1/subnetworks/cf-972cf02e6ad49112'
        # fetch by no region
        subnetwork = self.driver.ex_get_subnetwork(url)
        self.assertEqual(subnetwork.name, name)
        self.assertEqual(subnetwork.region.name, region_name)
        # test with a subnetwork that is under a different project
        url_other = 'https://www.googleapis.com/compute/v1/projects/other_name/regions/us-central1/subnetworks/cf-972cf02e6ad49114'
        subnetwork = self.driver.ex_get_subnetwork(url_other)
        self.assertEqual(subnetwork.name, "cf-972cf02e6ad49114")

    def test_ex_list_networks(self):
        networks = self.driver.ex_list_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[0].name, 'cf')
        self.assertEqual(networks[0].mode, 'auto')
        self.assertEqual(len(networks[0].subnetworks), 4)
        self.assertEqual(networks[1].name, 'custom')
        self.assertEqual(networks[1].mode, 'custom')
        self.assertEqual(len(networks[1].subnetworks), 1)
        self.assertEqual(networks[2].name, 'default')
        self.assertEqual(networks[2].mode, 'legacy')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        nodes_all = self.driver.list_nodes(ex_zone='all')
        nodes_uc1a = self.driver.list_nodes(ex_zone='us-central1-a')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(nodes_all), 8)
        self.assertEqual(len(nodes_uc1a), 1)
        self.assertEqual(nodes[0].name, 'node-name')
        self.assertEqual(nodes_uc1a[0].name, 'node-name')
        self.assertEqual(nodes_uc1a[0].extra['cpuPlatform'], 'Intel Skylake')
        self.assertEqual(nodes_uc1a[0].extra['minCpuPlatform'], 'Intel Skylake')

        names = [n.name for n in nodes_all]
        self.assertTrue('node-name' in names)

        states = [n.state for n in nodes_all]
        self.assertTrue(NodeState.SUSPENDED in states)

    def test_ex_list_regions(self):
        regions = self.driver.ex_list_regions()
        self.assertEqual(len(regions), 3)
        self.assertEqual(regions[0].name, 'europe-west1')

    def test_ex_list_snapshots(self):
        snapshots = self.driver.ex_list_snapshots()
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].name, 'lcsnapshot')

    def test_ex_list_targethttpproxies(self):
        target_proxies = self.driver.ex_list_targethttpproxies()
        self.assertEqual(len(target_proxies), 2)
        self.assertEqual(target_proxies[0].name, 'web-proxy')
        names = [t.name for t in target_proxies]
        self.assertListEqual(names, ['web-proxy', 'web-proxy2'])

    def test_ex_list_targetinstances(self):
        target_instances = self.driver.ex_list_targetinstances()
        target_instances_all = self.driver.ex_list_targetinstances('all')
        target_instances_uc1 = self.driver.ex_list_targetinstances(
            'us-central1-a')
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
        self.assertEqual(license.name, 'sles-12')
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

    def test_ex_list_instancegroupmanagers(self):
        instancegroupmanagers = self.driver.ex_list_instancegroupmanagers()
        instancegroupmanagers_all = self.driver.ex_list_instancegroupmanagers(
            'all')
        instancegroupmanagers_ue1b = self.driver.ex_list_instancegroupmanagers(
            'us-east1-b')
        self.assertEqual(len(instancegroupmanagers), 1)
        self.assertEqual(len(instancegroupmanagers_all), 2)
        self.assertEqual(len(instancegroupmanagers_ue1b), 1)

    def test_ex_instancegroupmanager_list_managed_instances(self):
        ig_name = 'myinstancegroup'
        ig_zone = 'us-central1-a'
        mig = self.driver.ex_get_instancegroupmanager(ig_name, ig_zone)
        instances = mig.list_managed_instances()
        self.assertTrue(all([x['currentAction'] == 'NONE' for x in instances]))
        self.assertTrue('base-foo-2vld' in [x['name'] for x in instances])
        self.assertEqual(len(instances), 4)

    def test_ex_list_instancetemplates(self):
        instancetemplates = self.driver.ex_list_instancetemplates()
        self.assertEqual(len(instancetemplates), 1)
        self.assertEqual(instancetemplates[0].name, 'my-instance-template1')

    def test_ex_list_autoscalers(self):
        autoscalers = self.driver.ex_list_autoscalers('all')
        self.assertEqual(len(autoscalers), 1)
        self.assertEqual(autoscalers[0].name, 'my-autoscaler')

    def test_ex_list_urlmaps(self):
        urlmaps_list = self.driver.ex_list_urlmaps()
        web_map = urlmaps_list[0]
        self.assertEqual(web_map.name, 'web-map')
        self.assertEqual(len(web_map.host_rules), 0)
        self.assertEqual(len(web_map.path_matchers), 0)
        self.assertEqual(len(web_map.tests), 0)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        volumes_all = self.driver.list_volumes('all')
        volumes_uc1a = self.driver.list_volumes('us-central1-a')
        self.assertEqual(len(volumes), 2)
        self.assertEqual(len(volumes_all), 17)
        self.assertEqual(len(volumes_uc1a), 2)
        self.assertEqual(volumes[0].name, 'lcdisk')
        self.assertEqual(volumes_uc1a[0].name, 'lcdisk')
        names = [v.name for v in volumes_all]
        self.assertTrue('libcloud-demo-europe-boot-disk' in names)

    def test_ex_list_zones(self):
        zones = self.driver.ex_list_zones()
        self.assertEqual(len(zones), 6)
        self.assertEqual(zones[0].name, 'asia-east1-a')

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

    def test_ex_create_address_internal(self):
        address_name = 'lcaddressinternal'
        address = self.driver.ex_create_address(address_name,
                                                region='us-central1',
                                                address='10.128.0.12',
                                                address_type='INTERNAL',
                                                subnetwork='subnet-1')
        self.assertTrue(isinstance(address, GCEAddress))
        self.assertEqual(address.name, address_name)
        self.assertEqual(address.address, '10.128.0.12')

        self.assertRaises(ValueError,
                          self.driver.ex_create_address,
                          address_name, address_type='WRONG')
        self.assertRaises(ValueError,
                          self.driver.ex_create_address,
                          address_name, address_type='EXTERNAL',
                          subnetwork='subnet-1')

    def test_ex_create_backend(self):
        # Note: this is an internal object, no API call is made
        # and no fixture is needed specifically for GCEBackend, however
        # it does rely on an InstanceGroup object.
        ig = self.driver.ex_get_instancegroup('myinstancegroup',
                                              'us-central1-a')

        backend = self.driver.ex_create_backend(ig)

        self.assertTrue(isinstance(backend, GCEBackend))
        self.assertEqual(backend.name,
                         '%s/instanceGroups/%s' % (ig.zone.name, ig.name))
        self.assertEqual(backend.instance_group.name, ig.name)
        self.assertEqual(backend.balancing_mode, 'UTILIZATION')

    def test_ex_create_backendservice(self):
        backendservice_name = 'web-service'

        ig1 = self.driver.ex_get_instancegroup('myinstancegroup',
                                               'us-central1-a')
        backend1 = self.driver.ex_create_backend(ig1)
        ig2 = self.driver.ex_get_instancegroup('myinstancegroup2',
                                               'us-central1-a')
        backend2 = self.driver.ex_create_backend(ig2)

        backendservice = self.driver.ex_create_backendservice(
            name=backendservice_name, healthchecks=['lchealthcheck'],
            backends=[backend1, backend2])
        self.assertTrue(isinstance(backendservice, GCEBackendService))
        self.assertEqual(backendservice.name, backendservice_name)
        self.assertEqual(len(backendservice.backends), 2)
        ig_links = [ig1.extra['selfLink'], ig2.extra['selfLink']]
        for be in backendservice.backends:
            self.assertTrue(be['group'] in ig_links)

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
        description = 'CoreOS, CoreOS stable, 1520.6.0, amd64-usr published on 2017-10-12'
        name = 'coreos'
        family = 'coreos-stable'
        licenses = ["projects/coreos-cloud/global/licenses/coreos-stable"]
        guest_os_features = ['VIRTIO_SCSI_MULTIQUEUE']
        expected_features = [{'type': 'VIRTIO_SCSI_MULTIQUEUE'}]
        mock_request = mock.Mock()
        mock_request.side_effect = self.driver.connection.async_request
        self.driver.connection.async_request = mock_request

        image = self.driver.ex_create_image(
            name, volume, description=description, family=family,
            guest_os_features=guest_os_features, ex_licenses=licenses)
        self.assertTrue(isinstance(image, GCENodeImage))
        self.assertTrue(image.name.startswith(name))
        self.assertEqual(image.extra['description'], description)
        self.assertEqual(image.extra['family'], family)
        self.assertEqual(image.extra['guestOsFeatures'], expected_features)
        self.assertEqual(image.extra['licenses'][0].name, licenses[0].split("/")[-1])
        expected_data = {'description': description,
                         'family': family,
                         'guestOsFeatures': expected_features,
                         'name': name,
                         'licenses': licenses,
                         'sourceDisk': volume.extra['selfLink'],
                         'zone': volume.extra['zone'].name}
        mock_request.assert_called_once_with('/global/images',
                                             data=expected_data, method='POST')

    def test_ex_copy_image(self):
        name = 'coreos'
        url = 'gs://storage.core-os.net/coreos/amd64-generic/247.0.0/coreos_production_gce.tar.gz'
        description = 'CoreOS, CoreOS stable, 1520.6.0, amd64-usr published on 2017-10-12'
        family = 'coreos-stable'
        guest_os_features = ['VIRTIO_SCSI_MULTIQUEUE']
        expected_features = [{'type': 'VIRTIO_SCSI_MULTIQUEUE'}]
        image = self.driver.ex_copy_image(name, url, description=description,
                                          family=family,
                                          guest_os_features=guest_os_features)
        self.assertTrue(image.name.startswith(name))
        self.assertEqual(image.extra['description'], description)
        self.assertEqual(image.extra['family'], family)
        self.assertEqual(image.extra['guestOsFeatures'], expected_features)

    def test_ex_create_firewall(self):
        name = 'lcfirewall'
        priority = 900
        description = "Libcloud Test Firewall"
        allowed = [{'IPProtocol': 'tcp', 'ports': ['4567']}]
        source_service_accounts = ['lcsource@gserviceaccount.com']
        target_tags = ['libcloud']
        network = 'default'
        firewall = self.driver.ex_create_firewall(
            name, allowed, description=description,
            network=network, priority=priority, target_tags=target_tags,
            source_service_accounts=source_service_accounts)
        self.assertTrue(isinstance(firewall, GCEFirewall))
        self.assertEqual(firewall.name, name)

    def test_ex_create_firewall_egress(self):
        name = 'lcfirewall-egress'
        priority = 900
        direction = 'EGRESS'
        description = "Libcloud Egress Firewall"
        allowed = [{'IPProtocol': 'tcp', 'ports': ['4567']}]
        target_service_accounts = ['lctarget@gserviceaccount.com']
        target_ranges = ['8.8.8.8/32']
        network = 'default'
        firewall = self.driver.ex_create_firewall(
            name, allowed,
            description=description, network=network,
            priority=priority, direction=direction,
            target_ranges=target_ranges,
            target_service_accounts=target_service_accounts)
        self.assertTrue(isinstance(firewall, GCEFirewall))
        self.assertEqual(firewall.name, name)

    def test_ex_create_firewall_deny(self):
        name = 'lcfirewall-deny'
        priority = 900
        denied = [{'IPProtocol': 'tcp', 'ports': ['4567']}]
        description = "Libcloud Deny Firewall"
        source_ranges = ['10.240.100.0/24']
        source_tags = ['libcloud']
        network = 'default'
        firewall = self.driver.ex_create_firewall(
            name, denied=denied,
            description=description, network=network,
            priority=priority, source_tags=source_tags,
            source_ranges=source_ranges)
        self.assertTrue(isinstance(firewall, GCEFirewall))
        self.assertEqual(firewall.name, name)

    def test_ex_create_forwarding_rule(self):
        fwr_name = 'lcforwardingrule'
        targetpool = 'lctargetpool'
        region = 'us-central1'
        address = 'lcaddress'
        port_range = '8000-8500'
        description = 'test forwarding rule'
        fwr = self.driver.ex_create_forwarding_rule(
            fwr_name, targetpool, region=region, address=address,
            port_range=port_range, description=description)
        self.assertTrue(isinstance(fwr, GCEForwardingRule))
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.region.name, region)
        self.assertEqual(fwr.protocol, 'TCP')
        self.assertEqual(fwr.extra['portRange'], port_range)
        self.assertEqual(fwr.extra['description'], description)

    def test_ex_create_forwarding_rule_global(self):
        fwr_name = 'http-rule'
        target_name = 'web-proxy'
        address = 'lcaddressglobal'
        port_range = '80-80'
        description = 'global forwarding rule'
        for target in (target_name,
                       self.driver.ex_get_targethttpproxy(target_name)):
            fwr = self.driver.ex_create_forwarding_rule(
                fwr_name, target, global_rule=True, address=address,
                port_range=port_range, description=description)
            self.assertTrue(isinstance(fwr, GCEForwardingRule))
            self.assertEqual(fwr.name, fwr_name)
            self.assertEqual(fwr.extra['portRange'], port_range)
            self.assertEqual(fwr.extra['description'], description)

    def test_ex_create_forwarding_rule_targetpool_keyword(self):
        """Test backwards compatibility with the targetpool kwarg."""
        fwr_name = 'lcforwardingrule'
        targetpool = 'lctargetpool'
        region = 'us-central1'
        address = self.driver.ex_get_address('lcaddress')
        port_range = '8000-8500'
        description = 'test forwarding rule'
        fwr = self.driver.ex_create_forwarding_rule(
            fwr_name, targetpool=targetpool, region=region, address=address,
            port_range=port_range, description=description)
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
        self.assertTrue(route.extra['nextHopInstance'].endswith(
            'libcloud-100'))
        self.assertEqual(route.dest_range, dest_range)

    def test_ex_create_network(self):
        network_name = 'lcnetwork'
        cidr = '10.11.0.0/16'
        routing_mode = 'REGIONAL'
        network = self.driver.ex_create_network(network_name, cidr, routing_mode='regional')
        self.assertTrue(isinstance(network, GCENetwork))
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, cidr)

        # Test using more options
        description = 'A custom network'
        network = self.driver.ex_create_network(network_name, cidr,
                                                description=description,
                                                routing_mode=routing_mode)
        self.assertEqual(network.extra['description'], description)
        self.assertEqual(network.extra['routingConfig']['routingMode'], routing_mode)

    def test_ex_create_network_bad_options(self):
        network_name = 'lcnetwork'
        cidr = '10.11.0.0/16'
        self.assertRaises(ValueError, self.driver.ex_create_network,
                          network_name, cidr, mode='auto')
        self.assertRaises(ValueError, self.driver.ex_create_network,
                          network_name, cidr, mode='foobar')
        self.assertRaises(ValueError, self.driver.ex_create_network,
                          network_name, None, mode='legacy')
        self.assertRaises(ValueError, self.driver.ex_create_network,
                          network_name, cidr, routing_mode='universal')

    def test_ex_set_machine_type_notstopped(self):
        # get running node, change machine type
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('node-name', zone)
        self.assertRaises(GoogleBaseError, self.driver.ex_set_machine_type,
                          node, 'custom-4-61440')

    def test_ex_set_machine_type(self):
        # get stopped node, change machine type
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('stopped-node', zone)
        self.assertEqual(node.size, 'n1-standard-1')
        self.assertEqual(node.extra['status'], 'TERMINATED')
        self.assertTrue(
            self.driver.ex_set_machine_type(node, 'custom-4-11264'))

    def test_ex_node_start(self):
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('stopped-node', zone)
        self.assertTrue(self.driver.ex_start_node(node))

    def test_ex_node_stop(self):
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('node-name', zone)
        self.assertTrue(self.driver.ex_stop_node(node))

        # try and stop a stopped node (should work)
        zone = 'us-central1-a'
        node = self.driver.ex_get_node('stopped-node', zone)
        self.assertTrue(self.driver.ex_stop_node(node))

    def test_create_node_req(self):
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        location = self.driver.zone
        network = self.driver.ex_get_network('default')
        tags = ['libcloud']
        metadata = [{'key': 'test_key', 'value': 'test_value'}]
        boot_disk = self.driver.ex_get_volume('lcdisk')
        node_request, node_data = self.driver._create_node_req(
            'lcnode', size, image, location, network, tags, metadata,
            boot_disk)
        self.assertEqual(node_request, '/zones/%s/instances' % location.name)
        self.assertEqual(node_data['metadata']['items'][0]['key'], 'test_key')
        self.assertEqual(node_data['tags']['items'][0], 'libcloud')
        self.assertEqual(node_data['name'], 'lcnode')
        self.assertTrue(node_data['disks'][0]['boot'])
        self.assertIsInstance(node_data['serviceAccounts'], list)
        self.assertIsInstance(node_data['serviceAccounts'][0], dict)
        self.assertEqual(node_data['serviceAccounts'][0]['email'], 'default')
        self.assertIsInstance(node_data['serviceAccounts'][0]['scopes'], list)
        self.assertEqual(len(node_data['serviceAccounts'][0]['scopes']), 1)
        self.assertEqual(len(node_data['networkInterfaces']), 1)
        self.assertTrue(node_data['networkInterfaces'][0][
            'network'].startswith('https://'))

    def test_create_node_network_opts(self):
        node_name = 'node-name'
        size = self.driver.ex_get_size('n1-standard-1')
        image = self.driver.ex_get_image('debian-7')
        zone = self.driver.ex_get_zone('us-central1-a')
        network = self.driver.ex_get_network('lcnetwork')
        address = self.driver.ex_get_address('lcaddress')
        ex_nic_gce_struct = [
            {
                "network": "global/networks/lcnetwork",
                "accessConfigs": [
                    {
                        "name": "lcnetwork-test",
                        "type": "ONE_TO_ONE_NAT"
                    }
                ]
            }
        ]
        # Test using default
        node = self.driver.create_node(node_name, size, image)
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')

        # Test using just the network
        node = self.driver.create_node(node_name, size, image, location=zone,
                                       ex_network=network)
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')

        # Test using just the struct
        node = self.driver.create_node(node_name, size, image, location=zone,
                                       ex_nic_gce_struct=ex_nic_gce_struct)
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')

        # Test both address and struct, should fail
        self.assertRaises(ValueError, self.driver.create_node, node_name, size,
                          image, location=zone, external_ip=address,
                          ex_nic_gce_struct=ex_nic_gce_struct)

        # Test both ex_network and struct, should fail
        self.assertRaises(ValueError, self.driver.create_node, node_name, size,
                          image, location=zone, ex_network=network,
                          ex_nic_gce_struct=ex_nic_gce_struct)

    def test_create_node_subnetwork_opts(self):
        node_name = 'sn-node-name'
        size = self.driver.ex_get_size('n1-standard-1')
        image = self.driver.ex_get_image('debian-7')
        zone = self.driver.ex_get_zone('us-central1-a')
        network = self.driver.ex_get_network('custom-network')
        subnetwork = self.driver.ex_get_subnetwork('cf-972cf02e6ad49112')

        ex_nic_gce_struct = [
            {
                "network": "global/networks/custom-network",
                "subnetwork":
                "projects/project_name/regions/us-central1/subnetworks/cf-972cf02e6ad49112",
                "accessConfigs": [
                    {
                        "name": "External NAT",
                        "type": "ONE_TO_ONE_NAT"
                    }
                ]
            }
        ]
        # Test using just the network and subnetwork
        node = self.driver.create_node(node_name, size, image, location=zone,
                                       ex_network=network,
                                       ex_subnetwork=subnetwork)
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')
        self.assertEqual(
            node.extra['networkInterfaces'][0]["subnetwork"].split('/')[-1],
            'cf-972cf02e6ad49112')

        # Test using just the struct
        node = self.driver.create_node(node_name, size, image, location=zone,
                                       ex_nic_gce_struct=ex_nic_gce_struct)
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')
        self.assertEqual(
            node.extra['networkInterfaces'][0]["subnetwork"].split('/')[-1],
            'cf-972cf02e6ad49112')

        # Test using subnetwork selfLink
        node = self.driver.create_node(
            node_name, size, image, location=zone, ex_network=network,
            ex_subnetwork=subnetwork.extra['selfLink'])
        self.assertEqual(node.extra['networkInterfaces'][0]["name"], 'nic0')
        self.assertEqual(
            node.extra['networkInterfaces'][0]["subnetwork"].split('/')[-1],
            'cf-972cf02e6ad49112')

    def test_create_node_disk_opts(self):
        node_name = 'node-name'
        size = self.driver.ex_get_size('n1-standard-1')
        image = self.driver.ex_get_image('debian-7')
        boot_disk = self.driver.ex_get_volume('lcdisk')
        disk_type = self.driver.ex_get_disktype('pd-ssd', 'us-central1-a')
        DEMO_BASE_NAME = "lc-test"
        gce_disk_struct = [
            {
                "type": "PERSISTENT",
                "deviceName": '%s-gstruct' % DEMO_BASE_NAME,
                "initializeParams": {
                    "diskName": '%s-gstruct' % DEMO_BASE_NAME,
                    "sourceImage": image.extra['selfLink']
                },
                "boot": True,
                "autoDelete": True
            }, {
                "type": "SCRATCH",
                "deviceName": '%s-gstruct-lssd' % DEMO_BASE_NAME,
                "initializeParams": {
                    "diskType": disk_type.extra['selfLink']
                },
                "autoDelete": True
            }
        ]

        self.assertRaises(ValueError, self.driver.create_node, node_name, size,
                          None)
        node = self.driver.create_node(node_name, size, image)
        self.assertTrue(isinstance(node, Node))
        node = self.driver.create_node(node_name, size, None,
                                       ex_boot_disk=boot_disk)
        self.assertTrue(isinstance(node, Node))
        node = self.driver.create_node(node_name, size, None,
                                       ex_disks_gce_struct=gce_disk_struct)
        self.assertTrue(isinstance(node, Node))
        self.assertRaises(ValueError, self.driver.create_node, node_name, size,
                          None, ex_boot_disk=boot_disk,
                          ex_disks_gce_struct=gce_disk_struct)

    def test_create_node(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        node = self.driver.create_node(node_name, size, image)
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.name, node_name)

    def test_create_node_disk_size(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        disk_size = 25
        node = self.driver.create_node(node_name, size, image,
                                       ex_disk_size=disk_size)
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.name, node_name)
        self.assertEqual(node.extra['boot_disk'].size, str(disk_size))

    def test_create_node_image_family(self):
        node_name = 'node-name'
        size = self.driver.ex_get_size('n1-standard-1')
        node = self.driver.create_node(node_name, size, image=None,
                                       ex_image_family='coreos-stable')
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.name, node_name)

        image = self.driver.ex_get_image('debian-7')
        self.assertRaises(ValueError, self.driver.create_node, node_name, size,
                          image, ex_image_family='coreos-stable')

    def test_create_node_req_with_serviceaccounts(self):
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        location = self.driver.zone
        network = self.driver.ex_get_network('default')
        # ex_service_accounts with specific scopes, default 'email'
        ex_sa = [{'scopes': ['compute-ro', 'pubsub', 'storage-ro']}]
        node_request, node_data = self.driver._create_node_req(
            'lcnode', size, image, location, network,
            ex_service_accounts=ex_sa)
        self.assertIsInstance(node_data['serviceAccounts'], list)
        self.assertIsInstance(node_data['serviceAccounts'][0], dict)
        self.assertEqual(node_data['serviceAccounts'][0]['email'], 'default')
        self.assertIsInstance(node_data['serviceAccounts'][0]['scopes'], list)
        self.assertEqual(len(node_data['serviceAccounts'][0]['scopes']), 3)
        self.assertTrue('https://www.googleapis.com/auth/devstorage.read_only'
                        in node_data['serviceAccounts'][0]['scopes'])
        self.assertTrue('https://www.googleapis.com/auth/compute.readonly' in
                        node_data['serviceAccounts'][0]['scopes'])

    def test_format_metadata(self):
        in_md = [{'key': 'k0', 'value': 'v0'}, {'key': 'k1', 'value': 'v1'}]
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 2)
        self.assertTrue(out_md['items'][0]['key'] in ['k0', 'k1'])
        self.assertTrue(out_md['items'][0]['value'] in ['v0', 'v1'])

        in_md = [{'k0': 'v0'}, {'k1': 'v1'}]
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 2)
        self.assertTrue(out_md['items'][0]['key'] in ['k0', 'k1'])
        self.assertTrue(out_md['items'][0]['value'] in ['v0', 'v1'])

        in_md = {'key': 'k0', 'value': 'v0'}
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 1, out_md)
        self.assertEqual(out_md['items'][0]['key'], 'k0')
        self.assertEqual(out_md['items'][0]['value'], 'v0')

        in_md = {'k0': 'v0'}
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 1)
        self.assertEqual(out_md['items'][0]['key'], 'k0')
        self.assertEqual(out_md['items'][0]['value'], 'v0')

        in_md = {'k0': 'v0', 'k1': 'v1', 'k2': 'v2'}
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 3)
        keys = [x['key'] for x in out_md['items']]
        vals = [x['value'] for x in out_md['items']]
        keys.sort()
        vals.sort()
        self.assertEqual(keys, ['k0', 'k1', 'k2'])
        self.assertEqual(vals, ['v0', 'v1', 'v2'])

        in_md = {'items': [{'key': 'k0',
                            'value': 'v0'}, {'key': 'k1',
                                             'value': 'v1'}]}
        out_md = self.driver._format_metadata('fp', in_md)
        self.assertTrue('fingerprint' in out_md)
        self.assertEqual(out_md['fingerprint'], 'fp')
        self.assertTrue('items' in out_md)
        self.assertEqual(len(out_md['items']), 2)
        self.assertTrue(out_md['items'][0]['key'] in ['k0', 'k1'])
        self.assertTrue(out_md['items'][0]['value'] in ['v0', 'v1'])

        in_md = {'items': 'foo'}
        self.assertRaises(ValueError, self.driver._format_metadata, 'fp',
                          in_md)
        in_md = {'items': {'key': 'k1', 'value': 'v0'}}
        self.assertRaises(ValueError, self.driver._format_metadata, 'fp',
                          in_md)
        in_md = ['k0', 'v1']
        self.assertRaises(ValueError, self.driver._format_metadata, 'fp',
                          in_md)

    def test_create_node_with_metadata(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        zone = self.driver.ex_get_zone('us-central1-a')

        # md is a list of dicts, each with 'key' and 'value' for
        # backwards compatibility
        md = [{'key': 'k0', 'value': 'v0'}, {'key': 'k1', 'value': 'v1'}]
        request, data = self.driver._create_node_req(node_name, size, image,
                                                     zone, metadata=md)
        self.assertTrue('items' in data['metadata'])
        self.assertEqual(len(data['metadata']['items']), 2)

        # md doesn't contain "items" key
        md = {'key': 'key1', 'value': 'value1'}
        request, data = self.driver._create_node_req(node_name, size, image,
                                                     zone, metadata=md)
        self.assertTrue('items' in data['metadata'])
        self.assertEqual(len(data['metadata']['items']), 1)

        # md contains "items" key
        md = {'items': [{'key': 'k0', 'value': 'v0'}]}
        request, data = self.driver._create_node_req(node_name, size, image,
                                                     zone, metadata=md)
        self.assertTrue('items' in data['metadata'])
        self.assertEqual(len(data['metadata']['items']), 1)
        self.assertEqual(data['metadata']['items'][0]['key'], 'k0')
        self.assertEqual(data['metadata']['items'][0]['value'], 'v0')

    def test_create_node_with_accelerator(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        zone = self.driver.ex_get_zone('us-central1-a')
        request, data = self.driver._create_node_req(
            node_name, size, image, zone,
            ex_accelerator_type='nvidia-tesla-k80', ex_accelerator_count=3)
        self.assertTrue('guestAccelerators' in data)
        self.assertEqual(len(data['guestAccelerators']), 1)
        self.assertTrue('nvidia-tesla-k80' in data['guestAccelerators'][0]['acceleratorType'])
        self.assertEqual(data['guestAccelerators'][0]['acceleratorCount'], 3)

    def test_create_node_with_labels(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        zone = self.driver.ex_get_zone('us-central1-a')

        # labels is a dict
        labels = {'label1': 'v1', 'label2': 'v2'}
        request, data = self.driver._create_node_req(node_name, size, image,
                                                     zone, ex_labels=labels)
        self.assertTrue(data['labels'] is not None)
        self.assertEqual(len(data['labels']), 2)
        self.assertEqual(data['labels']['label1'], 'v1')
        self.assertEqual(data['labels']['label2'], 'v2')

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
        disk_size = "25"
        # NOTE: We use small poll_interval to speed up the tests
        nodes = self.driver.ex_create_multiple_nodes(base_name, size, image,
                                                     number,
                                                     ex_disk_size=disk_size,
                                                     poll_interval=0.1)
        self.assertEqual(len(nodes), 2)
        self.assertTrue(isinstance(nodes[0], Node))
        self.assertTrue(isinstance(nodes[1], Node))
        self.assertEqual(nodes[0].name, '%s-000' % base_name)
        self.assertEqual(nodes[1].name, '%s-001' % base_name)
        self.assertEqual(nodes[0].extra['boot_disk'].size, disk_size)
        self.assertEqual(nodes[1].extra['boot_disk'].size, disk_size)

    def test_ex_create_multiple_nodes_image_family(self):
        base_name = 'lcnode'
        image = None
        size = self.driver.ex_get_size('n1-standard-1')
        number = 2
        # NOTE: We use small poll_interval to speed up the tests
        nodes = self.driver.ex_create_multiple_nodes(
            base_name, size, image, number, ex_image_family='coreos-stable',
            poll_interval=0.1)
        self.assertEqual(len(nodes), 2)
        self.assertTrue(isinstance(nodes[0], Node))
        self.assertTrue(isinstance(nodes[1], Node))
        self.assertEqual(nodes[0].name, '%s-000' % base_name)
        self.assertEqual(nodes[1].name, '%s-001' % base_name)

        image = self.driver.ex_get_image('debian-7')
        self.assertRaises(ValueError, self.driver.ex_create_multiple_nodes,
                          base_name, size, image, number,
                          ex_image_family='coreos-stable')

    def test_ex_create_targethttpproxy(self):
        proxy_name = 'web-proxy'
        urlmap_name = 'web-map'
        for urlmap in (urlmap_name, self.driver.ex_get_urlmap(urlmap_name)):
            proxy = self.driver.ex_create_targethttpproxy(proxy_name, urlmap)
            self.assertTrue(isinstance(proxy, GCETargetHttpProxy))
            self.assertEqual(proxy_name, proxy.name)

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
            targetpool_name, region=region, session_affinity=session_affinity)
        self.assertEqual(targetpool.name, targetpool_name)
        self.assertEqual(
            targetpool.extra.get('sessionAffinity'), session_affinity)

    def test_ex_create_urlmap(self):
        urlmap_name = 'web-map'
        for service in ('web-service',
                        self.driver.ex_get_backendservice('web-service')):
            urlmap = self.driver.ex_create_urlmap(urlmap_name, service)
            self.assertTrue(isinstance(urlmap, GCEUrlMap))
            self.assertEqual(urlmap_name, urlmap.name)

    def test_create_volume_image_family(self):
        volume_name = 'lcdisk'
        size = 10
        volume = self.driver.create_volume(size, volume_name,
                                           ex_image_family='coreos-stable')
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

        image = self.driver.ex_get_image('debian-7')
        self.assertRaises(ValueError, self.driver.create_volume, size,
                          volume_name, image=image,
                          ex_image_family='coreos-stable')

    def test_create_volume_location(self):
        volume_name = 'lcdisk'
        size = 10
        zone = self.driver.zone
        volume = self.driver.create_volume(size, volume_name, location=zone)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

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

    def test_ex_set_volume_labels(self):
        volume_name = 'lcdisk'
        zone = self.driver.zone
        volume_labels = {'one': '1', 'two': '2', 'three': '3'}
        size = 10
        new_vol = self.driver.create_volume(size, volume_name, location=zone)
        self.assertTrue(self.driver.ex_set_volume_labels(new_vol,
                                                         labels=volume_labels))
        exist_vol = self.driver.ex_get_volume(volume_name, self.driver.zone)
        self.assertEqual(exist_vol.extra['labels'], volume_labels)

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
        firewall.description = "LCFirewall-2"
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
        self.assertTrue(
            targetpool.set_backup_targetpool(backup_targetpool, 0.1))

    def test_ex_targetpool_remove_add_node(self):
        targetpool = self.driver.ex_get_targetpool('lctargetpool')
        node = self.driver.ex_get_node('libcloud-lb-demo-www-001',
                                       'us-central1-b')
        remove_node = self.driver.ex_targetpool_remove_node(targetpool, node)
        self.assertTrue(remove_node)
        self.assertEqual(len(targetpool.nodes), 1)

        add_node = self.driver.ex_targetpool_add_node(targetpool,
                                                      node.extra['selfLink'])
        self.assertTrue(add_node)
        self.assertEqual(len(targetpool.nodes), 2)

        remove_node = self.driver.ex_targetpool_remove_node(
            targetpool, node.extra['selfLink'])
        self.assertTrue(remove_node)
        self.assertEqual(len(targetpool.nodes), 1)

        add_node = self.driver.ex_targetpool_add_node(targetpool, node)
        self.assertTrue(add_node)
        self.assertEqual(len(targetpool.nodes), 2)

        # check that duplicates are filtered
        add_node = self.driver.ex_targetpool_add_node(targetpool,
                                                      node.extra['selfLink'])
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

    def test_attach_volume_invalid_usecase(self):
        node = self.driver.ex_get_node('node-name')
        self.assertRaises(ValueError, self.driver.attach_volume, node, None)
        self.assertRaises(ValueError, self.driver.attach_volume, node, None,
                          ex_source='foo/bar', device=None)

    def test_attach_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        node = self.driver.ex_get_node('node-name')
        attach = volume.attach(node)
        self.assertTrue(attach)

    def test_ex_resize_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        desired_size = int(volume.size) + 8
        resize = self.driver.ex_resize_volume(volume, desired_size)
        self.assertTrue(resize)

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
        self.assertEqual(address.name, 'lcaddressglobal')
        self.assertEqual(address.region, 'global')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_address(self):
        address = self.driver.ex_get_address('lcaddress')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_backendservice(self):
        backendservice = self.driver.ex_get_backendservice('web-service')
        destroyed = backendservice.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_healthcheck(self):
        hc = self.driver.ex_get_healthcheck('lchealthcheck')
        destroyed = hc.destroy()
        self.assertTrue(destroyed)

    def test_ex_delete_image(self):
        self.assertRaises(ResourceNotFoundError, self.driver.ex_get_image,
                          'missing-image')
        self.assertRaises(ResourceNotFoundError, self.driver.ex_delete_image,
                          'missing-image')

        image = self.driver.ex_get_image('debian-7')
        deleted = self.driver.ex_delete_image(image)
        self.assertTrue(deleted)

    def test_ex_deprecate_image(self):
        dep_ts = '2064-03-11T20:18:36.194-07:00'
        obs_ts = '2074-03-11T20:18:36.194-07:00'
        del_ts = '2084-03-11T20:18:36.194-07:00'
        image = self.driver.ex_get_image('debian-7-wheezy-v20131014')
        deprecated = image.deprecate('debian-7', 'DEPRECATED',
                                     deprecated=dep_ts, obsolete=obs_ts,
                                     deleted=del_ts)
        self.assertTrue(deprecated)
        self.assertEqual(image.extra['deprecated']['deprecated'], dep_ts)
        self.assertEqual(image.extra['deprecated']['obsolete'], obs_ts)
        self.assertEqual(image.extra['deprecated']['deleted'], del_ts)

    def test_ex_destroy_firewall(self):
        firewall = self.driver.ex_get_firewall('lcfirewall')
        destroyed = firewall.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_forwarding_rule(self):
        fwr = self.driver.ex_get_forwarding_rule('lcforwardingrule')
        destroyed = fwr.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_forwarding_rule_global(self):
        fwr = self.driver.ex_get_forwarding_rule('http-rule', global_rule=True)
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

    def test_destroy_targethttpproxy(self):
        proxy = self.driver.ex_get_targethttpproxy('web-proxy')
        destroyed = proxy.destroy()
        self.assertTrue(destroyed)

    def test_destroy_targetinstance(self):
        targetinstance = self.driver.ex_get_targetinstance('lctargetinstance')
        self.assertEqual(targetinstance.name, 'lctargetinstance')
        destroyed = targetinstance.destroy()
        self.assertTrue(destroyed)

    def test_destroy_targetpool(self):
        targetpool = self.driver.ex_get_targetpool('lctargetpool')
        destroyed = targetpool.destroy()
        self.assertTrue(destroyed)

    def test_destroy_urlmap(self):
        urlmap = self.driver.ex_get_urlmap('web-map')
        destroyed = urlmap.destroy()
        self.assertTrue(destroyed)

    def test_destroy_volume(self):
        disk = self.driver.ex_get_volume('lcdisk')
        destroyed = disk.destroy()
        self.assertTrue(destroyed)

    def test_ex_set_volume_auto_delete(self):
        node = self.driver.ex_get_node('node-name')
        volume = node.extra['boot_disk']
        auto_delete = self.driver.ex_set_volume_auto_delete(volume, node)
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

    def test_ex_get_backendservice(self):
        web_service = self.driver.ex_get_backendservice('web-service')
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

        web_service = self.driver.ex_get_backendservice('no-backends')
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
        self.assertEqual(firewall.target_tags, ['libcloud'])

    def test_ex_get_forwarding_rule(self):
        fwr_name = 'lcforwardingrule'
        fwr = self.driver.ex_get_forwarding_rule(fwr_name)
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.extra['portRange'], '8000-8500')
        self.assertEqual(fwr.targetpool.name, 'lctargetpool')
        self.assertEqual(fwr.protocol, 'TCP')

    def test_ex_get_forwarding_rule_global(self):
        fwr_name = 'http-rule'
        fwr = self.driver.ex_get_forwarding_rule(fwr_name, global_rule=True)
        self.assertEqual(fwr.name, fwr_name)
        self.assertEqual(fwr.extra['portRange'], '80-80')
        self.assertEqual(fwr.targetpool.name, 'web-proxy')
        self.assertEqual(fwr.protocol, 'TCP')
        self.assertEqual(fwr.address, '192.0.2.1')
        self.assertEqual(fwr.targetpool.name, 'web-proxy')

    def test_ex_get_image_license(self):
        image = self.driver.ex_get_image('sles-12-v20141023')
        self.assertTrue('licenses' in image.extra)
        self.assertEqual(image.extra['licenses'][0].name, 'sles-12')
        self.assertTrue(image.extra['licenses'][0].charges_use_fee)

    def test_ex_get_image(self):
        partial_name = 'debian-7'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-7-wheezy-v20131120')
        # A 'debian-7' image exists in the local project
        self.assertTrue(image.extra['description'].startswith('Debian'))

        partial_name = 'debian-6'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-6-squeeze-v20130926')
        self.assertTrue(image.extra['description'].startswith('Debian'))

        partial_name = 'debian-7'
        image = self.driver.ex_get_image(partial_name, ['debian-cloud'])
        self.assertEqual(image.name, 'debian-7-wheezy-v20131120')

        partial_name = 'debian-7'
        self.assertRaises(ResourceNotFoundError, self.driver.ex_get_image,
                          partial_name, 'suse-cloud',
                          ex_standard_projects=False)

    def test_ex_get_image_from_family(self):
        family = 'coreos-beta'
        description = 'CoreOS beta 522.3.0'
        image = self.driver.ex_get_image_from_family(family)
        self.assertEqual(image.name, 'coreos-beta-522-3-0-v20141226')
        self.assertEqual(image.extra['description'], description)
        self.assertEqual(image.extra['family'], family)

        url = ('https://www.googleapis.com/compute/v1/projects/coreos-cloud/'
               'global/images/family/coreos-beta')
        image = self.driver.ex_get_image_from_family(url)
        self.assertEqual(image.name, 'coreos-beta-522-3-0-v20141226')
        self.assertEqual(image.extra['description'], description)
        self.assertEqual(image.extra['family'], family)

        project_list = ['coreos-cloud']
        image = self.driver.ex_get_image_from_family(
            family, ex_project_list=project_list, ex_standard_projects=False)
        self.assertEqual(image.name, 'coreos-beta-522-3-0-v20141226')
        self.assertEqual(image.extra['description'], description)
        self.assertEqual(image.extra['family'], family)

        self.assertRaises(ResourceNotFoundError,
                          self.driver.ex_get_image_from_family, 'nofamily')

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
        # do the same but this time with URL
        url = 'https://www.googleapis.com/compute/v1/projects/project_name/global/networks/lcnetwork'
        network = self.driver.ex_get_network(url)
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, '10.11.0.0/16')
        self.assertEqual(network.extra['gatewayIPv4'], '10.11.0.1')
        self.assertEqual(network.extra['description'], 'A custom network')
        # do the same but with a network under a different project
        url_other = 'https://www.googleapis.com/compute/v1/projects/other_name/global/networks/lcnetwork'
        network = self.driver.ex_get_network(url_other)
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
        self.assertTrue(
            'fingerprint' in project.extra['commonInstanceMetadata'])
        self.assertTrue('items' in project.extra['commonInstanceMetadata'])
        self.assertTrue('usageExportLocation' in project.extra)
        self.assertTrue('bucketName' in project.extra['usageExportLocation'])
        self.assertEqual(project.extra['usageExportLocation']['bucketName'],
                         'gs://graphite-usage-reports')

    def test_ex_add_access_config(self):
        self.assertRaises(ValueError, self.driver.ex_add_access_config, 'node',
                          'name', 'nic')
        node = self.driver.ex_get_node('node-name', 'us-central1-a')
        self.assertTrue(self.driver.ex_add_access_config(node, 'foo', 'bar'))

    def test_ex_delete_access_config(self):
        self.assertRaises(ValueError, self.driver.ex_add_access_config, 'node',
                          'name', 'nic')
        node = self.driver.ex_get_node('node-name', 'us-central1-a')
        self.assertTrue(
            self.driver.ex_delete_access_config(node, 'foo', 'bar'))

    def test_ex_set_usage_export_bucket(self):
        self.assertRaises(ValueError, self.driver.ex_set_usage_export_bucket,
                          'foo')
        bucket_name = 'gs://foo'
        self.driver.ex_set_usage_export_bucket(bucket_name)

        bucket_name = 'https://www.googleapis.com/foo'
        self.driver.ex_set_usage_export_bucket(bucket_name)

        project = GCEProject(id=None, name=None, metadata=None, quotas=None,
                             driver=self.driver)
        project.set_usage_export_bucket(bucket=bucket_name)

    def test__set_project_metadata(self):
        self.assertEqual(
            len(self.driver._set_project_metadata(None, False, "")), 0)

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
        gce_md = {'items': [{'key': 'foo',
                             'value': 'one'}, {'key': 'sshKeys',
                                               'value': 'another test'}]}
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
        gce_md = {'items': [{'key': 'foo',
                             'value': 'one'}, {'key': 'sshKeys',
                                               'value': 'another test'}]}
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
        gce_md = {'items': [{'key': 'foo',
                             'value': 'one'}, {'key': 'nokeys',
                                               'value': 'two'}]}
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
        pydict = {'key': 'pydict', 'value': 1}
        self.driver.ex_set_common_instance_metadata(pydict)
        # test GCE badly formatted dict
        bad_gcedict = {'items': 'foo'}
        self.assertRaises(ValueError,
                          self.driver.ex_set_common_instance_metadata,
                          bad_gcedict)
        # test gce formatted dict
        gcedict = {'items': [{'key': 'gcedict1',
                              'value': 'v1'}, {'key': 'gcedict2',
                                               'value': 'v2'}]}
        self.driver.ex_set_common_instance_metadata(gcedict)

        # Verify project notation works
        project = GCEProject(id=None, name=None, metadata=None, quotas=None,
                             driver=self.driver)
        project.set_common_instance_metadata(metadata=gcedict)

    def test_ex_set_node_metadata(self):
        node = self.driver.ex_get_node('node-name', 'us-central1-a')
        # test non-dict
        self.assertRaises(ValueError, self.driver.ex_set_node_metadata, node,
                          ['bad', 'type'])
        # test standard python dict
        pydict = {'key': 'pydict', 'value': 1}
        self.driver.ex_set_node_metadata(node, pydict)
        # test GCE badly formatted dict
        bad_gcedict = {'items': 'foo'}
        self.assertRaises(ValueError, self.driver.ex_set_node_metadata, node,
                          bad_gcedict)
        # test gce formatted dict
        gcedict = {'items': [{'key': 'gcedict1',
                              'value': 'v1'}, {'key': 'gcedict2',
                                               'value': 'v2'}]}
        self.driver.ex_set_node_metadata(node, gcedict)

    def test_ex_set_node_labels(self):
        node = self.driver.ex_get_node('node-name', 'us-central1-a')
        # Test basic values
        simplelabel = {'key': 'value'}
        self.driver.ex_set_node_labels(node, simplelabel)
        # Test multiple values
        multilabels = {'item1': 'val1', 'item2': 'val2'}
        self.driver.ex_set_node_labels(node, multilabels)

    def test_ex_set_image_labels(self):
        image = self.driver.ex_get_image('custom-image')
        # Test basic values
        simplelabel = {'foo': 'bar'}
        self.driver.ex_set_image_labels(image, simplelabel)
        image = self.driver.ex_get_image('custom-image')
        self.assertTrue('foo' in image.extra['labels'])
        # Test multiple values
        multilabels = {'one': '1', 'two': 'two'}
        self.driver.ex_set_image_labels(image, multilabels)
        image = self.driver.ex_get_image('custom-image')
        self.assertEqual(len(image.extra['labels']), 3)
        self.assertTrue('two' in image.extra['labels'])
        self.assertTrue('two' in image.extra['labels'])

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

    def test_ex_get_targethttpproxy(self):
        targethttpproxy_name = 'web-proxy'
        targethttpproxy = self.driver.ex_get_targethttpproxy(
            targethttpproxy_name)
        self.assertEqual(targethttpproxy.name, targethttpproxy_name)
        self.assertEqual(targethttpproxy.urlmap.name, 'web-map')

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

    def test_ex_get_instancegroupmanager(self):
        igmgr_name = 'myinstancegroup'
        igmgr = self.driver.ex_get_instancegroupmanager(igmgr_name,
                                                        'us-central1-b')
        self.assertEqual(igmgr.name, igmgr_name)
        self.assertEqual(igmgr.size, 4)
        self.assertEqual(igmgr.zone.name, 'us-central1-b')

        # search all zones
        igmgr = self.driver.ex_get_instancegroupmanager(igmgr_name)
        self.assertEqual(igmgr.name, igmgr_name)
        self.assertEqual(igmgr.size, 4)
        self.assertEqual(igmgr.zone.name, 'us-central1-a')

    def test_ex_get_instancetemplate(self):
        instancetemplate_name = 'my-instance-template1'
        instancetemplate = self.driver.ex_get_instancetemplate(
            instancetemplate_name)
        self.assertEqual(instancetemplate.name, instancetemplate_name)
        self.assertEqual(instancetemplate.extra['properties']['machineType'],
                         'n1-standard-1')

    def test_ex_get_snapshot(self):
        snapshot_name = 'lcsnapshot'
        snapshot = self.driver.ex_get_snapshot(snapshot_name)
        self.assertEqual(snapshot.name, snapshot_name)
        self.assertEqual(snapshot.size, '10')
        self.assertEqual(snapshot.status, 'READY')

    def test_ex_get_urlmap(self):
        urlmap_name = 'web-map'
        urlmap = self.driver.ex_get_urlmap(urlmap_name)
        self.assertEqual(urlmap.name, urlmap_name)
        self.assertEqual(urlmap.default_service.name, 'web-service')

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
        self.assertIsNone(zone_no_mw.time_until_mw)


class GCEMockHttp(MockHttp):
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
        method_name = super(GCEMockHttp, self)._get_method_name(
            type, use_param, qs, path)
        return method_name

    def _setUsageExportBucket(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('setUsageExportBucket_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_custom_node(self, method, url, body,
                                                   header):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_custom_node.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setMachineType(
            self, method, url, body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_node_name_setMachineType.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_setMachineType_notstopped(
            self, method, url, body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_operations_operation_setMachineType_notstopped.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_custom_node_setMachineType(
            self, method, url, body, header):
        body = {
            "error": {
                "errors": [
                    {
                        "domain": "global",
                        "reason": "invalid",
                        "message":
                        "Invalid value for field 'resource.machineTypes': "
                        "'projects/project_name/zones/us-central1-a/machineTypes/custom-1-61440'.  Resource was not found.",
                    }
                ],
                "code": 400,
                "message": "Invalid value for field 'resource.machineTypes': "
                "'projects/project_name/zones/us-central1-a/machineTypes/custom-1-61440'.  Resource was not found."
            }
        }
        return (httplib.BAD_REQUEST, body, self.json_hdr,
                httplib.responses[httplib.BAD_REQUEST])

    def _zones_us_central1_a_instances_stopped_node_setMachineType(
            self, method, url, body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_stopped_node_setMachineType.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_setMachineType(
            self, method, url, body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_operations_operation_setMachineType.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_startnode(self, method, url,
                                                            body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_operations_operation_startnode.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_stopped_node_start(self, method, url,
                                                          body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_stopped_node_start.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_stopped_node_stop(self, method, url,
                                                         body, header):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_stopped_node_stop.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_stopped_node(self, method, url, body,
                                                    headers):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_stopped_node.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_stopnode(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'zones_us_central1_a_operations_operation_stopnode.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_stop(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_node_name_stop.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_acceleratorTypes_nvidia_tesla_k80(self, method,
                                                               url, body,
                                                               headers):
        body = self.fixtures.load(
            'zones_us_central1_a_acceleratorTypes_nvidia_tesla_k80.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setMetadata(self, method, url,
                                                             body, headers):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_node_name_setMetadata_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setLabels(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'zones_us_central1_a_instances_node_name_setLabels_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_custom_image_setLabels(self, method, url, body, headers):
        body = self.fixtures.load(
            'global_custom_image_setLabels_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _setCommonInstanceMetadata(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('setCommonInstanceMetadata_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_subnetworks(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_subnetworks.json')
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

    def _aggregated_instanceGroupManagers(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_instanceGroupManagers.json')
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
        if method == 'POST':
            body = self.fixtures.load('global_backendServices_post.json')
        else:
            backend_name = getattr(self.test, 'backendservices_mock',
                                   'web-service')
            body = self.fixtures.load('global_backendServices-%s.json' %
                                      backend_name)
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_backendServices_no_backends(self, method, url, body, headers):
        body = self.fixtures.load('global_backendServices_no_backends.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_backendServices_web_service(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_backendServices_web_service_delete.json')
        else:
            body = self.fixtures.load(
                'global_backendServices_web_service.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_forwardingRules(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_forwardingRules_post.json')
        else:
            body = self.fixtures.load('global_forwardingRules.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_forwardingRules_http_rule(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_forwardingRules_http_rule_delete.json')
        else:
            body = self.fixtures.load('global_forwardingRules_http_rule.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_httpHealthChecks_post.json')
        else:
            body = self.fixtures.load('global_httpHealthChecks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_httpHealthChecks_default_health_check(self, method, url, body,
                                                      headers):
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

    def _global_firewalls_lcfirewall_egress(self, method, url, body, headers):
        body = self.fixtures.load('global_firewalls_lcfirewall-egress.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_firewalls_lcfirewall_deny(self, method, url, body, headers):
        body = self.fixtures.load('global_firewalls_lcfirewall-deny.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_images_post.json')
        else:
            body = self.fixtures.load('global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images_debian_7_wheezy_v20131120(self, method, url, body,
                                                 headers):
        body = self.fixtures.load(
            'global_images_debian_7_wheezy_v20131120_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images_debian_7_wheezy_v20131014_deprecate(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'global_images_debian_7_wheezy_v20131014_deprecate.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images_family_coreos_beta(self, method, url, body, headers):
        body = self.fixtures.load('global_images_family_notfound.json')
        return (httplib.NOT_FOUND, body, self.json_hdr,
                httplib.responses[httplib.NOT_FOUND])

    def _global_images_family_coreos_stable(self, method, url, body, headers):
        body = self.fixtures.load('global_images_family_notfound.json')
        return (httplib.NOT_FOUND, body, self.json_hdr,
                httplib.responses[httplib.NOT_FOUND])

    def _global_images_family_nofamily(self, method, url, body, headers):
        body = self.fixtures.load('global_images_family_notfound.json')
        return (httplib.NOT_FOUND, body, self.json_hdr,
                httplib.responses[httplib.NOT_FOUND])

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

    def _global_networks_custom_network(self, method, url, body, headers):
        body = self.fixtures.load('global_networks_custom_network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_cf(self, method, url, body, headers):
        body = self.fixtures.load('global_networks_cf.json')
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

    def _global_operations_operation_setUsageExportBucket(self, method, url,
                                                          body, headers):
        body = self.fixtures.load(
            'operations_operation_setUsageExportBucket.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_setCommonInstanceMetadata(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_setCommonInstanceMetadata.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_backendServices_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_backendServices_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_backendServices_web_service_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_backendServices_web_service_delete'
            '.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_forwardingRules_http_rule_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_forwardingRules_http_rule_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_forwardingRules_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_forwardingRules_post.json')
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

    def _global_operations_operation_global_firewalls_post(self, method, url,
                                                           body, headers):
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

    def _global_operations_operation_global_routes_post(self, method, url,
                                                        body, headers):
        body = self.fixtures.load(
            'operations_operation_global_routes_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_networks_post(self, method, url,
                                                          body, headers):
        body = self.fixtures.load(
            'operations_operation_global_networks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_snapshots_lcsnapshot_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_snapshots_lcsnapshot_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_image_post(self, method, url, body,
                                                       headers):
        body = self.fixtures.load(
            'operations_operation_global_image_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_addresses_lcaddressglobal_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_addresses_lcaddressglobal_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_targetHttpProxies_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_targetHttpProxies_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_targetHttpProxies_web_proxy_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_targetHttpProxies_web_proxy_delete'
            '.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_urlMaps_post(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'operations_operation_global_urlMaps_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_urlMaps_web_map_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_urlMaps_web_map_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_targetHttpProxies(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_targetHttpProxies_post.json')
        else:
            body = self.fixtures.load('global_targetHttpProxies.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_targetHttpProxies_web_proxy(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_targetHttpProxies_web_proxy_delete.json')
        else:
            body = self.fixtures.load(
                'global_targetHttpProxies_web_proxy.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_urlMaps(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_urlMaps_post.json')
        else:
            body = self.fixtures.load('global_urlMaps.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_urlMaps_web_map(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('global_urlMaps_web_map_delete.json')
        else:
            body = self.fixtures.load('global_urlMaps_web_map.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_east1_subnetworks_cf_972cf02e6ad49113(self, method, url,
                                                          body, headers):
        body = self.fixtures.load(
            'regions_us-east1_subnetworks_cf_972cf02e6ad49113.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_subnetworks_cf_972cf02e6ad49112(self, method, url,
                                                             body, headers):
        body = self.fixtures.load(
            'regions_us-central1_subnetworks_cf_972cf02e6ad49112.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_regions_us_central1(self, method, url, body, headers):
        body = self.fixtures.load('projects_other_name_regions_us-central1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_global_networks_lcnetwork(self, method, url, body, headers):
        body = self.fixtures.load('projects_other_name_global_networks_lcnetwork.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_global_networks_cf(self, method, url, body, headers):
        body = self.fixtures.load('projects_other_name_global_networks_cf.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_global_networks_shared_network_for_mig(self, method, url, body, headers):
        body = self.fixtures.load('projects_other_name_global_networks_shared_network_for_mig.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_regions_us_central1_subnetworks_cf_972cf02e6ad49114(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'projects_other_name_regions_us-central1_subnetworks_cf_972cf02e6ad49114.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_other_name_regions_us_central1_subnetworks_shared_subnetwork_for_mig(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'projects_other_name_regions_us-central1_subnetworks_shared_subnetwork_for_mig.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_lcaddress_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_lcaddress_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_addresses_post(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'operations_operation_global_addresses_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_subnetworks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_subnetworks_post.json')
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

    def _zones_us_central1_a_instances_node_name_deleteAccessConfig(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node_name_deleteAccessConfig_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_serialPort(self, method, url,
                                                            body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node_name_getSerialOutput.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_addAccessConfig(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node_name_addAccessConfig_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_setMetadata_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_node_name_setMetadata_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_setLabels_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_node_name_setLabels_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_setImageLabels_post(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'global_operations_operation_setImageLabels_post.json')
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

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_addAccessConfig_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node_name_addAccessConfig_done.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_deleteAccessConfig_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node_name_deleteAccessConfig_done.json')
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

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_lcdisk_resize_post(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_lcdisk_resize_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_lcdisk_setLabels_post(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_lcdisk_setLabels_post.json')
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

    def _projects_windows_cloud_global_licenses_windows_server_2008_r2_dc(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'projects_windows-cloud_global_licenses_windows_server_2008_r2_dc.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_licenses_sles_11(self, method, url, body,
                                                     headers):
        body = self.fixtures.load(
            'projects_suse-cloud_global_licenses_sles_11.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_rhel_cloud_global_licenses_rhel_7_server(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'projects_rhel-cloud_global_licenses_rhel_server.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_coreos_cloud_global_licenses_coreos_stable(self, method, url,
                                                             body, headers):
        body = self.fixtures.load(
            'projects_coreos-cloud_global_licenses_coreos_stable.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_licenses_sles_12(self, method, url, body,
                                                     headers):
        body = self.fixtures.load(
            'projects_suse-cloud_global_licenses_sles_12.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_windows_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_windows-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_windows_sql_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_windows-sql-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_rhel_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_rhel-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_coreos_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_coreos-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_coreos_cloud_global_images_family_coreos_beta(self, method,
                                                                url, body,
                                                                header):
        body = self.fixtures.load(
            'projects_coreos-cloud_global_images_family_coreos_beta.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_coreos_cloud_global_images_family_coreos_stable(self, method,
                                                                  url, body,
                                                                  header):
        body = self.fixtures.load(
            'projects_coreos-cloud_global_images_family_coreos_stable.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_cos_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_cos-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_opensuse_cloud_global_images(self, method, url, body,
                                               header):
        body = self.fixtures.load('projects_opensuse-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_ubuntu_os_cloud_global_images(self, method, url, body,
                                                header):
        body = self.fixtures.load(
            'projects_ubuntu-os-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_centos_cloud_global_images(self, method, url, body, header):
        body = self.fixtures.load('projects_centos-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_byos_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-byos-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_suse_sap_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_suse-sap-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_debian_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_debian-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions(self, method, url, body, headers):
        if 'pageToken' in url or 'filter' in url:
            body = self.fixtures.load('regions-paged-2.json')
        elif 'maxResults' in url:
            body = self.fixtures.load('regions-paged-1.json')
        else:
            body = self.fixtures.load('regions.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_addresses(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_addresses_post.json')
        else:
            body = self.fixtures.load('global_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_europe_west1(self, method, url, body, headers):
        body = self.fixtures.load('regions_europe-west1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_asia_east1(self, method, url, body, headers):
        body = self.fixtures.load('regions_asia-east1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1(self, method, url, body, headers):
        body = self.fixtures.load('regions_us-central1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_east1(self, method, url, body, headers):
        body = self.fixtures.load('regions_us-east1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_subnetworks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_subnetworks_post.json')
        else:
            body = self.fixtures.load('regions_us-central1_subnetworks.json')
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

    def _regions_us_central1_addresses_testaddress(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('regions_us-central1_addresses_testaddress.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_subnetworks_subnet_1(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('regions_us-central1_subnetworks_subnet_1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_addresses_lcaddressinternal(self, method, url, body,
                                                         headers):
        body = self.fixtures.load('regions_us-central1_addresses_lcaddressinternal.json')
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
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_targetPools_post.json')
        else:
            body = self.fixtures.load('regions_us-central1_targetPools.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_targetInstances_lctargetinstance(
            self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances_lctargetinstance_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_targetInstances_lctargetinstance.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lb_pool_getHealth(self, method, url,
                                                           body, headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lb_pool_getHealth.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lb_pool(self, method, url, body,
                                                 headers):
        body = self.fixtures.load(
            'regions_us-central1_targetPools_lb_pool.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_targetPools_lctargetpool(self, method, url, body,
                                                      headers):
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

    def _regions_us_central1_targetPools_backup_pool(self, method, url, body,
                                                     headers):
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

    def _regions_us_central1_targetPools_lb_pool_setBackup(self, method, url,
                                                           body, headers):
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

    def _zones_asia_east_1a(self, method, url, body, headers):
        body = self.fixtures.load('zones_asia-east1-a.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_asia_east1_b(self, method, url, body, headers):
        body = self.fixtures.load('zones_asia-east1-b.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_east1_b(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-east1-b.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_diskTypes(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-central1-a_diskTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_diskTypes_pd_standard(self, method, url, body,
                                                   headers):
        body = self.fixtures.load(
            'zones_us-central1-a_diskTypes_pd_standard.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_diskTypes_pd_ssd(self, method, url, body,
                                              headers):
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

    def _zones_us_central1_a_disks_lcdisk_resize(self, method, url,
                                                 body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_disks_lcdisk_resize_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcdisk_setLabels(self, method, url,
                                                    body, header):
        body = self.fixtures.load(
            'zones_us-central1-a_disks_lcdisk_setLabel_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_node_name(self, method, url, body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcnode_000(self, method, url, body,
                                              headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcnode_001(self, method, url, body,
                                              headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_000(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_001(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_disks_libcloud_lb_demo_www_002(self, method, url,
                                                            body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_boot_disk(self, method, url,
                                                           body, headers):
        body = self.fixtures.load('generic_disk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central2_a_disks_libcloud_demo_np_node(self, method, url,
                                                         body, headers):
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

    def _zones_europe_west1_a_diskTypes_pd_standard(self, method, url, body,
                                                    headers):
        body = self.fixtures.load(
            'zones_europe-west1-a_diskTypes_pd_standard.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_sn_node_name(self, method, url, body,
                                                    headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_sn-node-name.json')
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

    def _zones_us_central1_a_instances_node_name_attachDisk(self, method, url,
                                                            body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_attachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_detachDisk(self, method, url,
                                                            body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_detachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setTags(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_setTags_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_reset(self, method, url, body,
                                                       headers):
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

    def _zones_us_central1_b_instances_libcloud_lb_nopubip_001(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instances_libcloud-lb-nopubip-001.json')
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

    def _zones_us_central1_a_instanceGroups_myinstancegroup(self, method, url,
                                                            body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instanceGroup_myinstancegroup.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myinstancegroup2(self, method, url,
                                                             body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instanceGroup_myinstancegroup2.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_instanceGroups_myinstancegroup(self, method, url,
                                                            body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instanceGroup_myinstancegroup.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_east1_b_instanceGroups_myinstancegroup(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'zones_us-east1-b_instanceGroup_myinstancegroup.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myinstancegroup_shared_network(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instanceGroup_myinstancegroup_shared_network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroupManagers_myinstancegroup(
            self, method, url, body, headers):
        if method == 'PATCH':
            # test_ex_instancegroupmanager_set_autohealing_policies
            body = self.fixtures.load(
                'zones_us-central1-a_operations_operation_zones_us-central1-a_instanceGroupManagers_insert_post.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instanceGroupManagers_myinstancegroup.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroupManagers_myinstancegroup_shared_network(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instanceGroupManagers_myinstancegroup_shared_network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_b_instanceGroupManagers_myinstancegroup(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-b_instanceGroupManagers_myinstancegroup.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroupManagers_myinstancegroup_listManagedInstances(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_zones_us_central1_a_instanceGroupManagers_myinstancegroup_listManagedInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_east1_b_instanceGroupManagers(self, method, url, body,
                                                headers):
        body = self.fixtures.load(
            'zones_us-east1-b_instanceGroupManagers.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroupManagers(self, method, url, body,
                                                   headers):
        # do an insert.  Returns an operations link, which then
        # returns the MIG URI.
        if method == 'POST':
            body = self.fixtures.load(
                'zones_us-central1-a_instanceGroupManagers_insert.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instanceGroupManagers.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroupManagers_insert_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_operations_operation_zones_us-central1-a_instanceGroupManagers_insert_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_instanceTemplates(self, method, url, body, headers):
        if method == 'POST':
            # insert
            body = self.fixtures.load('global_instanceTemplates_insert.json')
        else:
            # get or list call
            body = self.fixtures.load('global_instanceTemplates.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_instanceTemplates_my_instance_template1_insert(
            self, method, url, body, headers):
        """ Redirects from _global_instanceTemplates """
        body = self.fixtures.load(
            'operations_operation_global_instanceTemplates_insert.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_instanceTemplates_my_instance_template1(self, method, url,
                                                        body, headers):
        body = self.fixtures.load(
            'global_instanceTemplates_my_instance_template1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_instanceTemplates_my_instance_template_shared_network(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'global_instanceTemplates_my_instance_template_shared_network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_autoscalers(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_autoscalers.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_sslCertificates(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_sslcertificates_post.json')
        else:
            body = self.fixtures.load('global_sslcertificates.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_sslCertificates_example(self, method, url, body, headers):
        body = self.fixtures.load('global_sslcertificates_example.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_sslcertificates_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_sslcertificates_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myname(self, method, url, body,
                                                   headers):
        if method == 'DELETE':
            # delete
            body = self.fixtures.load(
                'zones_us_central1_a_instanceGroups_myname_delete.json')
        else:
            # get or list call
            body = self.fixtures.load(
                'zones_us_central1_a_instanceGroups_myname.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroups_myname_delete(
            self, method, url, body, headers):
        """ Redirects from _zones_us_central1_a_instanceGroups_myname """
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_instanceGroups_myname_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups(self, method, url, body, headers):
        if method == 'POST':
            # insert
            body = self.fixtures.load(
                'zones_us_central1_a_instanceGroups_insert.json')
        else:
            # get or list call
            body = self.fixtures.load(
                'zones_us_central1_a_instanceGroups.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroups_myname_insert(
            self, method, url, body, headers):
        """ Redirects from _zones_us_central1_a_instanceGroups """
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_instanceGroups_insert.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myname_listInstances(
            self, method, url, body, headers):
        # POST
        body = self.fixtures.load(
            'zones_us_central1_a_instanceGroups_myname_listInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myname_addInstances(
            self, method, url, body, headers):
        # POST
        body = self.fixtures.load(
            'zones_us_central1_a_instanceGroups_myname_addInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroups_myname_addInstances(
            self, method, url, body, headers):
        """ Redirects from _zones_us_central1_a_instanceGroups_myname_addInstances """
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_instanceGroups_myname_addInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myname_removeInstances(
            self, method, url, body, headers):
        # POST
        body = self.fixtures.load(
            'zones_us_central1_a_instanceGroups_myname_removeInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroups_myname_removeInstances(
            self, method, url, body, headers):
        """ Redirects from _zones_us_central1_a_instanceGroups_myname_removeInstances """
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_instanceGroups_myname_removeInstances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instanceGroups_myname_setNamedPorts(
            self, method, url, body, headers):
        # POST
        body = self.fixtures.load(
            'zones_us_central1_a_instanceGroups_myname_setNamedPorts.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instanceGroups_myname_setNamedPorts(
            self, method, url, body, headers):
        """ Redirects from _zones_us_central1_a_instanceGroups_myname_setNamedPorts """
        body = self.fixtures.load(
            'operations_operation_zones_us_central1_a_instanceGroups_myname_setNamedPorts.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
