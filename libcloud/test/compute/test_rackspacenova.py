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

from libcloud.utils.py3 import method_type
from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.rackspacenova import RackspaceNovaBetaNodeDriver, \
                                                   RackspaceNovaDfwNodeDriver, \
                                                   RackspaceNovaOrdNodeDriver, \
                                                   RackspaceNovaLonNodeDriver
from libcloud.test.compute.test_openstack import OpenStack_1_1_Tests, OpenStack_1_1_MockHttp
from libcloud.pricing import clear_pricing_data

from libcloud.test.secrets import RACKSPACE_NOVA_PARAMS


class RackspaceNovaMockHttp(OpenStack_1_1_MockHttp):
    def __init__(self, *args, **kwargs):
        super(RackspaceNovaMockHttp, self).__init__(*args, **kwargs)

        methods1 = OpenStack_1_1_MockHttp.__dict__

        names1 = [m for m in methods1 if m.find('_v1_1') == 0]

        for name in names1:
            method = methods1[name]
            new_name = name.replace('_v1_1_slug_', '_v2_1337_')
            setattr(self, new_name, method_type(method, self,
                RackspaceNovaMockHttp))


class RackspaceNovaLonMockHttp(RackspaceNovaMockHttp):

    def _v2_0_tokens(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v2_0__auth_lon.json')
        return (httplib.OK, body, self.json_content_headers, httplib.responses[httplib.OK])


class RackspaceNovaBetaTests(OpenStack_1_1_Tests):

    driver_klass = RackspaceNovaBetaNodeDriver
    driver_type = RackspaceNovaBetaNodeDriver
    driver_args = RACKSPACE_NOVA_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '2.0'}

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (RackspaceNovaMockHttp, RackspaceNovaMockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v2.0/"
        self.driver = self.create_driver()
        # normally authentication happens lazily, but we force it here
        self.driver.connection._populate_hosts_and_request_paths()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

    def test_service_catalog(self):
        self.assertEqual('https://preprod.dfw.servers.api.rackspacecloud.com/v2/1337', self.driver.connection.get_endpoint())


class RackspaceNovaDfwTests(OpenStack_1_1_Tests):

    driver_klass = RackspaceNovaDfwNodeDriver
    driver_type = RackspaceNovaDfwNodeDriver
    driver_args = RACKSPACE_NOVA_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '2.0'}

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (RackspaceNovaMockHttp, RackspaceNovaMockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v2.0/"
        self.driver = self.create_driver()
        # normally authentication happens lazily, but we force it here
        self.driver.connection._populate_hosts_and_request_paths()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

    def test_service_catalog(self):
        self.assertEqual('https://dfw.servers.api.rackspacecloud.com/v2/1337', self.driver.connection.get_endpoint())


class RackspaceNovaOrdTests(OpenStack_1_1_Tests):

    driver_klass = RackspaceNovaOrdNodeDriver
    driver_type = RackspaceNovaOrdNodeDriver
    driver_args = RACKSPACE_NOVA_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '2.0'}

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (RackspaceNovaMockHttp, RackspaceNovaMockHttp)
        self.driver_klass.connectionCls.auth_url = "https://auth.api.example.com/v2.0/"
        self.driver = self.create_driver()
        # normally authentication happens lazily, but we force it here
        self.driver.connection._populate_hosts_and_request_paths()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

    def test_service_catalog(self):
        self.assertEqual('https://ord.servers.api.rackspacecloud.com/v2/1337', self.driver.connection.get_endpoint())


class RackspaceNovaLonTests(OpenStack_1_1_Tests):

    driver_klass = RackspaceNovaLonNodeDriver
    driver_type = RackspaceNovaLonNodeDriver
    driver_args = RACKSPACE_NOVA_PARAMS + ('1.1',)
    driver_kwargs = {'ex_force_auth_version': '2.0'}

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args, **self.driver_kwargs)

    def setUp(self):
        self.driver_klass.connectionCls.conn_classes = (RackspaceNovaLonMockHttp, RackspaceNovaLonMockHttp)
        self.driver_klass.connectionCls.auth_url = "https://lon.auth.api.example.com/v2.0/"
        self.driver = self.create_driver()
        # normally authentication happens lazily, but we force it here
        self.driver.connection._populate_hosts_and_request_paths()
        clear_pricing_data()
        self.node = self.driver.list_nodes()[1]

    def test_service_catalog(self):
        self.assertEqual('https://lon.servers.api.rackspacecloud.com/v2/1337', self.driver.connection.get_endpoint())


if __name__ == '__main__':
    sys.exit(unittest.main())
