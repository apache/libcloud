# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more§
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
import time
import unittest

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import u

from libcloud.compute.deployment import MultiStepDeployment, Deployment
from libcloud.compute.deployment import SSHKeyDeployment, ScriptDeployment
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState, DeploymentError, LibcloudError
from libcloud.compute.ssh import BaseSSHClient
from libcloud.compute.drivers.rackspace import RackspaceNodeDriver as Rackspace

from test import MockHttp, XML_HEADERS
from test.file_fixtures import ComputeFileFixtures, OpenStackFixtures
from mock import Mock, patch

from test.secrets import RACKSPACE_PARAMS

class MockDeployment(Deployment):
    def run(self, node, client):
        return node

class MockClient(BaseSSHClient):
    def __init__(self, *args, **kwargs):
        self.stdout = ''
        self.stderr = ''
        self.exit_status = 0

    def put(self, path, contents, chmod=755):
        return contents

    def run(self, name):
        return self.stdout, self.stderr, self.exit_status

    def delete(self, name):
        return True

class DeploymentTests(unittest.TestCase):

    def setUp(self):
        Rackspace.connectionCls.conn_classes = (None, RackspaceMockHttp)
        RackspaceMockHttp.type = None
        self.driver = Rackspace(*RACKSPACE_PARAMS)
        self.driver.features = {'create_node': ['generates_password']}
        self.node = Node(id=12345, name='test', state=NodeState.RUNNING,
                   public_ips=['1.2.3.4'], private_ips=['1.2.3.5'],
                   driver=Rackspace)

    def test_multi_step_deployment(self):
        msd = MultiStepDeployment()
        self.assertEqual(len(msd.steps), 0)

        msd.add(MockDeployment())
        self.assertEqual(len(msd.steps), 1)

        self.assertEqual(self.node, msd.run(node=self.node, client=None))

    def test_ssh_key_deployment(self):
        sshd = SSHKeyDeployment(key='1234')

        self.assertEqual(self.node, sshd.run(node=self.node,
                        client=MockClient(hostname='localhost')))

    def test_script_deployment(self):
        sd1 = ScriptDeployment(script='foobar', delete=True)
        sd2 = ScriptDeployment(script='foobar', delete=False)
        sd3 = ScriptDeployment(script='foobar', delete=False, name='foobarname')

        self.assertTrue(sd1.name.find('deployment') != '1')
        self.assertEqual(sd3.name, 'foobarname')

        self.assertEqual(self.node, sd1.run(node=self.node,
                        client=MockClient(hostname='localhost')))
        self.assertEqual(self.node, sd2.run(node=self.node,
                        client=MockClient(hostname='localhost')))

    def test_script_deployment_and_sshkey_deployment_argument_types(self):
        class FileObject(object):
            def __init__(self, name):
                self.name = name

            def read(self):
                return 'bar'

        ScriptDeployment(script='foobar')
        ScriptDeployment(script=u('foobar'))
        ScriptDeployment(script=FileObject('test'))

        SSHKeyDeployment(key='foobar')
        SSHKeyDeployment(key=u('foobar'))
        SSHKeyDeployment(key=FileObject('test'))

        try:
            ScriptDeployment(script=[])
        except TypeError:
            pass
        else:
            self.fail('TypeError was not thrown')

        try:
            SSHKeyDeployment(key={})
        except TypeError:
            pass
        else:
            self.fail('TypeError was not thrown')

    def test_wait_until_running_running_instantly(self):
        node2 = self.driver._wait_until_running(node=self.node, wait_period=1,
                                                timeout=10)
        self.assertEqual(self.node.uuid, node2.uuid)

    def test_wait_until_running_running_after_1_second(self):
        RackspaceMockHttp.type = '1_SECOND_DELAY'
        node2 = self.driver._wait_until_running(node=self.node, wait_period=1,
                                                timeout=10)
        self.assertEqual(self.node.uuid, node2.uuid)

    def test_wait_until_running_timeout(self):
        RackspaceMockHttp.type = 'TIMEOUT'

        try:
            self.driver._wait_until_running(node=self.node, wait_period=0.5,
                                            timeout=1)
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(e.value.find('Timed out') != -1)
        else:
            self.fail('Exception was not thrown')


    def test_wait_until_running_running_node_missing_from_list_nodes(self):
        RackspaceMockHttp.type = 'MISSING'

        try:
            self.driver._wait_until_running(node=self.node, wait_period=0.5,
                                            timeout=1)
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(e.value.find('is missing from list_nodes') != -1)
        else:
            self.fail('Exception was not thrown')

    def test_wait_until_running_running_multiple_nodes_have_same_uuid(self):
        RackspaceMockHttp.type = 'SAME_UUID'

        try:
            self.driver._wait_until_running(node=self.node, wait_period=0.5,
                                            timeout=1)
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(e.value.find('multiple nodes have same UUID') != -1)
        else:
            self.fail('Exception was not thrown')


    def test_ssh_client_connect_success(self):
        mock_ssh_client = Mock()
        mock_ssh_client.return_value = None

        ssh_client = self.driver._ssh_client_connect(ssh_client=mock_ssh_client,
                                                     timeout=10)
        self.assertEqual(mock_ssh_client, ssh_client)

    def test_ssh_client_connect_timeout(self):
        mock_ssh_client = Mock()
        mock_ssh_client.connect = Mock()
        mock_ssh_client.connect.side_effect = IOError('bam')

        try:
            self.driver._ssh_client_connect(ssh_client=mock_ssh_client,
                                            timeout=1)
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(e.value.find('Giving up') != -1)
        else:
            self.fail('Exception was not thrown')

    def test_run_deployment_script_success(self):
        task = Mock()
        ssh_client = Mock()

        ssh_client2 = self.driver._run_deployment_script(task=task,
                                                         node=self.node,
                                                         ssh_client=ssh_client,
                                                         max_tries=2)
        self.assertTrue(isinstance(ssh_client2, Mock))

    def test_run_deployment_script_exception(self):
        task = Mock()
        task.run = Mock()
        task.run.side_effect = Exception('bar')
        ssh_client = Mock()

        try:
            self.driver._run_deployment_script(task=task,
                                               node=self.node,
                                               ssh_client=ssh_client,
                                               max_tries=2)
        except LibcloudError:
            e = sys.exc_info()[1]
            self.assertTrue(e.value.find('Failed after 2 tries') != -1)
        else:
            self.fail('Exception was not thrown')

    @patch('libcloud.compute.base.SSHClient')
    @patch('libcloud.compute.ssh')
    def test_deploy_node_success(self, mock_ssh_module, _):
        self.driver.create_node = Mock()
        self.driver.create_node.return_value = self.node
        mock_ssh_module.have_paramiko = True

        deploy = Mock()

        node = self.driver.deploy_node(deploy=deploy)
        self.assertEqual(self.node.id, node.id)

    @patch('libcloud.compute.base.SSHClient')
    @patch('libcloud.compute.ssh')
    def test_deploy_node_exception_run_deployment_script(self, mock_ssh_module,
                                                         _):
        self.driver.create_node = Mock()
        self.driver.create_node.return_value = self.node
        mock_ssh_module.have_paramiko = True

        deploy = Mock()
        deploy.run = Mock()
        deploy.run.side_effect = Exception('foo')

        try:
            self.driver.deploy_node(deploy=deploy)
        except DeploymentError:
            e = sys.exc_info()[1]
            self.assertTrue(e.node.id, self.node.id)
        else:
            self.fail('Exception was not thrown')

    @patch('libcloud.compute.base.SSHClient')
    @patch('libcloud.compute.ssh')
    def test_deploy_node_exception_ssh_client_connect(self, mock_ssh_module,
                                                      ssh_client):
        self.driver.create_node = Mock()
        self.driver.create_node.return_value = self.node

        mock_ssh_module.have_paramiko = True

        deploy = Mock()
        ssh_client.side_effect = IOError('bar')

        try:
            self.driver.deploy_node(deploy=deploy)
        except DeploymentError:
            e = sys.exc_info()[1]
            self.assertTrue(e.node.id, self.node.id)
        else:
            self.fail('Exception was not thrown')

    @patch('libcloud.compute.ssh')
    def test_deploy_node_depoy_node_not_implemented(self, mock_ssh_module):
        self.driver.features = {'create_node': []}
        mock_ssh_module.have_paramiko = True

        try:
            self.driver.deploy_node(deploy=Mock())
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

        self.driver.features = {}

        try:
            self.driver.deploy_node(deploy=Mock())
        except NotImplementedError:
            pass
        else:
            self.fail('Exception was not thrown')

    @patch('libcloud.compute.base.SSHClient')
    @patch('libcloud.compute.ssh')
    def test_deploy_node_password_auth(self, mock_ssh_module, _):
        self.driver.features = {'create_node': ['password']}
        mock_ssh_module.have_paramiko = True

        self.driver.create_node = Mock()
        self.driver.create_node.return_value = self.node

        node = self.driver.deploy_node(deploy=Mock())
        self.assertEqual(self.node.id, node.id)

    @patch('libcloud.compute.base.SSHClient')
    @patch('libcloud.compute.ssh')
    def test_exception_is_thrown_is_paramiko_is_not_available(self,
                                                              mock_ssh_module,
                                                              _):
        self.driver.features = {'create_node': ['password']}
        self.driver.create_node = Mock()
        self.driver.create_node.return_value = self.node

        mock_ssh_module.have_paramiko = False

        try:
            self.driver.deploy_node(deploy=Mock())
        except RuntimeError:
            e = sys.exc_info()[1]
            self.assertTrue(str(e).find('paramiko is not installed') != -1)
        else:
            self.fail('Exception was not thrown')

        mock_ssh_module.have_paramiko = True
        node = self.driver.deploy_node(deploy=Mock())
        self.assertEqual(self.node.id, node.id)

class RackspaceMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('openstack')
    auth_fixtures = OpenStackFixtures()

    def _v1_1_auth(self, method, url, body, headers):
        body = self.auth_fixtures.load('_v1_1__auth.json')
        return (httplib.OK, body, {'content-type': 'application/json; charset=UTF-8'}, httplib.responses[httplib.OK])

    # fake auth token response
    def _v1_0(self, method, url, body, headers):
        headers = {'x-server-management-url': 'https://servers.api.rackspacecloud.com/v1.0/slug',
                   'x-auth-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-cdn-management-url': 'https://cdn.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-token': 'FE011C19-CF86-4F87-BE5D-9229145D7A06',
                   'x-storage-url': 'https://storage4.clouddrive.com/v1/MossoCloudFS_FE011C19-CF86-4F87-BE5D-9229145D7A06'}
        return (httplib.NO_CONTENT, "", headers, httplib.responses[httplib.NO_CONTENT])

    def _v1_0_slug_servers_detail(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_deployment_success.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_1_SECOND_DELAY(self, method, url, body, headers):
        time.sleep(1)
        body = self.fixtures.load('v1_slug_servers_detail_deployment_success.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_TIMEOUT(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_deployment_pending.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_MISSING(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_deployment_missing.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])

    def _v1_0_slug_servers_detail_SAME_UUID(self, method, url, body, headers):
        body = self.fixtures.load('v1_slug_servers_detail_deployment_same_uuid.xml')
        return (httplib.OK, body, XML_HEADERS, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
