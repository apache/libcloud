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
import unittest

from datetime import datetime
from libcloud.utils.iso8601 import UTC

try:
    import simplejson as json
except ImportError:
    import json  # NOQA

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import assertRaisesRegex

from libcloud.common.types import InvalidCredsError
from libcloud.common.digitalocean import DigitalOcean_v1_Error
from libcloud.compute.base import NodeImage
from libcloud.compute.drivers.digitalocean import DigitalOceanNodeDriver

from libcloud.test import LibcloudTestCase, MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import DIGITALOCEAN_v1_PARAMS
from libcloud.test.secrets import DIGITALOCEAN_v2_PARAMS


# class DigitalOceanTests(unittest.TestCase, TestCaseMixin):
class DigitalOcean_v2_Tests(LibcloudTestCase):

    def setUp(self):
        DigitalOceanNodeDriver.connectionCls.conn_class = \
            DigitalOceanMockHttp
        DigitalOceanMockHttp.type = None
        self.driver = DigitalOceanNodeDriver(*DIGITALOCEAN_v2_PARAMS)

    def test_v1_Error(self):
        self.assertRaises(DigitalOcean_v1_Error, DigitalOceanNodeDriver,
                          *DIGITALOCEAN_v1_PARAMS, api_version='v1')

    def test_v2_uses_v1_key(self):
        self.assertRaises(InvalidCredsError, DigitalOceanNodeDriver,
                          *DIGITALOCEAN_v1_PARAMS, api_version='v2')

    def test_authentication(self):
        DigitalOceanMockHttp.type = 'UNAUTHORIZED'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

    def test_list_images_success(self):
        images = self.driver.list_images()
        self.assertTrue(len(images) >= 1)

        image = images[0]
        self.assertTrue(image.id is not None)
        self.assertTrue(image.name is not None)

    def test_list_sizes_success(self):
        sizes = self.driver.list_sizes()
        self.assertTrue(len(sizes) >= 1)

        size = sizes[0]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '512mb')
        self.assertEqual(size.ram, 512)

        size = sizes[1]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '1gb')
        self.assertEqual(size.ram, 1024)

    def test_list_sizes_filter_by_location_success(self):
        location = self.driver.list_locations()[1]
        sizes = self.driver.list_sizes(location=location)
        self.assertTrue(len(sizes) >= 1)

        size = sizes[0]
        self.assertTrue(size.id is not None)
        self.assertEqual(size.name, '512mb')
        self.assertTrue(location.id in size.extra['regions'])

        location = self.driver.list_locations()[1]
        location.id = 'doesntexist'
        sizes = self.driver.list_sizes(location=location)
        self.assertEqual(len(sizes), 0)

    def test_list_locations_success(self):
        locations = self.driver.list_locations()
        self.assertTrue(len(locations) == 2)

        location = locations[0]
        self.assertEqual(location.id, 'nyc1')
        self.assertEqual(location.name, 'New York 1')

        locations = self.driver.list_locations(ex_available=True)
        self.assertTrue(len(locations) == 2)

        locations = self.driver.list_locations(ex_available=False)
        self.assertTrue(len(locations) == 3)

    def test_list_nodes_success(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, 'ubuntu-s-1vcpu-1gb-sfo3-01')
        self.assertEqual(nodes[0].public_ips, ['128.199.13.158'])
        self.assertEqual(nodes[0].extra['image']['id'], 69463186)
        self.assertEqual(nodes[0].extra['size_slug'], 's-1vcpu-1gb')
        self.assertEqual(len(nodes[0].extra['tags']), 0)

    def test_list_nodes_fills_created_datetime(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(nodes[0].created_at,
                         datetime(2020, 10, 15, 13, 58, 22, tzinfo=UTC))

    def test_create_node_invalid_size(self):
        image = NodeImage(id='invalid', name=None, driver=self.driver)
        size = self.driver.list_sizes()[0]
        location = self.driver.list_locations()[0]

        DigitalOceanMockHttp.type = 'INVALID_IMAGE'
        expected_msg = \
            r'You specified an invalid image for Droplet creation.' + \
            r' \(code: (404|HTTPStatus.NOT_FOUND)\)'
        assertRaisesRegex(self, Exception, expected_msg,
                          self.driver.create_node,
                          name='test', size=size, image=image,
                          location=location)

    def test_reboot_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'REBOOT'
        result = self.driver.reboot_node(node)
        self.assertTrue(result)

    def test_create_image_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'SNAPSHOT'
        result = self.driver.create_image(node, 'My snapshot')
        self.assertTrue(result)

    def test_get_image_success(self):
        image = self.driver.get_image(12345)
        self.assertEqual(image.name, 'My snapshot')
        self.assertEqual(image.id, '12345')
        self.assertEqual(image.extra['distribution'], 'Ubuntu')

    def test_delete_image_success(self):
        image = self.driver.get_image(12345)
        DigitalOceanMockHttp.type = 'DESTROY'
        result = self.driver.delete_image(image)
        self.assertTrue(result)

    def test_ex_power_on_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'POWERON'
        result = self.driver.ex_power_on_node(node)
        self.assertTrue(result)

    def test_ex_shutdown_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'SHUTDOWN'
        result = self.driver.ex_shutdown_node(node)
        self.assertTrue(result)

    def test_ex_hard_reboot_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'POWERCYCLE'
        result = self.driver.ex_hard_reboot(node)
        self.assertTrue(result)

    def test_ex_rebuild_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'REBUILD'
        result = self.driver.ex_rebuild_node(node)
        self.assertTrue(result)

    def test_ex_resize_node_success(self):
        node = self.driver.list_nodes()[0]
        size = self.driver.list_sizes()[0]
        DigitalOceanMockHttp.type = 'RESIZE'
        result = self.driver.ex_resize_node(node, size)
        self.assertTrue(result)

    def test_destroy_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'DESTROY'
        result = self.driver.destroy_node(node)
        self.assertTrue(result)

    def test_ex_change_kernel_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'KERNELCHANGE'
        result = self.driver.ex_change_kernel(node, 7515)
        self.assertTrue(result)

    def test_ex_enable_ipv6_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'ENABLEIPV6'
        result = self.driver.ex_enable_ipv6(node)
        self.assertTrue(result)

    def test_ex_rename_node_success(self):
        node = self.driver.list_nodes()[0]
        DigitalOceanMockHttp.type = 'RENAME'
        result = self.driver.ex_rename_node(node, 'fedora helios')
        self.assertTrue(result)

    def test_list_key_pairs(self):
        keys = self.driver.list_key_pairs()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0].extra['id'], 7717)
        self.assertEqual(keys[0].name, 'test1')
        self.assertEqual(keys[0].public_key,
                         "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAQQDGk5 example")

    def test_create_key_pair(self):
        DigitalOceanMockHttp.type = 'CREATE'
        key = self.driver.create_key_pair(
            name="test1",
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQsxRiUKn example"
        )
        self.assertEqual(key.name, "test1")
        self.assertEqual(key.fingerprint,
                         "f5:d1:78:ed:28:72:5f:e1:ac:94:fd:1f:e0:a3:48:6d")

    def test_delete_key_pair(self):
        key = self.driver.list_key_pairs()[0]
        result = self.driver.delete_key_pair(key)
        self.assertTrue(result)

    def test__paginated_request_single_page(self):
        nodes = self.driver._paginated_request('/v2/droplets', 'droplets')
        self.assertEqual(nodes[0]['name'], 'ubuntu-s-1vcpu-1gb-sfo3-01')
        self.assertEqual(nodes[0]['image']['id'], 69463186)
        self.assertEqual(nodes[0]['size_slug'], 's-1vcpu-1gb')

    def test__paginated_request_two_pages(self):
        DigitalOceanMockHttp.type = 'PAGE_ONE'
        nodes = self.driver._paginated_request('/v2/droplets', 'droplets')
        self.assertEqual(len(nodes), 2)

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 1)
        volume = volumes[0]
        self.assertEqual(volume.id, "62766883-2c28-11e6-b8e6-000f53306ae1")
        self.assertEqual(volume.name, "example")
        self.assertEqual(volume.size, 4)
        self.assertEqual(volume.driver, self.driver)

    def test_list_volumes_empty(self):
        DigitalOceanMockHttp.type = 'EMPTY'
        volumes = self.driver.list_volumes()
        self.assertEqual(len(volumes), 0)

    def test_create_volume(self):
        nyc1 = [r for r in self.driver.list_locations() if r.id == 'nyc1'][0]
        DigitalOceanMockHttp.type = 'CREATE'
        volume = self.driver.create_volume(4, 'example', nyc1)
        self.assertEqual(volume.id, "62766883-2c28-11e6-b8e6-000f53306ae1")
        self.assertEqual(volume.name, "example")
        self.assertEqual(volume.size, 4)
        self.assertEqual(volume.driver, self.driver)

    def test_attach_volume(self):
        node = self.driver.list_nodes()[0]
        volume = self.driver.list_volumes()[0]
        DigitalOceanMockHttp.type = 'ATTACH'
        resp = self.driver.attach_volume(node, volume)
        self.assertTrue(resp)

    def test_detach_volume(self):
        volume = self.driver.list_volumes()[0]
        DigitalOceanMockHttp.type = 'DETACH'
        resp = self.driver.detach_volume(volume)
        self.assertTrue(resp)

    def test_destroy_volume(self):
        volume = self.driver.list_volumes()[0]
        DigitalOceanMockHttp.type = 'DESTROY'
        resp = self.driver.destroy_volume(volume)
        self.assertTrue(resp)

    def test_list_volume_snapshots(self):
        volume = self.driver.list_volumes()[0]
        snapshots = self.driver.list_volume_snapshots(volume)
        self.assertEqual(len(snapshots), 3)
        snapshot1, snapshot2, snapshot3 = snapshots
        self.assertEqual(snapshot1.id, "c0def940-9324-11e6-9a56-000f533176b1")
        self.assertEqual(snapshot2.id, "c2036724-9343-11e6-aef4-000f53315a41")
        self.assertEqual(snapshot3.id, "d347e033-9343-11e6-9a56-000f533176b1")

    def test_create_volume_snapshot(self):
        volume = self.driver.list_volumes()[0]
        DigitalOceanMockHttp.type = 'CREATE'
        snapshot = self.driver.create_volume_snapshot(volume, 'test-snapshot')
        self.assertEqual(snapshot.id, "c0def940-9324-11e6-9a56-000f533176b1")
        self.assertEqual(snapshot.name, 'test-snapshot')
        self.assertEqual(volume.driver, self.driver)

    def test_delete_volume_snapshot(self):
        volume = self.driver.list_volumes()[0]
        snapshot = self.driver.list_volume_snapshots(volume)[0]
        DigitalOceanMockHttp.type = 'DELETE'
        result = self.driver.delete_volume_snapshot(snapshot)
        self.assertTrue(result)

    def test_ex_get_node_details(self):
        node = self.driver.ex_get_node_details('3164444')
        self.assertEqual(node.name, 'example.com')
        self.assertEqual(node.public_ips, ['36.123.0.123'])
        self.assertEqual(node.extra['image']['id'], 12089443)
        self.assertEqual(node.extra['size_slug'], '8gb')
        self.assertEqual(len(node.extra['tags']), 2)

    def test_ex_create_floating_ip(self):
        nyc1 = [r for r in self.driver.list_locations() if r.id == 'nyc1'][0]
        floating_ip = self.driver.ex_create_floating_ip(nyc1)

        # Note that this is the ID. There is no real ID for a floating IP at
        # DigitalOcean, but the IP is unique so we can use that instead.
        self.assertEqual(floating_ip.id, '167.138.123.111')
        self.assertEqual(floating_ip.ip_address, '167.138.123.111')
        self.assertEqual(floating_ip.extra['region']['slug'], 'nyc1')
        # The newly created floating IP reserved to a region is not
        # associated with any droplet. See the DigitalOcean API docs
        # how to create a floating IP that is associated with an instance
        # from the start. This API call creates an unattached IP.
        self.assertIsNone(floating_ip.node_id)

    def test_ex_delete_floating_ip(self):
        nyc1 = [r for r in self.driver.list_locations() if r.id == 'nyc1'][0]
        floating_ip = self.driver.ex_create_floating_ip(nyc1)
        ret = self.driver.ex_delete_floating_ip(floating_ip)

        # The API returns 204 NO CONTENT if all is well.
        self.assertTrue(ret)

    def test_floating_ip_can_be_deleted_by_calling_delete_on_floating_ip_object(self):  # noqa: E501
        nyc1 = [r for r in self.driver.list_locations() if r.id == 'nyc1'][0]
        floating_ip = self.driver.ex_create_floating_ip(nyc1)
        ret = floating_ip.delete()

        self.assertTrue(ret)

    def test_list_floating_ips(self):
        floating_ips = self.driver.ex_list_floating_ips()

        self.assertEqual(len(floating_ips), 2, 'Wrong floating IPs count')

        floating_ip = floating_ips[0]
        self.assertEqual(floating_ip.id, '133.166.122.204')
        self.assertEqual(floating_ip.ip_address, '133.166.122.204')
        self.assertEqual(floating_ip.extra['region']['slug'], 'ams3')
        self.assertEqual(84155775, floating_ip.node_id)

    def test_get_floating_ip(self):
        floating_ip = self.driver.ex_get_floating_ip('133.166.122.204')

        self.assertEqual(floating_ip.id, '133.166.122.204')
        self.assertEqual(floating_ip.ip_address, '133.166.122.204')
        self.assertEqual(floating_ip.extra['region']['slug'], 'ams3')
        self.assertEqual(84155775, floating_ip.node_id)

    def test_ex_attach_floating_ip_to_node(self):
        node = self.driver.list_nodes()[0]
        floating_ip = self.driver.ex_get_floating_ip('133.166.122.204')

        ret = self.driver.ex_attach_floating_ip_to_node(node, floating_ip)

        self.assertTrue(ret)

    def test_ex_detach_floating_ip_from_node(self):
        node = self.driver.list_nodes()[0]
        floating_ip = self.driver.ex_get_floating_ip('154.138.103.175')

        ret = self.driver.ex_detach_floating_ip_from_node(node, floating_ip)

        self.assertTrue(ret)


class DigitalOceanMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('digitalocean_v2')

    def _v2_regions(self, method, url, body, headers):
        body = self.fixtures.load('list_locations.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_images(self, method, url, body, headers):
        body = self.fixtures.load('list_images.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_sizes(self, method, url, body, headers):
        body = self.fixtures.load('list_sizes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_droplets(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_droplets_3164444(self, method, url, body, headers):
        body = self.fixtures.load('list_node.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_droplets_INVALID_IMAGE(self, method, url, body, headers):
        body = self.fixtures.load('error_invalid_image.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _v2_droplets_3164444_actions_REBOOT(self, method, url, body, headers):
        # reboot_node
        body = self.fixtures.load('reboot_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_DESTROY(self, method, url, body, headers):
        # destroy_node
        return (httplib.NO_CONTENT, body, {},
                httplib.responses[httplib.NO_CONTENT])

    def _v2_droplets_3164444_actions_KERNELCHANGE(
            self, method, url, body, headers):
        # change_kernel
        body = self.fixtures.load('ex_change_kernel.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_actions_ENABLEIPV6(
            self, method, url, body, headers):
        # enable_ipv6
        body = self.fixtures.load('ex_enable_ipv6.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_actions_RENAME(self, method, url, body, headers):
        # rename_node
        body = self.fixtures.load('ex_rename_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_actions_SNAPSHOT(self, method, url,
                                              body, headers):
        # create_image
        body = self.fixtures.load('create_image.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_images_12345(self, method, url, body, headers):
        # get_image
        body = self.fixtures.load('get_image.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_images_12345_DESTROY(self, method, url, body, headers):
        # delete_image
        return (httplib.NO_CONTENT, body, {},
                httplib.responses[httplib.NO_CONTENT])

    def _v2_droplets_3164444_actions_POWERON(self, method, url, body, headers):
        # ex_power_on_node
        body = self.fixtures.load('ex_power_on_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_actions_SHUTDOWN(self, method, url,
                                              body, headers):
        # ex_shutdown_node
        body = self.fixtures.load('ex_shutdown_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_3164444_actions_POWERCYCLE(self, method, url,
                                                body, headers):
        # ex_hard_reboot
        body = self.fixtures.load('ex_hard_reboot.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.OK])

    def _v2_droplets_3164444_actions_REBUILD(self, method, url,
                                             body, headers):
        # ex_rebuild_node
        body = self.fixtures.load('ex_rebuild_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.OK])

    def _v2_droplets_3164444_actions_RESIZE(self, method, url,
                                            body, headers):
        # ex_resize_node
        body = self.fixtures.load('ex_resize_node.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.OK])

    def _v2_account_keys(self, method, url, body, headers):
        body = self.fixtures.load('list_key_pairs.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_account_keys_7717(self, method, url, body, headers):
        # destroy_ssh_key
        return (httplib.NO_CONTENT, body, {},
                httplib.responses[httplib.NO_CONTENT])

    def _v2_account_keys_CREATE(self, method, url, body, headers):
        # create_ssh_key
        body = self.fixtures.load('create_key_pair.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_droplets_UNAUTHORIZED(self, method, url, body, headers):
        body = self.fixtures.load('error.json')
        return (httplib.UNAUTHORIZED, body, {},
                httplib.responses[httplib.UNAUTHORIZED])

    def _v2_droplets_PAGE_ONE(self, method, url, body, headers):
        body = self.fixtures.load('list_nodes_page_1.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_volumes(self, method, url, body, headers):
        body = self.fixtures.load('list_volumes.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_volumes_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load('list_volumes_empty.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_volumes_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('create_volume.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_volumes_actions_ATTACH(self, method, url, body, headers):
        body = self.fixtures.load('attach_volume.json')
        return (httplib.ACCEPTED, body, {},
                httplib.responses[httplib.ACCEPTED])

    def _v2_volumes_DETACH(self, method, url, body, headers):
        body = self.fixtures.load('detach_volume.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_volumes_62766883_2c28_11e6_b8e6_000f53306ae1_DESTROY(self, method,
                                                                 url, body,
                                                                 headers):
        return (httplib.NO_CONTENT, None, {},
                httplib.responses[httplib.NO_CONTENT])

    def _v2_volumes_62766883_2c28_11e6_b8e6_000f53306ae1_snapshots_CREATE(
            self, method, url, body, headers):
        body = self.fixtures.load('create_volume_snapshot.json')
        return (httplib.CREATED, body, {}, httplib.responses[httplib.CREATED])

    def _v2_volumes_62766883_2c28_11e6_b8e6_000f53306ae1_snapshots(
            self, method, url, body, headers):
        body = self.fixtures.load('list_volume_snapshots.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v2_snapshots_c0def940_9324_11e6_9a56_000f533176b1_DELETE(
            self, method, url, body, headers):
        return (httplib.NO_CONTENT, None, {},
                httplib.responses[httplib.NO_CONTENT])

    def _v2_floating_ips(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('create_floating_ip.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            body = self.fixtures.load('list_floating_ips.json')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            raise NotImplementedError()

    def _v2_floating_ips_167_138_123_111(self, method, url, body, headers):
        if method == 'DELETE':
            body = ''
            return (httplib.NO_CONTENT, body, {},
                    httplib.responses[httplib.NO_CONTENT])
        else:
            raise NotImplementedError()

    def _v2_floating_ips_133_166_122_204_actions(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('attach_floating_ip.json')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])
        else:
            raise NotImplementedError()

    def _v2_floating_ips_154_138_103_175_actions(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('detach_floating_ip.json')
            return (httplib.CREATED, body, {},
                    httplib.responses[httplib.CREATED])
        else:
            raise NotImplementedError()


if __name__ == '__main__':
    sys.exit(unittest.main())
