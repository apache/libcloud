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

import json
import sys
import unittest
import libcloud.test.secrets as secrets

from libcloud.compute.drivers.gce import GoogleComputeEngineNodeDriver
from libcloud.test.file_fixtures import ComputeFileFixtures


class MockAccessConfig:
    def __init__(self, natIP):
        self.natIP = natIP


class MockImage:
    def __init__(self, id, selfLink, preferredKernel, description,
                 creationTimestamp):
        self.id = id
        self.selfLink = selfLink
        self.preferredKernel = preferredKernel
        self.description = description
        self.creationTimestamp = creationTimestamp


class MockInstance:
    def __init__(self, status, kind, machineType, description, zone, image,
                 disks, networkInterfaces, id, selfLink, name, metadata):
        self.status = status
        self.kind = kind
        self.machineType = machineType
        self.description = description
        self.zone = zone
        self.image = image
        self.disks = disks
        self.networkInterfaces = networkInterfaces
        self.id = id
        self.selfLink = selfLink
        self.name = name
        self.metadata = metadata


class MockLocation:
    def __init__(self, id, name, country):
        self.id = id
        self.name = name
        self.country = country


class MockMachine:
    def __init__(self, id, name, memoryMb, imageSpaceGb, bandwidth, price):
        self.id = id
        self.name = name
        self.memoryMb = memoryMb
        self.imageSpaceGb = imageSpaceGb
        self.bandwidth = bandwidth
        self.price = price


class MockNetworkIP:
    def __init__(self, networkIP, accessConfigs):
        self.networkIP = networkIP
        self.accessConfigs = accessConfigs


class MockSSHClient():
    def __init__(self):
        self.testTypes = {
            'reboot_instance': 'PASS'
        }

    def set_missing_host_key_policy(self, host_key_policy):
        pass

    def connect(self, host, username=None, pkey=None):
        pass

    def close(self):
        pass

    def exec_command(self, command):
        if self.testTypes['reboot_instance'] == 'PASS':
            return
        else:
            raise Exception


class MockGcelibInstance:
    fixtures = ComputeFileFixtures('gce')

    def __init__(self):
        self.testTypes = {
            'list_nodes': 'PASS',
            'list_images': 'PASS',
            'list_machine_types': 'PASS',
            'list_locations': 'PASS',
            'insert_instance': 'PASS',
            'deploy_instance': 'PASS'
        }

    def load_fixtures(self, method_name, test_type):
        fixture_file_name = method_name

        if test_type == 'FAIL':
            fixture_file_name += '_fail'
        fixture_file_name += '.json'

        return json.loads(self.fixtures.load(fixture_file_name))

    def all_instances(self):
        method_name = 'list_nodes'
        instance_list = self.load_fixtures(method_name,
                                           self.testTypes[method_name])
        list_mock_instances = []

        for instance in instance_list:
            if instance == 'error':
                continue
            else:
                mock_network_interface = self._get_mock_network_interfaces(
                    instance)
                mock_instance = self._to_mock_instance(
                    instance, mock_network_interface)
                list_mock_instances.append(mock_instance)

        return list_mock_instances

    def list_images(self, project):
        method_name = 'list_images'
        image_list = self.load_fixtures(method_name,
                                        self.testTypes[method_name])
        list_mock_images = []

        for image in image_list:
            if image == 'error':
                continue
            else:
                mock_image = self._to_mock_image(image)
                list_mock_images.append(mock_image)

        return list_mock_images

    def list_machine_types(self):
        method_name = 'list_machine_types'
        machine_type_list = self.load_fixtures(method_name,
                                               self.testTypes[method_name])
        list_mock_machine_types = []

        for machine in machine_type_list:
            if machine == 'error':
                continue
            else:
                mock_machine = self._to_mock_machine(machine)
                list_mock_machine_types.append(mock_machine)

        return list_mock_machine_types

    def list_zones(self):
        method_name = 'list_locations'
        location_list = self.load_fixtures(method_name,
                                           self.testTypes[method_name])
        list_mock_locations = []

        for location in location_list:
            if location == 'error':
                continue
            else:
                mock_location = self._to_mock_location(location)
                list_mock_locations.append(mock_location)

        return list_mock_locations

    def get_instance(self, mock_instance):
        if mock_instance == 'foonode2':
            method_name = 'deploy_instance'
        else:
            method_name = 'insert_instance'
        instance_data = self.load_fixtures(method_name,
                                           self.testTypes[method_name])

        if instance_data.get('error', None) is None:
            mock_network_interface = self._get_mock_network_interfaces(
                instance_data)
            return self._to_mock_instance(instance_data,
                                          mock_network_interface)
        else:
            return None

    def insert_instance(self, name, machineType, image, zone, project,
                        metadata):
        return

    def delete_instance(self, instance):
        list_nodes = self.all_instances()
        node_to_destory = list_nodes[0]
        assert node_to_destory.name == instance

        if self.testTypes['delete_instance'] == 'PASS':
            return
        else:
            raise Exception

    def _get_mock_network_interfaces(self, mock_instance):
        mock_network_interfaces = []

        for mock_network_interface in mock_instance['networkInterfaces']:
            mock_access_configs = []
            for mock_access_config in mock_network_interface['accessConfigs']:
                mock_access_configs.append(
                    MockAccessConfig(mock_access_config))
                mock_network_interfaces.append(
                    MockNetworkIP(mock_network_interface['networkIP'],
                                  mock_access_configs))

        return mock_network_interfaces

    def _to_mock_instance(self, mock_instance, mock_network_interfaces):
        mock_instance.setdefault('metadata', None)

        return MockInstance(mock_instance['status'], mock_instance['kind'],
                            mock_instance['machineType'], ['description'],
                            mock_instance['zone'], mock_instance['image'],
                            mock_instance['disks'], mock_network_interfaces,
                            mock_instance['id'], mock_instance['selfLink'],
                            mock_instance['name'], mock_instance['metadata'])

    def _to_mock_image(self, mock_image):
        return MockImage(mock_image['id'], mock_image['selfLink'],
                         mock_image['preferredKernel'],
                         mock_image['description'],
                         mock_image['creationTimestamp'])

    def _to_mock_location(self, mock_location):
        mock_location['country'] = 'US'

        return MockLocation(mock_location['id'], mock_location['name'],
                            mock_location['country'])

    def _to_mock_machine(self, mock_machine):
        mock_machine['bandwidth'] = 0
        mock_machine['price'] = '123'

        return MockMachine(mock_machine['id'], mock_machine['name'],
                           mock_machine['memoryMb'],
                           mock_machine['imageSpaceGb'],
                           mock_machine['bandwidth'],
                           mock_machine['price'])


