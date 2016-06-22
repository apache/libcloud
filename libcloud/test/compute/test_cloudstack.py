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

from libcloud.compute.base import NodeLocation
from libcloud.common.types import ProviderError
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver, \
    CloudStackAffinityGroupType
from libcloud.compute.types import LibcloudError, Provider, InvalidCredsError
from libcloud.compute.types import KeyPairDoesNotExistError
from libcloud.compute.types import NodeState
from libcloud.compute.providers import get_driver

from libcloud.test import unittest
from libcloud.test import MockHttpTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures


class CloudStackCommonTestCase(TestCaseMixin):
    driver_klass = CloudStackNodeDriver

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = \
            (None, CloudStackMockHttp)
        self.driver = self.driver_klass('apikey', 'secret',
                                        path='/test/path',
                                        host='api.dummy.com')
        self.driver.path = '/test/path'
        self.driver.type = -1
        CloudStackMockHttp.type = None
        CloudStackMockHttp.fixture_tag = 'default'
        self.driver.connection.poll_interval = 0.0

    def test_invalid_credentials(self):
        CloudStackMockHttp.type = 'invalid_credentials'
        driver = self.driver_klass('invalid', 'invalid', path='/test/path',
                                   host='api.dummy.com')
        self.assertRaises(InvalidCredsError, driver.list_nodes)

    def test_import_keypair_from_string_api_error(self):
        CloudStackMockHttp.type = 'api_error'

        name = 'test-pair'
        key_material = ''

        expected_msg = 'Public key is invalid'
        self.assertRaisesRegexp(ProviderError, expected_msg,
                                self.driver.import_key_pair_from_string,
                                name=name, key_material=key_material)

    def test_create_node_immediate_failure(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        CloudStackMockHttp.fixture_tag = 'deployfail'
        self.assertRaises(
            Exception,
            self.driver.create_node,
            name='node-name', image=image, size=size)

    def test_create_node_delayed_failure(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        CloudStackMockHttp.fixture_tag = 'deployfail2'
        self.assertRaises(
            Exception,
            self.driver.create_node,
            name='node-name', image=image, size=size)

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
        self.assertEqual(node.extra['zone_id'], default_location.id)

    def test_create_node_ex_networks(self):
        CloudStackMockHttp.fixture_tag = 'deploynetworks'
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]

        networks = [nw for nw in self.driver.ex_list_networks()
                    if str(nw.zoneid) == str(location.id)]

        node = self.driver.create_node(name='deploynetworks',
                                       location=location,
                                       image=image,
                                       size=size,
                                       networks=networks)
        self.assertEqual(node.name, 'deploynetworks')
        self.assertEqual(node.extra['size_id'], size.id)
        self.assertEqual(node.extra['zone_id'], location.id)
        self.assertEqual(node.extra['image_id'], image.id)
        self.assertEqual(len(node.private_ips), 2)

    def test_create_node_ex_ipaddress(self):
        CloudStackMockHttp.fixture_tag = 'deployip'
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        ipaddress = '10.1.0.128'

        networks = [nw for nw in self.driver.ex_list_networks()
                    if str(nw.zoneid) == str(location.id)]

        node = self.driver.create_node(name='deployip',
                                       location=location,
                                       image=image,
                                       size=size,
                                       networks=networks,
                                       ex_ip_address=ipaddress)
        self.assertEqual(node.name, 'deployip')
        self.assertEqual(node.extra['size_id'], size.id)
        self.assertEqual(node.extra['zone_id'], location.id)
        self.assertEqual(node.extra['image_id'], image.id)
        self.assertEqual(node.private_ips[0], ipaddress)

    def test_create_node_ex_rootdisksize(self):
        CloudStackMockHttp.fixture_tag = 'rootdisksize'
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        volumes = self.driver.list_volumes()
        rootdisksize = '50'

        networks = [nw for nw in self.driver.ex_list_networks()
                    if str(nw.zoneid) == str(location.id)]

        node = self.driver.create_node(name='rootdisksize',
                                       location=location,
                                       image=image,
                                       size=size,
                                       networks=networks,
                                       ex_rootdisksize=rootdisksize)
        self.assertEqual(node.name, 'rootdisksize')
        self.assertEqual(node.extra['size_id'], size.id)
        self.assertEqual(node.extra['zone_id'], location.id)
        self.assertEqual(node.extra['image_id'], image.id)
        self.assertEqual(1, len(volumes))
        self.assertEqual('ROOT-69941', volumes[0].name)
        self.assertEqual(53687091200, volumes[0].size)

    def test_create_node_ex_start_vm_false(self):
        CloudStackMockHttp.fixture_tag = 'stoppedvm'
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]

        networks = [nw for nw in self.driver.ex_list_networks()
                    if str(nw.zoneid) == str(location.id)]

        node = self.driver.create_node(name='stopped_vm',
                                       location=location,
                                       image=image,
                                       size=size,
                                       networks=networks,
                                       ex_start_vm=False)
        self.assertEqual(node.name, 'stopped_vm')
        self.assertEqual(node.extra['size_id'], size.id)
        self.assertEqual(node.extra['zone_id'], location.id)
        self.assertEqual(node.extra['image_id'], image.id)

        self.assertEqual(node.state, NodeState.STOPPED)

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
        self.assertEqual(node.extra['security_group'], sg)
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
        self.assertEqual(node.extra['key_name'], 'foobar')

    def test_create_node_ex_userdata(self):
        self.driver.path = '/test/path/userdata'
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        CloudStackMockHttp.fixture_tag = 'deploykeyname'
        node = self.driver.create_node(name='test',
                                       location=location,
                                       image=image,
                                       size=size,
                                       ex_userdata='foobar')
        self.assertEqual(node.name, 'test')

    def test_create_node_project(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        location = self.driver.list_locations()[0]
        project = self.driver.ex_list_projects()[0]
        CloudStackMockHttp.fixture_tag = 'deployproject'
        node = self.driver.create_node(name='test',
                                       location=location,
                                       image=image,
                                       size=size,
                                       project=project)
        self.assertEqual(node.name, 'TestNode')
        self.assertEqual(node.extra['project'], 'Test Project')

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

    def test_ex_list_network_offerings(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listNetworkOfferings_default.json')
        fixture_networkoffers = \
            fixture['listnetworkofferingsresponse']['networkoffering']

        networkoffers = self.driver.ex_list_network_offerings()

        for i, networkoffer in enumerate(networkoffers):
            self.assertEqual(networkoffer.id, fixture_networkoffers[i]['id'])
            self.assertEqual(networkoffer.name,
                             fixture_networkoffers[i]['name'])
            self.assertEqual(networkoffer.display_text,
                             fixture_networkoffers[i]['displaytext'])
            self.assertEqual(networkoffer.for_vpc,
                             fixture_networkoffers[i]['forvpc'])
            self.assertEqual(networkoffer.guest_ip_type,
                             fixture_networkoffers[i]['guestiptype'])
            self.assertEqual(networkoffer.service_offering_id,
                             fixture_networkoffers[i]['serviceofferingid'])

    def test_ex_create_network(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'createNetwork_default.json')

        fixture_network = fixture['createnetworkresponse']['network']

        netoffer = self.driver.ex_list_network_offerings()[0]
        location = self.driver.list_locations()[0]
        network = self.driver.ex_create_network(display_text='test',
                                                name='test',
                                                network_offering=netoffer,
                                                location=location,
                                                gateway='10.1.1.1',
                                                netmask='255.255.255.0',
                                                network_domain='cloud.local',
                                                vpc_id="2",
                                                project_id="2")

        self.assertEqual(network.name, fixture_network['name'])
        self.assertEqual(network.displaytext, fixture_network['displaytext'])
        self.assertEqual(network.id, fixture_network['id'])
        self.assertEqual(network.extra['gateway'], fixture_network['gateway'])
        self.assertEqual(network.extra['netmask'], fixture_network['netmask'])
        self.assertEqual(network.networkofferingid,
                         fixture_network['networkofferingid'])
        self.assertEqual(network.extra['vpc_id'], fixture_network['vpcid'])
        self.assertEqual(network.extra['project_id'],
                         fixture_network['projectid'])

    def test_ex_delete_network(self):

        network = self.driver.ex_list_networks()[0]

        result = self.driver.ex_delete_network(network=network)
        self.assertTrue(result)

    def test_ex_list_nics(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listNics_default.json')

        fixture_nic = fixture['listnicsresponse']['nic']
        vm = self.driver.list_nodes()[0]
        nics = self.driver.ex_list_nics(vm)

        for i, nic in enumerate(nics):
            self.assertEqual(nic.id, fixture_nic[i]['id'])
            self.assertEqual(nic.network_id,
                             fixture_nic[i]['networkid'])
            self.assertEqual(nic.net_mask,
                             fixture_nic[i]['netmask'])
            self.assertEqual(nic.gateway,
                             fixture_nic[i]['gateway'])
            self.assertEqual(nic.ip_address,
                             fixture_nic[i]['ipaddress'])
            self.assertEqual(nic.is_default,
                             fixture_nic[i]['isdefault'])
            self.assertEqual(nic.mac_address,
                             fixture_nic[i]['macaddress'])

    def test_ex_add_nic_to_node(self):

        vm = self.driver.list_nodes()[0]
        network = self.driver.ex_list_networks()[0]
        ip = "10.1.4.123"

        result = self.driver.ex_attach_nic_to_node(node=vm, network=network, ip_address=ip)
        self.assertTrue(result)

    def test_ex_remove_nic_from_node(self):

        vm = self.driver.list_nodes()[0]
        nic = self.driver.ex_list_nics(node=vm)[0]

        result = self.driver.ex_detach_nic_from_node(node=vm, nic=nic)
        self.assertTrue(result)

    def test_ex_list_vpc_offerings(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listVPCOfferings_default.json')
        fixture_vpcoffers = \
            fixture['listvpcofferingsresponse']['vpcoffering']

        vpcoffers = self.driver.ex_list_vpc_offerings()

        for i, vpcoffer in enumerate(vpcoffers):
            self.assertEqual(vpcoffer.id, fixture_vpcoffers[i]['id'])
            self.assertEqual(vpcoffer.name,
                             fixture_vpcoffers[i]['name'])
            self.assertEqual(vpcoffer.display_text,
                             fixture_vpcoffers[i]['displaytext'])

    def test_ex_list_vpcs(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listVPCs_default.json')
        fixture_vpcs = fixture['listvpcsresponse']['vpc']

        vpcs = self.driver.ex_list_vpcs()

        for i, vpc in enumerate(vpcs):
            self.assertEqual(vpc.id, fixture_vpcs[i]['id'])
            self.assertEqual(vpc.display_text, fixture_vpcs[i]['displaytext'])
            self.assertEqual(vpc.name, fixture_vpcs[i]['name'])
            self.assertEqual(vpc.vpc_offering_id,
                             fixture_vpcs[i]['vpcofferingid'])
            self.assertEqual(vpc.zone_id, fixture_vpcs[i]['zoneid'])

    def test_ex_list_routers(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listRouters_default.json')
        fixture_routers = fixture['listroutersresponse']['router']

        routers = self.driver.ex_list_routers()

        for i, router in enumerate(routers):
            self.assertEqual(router.id, fixture_routers[i]['id'])
            self.assertEqual(router.name, fixture_routers[i]['name'])
            self.assertEqual(router.state, fixture_routers[i]['state'])
            self.assertEqual(router.public_ip, fixture_routers[i]['publicip'])
            self.assertEqual(router.vpc_id, fixture_routers[i]['vpcid'])

    def test_ex_create_vpc(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'createVPC_default.json')

        fixture_vpc = fixture['createvpcresponse']

        vpcoffer = self.driver.ex_list_vpc_offerings()[0]
        vpc = self.driver.ex_create_vpc(cidr='10.1.1.0/16',
                                        display_text='cloud.local',
                                        name='cloud.local',
                                        vpc_offering=vpcoffer,
                                        zone_id="2")

        self.assertEqual(vpc.id, fixture_vpc['id'])

    def test_ex_delete_vpc(self):

        vpc = self.driver.ex_list_vpcs()[0]

        result = self.driver.ex_delete_vpc(vpc=vpc)
        self.assertTrue(result)

    def test_ex_create_network_acllist(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'createNetworkACLList_default.json')

        fixture_network_acllist = fixture['createnetworkacllistresponse']

        vpc = self.driver.ex_list_vpcs()[0]
        network_acllist = self.driver.ex_create_network_acllist(
            name='test_acllist',
            vpc_id=vpc.id,
            description='test description')

        self.assertEqual(network_acllist.id, fixture_network_acllist['id'])

    def test_ex_list_network_acllist(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listNetworkACLLists_default.json')
        fixture_acllist = \
            fixture['listnetworkacllistsresponse']['networkacllist']

        acllist = self.driver.ex_list_network_acllists()

        for i, acllist in enumerate(acllist):
            self.assertEqual(acllist.id,
                             fixture_acllist[i]['id'])
            self.assertEqual(acllist.name,
                             fixture_acllist[i]['name'])
            self.assertEqual(acllist.description,
                             fixture_acllist[i]['description'])

    def test_ex_create_network_acl(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'createNetworkACL_default.json')

        fixture_network_acllist = fixture['createnetworkaclresponse']

        acllist = self.driver.ex_list_network_acllists()[0]

        network_acl = self.driver.ex_create_network_acl(
            protocol='test_acllist',
            acl_id=acllist.id,
            cidr_list='',
            start_port='80',
            end_port='80')

        self.assertEqual(network_acl.id, fixture_network_acllist['id'])

    def test_ex_list_projects(self):
        _, fixture = CloudStackMockHttp()._load_fixture(
            'listProjects_default.json')
        fixture_projects = fixture['listprojectsresponse']['project']

        projects = self.driver.ex_list_projects()

        for i, project in enumerate(projects):
            self.assertEqual(project.id, fixture_projects[i]['id'])
            self.assertEqual(
                project.display_text, fixture_projects[i]['displaytext'])
            self.assertEqual(project.name, fixture_projects[i]['name'])
            self.assertEqual(
                project.extra['domainid'],
                fixture_projects[i]['domainid'])
            self.assertEqual(
                project.extra['cpulimit'],
                fixture_projects[i]['cpulimit'])
            # Note -1 represents unlimited
            self.assertEqual(project.extra['networklimit'], -1)

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

    def test_create_volume_no_matching_volume_type(self):
        """If the ex_disk_type does not exit, then an exception should be
        thrown."""

        location = self.driver.list_locations()[0]

        self.assertRaises(
            LibcloudError,
            self.driver.create_volume,
            'vol-0', location, 11, ex_volume_type='FooVolumeType')

    def test_create_volume_with_defined_volume_type(self):
        CloudStackMockHttp.fixture_tag = 'withvolumetype'

        volumeName = 'vol-0'
        volLocation = self.driver.list_locations()[0]
        diskOffering = self.driver.ex_list_disk_offerings()[0]
        volumeType = diskOffering.name

        volume = self.driver.create_volume(10, volumeName, location=volLocation,
                                           ex_volume_type=volumeType)

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

    def test_ex_get_volume(self):
        volume = self.driver.ex_get_volume(2600)
        self.assertEqual('ROOT-69942', volume.name)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(2, len(nodes))
        self.assertEqual('test', nodes[0].name)
        self.assertEqual('2600', nodes[0].id)
        self.assertEqual(0, len(nodes[0].private_ips))
        self.assertEqual([], nodes[0].extra['security_group'])
        self.assertEqual(None, nodes[0].extra['key_name'])
        self.assertEqual(1, len(nodes[0].public_ips))
        self.assertEqual('1.1.1.116', nodes[0].public_ips[0])
        self.assertEqual(1, len(nodes[0].extra['ip_addresses']))
        self.assertEqual(34000, nodes[0].extra['ip_addresses'][0].id)
        self.assertEqual(1, len(nodes[0].extra['ip_forwarding_rules']))
        self.assertEqual('772fd410-6649-43ed-befa-77be986b8906',
                         nodes[0].extra['ip_forwarding_rules'][0].id)
        self.assertEqual(1, len(nodes[0].extra['port_forwarding_rules']))
        self.assertEqual('bc7ea3ee-a2c3-4b86-a53f-01bdaa1b2e32',
                         nodes[0].extra['port_forwarding_rules'][0].id)
        self.assertEqual({"testkey": "testvalue", "foo": "bar"},
                         nodes[0].extra['tags'])

    def test_list_nodes_location_filter(self):
        def list_nodes_mock(self, **kwargs):
            self.assertTrue('zoneid' in kwargs)
            self.assertEqual('1', kwargs.get('zoneid'))

            body, obj = self._load_fixture('listVirtualMachines_default.json')
            return (httplib.OK, body, obj, httplib.responses[httplib.OK])

        CloudStackMockHttp._cmd_listVirtualMachines = list_nodes_mock
        try:
            location = NodeLocation(1, 'Sydney', 'Unknown', self.driver)
            self.driver.list_nodes(location=location)
        finally:
            del CloudStackMockHttp._cmd_listVirtualMachines

    def test_ex_get_node(self):
        node = self.driver.ex_get_node(2600)
        self.assertEqual('test', node.name)
        self.assertEqual('2600', node.id)
        self.assertEqual([], node.extra['security_group'])
        self.assertEqual(None, node.extra['key_name'])
        self.assertEqual(1, len(node.public_ips))
        self.assertEqual('1.1.1.116', node.public_ips[0])
        self.assertEqual(1, len(node.extra['ip_addresses']))
        self.assertEqual(34000, node.extra['ip_addresses'][0].id)

    def test_ex_get_node_doesnt_exist(self):
        self.assertRaises(Exception, self.driver.ex_get_node(26), node_id=26)

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

    def test_expunge_node(self):
        node = self.driver.list_nodes()[0]
        res = self.driver.destroy_node(node, ex_expunge=True)
        self.assertTrue(res)

    def test_reboot_node(self):
        node = self.driver.list_nodes()[0]
        res = node.reboot()
        self.assertTrue(res)

    def test_list_key_pairs(self):
        keypairs = self.driver.list_key_pairs()
        fingerprint = '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:' + \
                      '00:00:00:00:00'

        self.assertEqual(keypairs[0].name, 'cs-keypair')
        self.assertEqual(keypairs[0].fingerprint, fingerprint)

        # Test old and deprecated way
        keypairs = self.driver.ex_list_keypairs()

        self.assertEqual(keypairs[0]['name'], 'cs-keypair')
        self.assertEqual(keypairs[0]['fingerprint'], fingerprint)

    def test_list_key_pairs_no_keypair_key(self):
        CloudStackMockHttp.fixture_tag = 'no_keys'
        keypairs = self.driver.list_key_pairs()
        self.assertEqual(keypairs, [])

    def test_get_key_pair(self):
        CloudStackMockHttp.fixture_tag = 'get_one'
        key_pair = self.driver.get_key_pair(name='cs-keypair')
        self.assertEqual(key_pair.name, 'cs-keypair')

    def test_get_key_pair_doesnt_exist(self):
        CloudStackMockHttp.fixture_tag = 'get_one_doesnt_exist'

        self.assertRaises(KeyPairDoesNotExistError, self.driver.get_key_pair,
                          name='does-not-exist')

    def test_create_keypair(self):
        key_pair = self.driver.create_key_pair(name='test-keypair')

        self.assertEqual(key_pair.name, 'test-keypair')
        self.assertTrue(key_pair.fingerprint is not None)
        self.assertTrue(key_pair.private_key is not None)

        # Test old and deprecated way
        res = self.driver.ex_create_keypair(name='test-keypair')
        self.assertEqual(res['name'], 'test-keypair')
        self.assertTrue(res['fingerprint'] is not None)
        self.assertTrue(res['privateKey'] is not None)

    def test_import_keypair_from_file(self):
        fingerprint = 'c4:a1:e5:d4:50:84:a9:4c:6b:22:ee:d6:57:02:b8:15'
        path = os.path.join(os.path.dirname(__file__), 'fixtures',
                            'cloudstack',
                            'dummy_rsa.pub')

        key_pair = self.driver.import_key_pair_from_file('foobar', path)
        self.assertEqual(key_pair.name, 'foobar')
        self.assertEqual(key_pair.fingerprint, fingerprint)

        # Test old and deprecated way
        res = self.driver.ex_import_keypair('foobar', path)
        self.assertEqual(res['keyName'], 'foobar')
        self.assertEqual(res['keyFingerprint'], fingerprint)

    def test_ex_import_keypair_from_string(self):
        fingerprint = 'c4:a1:e5:d4:50:84:a9:4c:6b:22:ee:d6:57:02:b8:15'
        path = os.path.join(os.path.dirname(__file__), 'fixtures',
                            'cloudstack',
                            'dummy_rsa.pub')
        fh = open(path)
        key_material = fh.read()
        fh.close()

        key_pair = self.driver.import_key_pair_from_string('foobar', key_material=key_material)
        self.assertEqual(key_pair.name, 'foobar')
        self.assertEqual(key_pair.fingerprint, fingerprint)

        # Test old and deprecated way
        res = self.driver.ex_import_keypair_from_string('foobar', key_material=key_material)
        self.assertEqual(res['keyName'], 'foobar')
        self.assertEqual(res['keyFingerprint'], fingerprint)

    def test_delete_key_pair(self):
        key_pair = self.driver.list_key_pairs()[0]

        res = self.driver.delete_key_pair(key_pair=key_pair)
        self.assertTrue(res)

        # Test old and deprecated way
        res = self.driver.ex_delete_keypair(keypair='cs-keypair')
        self.assertTrue(res)

    def test_ex_list_security_groups(self):
        groups = self.driver.ex_list_security_groups()
        self.assertEqual(2, len(groups))
        self.assertEqual(groups[0]['name'], 'default')
        self.assertEqual(groups[1]['name'], 'mongodb')

    def test_ex_list_security_groups_no_securitygroup_key(self):
        CloudStackMockHttp.fixture_tag = 'no_groups'

        groups = self.driver.ex_list_security_groups()
        self.assertEqual(groups, [])

    def test_ex_create_security_group(self):
        group = self.driver.ex_create_security_group(name='MySG')
        self.assertEqual(group['name'], 'MySG')

    def test_ex_delete_security_group(self):
        res = self.driver.ex_delete_security_group(name='MySG')
        self.assertTrue(res)

    def test_ex_authorize_security_group_ingress(self):
        res = self.driver.ex_authorize_security_group_ingress('test_sg',
                                                              'udp',
                                                              '0.0.0.0/0',
                                                              '0',
                                                              '65535')
        self.assertEqual(res.get('name'), 'test_sg')
        self.assertTrue('ingressrule' in res)
        rules = res['ingressrule']
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule['cidr'], '0.0.0.0/0')
        self.assertEqual(rule['endport'], 65535)
        self.assertEqual(rule['protocol'], 'udp')
        self.assertEqual(rule['startport'], 0)

    def test_ex_create_affinity_group(self):
        res = self.driver.ex_create_affinity_group('MyAG2',
                                                   CloudStackAffinityGroupType('MyAGType'))
        self.assertEqual(res.name, 'MyAG2')
        self.assertIsInstance(res.type, CloudStackAffinityGroupType)
        self.assertEqual(res.type.type, 'MyAGType')

    def test_ex_create_affinity_group_already_exists(self):
        self.assertRaises(LibcloudError,
                          self.driver.ex_create_affinity_group,
                          'MyAG', CloudStackAffinityGroupType('MyAGType'))

    def test_delete_ex_affinity_group(self):
        afg = self.driver.ex_create_affinity_group('MyAG3',
                                                   CloudStackAffinityGroupType('MyAGType'))
        res = self.driver.ex_delete_affinity_group(afg)
        self.assertTrue(res)

    def test_ex_update_node_affinity_group(self):
        affinity_group_list = self.driver.ex_list_affinity_groups()
        nodes = self.driver.list_nodes()
        node = self.driver.ex_update_node_affinity_group(nodes[0],
                                                         affinity_group_list)
        self.assertEqual(node.extra['affinity_group'][0],
                         affinity_group_list[0].id)

    def test_ex_list_affinity_groups(self):
        res = self.driver.ex_list_affinity_groups()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, '11112')
        self.assertEqual(res[0].name, 'MyAG')
        self.assertIsInstance(res[0].type, CloudStackAffinityGroupType)
        self.assertEqual(res[0].type.type, 'MyAGType')

    def test_ex_list_affinity_group_types(self):
        res = self.driver.ex_list_affinity_group_types()
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], CloudStackAffinityGroupType)
        self.assertEqual(res[0].type, 'MyAGType')

    def test_ex_list_public_ips(self):
        ips = self.driver.ex_list_public_ips()
        self.assertEqual(ips[0].address, '1.1.1.116')
        self.assertEqual(ips[0].virtualmachine_id, '2600')

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
        rule = self.driver.ex_create_port_forwarding_rule(node,
                                                          address,
                                                          private_port,
                                                          public_port,
                                                          protocol,
                                                          public_end_port,
                                                          private_end_port,
                                                          openfirewall)
        self.assertEqual(rule.address, address)
        self.assertEqual(rule.protocol, protocol)
        self.assertEqual(rule.public_port, public_port)
        self.assertEqual(rule.public_end_port, public_end_port)
        self.assertEqual(rule.private_port, private_port)
        self.assertEqual(rule.private_end_port, private_end_port)

    def test_ex_list_firewall_rules(self):
        rules = self.driver.ex_list_firewall_rules()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.address.address, '1.1.1.116')
        self.assertEqual(rule.protocol, 'tcp')
        self.assertEqual(rule.cidr_list, '192.168.0.0/16')
        self.assertIsNone(rule.icmp_code)
        self.assertIsNone(rule.icmp_type)
        self.assertEqual(rule.start_port, '33')
        self.assertEqual(rule.end_port, '34')

    def test_ex_list_firewall_rules_icmp(self):
        CloudStackMockHttp.fixture_tag = 'firewallicmp'
        rules = self.driver.ex_list_firewall_rules()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.address.address, '1.1.1.116')
        self.assertEqual(rule.protocol, 'icmp')
        self.assertEqual(rule.cidr_list, '192.168.0.0/16')
        self.assertEqual(rule.icmp_code, 0)
        self.assertEqual(rule.icmp_type, 8)
        self.assertIsNone(rule.start_port)
        self.assertIsNone(rule.end_port)

    def test_ex_delete_firewall_rule(self):
        rules = self.driver.ex_list_firewall_rules()
        res = self.driver.ex_delete_firewall_rule(rules[0])
        self.assertTrue(res)

    def test_ex_create_firewall_rule(self):
        address = self.driver.ex_list_public_ips()[0]
        cidr_list = '192.168.0.0/16'
        protocol = 'TCP'
        start_port = 33
        end_port = 34
        rule = self.driver.ex_create_firewall_rule(address,
                                                   cidr_list,
                                                   protocol,
                                                   start_port=start_port,
                                                   end_port=end_port)
        self.assertEqual(rule.address, address)
        self.assertEqual(rule.protocol, protocol)
        self.assertIsNone(rule.icmp_code)
        self.assertIsNone(rule.icmp_type)
        self.assertEqual(rule.start_port, start_port)
        self.assertEqual(rule.end_port, end_port)

    def test_ex_create_firewall_rule_icmp(self):
        address = self.driver.ex_list_public_ips()[0]
        cidr_list = '192.168.0.0/16'
        protocol = 'icmp'
        icmp_code = 0
        icmp_type = 8
        rule = self.driver.ex_create_firewall_rule(address,
                                                   cidr_list,
                                                   protocol,
                                                   icmp_code=icmp_code,
                                                   icmp_type=icmp_type)
        self.assertEqual(rule.address, address)
        self.assertEqual(rule.protocol, protocol)
        self.assertEqual(rule.icmp_code, 0)
        self.assertEqual(rule.icmp_type, 8)
        self.assertIsNone(rule.start_port)
        self.assertIsNone(rule.end_port)

    def test_ex_list_egress_firewall_rules(self):
        rules = self.driver.ex_list_egress_firewall_rules()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.network_id, '874be2ca-20a7-4360-80e9-7356c0018c0b')
        self.assertEqual(rule.cidr_list, '192.168.0.0/16')
        self.assertEqual(rule.protocol, 'tcp')
        self.assertIsNone(rule.icmp_code)
        self.assertIsNone(rule.icmp_type)
        self.assertEqual(rule.start_port, '80')
        self.assertEqual(rule.end_port, '80')

    def test_ex_delete_egress_firewall_rule(self):
        rules = self.driver.ex_list_egress_firewall_rules()
        res = self.driver.ex_delete_egress_firewall_rule(rules[0])
        self.assertTrue(res)

    def test_ex_create_egress_firewall_rule(self):
        network_id = '874be2ca-20a7-4360-80e9-7356c0018c0b'
        cidr_list = '192.168.0.0/16'
        protocol = 'TCP'
        start_port = 33
        end_port = 34
        rule = self.driver.ex_create_egress_firewall_rule(
            network_id,
            cidr_list,
            protocol,
            start_port=start_port,
            end_port=end_port)

        self.assertEqual(rule.network_id, network_id)
        self.assertEqual(rule.cidr_list, cidr_list)
        self.assertEqual(rule.protocol, protocol)
        self.assertIsNone(rule.icmp_code)
        self.assertIsNone(rule.icmp_type)
        self.assertEqual(rule.start_port, start_port)
        self.assertEqual(rule.end_port, end_port)

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

    def test_node_ex_delete_port_forwarding_rule(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(len(node.extra['port_forwarding_rules']), 1)
        node.extra['port_forwarding_rules'][0].delete()
        self.assertEqual(len(node.extra['port_forwarding_rules']), 0)

    def test_node_ex_create_port_forwarding_rule(self):
        node = self.driver.list_nodes()[0]
        self.assertEqual(len(node.extra['port_forwarding_rules']), 1)
        address = self.driver.ex_list_public_ips()[0]
        private_port = 33
        private_end_port = 34
        public_port = 33
        public_end_port = 34
        openfirewall = True
        protocol = 'TCP'
        rule = node.ex_create_port_forwarding_rule(address,
                                                   private_port,
                                                   public_port,
                                                   protocol,
                                                   public_end_port,
                                                   private_end_port,
                                                   openfirewall)
        self.assertEqual(rule.address, address)
        self.assertEqual(rule.protocol, protocol)
        self.assertEqual(rule.public_port, public_port)
        self.assertEqual(rule.public_end_port, public_end_port)
        self.assertEqual(rule.private_port, private_port)
        self.assertEqual(rule.private_end_port, private_end_port)
        self.assertEqual(len(node.extra['port_forwarding_rules']), 2)

    def test_ex_list_ip_forwarding_rules(self):
        rules = self.driver.ex_list_ip_forwarding_rules()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertTrue(rule.node)
        self.assertEqual(rule.protocol, 'tcp')
        self.assertEqual(rule.start_port, 33)
        self.assertEqual(rule.end_port, 34)
        self.assertEqual(rule.address.address, '1.1.1.116')

    def test_ex_limits(self):
        limits = self.driver.ex_limits()
        self.assertEqual(limits['max_images'], 20)
        self.assertEqual(limits['max_networks'], 20)
        self.assertEqual(limits['max_public_ips'], -1)
        self.assertEqual(limits['max_vpc'], 20)
        self.assertEqual(limits['max_instances'], 20)
        self.assertEqual(limits['max_projects'], -1)
        self.assertEqual(limits['max_volumes'], 20)
        self.assertEqual(limits['max_snapshots'], 20)

    def test_ex_create_tags(self):
        node = self.driver.list_nodes()[0]
        tags = {'Region': 'Canada'}
        resp = self.driver.ex_create_tags([node.id], 'UserVm', tags)
        self.assertTrue(resp)

    def test_ex_delete_tags(self):
        node = self.driver.list_nodes()[0]
        tag_keys = ['Region']
        resp = self.driver.ex_delete_tags([node.id], 'UserVm', tag_keys)
        self.assertTrue(resp)

    def test_list_snapshots(self):
        snapshots = self.driver.list_snapshots()
        self.assertEqual(len(snapshots), 3)

        snap = snapshots[0]
        self.assertEqual(snap.id, 188402)
        self.assertEqual(snap.extra['name'], "i-123-87654-VM_ROOT-12344_20140917105548")
        self.assertEqual(snap.extra['volume_id'], 89341)

    def test_create_volume_snapshot(self):
        volume = self.driver.list_volumes()[0]
        snapshot = self.driver.create_volume_snapshot(volume)

        self.assertEqual(snapshot.id, 190547)
        self.assertEqual(snapshot.extra['name'], "i-123-87654-VM_ROOT-23456_20140917105548")
        self.assertEqual(snapshot.extra['volume_id'], "fe1ada16-57a0-40ae-b577-01a153690fb4")

    def test_destroy_volume_snapshot(self):
        snapshot = self.driver.list_snapshots()[0]
        resp = self.driver.destroy_volume_snapshot(snapshot)
        self.assertTrue(resp)

    def test_ex_create_snapshot_template(self):
        snapshot = self.driver.list_snapshots()[0]

        template = self.driver.ex_create_snapshot_template(snapshot, "test-libcloud-template", 99)

        self.assertEqual(template.id, '10260')
        self.assertEqual(template.name, "test-libcloud-template")
        self.assertEqual(template.extra['displaytext'], "test-libcloud-template")
        self.assertEqual(template.extra['hypervisor'], "VMware")
        self.assertEqual(template.extra['os'], "Other Linux (64-bit)")

    def test_ex_list_os_types(self):
        os_types = self.driver.ex_list_os_types()

        self.assertEqual(len(os_types), 146)

        self.assertEqual(os_types[0]['id'], 69)
        self.assertEqual(os_types[0]['oscategoryid'], 7)
        self.assertEqual(os_types[0]['description'], "Asianux 3(32-bit)")

    def test_ex_list_vpn_gateways(self):
        vpn_gateways = self.driver.ex_list_vpn_gateways()

        self.assertEqual(len(vpn_gateways), 1)

        self.assertEqual(vpn_gateways[0].id, 'cffa0cab-d1da-42a7-92f6-41379267a29f')
        self.assertEqual(vpn_gateways[0].account, 'some_account')
        self.assertEqual(vpn_gateways[0].domain, 'some_domain')
        self.assertEqual(vpn_gateways[0].domain_id, '9b397dea-25ef-4c5d-b47d-627eaebe8ed8')
        self.assertEqual(vpn_gateways[0].public_ip, '1.2.3.4')
        self.assertEqual(vpn_gateways[0].vpc_id, '4d25e181-8850-4d52-8ecb-a6f35bbbabde')

    def test_ex_create_vpn_gateway(self):
        vpc = self.driver.ex_list_vpcs()[0]

        vpn_gateway = self.driver.ex_create_vpn_gateway(vpc)

        self.assertEqual(vpn_gateway.id, '5ef6794e-cec8-4018-9fef-c4dacbadee14')
        self.assertEqual(vpn_gateway.account, 'some_account')
        self.assertEqual(vpn_gateway.domain, 'some_domain')
        self.assertEqual(vpn_gateway.domain_id, '9b397dea-25ef-4c5d-b47d-627eaebe8ed8')
        self.assertEqual(vpn_gateway.public_ip, '2.3.4.5')
        self.assertEqual(vpn_gateway.vpc_id, vpc.id)

    def test_ex_delete_vpn_gateway(self):
        vpn_gateway = self.driver.ex_list_vpn_gateways()[0]
        self.assertTrue(vpn_gateway.delete())

    def test_ex_list_vpn_customer_gateways(self):
        vpn_customer_gateways = self.driver.ex_list_vpn_customer_gateways()

        self.assertEqual(len(vpn_customer_gateways), 1)

        self.assertEqual(vpn_customer_gateways[0].id, 'ea67eaae-1c2a-4e65-b910-441e77f69bea')
        self.assertEqual(vpn_customer_gateways[0].cidr_list, '10.2.2.0/24')
        self.assertEqual(vpn_customer_gateways[0].esp_policy, '3des-md5')
        self.assertEqual(vpn_customer_gateways[0].gateway, '10.2.2.1')
        self.assertEqual(vpn_customer_gateways[0].ike_policy, '3des-md5')
        self.assertEqual(vpn_customer_gateways[0].ipsec_psk, 'some_psk')

    def test_ex_create_vpn_customer_gateway(self):
        vpn_customer_gateway = self.driver.ex_create_vpn_customer_gateway(
            cidr_list='10.0.0.0/24',
            esp_policy='3des-md5',
            gateway='10.0.0.1',
            ike_policy='3des-md5',
            ipsec_psk='ipsecpsk')

        self.assertEqual(vpn_customer_gateway.id, 'cef3c766-116a-4e83-9844-7d08ab7d3fd4')
        self.assertEqual(vpn_customer_gateway.esp_policy, '3des-md5')
        self.assertEqual(vpn_customer_gateway.gateway, '10.0.0.1')
        self.assertEqual(vpn_customer_gateway.ike_policy, '3des-md5')
        self.assertEqual(vpn_customer_gateway.ipsec_psk, 'ipsecpsk')

    def test_ex_ex_delete_vpn_customer_gateway(self):
        vpn_customer_gateway = self.driver.ex_list_vpn_customer_gateways()[0]
        self.assertTrue(vpn_customer_gateway.delete())

    def test_ex_list_vpn_connections(self):
        vpn_connections = self.driver.ex_list_vpn_connections()

        self.assertEqual(len(vpn_connections), 1)

        self.assertEqual(vpn_connections[0].id, '8f482d9a-6cee-453b-9e78-b0e1338ffce9')
        self.assertEqual(vpn_connections[0].passive, False)
        self.assertEqual(vpn_connections[0].vpn_customer_gateway_id, 'ea67eaae-1c2a-4e65-b910-441e77f69bea')
        self.assertEqual(vpn_connections[0].vpn_gateway_id, 'cffa0cab-d1da-42a7-92f6-41379267a29f')
        self.assertEqual(vpn_connections[0].state, 'Connected')

    def test_ex_create_vpn_connection(self):
        vpn_customer_gateway = self.driver.ex_list_vpn_customer_gateways()[0]
        vpn_gateway = self.driver.ex_list_vpn_gateways()[0]

        vpn_connection = self.driver.ex_create_vpn_connection(
            vpn_customer_gateway,
            vpn_gateway)

        self.assertEqual(vpn_connection.id, 'f45c3af8-f909-4f16-9d40-ed4409c575f8')
        self.assertEqual(vpn_connection.passive, False)
        self.assertEqual(vpn_connection.vpn_customer_gateway_id, 'ea67eaae-1c2a-4e65-b910-441e77f69bea')
        self.assertEqual(vpn_connection.vpn_gateway_id, 'cffa0cab-d1da-42a7-92f6-41379267a29f')
        self.assertEqual(vpn_connection.state, 'Connected')

    def test_ex_delete_vpn_connection(self):
        vpn_connection = self.driver.ex_list_vpn_connections()[0]
        self.assertTrue(vpn_connection.delete())


class CloudStackTestCase(CloudStackCommonTestCase, unittest.TestCase):
    def test_driver_instantiation(self):
        urls = [
            'http://api.exoscale.ch/compute1',  # http, default port
            'https://api.exoscale.ch/compute2',  # https, default port
            'http://api.exoscale.ch:8888/compute3',  # https, custom port
            'https://api.exoscale.ch:8787/compute4',  # https, custom port
            'https://api.test.com/compute/endpoint'  # https, default port
        ]

        expected_values = [
            {'host': 'api.exoscale.ch', 'port': 80, 'path': '/compute1'},
            {'host': 'api.exoscale.ch', 'port': 443, 'path': '/compute2'},
            {'host': 'api.exoscale.ch', 'port': 8888, 'path': '/compute3'},
            {'host': 'api.exoscale.ch', 'port': 8787, 'path': '/compute4'},
            {'host': 'api.test.com', 'port': 443, 'path': '/compute/endpoint'}
        ]

        cls = get_driver(Provider.CLOUDSTACK)

        for url, expected in zip(urls, expected_values):
            driver = cls('key', 'secret', url=url)

            self.assertEqual(driver.host, expected['host'])
            self.assertEqual(driver.path, expected['path'])
            self.assertEqual(driver.connection.port, expected['port'])

    def test_user_must_provide_host_and_path_or_url(self):
        expected_msg = ('When instantiating CloudStack driver directly '
                        'you also need to provide url or host and path '
                        'argument')
        cls = get_driver(Provider.CLOUDSTACK)

        self.assertRaisesRegexp(Exception, expected_msg, cls,
                                'key', 'secret')

        try:
            cls('key', 'secret', True, 'localhost', '/path')
        except Exception:
            self.fail('host and path provided but driver raised an exception')

        try:
            cls('key', 'secret', url='https://api.exoscale.ch/compute')
        except Exception:
            self.fail('url provided but driver raised an exception')


class CloudStackMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('cloudstack')
    fixture_tag = 'default'

    def _load_fixture(self, fixture):
        body = self.fixtures.load(fixture)
        return body, json.loads(body)

    def _test_path_invalid_credentials(self, method, url, body, headers):
        body = ''
        return (httplib.UNAUTHORIZED, body, {},
                httplib.responses[httplib.UNAUTHORIZED])

    def _test_path_api_error(self, method, url, body, headers):
        body = self.fixtures.load('registerSSHKeyPair_error.json')
        return (431, body, {},
                httplib.responses[httplib.OK])

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

    def _test_path_userdata(self, method, url, body, headers):
        if 'deployVirtualMachine' in url:
            self.assertUrlContainsQueryParams(url, {'userdata': 'Zm9vYmFy'})
        return self._test_path(method, url, body, headers)

    def _cmd_queryAsyncJobResult(self, jobid):
        fixture = 'queryAsyncJobResult' + '_' + str(jobid) + '.json'
        body, obj = self._load_fixture(fixture)
        return (httplib.OK, body, obj, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
