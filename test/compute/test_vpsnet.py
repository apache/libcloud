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
from libcloud.utils.py3 import httplib

from libcloud.compute.drivers.vpsnet import VPSNetNodeDriver
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin

from test.secrets import VPSNET_PARAMS

class VPSNetTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        VPSNetNodeDriver.connectionCls.conn_classes = (None, VPSNetMockHttp)
        self.driver = VPSNetNodeDriver(*VPSNET_PARAMS)

    def test_create_node(self):
        VPSNetMockHttp.type = 'create'
        image = self.driver.list_images()[0]
        size = self.driver.list_sizes()[0]
        node = self.driver.create_node('foo', image, size)
        self.assertEqual(node.name, 'foo')

    def test_list_nodes(self):
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]
        self.assertEqual(node.id, '1384')
        self.assertEqual(node.state, NodeState.RUNNING)

    def test_reboot_node(self):
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]

        VPSNetMockHttp.type = 'reboot'
        ret = self.driver.reboot_node(node)
        self.assertEqual(ret, True)

    def test_destroy_node(self):
        VPSNetMockHttp.type = 'delete'
        node = Node('2222', None, None, None, None, self.driver)
        ret = self.driver.destroy_node(node)
        self.assertTrue(ret)
        VPSNetMockHttp.type = 'delete_fail'
        node = Node('2223', None, None, None, None, self.driver)
        self.assertRaises(Exception, self.driver.destroy_node, node)

    def test_list_images(self):
        VPSNetMockHttp.type = 'templates'
        ret = self.driver.list_images()
        self.assertEqual(ret[0].id, '9')
        self.assertEqual(ret[-1].id, '160')

    def test_list_sizes(self):
        VPSNetMockHttp.type = 'sizes'
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].id, '1')
        self.assertEqual(ret[0].name, '1 Node')

    def test_destroy_node_response(self):
        # should return a node object
        node = Node('2222', None, None, None, None, self.driver)
        VPSNetMockHttp.type = 'delete'
        ret = self.driver.destroy_node(node)
        self.assertTrue(isinstance(ret, bool))

    def test_reboot_node_response(self):
        # should return a node object
        VPSNetMockHttp.type = 'virtual_machines'
        node = self.driver.list_nodes()[0]
        VPSNetMockHttp.type = 'reboot'
        ret = self.driver.reboot_node(node)
        self.assertTrue(isinstance(ret, bool))