# TODO(zmir): Determine if there is a way to programmatically generate all test
# cases, and mock types, and subsequently, automate the entire testing suite
# for gce.
class GoogleComputeEngineTest(unittest.TestCase):
    def setUp(self):
        ssh_username, ssh_private_key_file, project = getattr(secrets,
                                                              'GCE_PARAMS',
                                                              ())
        self.driver = GoogleComputeEngineNodeDriver(ssh_username,
                                                    ssh_private_key_file,
                                                    project)
        self.driver.SSHClient = MockSSHClient()
        self.driver.gcelib_instance = MockGcelibInstance()

    def test_list_nodes(self):
        self.driver.gcelib_instance.testTypes['list_nodes'] = 'PASS'
        list_nodes = self.driver.list_nodes()
        self.assertEqual(len(list_nodes), 2)

        node1, node2 = list_nodes[0], list_nodes[1]
        self.assertEqual(node1.name, 'foo')
        self.assertEqual(node2.name, 'bar')
        self.assertEqual(node1.state, 0)
        self.assertEqual(node2.state, 0)
        self.assertEqual(node1.size.split('/')[-1], 'n1-standard-1')
        self.assertEqual(node2.size.split('/')[-1], 'n1-standard-2')

        self.driver.gcelib_instance.testTypes['list_nodes'] = 'FAIL'
        list_nodes = self.driver.list_nodes()
        self.assertEqual(len(list_nodes), 0)

    def test_list_images(self):
        self.driver.gcelib_instance.testTypes['list_images'] = 'PASS'
        list_images = self.driver.list_images()
        self.assertEqual(len(list_images), 6)

        image1, image2 = list_images[0], list_images[-1]
        self.assertEqual(image1.name.split('/')[-1], 'centos-6-2-v20120611')
        self.assertEqual(image2.name.split('/')[-1], 'ubuntu-10-04-v20120106')
        self.assertEqual(image1.id, '12917726455664967299')
        self.assertEqual(image2.id, '12941196956151834933')

        self.driver.gcelib_instance.testTypes['list_images'] = 'FAIL'
        list_images = self.driver.list_images()
        self.assertEqual(len(list_images), 0)

    def test_list_sizes(self):
        self.driver.gcelib_instance.testTypes['list_machine_types'] = 'PASS'
        list_sizes = self.driver.list_sizes()
        self.assertEqual(len(list_sizes), 7)

        size1, size2 = list_sizes[0], list_sizes[-1]
        self.assertEqual(size1.name, 'n1-standard-2-d')
        self.assertEqual(size2.name, 'n1-standard-1-d')
        self.assertEqual(size1.ram, 7680)
        self.assertEqual(size2.ram, 3840)
        self.assertEqual(size1.id, '12908559582417967837')
        self.assertEqual(size2.id, '12908559201265214706')

        self.driver.gcelib_instance.testTypes['list_machine_types'] = 'FAIL'
        list_sizes = self.driver.list_sizes()
        self.assertEqual(len(list_sizes), 0)

    def test_list_locations(self):
        self.driver.gcelib_instance.testTypes['list_machine_types'] = 'PASS'
        list_locations = self.driver.list_locations()
        self.assertEqual(len(list_locations), 2)

        location1, location2 = list_locations
        self.assertEqual(location1.name, 'us-central1-a')
        self.assertEqual(location2.name, 'us-central2-a')
        self.assertEqual(location1.id, '12889558432979476247')
        self.assertEqual(location2.id, '12889559460378820818')
        self.assertEqual(location1.country, 'US')
        self.assertEqual(location2.country, 'US')

        self.driver.gcelib_instance.testTypes['list_locations'] = 'FAIL'
        list_locations = self.driver.list_locations()
        self.assertEqual(len(list_locations), 0)

    def test_create_node(self):
        node_name = 'foonode'
        node_size = self.driver.list_sizes()[0]
        node_image = self.driver.list_images()[0]
        node_location = self.driver.list_locations()[0]

        self.driver.gcelib_instance.testTypes['insert_instance'] = 'PASS'
        new_node = self.driver.create_node(node_name, node_size, node_image,
                                           node_location)

        new_node_image = new_node.image.split('/')[-1]
        new_node_zone = new_node.extra['zone'].split('/')[-1]
        new_node_machine_type = new_node.extra['machineType'].split('/')[-1]

        self.assertEqual(new_node.name, 'foonode')
        self.assertEqual(new_node.id, '12989505666010310007')
        self.assertEqual(new_node.state, 0)
        self.assertEqual(new_node_image, 'centos-6-2-v20120326')
        self.assertEqual(new_node_zone, 'us-central1-a')
        self.assertEqual(new_node_machine_type, 'n1-standard-1')

        self.driver.gcelib_instance.testTypes['insert_instance'] = 'FAIL'
        new_node = self.driver.create_node(node_name, node_size, node_image,
                                           node_location)
        self.assertEqual(new_node, None)

    def test_reboot_node(self):
        self.driver.SSHClient.testTypes['reboot_instance'] = 'PASS'
        node_to_reboot = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node_to_reboot)
        self.assertTrue(ret)

        self.driver.SSHClient.testTypes['reboot_instance'] = 'FAIL'
        node_to_reboot = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node_to_reboot)
        self.assertFalse(ret)

    def test_deploy_node(self):
        node_name = 'foonode2'
        node_size = self.driver.list_sizes()[0]
        node_image = self.driver.list_images()[0]
        node_location = self.driver.list_locations()[0]
        script_location = \
            'libcloud/test/compute/fixtures/gce/install-apache.sh'

        self.driver.gcelib_instance.testTypes['deploy_instance'] = 'PASS'
        new_node = self.driver.deploy_node(node_name,
                                           node_size,
                                           node_image,
                                           node_location,
                                           script_location)

        new_node_image = new_node.image.split('/')[-1]
        new_node_zone = new_node.extra['zone'].split('/')[-1]
        new_node_machine_type = new_node.extra['machineType'].split('/')[-1]

        self.assertEqual(new_node.name, 'foonode2')
        self.assertEqual(new_node.id, '12990402818933463403')
        self.assertEqual(new_node.state, 0)
        self.assertEqual(new_node_image, 'centos-6-2-v20120326')
        self.assertEqual(new_node_zone, 'us-central1-a')
        self.assertEqual(new_node_machine_type, 'n1-standard-1')

        self.driver.gcelib_instance.testTypes['deploy_instance'] = 'FAIL'
        new_node = self.driver.deploy_node(node_name,
                                           node_size,
                                           node_image,
                                           node_location,
                                           script_location)
        self.assertEqual(new_node, None)

    def test_destroy_node(self):
        list_nodes = self.driver.list_nodes()
        node_to_destroy = list_nodes[0]

        self.driver.gcelib_instance.testTypes['delete_instance'] = 'PASS'
        ret = self.driver.destroy_node(node_to_destroy)
        self.assertTrue(ret)

        self.driver.gcelib_instance.testTypes['delete_instance'] = 'FAIL'
        ret = self.driver.destroy_node(node_to_destroy)
        self.assertFalse(ret)

if __name__ == '__main__':
    sys.exit(unittest.main())
