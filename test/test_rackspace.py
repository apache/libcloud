# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
import unittest

from libcloud.types import InvalidCredsException
from libcloud.providers import Rackspace
from libcloud.types import Provider
from libcloud.base import Node, NodeImage, NodeSize

from test import MockHttp, TestCaseMixin
from secrets import RACKSPACE_USER, RACKSPACE_KEY
import httplib

class RackspaceTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        Rackspace.connectionCls.conn_classes = (None, RackspaceMockHttp)
        RackspaceMockHttp.type = None
        self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)

    def test_auth(self):
        RackspaceMockHttp.type = 'UNAUTHORIZED'
        try:
            self.driver = Rackspace(RACKSPACE_USER, RACKSPACE_KEY)
        except InvalidCredsException, e:
            self.assertEqual(True, isinstance(e, InvalidCredsException))
        else:
            self.fail('test should have thrown')

    def test_list_nodes(self):
        RackspaceMockHttp.type = 'EMPTY'
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 0)
        RackspaceMockHttp.type = None
        ret = self.driver.list_nodes()
        self.assertEqual(len(ret), 1)
        node = ret[0]
        self.assertTrue(node.public_ip[0])
        self.assertTrue(node.private_ip[0])
        self.assertEqual(node.extra.get('flavorId'), '1')
        self.assertEqual(node.extra.get('imageId'), '11')

    def test_list_sizes(self):
        ret = self.driver.list_sizes()
        self.assertEqual(len(ret), 7)
        size = ret[0]
        self.assertEqual(size.name, '256 slice')

    def test_list_images(self):
        ret = self.driver.list_images()

    def test_create_node(self):
        image = NodeImage(id=11, name='Ubuntu 8.10 (intrepid)', driver=self.driver)
        size = NodeSize(1, '256 slice', None, None, None, None, driver=self.driver)
        node = self.driver.create_node('racktest', image, size)
        self.assertEqual(node.name, 'racktest')
        self.assertEqual(node.extra.get('password'), 'racktestvJq7d3')

    def test_reboot_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.reboot()
        self.assertTrue(ret is True)

    def test_destroy_node(self):
        node = Node(id=72258, name=None, state=None, public_ip=None, private_ip=None,
                    driver=self.driver)
        ret = node.destroy()
        self.assertTrue(ret is True)

class RackspaceMockHttp(MockHttp):

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}

        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])
    def _v1_0_UNAUTHORIZED(self, method, url, body, headers):
        return  (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _v1_0_slug_servers_detail_EMPTY(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><servers xmlns="http://docs.rackspacecloud.com/servers/api/v1.0"/>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><servers xmlns="http://docs.rackspacecloud.com/servers/api/v1.0"><server status="ACTIVE" progress="100" hostId="9dd380940fcbe39cb30255ed4664f1f3" flavorId="1" imageId="11" id="72258" name="racktest"><metadata/><addresses><public><ip addr="67.23.21.33"/></public><private><ip addr="10.176.168.218"/></private></addresses></server></servers>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_flavors_detail(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><flavors xmlns="http://docs.rackspacecloud.com/servers/api/v1.0"><flavor disk="10" ram="256" name="256 slice" id="1"/><flavor disk="20" ram="512" name="512 slice" id="2"/><flavor disk="40" ram="1024" name="1GB slice" id="3"/><flavor disk="80" ram="2048" name="2GB slice" id="4"/><flavor disk="160" ram="4096" name="4GB slice" id="5"/><flavor disk="320" ram="8192" name="8GB slice" id="6"/><flavor disk="620" ram="15872" name="15.5GB slice" id="7"/></flavors>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _v1_0_slug_images_detail(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><images xmlns="http://docs.rackspacecloud.com/servers/api/v1.0"><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="CentOS 5.2" id="2"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Gentoo 2008.0" id="3"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Debian 5.0 (lenny)" id="4"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Fedora 10 (Cambridge)" id="5"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="CentOS 5.3" id="7"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Ubuntu 9.04 (jaunty)" id="8"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Arch 2009.02" id="9"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Ubuntu 8.04.2 LTS (hardy)" id="10"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Ubuntu 8.10 (intrepid)" id="11"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Red Hat EL 5.3" id="12"/><image status="ACTIVE" created="2009-07-20T09:14:37-05:00" updated="2009-07-20T09:14:37-05:00" name="Fedora 11 (Leonidas)" id="13"/></images>"""
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        
    def _v1_0_slug_servers(self, method, url, body, headers):
        body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><server xmlns="http://docs.rackspacecloud.com/servers/api/v1.0" status="BUILD" progress="0" hostId="9dd380940fcbe39cb30255ed4664f1f3" flavorId="1" imageId="11" adminPass="racktestvJq7d3" id="72258" name="racktest"><metadata/><addresses><public><ip addr="67.23.21.33"/></public><private><ip addr="10.176.168.218"/></private></addresses></server>"""
        return (httplib.ACCEPTED, body, {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258_action(self, method, url, body, headers):
        if method != "POST" or body[:8] != "<reboot ":
            raise NotImplemented
        # only used by reboot() right now, but we will need to parse body someday !!!!
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

    def _v1_0_slug_servers_72258(self, method, url, body, headers):
        if method != "DELETE":
            raise NotImplemented
        # only used by destroy node()
        return (httplib.ACCEPTED, "", {}, httplib.responses[httplib.ACCEPTED])