class VPSNetMockHttp(MockHttp):


    def _nodes_api10json_sizes(self, method, url, body, headers):
        body = """[{"slice":{"virtual_machine_id":8592,"id":12256,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12258,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12434,"consumer_id":0}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _nodes_api10json_create(self, method, url, body, headers):
        body = """[{"slice":{"virtual_machine_id":8592,"id":12256,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12258,"consumer_id":0}},
                   {"slice":{"virtual_machine_id":null,"id":12434,"consumer_id":0}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_2222_api10json_delete_fail(self, method, url, body, headers):
        return (httplib.FORBIDDEN, '', {}, httplib.responses[httplib.FORBIDDEN])

    def _virtual_machines_2222_api10json_delete(self, method, url, body, headers):
        return (httplib.OK, '', {}, httplib.responses[httplib.OK])

    def _virtual_machines_1384_reboot_api10json_reboot(self, method, url, body, headers):
        body = """{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "foo",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              }"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_api10json_create(self, method, url, body, headers):
        body = """{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "foo",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              }"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _virtual_machines_api10json_virtual_machines(self, method, url, body, headers):
        body = """     [{
              "virtual_machine":
                {
                  "running": true,
                  "updated_at": "2009-05-15T06:55:02-04:00",
                  "power_action_pending": false,
                  "system_template_id": 41,
                  "id": 1384,
                  "cloud_id": 3,
                  "domain_name": "demodomain.com",
                  "hostname": "web01",
                  "consumer_id": 0,
                  "backups_enabled": false,
                  "password": "a8hjsjnbs91",
                  "label": "Web Server 01",
                  "slices_count": null,
                  "created_at": "2009-04-16T08:17:39-04:00"
                }
              },
              {
                "virtual_machine":
                  {
                    "running": true,
                    "updated_at": "2009-05-15T06:55:02-04:00",
                    "power_action_pending": false,
                    "system_template_id": 41,
                    "id": 1385,
                    "cloud_id": 3,
                    "domain_name": "demodomain.com",
                    "hostname": "mysql01",
                    "consumer_id": 0,
                    "backups_enabled": false,
                    "password": "dsi8h38hd2s",
                    "label": "MySQL Server 01",
                    "slices_count": null,
                    "created_at": "2009-04-16T08:17:39-04:00"
                  }
                }]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _available_clouds_api10json_templates(self, method, url, body, headers):
        body = """[{"cloud":{"system_templates":[{"id":9,"label":"Ubuntu 8.04 x64"},{"id":10,"label":"CentOS 5.2 x64"},{"id":11,"label":"Gentoo 2008.0 x64"},{"id":18,"label":"Ubuntu 8.04 x64 LAMP"},{"id":19,"label":"Ubuntu 8.04 x64 MySQL"},{"id":20,"label":"Ubuntu 8.04 x64 Postfix"},{"id":21,"label":"Ubuntu 8.04 x64 Apache"},{"id":22,"label":"CentOS 5.2 x64 MySQL"},{"id":23,"label":"CentOS 5.2 x64 LAMP"},{"id":24,"label":"CentOS 5.2 x64 HAProxy"},{"id":25,"label":"CentOS 5.2 x64 Postfix"},{"id":26,"label":"CentOS 5.2 x64 Varnish"},{"id":27,"label":"CentOS 5.2 x64 Shoutcast"},{"id":28,"label":"CentOS 5.2 x64 Apache"},{"id":40,"label":"cPanel"},{"id":42,"label":"Debian 5.0 (Lenny) x64"},{"id":58,"label":"Django on Ubuntu 8.04 (x86)"},{"id":59,"label":"Drupal 5 on Ubuntu 8.04 (x86)"},{"id":60,"label":"Drupal 6 on Ubuntu 8.04 (x86)"},{"id":61,"label":"Google App Engine on Ubuntu 8.04 (x86)"},{"id":62,"label":"LAMP on Ubuntu 8.04 (x86)"},{"id":63,"label":"LAPP on Ubuntu 8.04 (x86)"},{"id":64,"label":"MediaWiki on Ubuntu 8.04 (x86)"},{"id":65,"label":"MySQL on Ubuntu 8.04 (x86)"},{"id":66,"label":"phpBB on Ubuntu 8.04 (x86)"},{"id":67,"label":"PostgreSQL on Ubuntu 8.04 (x86)"},{"id":68,"label":"Rails on Ubuntu 8.04 (x86)"},{"id":69,"label":"Tomcat on Ubuntu 8.04 (x86)"},{"id":70,"label":"Wordpress on Ubuntu 8.04 (x86)"},{"id":71,"label":"Joomla on Ubuntu 8.04 (x86)"},{"id":72,"label":"Ubuntu 8.04 Default Install (turnkey)"},{"id":128,"label":"CentOS Optimised"},{"id":129,"label":"Optimised CentOS + Apache + MySQL + PHP"},{"id":130,"label":"Optimised CentOS + Apache + MySQL + Ruby"},{"id":131,"label":"Optimised CentOS + Apache + MySQL + Ruby + PHP"},{"id":132,"label":"Debian Optimised"},{"id":133,"label":"Optimised Debian + Apache + MySQL + PHP"},{"id":134,"label":"Optimised Debian + NGINX + MySQL + PHP"},{"id":135,"label":"Optimised Debian + Lighttpd + MySQL + PHP"},{"id":136,"label":"Optimised Debian + Apache + MySQL + Ruby + PHP"},{"id":137,"label":"Optimised Debian + Apache + MySQL + Ruby"},{"id":138,"label":"Optimised Debian + NGINX + MySQL + Ruby + PHP"},{"id":139,"label":"Optimised Debian + NGINX + MySQL + Ruby"},{"id":140,"label":"Optimised Debian + Apache + MySQL + PHP + Magento"},{"id":141,"label":"Optimised Debian + NGINX + MySQL + PHP + Magento"},{"id":142,"label":"Optimised Debian + Lighttpd + MySQL + PHP + Wordpress"}],"id":2,"label":"USA VPS Cloud"}},{"cloud":{"system_templates":[{"id":15,"label":"Ubuntu 8.04 x64"},{"id":16,"label":"CentOS 5.2 x64"},{"id":17,"label":"Gentoo 2008.0 x64"},{"id":29,"label":"Ubuntu 8.04 x64 LAMP"},{"id":30,"label":"Ubuntu 8.04 x64 MySQL"},{"id":31,"label":"Ubuntu 8.04 x64 Postfix"},{"id":32,"label":"Ubuntu 8.04 x64 Apache"},{"id":33,"label":"CentOS 5.2 x64 MySQL"},{"id":34,"label":"CentOS 5.2 x64 LAMP"},{"id":35,"label":"CentOS 5.2 x64 HAProxy"},{"id":36,"label":"CentOS 5.2 x64 Postfix"},{"id":37,"label":"CentOS 5.2 x64 Varnish"},{"id":38,"label":"CentOS 5.2 x64 Shoutcast"},{"id":39,"label":"CentOS 5.2 x64 Apache"},{"id":41,"label":"cPanel"},{"id":43,"label":"Debian 5.0 (Lenny) x64"},{"id":44,"label":"Django on Ubuntu 8.04 (x86)"},{"id":45,"label":"Drupal 5 on Ubuntu 8.04 (x86)"},{"id":46,"label":"Drupal 6 on Ubuntu 8.04 (x86)"},{"id":47,"label":"Google App Engine on Ubuntu 8.04 (x86)"},{"id":48,"label":"LAMP on Ubuntu 8.04 (x86)"},{"id":49,"label":"LAPP on Ubuntu 8.04 (x86)"},{"id":50,"label":"MediaWiki on Ubuntu 8.04 (x86)"},{"id":51,"label":"MySQL on Ubuntu 8.04 (x86)"},{"id":52,"label":"phpBB on Ubuntu 8.04 (x86)"},{"id":53,"label":"PostgreSQL on Ubuntu 8.04 (x86)"},{"id":54,"label":"Rails on Ubuntu 8.04 (x86)"},{"id":55,"label":"Tomcat on Ubuntu 8.04 (x86)"},{"id":56,"label":"Wordpress on Ubuntu 8.04 (x86)"},{"id":57,"label":"Joomla on Ubuntu 8.04 (x86)"},{"id":73,"label":"Ubuntu 8.04 Default Install (turnkey)"},{"id":148,"label":"CentOS Optimised"},{"id":149,"label":"Optimised CentOS + Apache + MySQL + PHP"},{"id":150,"label":"Optimised CentOS + Apache + MySQL + Ruby"},{"id":151,"label":"Optimised CentOS + Apache + MySQL + Ruby + PHP"},{"id":152,"label":"Debian Optimised"},{"id":153,"label":"Optimised Debian + Apache + MySQL + PHP"},{"id":154,"label":"Optimised Debian + NGINX + MySQL + PHP"},{"id":155,"label":"Optimised Debian + Lighttpd + MySQL + PHP"},{"id":156,"label":"Optimised Debian + Apache + MySQL + Ruby + PHP"},{"id":157,"label":"Optimised Debian + Apache + MySQL + Ruby"},{"id":158,"label":"Optimised Debian + NGINX + MySQL + Ruby + PHP"},{"id":159,"label":"Optimised Debian + NGINX + MySQL + Ruby"},{"id":160,"label":"Optimised Debian + Lighttpd + MySQL + PHP + Wordpress"}],"id":3,"label":"UK VPS Cloud"}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
    def _available_clouds_api10json_create(self, method, url, body, headers):
        body = """[{"cloud":{"system_templates":[{"id":9,"label":"Ubuntu 8.04 x64"}],"id":2,"label":"USA VPS Cloud"}}]"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
