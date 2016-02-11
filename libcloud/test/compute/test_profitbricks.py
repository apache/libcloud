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
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.providers import get_driver
from libcloud.test import unittest
from libcloud.test.secrets import PROFIT_BRICKS_PARAMS


class ProfitBricksTests(unittest.TestCase):

    def setUp(self):
        ProfitBricks = get_driver(Provider.PROFIT_BRICKS)
        ProfitBricks.connectionCls.conn_classes = (None, ProfitBricksMockHttp)
        self.driver = ProfitBricks(*PROFIT_BRICKS_PARAMS)

    ''' Server Function Tests
    '''
    def test_list_nodes(self):
        nodes = self.driver.list_nodes()

        self.assertEqual(len(nodes), 3)

        node = nodes[0]
        self.assertEqual(node.id, "c8e57d7b-e731-46ad-a913-1828c0562246")
        self.assertEqual(node.name, "server001")
        self.assertEqual(node.state, NodeState.RUNNING)
        self.assertEqual(node.public_ips, ['162.254.25.197'])
        self.assertEqual(node.private_ips, ['10.10.108.12', '10.13.198.11'])
        self.assertEqual(node.extra['datacenter_id'], "e1e8ec0d-b47f-4d39-a91b-6e885483c899")
        self.assertEqual(node.extra['datacenter_version'], "5")
        self.assertEqual(node.extra['provisioning_state'], NodeState.RUNNING)
        self.assertEqual(node.extra['creation_time'], "2014-07-14T20:52:20.839Z")
        self.assertEqual(node.extra['last_modification_time'], "2014-07-14T22:11:09.324Z")
        self.assertEqual(node.extra['os_type'], "LINUX")
        self.assertEqual(node.extra['availability_zone'], "ZONE_1")

    def test_ex_describe_node(self):
        image = type('NodeImage', (object,),
                     dict(id="cd59b162-0289-11e4-9f63-52540066fee9",
                          name="Debian-7-server-2014-07-01"))
        size = type('NodeSize', (object,),
                    dict(id="2",
                         name="Small Instance",
                         ram=2048,
                         disk=50,
                         extra={'cores': 1}))

        node = self.driver.create_node(name="SPC-Server",
                                       image=image,
                                       size=size)

        self.assertEqual(node.id, "7b18b85f-cc93-4c2d-abcc-5ce732d35750")

    def test_reboot_node(self):
        node = type('Node', (object,),
                    dict(id="c8e57d7b-e731-46ad-a913-1828c0562246"))
        reboot = self.driver.reboot_node(node=node)

        self.assertTrue(reboot)

    def test_ex_stop_node(self):
        node = type('Node', (object,),
                    dict(id="c8e57d7b-e731-46ad-a913-1828c0562246"))
        stop = self.driver.ex_stop_node(node=node)

        self.assertTrue(stop)

    def test_ex_start_node(self):
        node = type('Node', (object,),
                    dict(id="c8e57d7b-e731-46ad-a913-1828c0562246"))
        start = self.driver.ex_start_node(node=node)

        self.assertTrue(start)

    def test_destroy_node(self):
        node = type('Node', (object,),
                    dict(id="c8e57d7b-e731-46ad-a913-1828c0562246"))
        destroy = self.driver.destroy_node(node=node)

        self.assertTrue(destroy)

    def test_ex_update_node(self):
        node = type('Node', (object,),
                    dict(id="c8e57d7b-e731-46ad-a913-1828c0562246"))

        zone = type('ExProfitBricksAvailabilityZone', (object,),
                    dict(name="ZONE_2"))

        update = self.driver.ex_update_node(node=node, ram=2048, cores=2, name="server002", availability_zone=zone)

        self.assertTrue(update)

    ''' Volume Function Tests
    '''
    def test_list_volumes(self):
        volumes = self.driver.list_volumes()

        self.assertEqual(len(volumes), 4)

        volume = volumes[0]
        self.assertEqual(volume.id, "453582cf-8d54-4ec8-bc0b-f9962f7fd232")
        self.assertEqual(volume.name, "storage001")
        self.assertEqual(volume.size, 50)
        self.assertEqual(volume.extra['server_id'], "ebee7d83-912b-42f1-9b62-b953351a7e29")
        self.assertEqual(volume.extra['provisioning_state'], NodeState.RUNNING)
        self.assertEqual(volume.extra['creation_time'], "2014-07-15T03:19:38.252Z")
        self.assertEqual(volume.extra['last_modification_time'], "2014-07-15T03:28:58.724Z")
        self.assertEqual(volume.extra['image_id'], "d2f627c4-0289-11e4-9f63-52540066fee9")
        self.assertEqual(volume.extra['image_name'], "CentOS-6-server-2014-07-01")
        self.assertEqual(volume.extra['datacenter_id'], "06eac419-c2b3-4761-aeb9-10efdd2cf292")

    def test_create_volume(self):
        datacenter = type('Datacenter', (object,),
                          dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        image = type('NodeImage', (object,),
                     dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        create = self.driver.create_volume(name="StackPointCloudStorage001",
                                           size=50,
                                           ex_datacenter=datacenter,
                                           ex_image=image)

        self.assertTrue(create)

    def test_attach_volume_general(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        node = type('Node', (object,),
                    dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        attach = self.driver.attach_volume(node=node,
                                           volume=volume,
                                           device=None, ex_bus_type=None)

        self.assertTrue(attach)

    def test_attach_volume_device_defined(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        node = type('Node', (object,),
                    dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        attach = self.driver.attach_volume(node=node, volume=volume, device=1, ex_bus_type=None)

        self.assertTrue(attach)

    def test_attach_volume_bus_type_defined(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        node = type('Node', (object,),
                    dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        attach = self.driver.attach_volume(node=node,
                                           volume=volume,
                                           device=None,
                                           ex_bus_type="IDE")

        self.assertTrue(attach)

    def test_attach_volume_options_defined(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        node = type('Node', (object,),
                    dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        attach = self.driver.attach_volume(node=node, volume=volume,
                                           device=1, ex_bus_type="IDE")

        self.assertTrue(attach)

    def test_detach_volume(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476",
                           extra={'server_id': "cd59b162-0289-11e4-9f63-52540066fee9"}
                           ))

        attach = self.driver.detach_volume(volume=volume)

        self.assertTrue(attach)

    def test_destroy_volume(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        destroy = self.driver.destroy_volume(volume=volume)

        self.assertTrue(destroy)

    def test_update_volume(self):
        volume = type('StorageVolume', (object,),
                      dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))

        destroy = self.driver.ex_update_volume(volume=volume)

        self.assertTrue(destroy)

    def test_ex_describe_volume(self):
        describe = self.driver.ex_describe_volume(volume_id="8669a69f-2274-4520-b51e-dbdf3986a476")

        self.assertEqual(describe.id, "00d0b9e7-e016-456f-85a0-517aa9a34bf5")
        self.assertEqual(describe.size, 50)
        self.assertEqual(describe.name, "StackPointCloud-Volume")
        self.assertEqual(describe.extra['provisioning_state'], NodeState.RUNNING)

    ''' Image Function Tests
    '''
    def test_list_images(self):
        images = self.driver.list_images()

        self.assertEqual(len(images), 3)

        image = images[0]
        self.assertEqual(image.extra['cpu_hotpluggable'], "false")
        self.assertEqual(image.id, "03b6c3e7-f2ad-11e3-a036-52540066fee9")
        self.assertEqual(image.name, "windows-2012-r2-server-2014-06")
        self.assertEqual(image.extra['image_size'], "11264")
        self.assertEqual(image.extra['image_type'], "HDD")
        self.assertEqual(image.extra['memory_hotpluggable'], "false")
        self.assertEqual(image.extra['os_type'], "WINDOWS")
        self.assertEqual(image.extra['public'], "true")
        self.assertEqual(image.extra['location'], None)
        self.assertEqual(image.extra['writeable'], "true")

    ''' Datacenter Function Tests
    '''
    def test_ex_create_datacenter(self):
        datacenter = self.driver.ex_create_datacenter(name="StackPointCloud",
                                                      location="us/la")

        self.assertEqual(datacenter.id, '0c793dd1-d4cd-4141-86f3-8b1a24b2d604')
        self.assertEqual(datacenter.extra['location'], 'us/las')
        self.assertEqual(datacenter.version, '1')

    def test_ex_destroy_datacenter(self):
        datacenter = type('Datacenter', (object,),
                          dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))
        destroy = self.driver.ex_destroy_datacenter(datacenter=datacenter)

        self.assertTrue(destroy)

    def test_ex_describe_datacenter(self):
        datacenter = type('Datacenter', (object,),
                          dict(id="d96dfafc-9a8c-4c0e-8a0c-857a15db572d"))
        describe = self.driver.ex_describe_datacenter(datacenter_id=datacenter.id)

        self.assertEqual(describe.id, 'a3e6f83a-8982-4d6a-aebc-60baf5755ede')
        self.assertEqual(describe.name, 'StackPointCloud')
        self.assertEqual(describe.version, '1')
        self.assertEqual(describe.extra['location'], 'us/las')
        self.assertEqual(describe.extra['provisioning_state'], NodeState.RUNNING)

    def test_ex_clear_datacenter(self):
        datacenter = type('Datacenter', (object,),
                          dict(id="8669a69f-2274-4520-b51e-dbdf3986a476"))
        clear = self.driver.ex_clear_datacenter(datacenter=datacenter)

        self.assertTrue(clear)

    def test_ex_list_datacenters(self):
        datacenters = self.driver.ex_list_datacenters()

        self.assertEqual(len(datacenters), 2)

        dc1 = datacenters[0]
        self.assertEqual(dc1.id, "a3e6f83a-8982-4d6a-aebc-60baf5755ede")
        self.assertEqual(dc1.name, "StackPointCloud")
        self.assertEqual(dc1.version, "1")

    def test_ex_rename_datacenter(self):
        datacenter = type('Datacenter', (object,),
                          dict(id="d96dfafc-9a8c-4c0e-8a0c-857a15db572d"))

        update = self.driver.ex_rename_datacenter(datacenter=datacenter,
                                                  name="StackPointCloud")

        self.assertTrue(update)

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 3)

        locationNamesResult = sorted(list(a.name for a in locations))
        locationNamesExpected = ['de/fkb', 'de/fra', 'us/las']

        self.assertEqual(locationNamesResult, locationNamesExpected)

    ''' Availability Zone Tests
    '''

    def test_ex_list_availability_zones(self):
        zones = self.driver.ex_list_availability_zones()
        self.assertEqual(len(zones), 3)

        zoneNamesResult = sorted(list(a.name for a in zones))
        zoneNamesExpected = ['AUTO', 'ZONE_1', 'ZONE_2']

        self.assertEqual(zoneNamesResult, zoneNamesExpected)

    ''' Interface Tests
    '''

    def test_ex_list_interfaces(self):
        interfaces = self.driver.ex_list_network_interfaces()

        self.assertEqual(len(interfaces), 3)

        interface = interfaces[0]
        self.assertEqual(interface.id, "6b38a4f3-b851-4614-9e3a-5ddff4727727")
        self.assertEqual(interface.name, "StackPointCloud")
        self.assertEqual(interface.state, NodeState.RUNNING)
        self.assertEqual(interface.extra['server_id'], "234f0cf9-1efc-4ade-b829-036456584116")
        self.assertEqual(interface.extra['lan_id'], '3')
        self.assertEqual(interface.extra['internet_access'], 'false')
        self.assertEqual(interface.extra['mac_address'], "02:01:40:47:90:04")
        self.assertEqual(interface.extra['dhcp_active'], "true")
        self.assertEqual(interface.extra['gateway_ip'], None)
        self.assertEqual(interface.extra['ips'], ['10.14.96.11', '162.254.26.14', '162.254.26.15'])

    def test_ex_create_network_interface(self):
        node = type('Node', (object,),
                    dict(id="cd59b162-0289-11e4-9f63-52540066fee9"))

        interface = self.driver.ex_create_network_interface(node=node)
        self.assertEqual(interface.id, '6b38a4f3-b851-4614-9e3a-5ddff4727727')

    def test_ex_destroy_network_interface(self):
        network_interface = type('ProfitBricksNetworkInterface', (object,),
                                 dict(
                                 id="cd59b162-0289-11e4-9f63-52540066fee9"))

        destroy = self.driver.ex_destroy_network_interface(
            network_interface=network_interface)

        self.assertTrue(destroy)

    def test_ex_update_network_interface(self):
        network_interface = type('ProfitBricksNetworkInterface', (object,),
                                 dict(
                                 id="cd59b162-0289-11e4-9f63-52540066fee9"))

        create = self.driver.ex_update_network_interface(
            network_interface=network_interface)

        self.assertTrue(create)

    def test_ex_describe_network_interface(self):
        network_interface = type('ProfitBricksNetworkInterface', (object,),
                                 dict(
                                 id="cd59b162-0289-11e4-9f63-52540066fee9"))

        describe = self.driver.ex_describe_network_interface(network_interface=network_interface)

        self.assertEqual(describe.id, "f1c7a244-2fa6-44ee-8fb6-871f337683a3")
        self.assertEqual(describe.name, None)
        self.assertEqual(describe.state, NodeState.RUNNING)
        self.assertEqual(describe.extra['datacenter_id'], "a3a2e730-0dc3-47e6-bac6-4c056d5e2aee")
        self.assertEqual(describe.extra['datacenter_version'], "6")
        self.assertEqual(describe.extra['server_id'], "c09f4f31-336c-4ad2-9ec7-591778513408")
        self.assertEqual(describe.extra['lan_id'], "1")
        self.assertEqual(describe.extra['internet_access'], "false")
        self.assertEqual(describe.extra['mac_address'], "02:01:96:d7:60:e0")
        self.assertEqual(describe.extra['dhcp_active'], "true")
        self.assertEqual(describe.extra['gateway_ip'], None)
        self.assertEqual(describe.extra['ips'], ['10.10.38.12'])

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()

        self.assertEqual(len(sizes), 7)


class ProfitBricksMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('profitbricks')

    def _1_3_clearDataCenter(self, method, url, body, headers):
        body = self.fixtures.load('ex_clear_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_createDataCenter(self, method, url, body, headers):
        body = self.fixtures.load('ex_create_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_deleteDataCenter(self, method, url, body, headers):
        body = self.fixtures.load('ex_destroy_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getDataCenter(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getAllDataCenters(self, method, url, body, headers):
        body = self.fixtures.load('ex_list_datacenters.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_updateDataCenter(self, method, url, body, headers):
        body = self.fixtures.load('ex_update_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getAllImages(self, method, url, body, headers):
        body = self.fixtures.load('list_images.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getAllServers(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_resetServer(self, method, url, body, headers):
        body = self.fixtures.load('reboot_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_stopServer(self, method, url, body, headers):
        body = self.fixtures.load('ex_stop_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_startServer(self, method, url, body, headers):
        body = self.fixtures.load('ex_start_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_deleteServer(self, method, url, body, headers):
        body = self.fixtures.load('destroy_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getAllStorages(self, method, url, body, headers):
        body = self.fixtures.load('list_volumes.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_createStorage(self, method, url, body, headers):
        body = self.fixtures.load('create_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_connectStorageToServer(self, method, url, body, headers):
        body = self.fixtures.load('attach_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_disconnectStorageFromServer(self, method, url, body, headers):
        body = self.fixtures.load('detach_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_deleteStorage(self, method, url, body, headers):
        body = self.fixtures.load('destroy_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_updateStorage(self, method, url, body, headers):
        body = self.fixtures.load('ex_update_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_updateServer(self, method, url, body, headers):
        body = self.fixtures.load('ex_update_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getNic(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getAllNic(self, method, url, body, headers):
        body = self.fixtures.load('ex_list_network_interfaces.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_createNic(self, method, url, body, headers):
        body = self.fixtures.load('ex_list_network_interfaces.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_deleteNic(self, method, url, body, headers):
        body = self.fixtures.load('ex_destroy_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_updateNic(self, method, url, body, headers):
        body = self.fixtures.load('ex_update_network_interface.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getServer(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_getStorage(self, method, url, body, headers):
        body = self.fixtures.load('ex_describe_volume.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _1_3_createServer(self, method, url, body, headers):
        body = self.fixtures.load('create_node.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
