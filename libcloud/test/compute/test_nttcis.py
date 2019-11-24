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
from types import GeneratorType

import pytest

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import ET
from libcloud.common.types import InvalidCredsError
from libcloud.common.nttcis import NttCisAPIException, NetworkDomainServicePlan
from libcloud.common.nttcis import NttCisServerCpuSpecification, NttCisServerDisk, NttCisServerVMWareTools
from libcloud.common.nttcis import NttCisTag, NttCisTagKey
from libcloud.common.nttcis import ClassFactory
from libcloud.common.nttcis import TYPES_URN
from libcloud.compute.drivers.nttcis import NttCisNodeDriver as NttCis
from libcloud.compute.drivers.nttcis import NttCisNic
from libcloud.compute.base import Node, NodeAuthPassword, NodeLocation
from libcloud.test import MockHttp
from libcloud.test.file_fixtures import ComputeFileFixtures
from libcloud.test.secrets import NTTCIS_PARAMS
from libcloud.utils.xml import fixxpath, findtext, findall


@pytest.fixture()
def driver():
    NttCis.connectionCls.active_api_version = "2.7"
    NttCis.connectionCls.conn_class = NttCisMockHttp
    NttCisMockHttp.type = None
    driver = NttCis(*NTTCIS_PARAMS)
    return driver


def test_auth_fails(driver):
    with pytest.raises(ValueError):
        NttCis(*NTTCIS_PARAMS, region='blah')


def test_get_account_details(driver):
    NttCisMockHttp.type = None
    ret = driver.connection.get_account_details()
    assert ret.full_name == 'Test User'
    assert ret.first_name == 'Test'
    assert ret.email == 'test@example.com'


def test_invalid_creds(driver):
    NttCisMockHttp.type = 'UNAUTHORIZED'
    with pytest.raises(InvalidCredsError):
        driver.list_nodes()


def test_list_locations_response(driver):
    NttCisMockHttp.type = None
    ret = driver.list_locations()
    assert len(ret) == 5
    first_loc = ret[0]
    assert first_loc.id == 'NA3'
    assert first_loc.name == 'US - West'
    assert first_loc.country == 'US'


def test_list_nodes_response(driver):
    NttCisMockHttp.type = None
    ret = driver.list_nodes()
    assert len(ret) == 7


def test_node_extras(driver):
    NttCisMockHttp.type = None
    ret = driver.list_nodes()
    assert isinstance(ret[0].extra['vmWareTools'], NttCisServerVMWareTools)
    assert isinstance(ret[0].extra['cpu'], NttCisServerCpuSpecification)
    assert isinstance(ret[0].extra['disks'], list)
    assert isinstance(ret[0].extra['disks'][0], NttCisServerDisk)
    assert ret[0].extra['disks'][0].size_gb, 10
    assert isinstance(ret[1].extra['disks'], list)
    assert isinstance(ret[1].extra['disks'][0], NttCisServerDisk)
    assert ret[1].extra['disks'][0].size_gb, 10


def test_server_states(driver):
    NttCisMockHttp.type = None
    ret = driver.list_nodes()
    assert ret[0].state == 'running'
    assert ret[1].state == 'starting'
    assert ret[2].state == 'stopping'
    assert ret[3].state == 'reconfiguring'
    assert ret[4].state == 'running'
    assert ret[5].state == 'terminated'
    assert ret[6].state == 'stopped'
    assert len(ret) == 7


def test_list_nodes_response_PAGINATED(driver):
    NttCisMockHttp.type = 'PAGINATED'
    ret = driver.list_nodes()
    assert len(ret) == 7


def test_paginated_mcp2_call_EMPTY(driver):
    # cache org
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'EMPTY'
    node_list_generator = driver.connection.paginated_request_with_orgId_api_2('server/server')
    empty_node_list = []
    for node_list in node_list_generator:
        empty_node_list.extend(node_list)
    assert len(empty_node_list) == 0


def test_paginated_mcp2_call_PAGED_THEN_EMPTY(driver):
    # cache org
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'PAGED_THEN_EMPTY'
    node_list_generator = driver.connection.paginated_request_with_orgId_api_2('server/server')
    final_node_list = []
    for node_list in node_list_generator:
        final_node_list.extend(node_list)
    assert len(final_node_list) == 2


def test_paginated_mcp2_call_with_page_size(driver):
    # cache org
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'PAGESIZE50'
    node_list_generator = driver.connection.paginated_request_with_orgId_api_2('server/server', page_size=50)
    assert isinstance(node_list_generator, GeneratorType)


# We're making sure here the filters make it to the URL
# See  _caas_2_4_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_ALLFILTERS for asserts
def test_list_nodes_response_strings_ALLFILTERS(driver):
    NttCisMockHttp.type = 'ALLFILTERS'
    ret = driver.list_nodes(ex_location='fake_loc', ex_name='fake_name',
                            ex_ipv6='fake_ipv6', ex_ipv4='fake_ipv4', ex_vlan='fake_vlan',
                            ex_image='fake_image', ex_deployed=True,
                            ex_started=True, ex_state='fake_state',
                            ex_network_domain='fake_network_domain')
    assert isinstance(ret, list)
    assert len(ret) == 7

    node = ret[3]
    assert isinstance(node.extra['disks'], list)
    assert isinstance(node.extra['disks'][0], NttCisServerDisk)
    assert node.image.id == '3ebf3c0f-90fe-4a8b-8585-6e65b316592c'
    assert node.image.name == 'WIN2008S/32'
    disk = node.extra['disks'][0]
    assert disk.id == "c2e1f199-116e-4dbc-9960-68720b832b0a"
    assert disk.scsi_id == 0
    assert disk.size_gb == 50
    assert disk.speed == "STANDARD"
    assert disk.state == "NORMAL"


def test_list_nodes_response_LOCATION(driver):
    NttCisMockHttp.type = None
    ret = driver.list_locations()
    first_loc = ret[0]
    ret = driver.list_nodes(ex_location=first_loc)
    for node in ret:
        assert node.extra['datacenterId'] == 'NA3'


def test_list_nodes_response_LOCATION_STR(driver):
    NttCisMockHttp.type = None
    ret = driver.list_nodes(ex_location='NA3')
    for node in ret:
        assert node.extra['datacenterId'] == 'NA3'


def test_list_sizes_response(driver):
    NttCisMockHttp.type = None
    ret = driver.list_sizes()
    assert len(ret) == 1
    size = ret[0]
    assert size.name == 'default'


def test_list_datacenter_snapshot_windows(driver):
    NttCisMockHttp.type = None
    ret = driver.list_snapshot_windows("f1d6a564-490e-4166-b91d-feddc1f92025", "ADVANCED")
    assert isinstance(ret[0], dict)


def test_list_snapshots(driver):
    NttCisMockHttp.type = None
    snapshots = driver.list_snapshots('sdk_server_1', page_size=1)
    assert len(snapshots) == 1
    assert snapshots[0]['id'] == "d11940a8-1455-43bf-a2de-b51a38c2aa94"


def test_enable_snapshot_service(driver):
    NttCisMockHttp.type = None
    window_id = 'ea646520-4272-11e8-838c-180373fb68df'
    node = 'e1eb7d71-93c9-4b9c-807c-e05932dc8143'
    result = driver.ex_enable_snapshots(node, window_id)
    assert result is True


def test_initiate_manual_snapshot(driver):
    NttCisMockHttp.type = None
    result = driver.ex_initiate_manual_snapshot('test', 'e1eb7d71-93c9-4b9c-807c-e05932dc8143')
    assert result is True


def test_create_snapshot_preview_server(driver):
    snapshot_id = "dd9a9e7e-2de7-4543-adef-bb1fda7ac030"
    server_name = "test_snapshot"
    start = "true"
    nic_connected = "true"
    result = driver.ex_create_snapshot_preview_server(
        snapshot_id, server_name, start, nic_connected)
    assert result is True


def test_disable_node_snapshot(driver):
    node = "e1eb7d71-93c9-4b9c-807c-e05932dc8143"
    assert driver.ex_disable_snapshots(node) is True


def test_reboot_node_response(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = node.reboot()
    assert ret is True


def test_reboot_node_response_INPROGRESS(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    with pytest.raises(NttCisAPIException):
        node.reboot()


def test_destroy_node_response(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = node.destroy()
    assert ret is True


def test_destroy_node_response_RESOURCE_BUSY(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    with pytest.raises(NttCisAPIException):
        node.destroy()


def test_list_images(driver):
    images = driver.list_images()
    assert len(images) == 3
    assert images[0].name == 'RedHat 6 64-bit 2 CPU'
    assert images[0].id == 'c14b1a46-2428-44c1-9c1a-b20e6418d08c'
    assert images[0].extra['location'].id == 'NA9'
    assert images[0].extra['cpu'].cpu_count == 2
    assert images[0].extra['OS_displayName'] == 'REDHAT6/64'


def test_clean_failed_deployment_response_with_node(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_clean_failed_deployment(node)
    assert ret is True


def test_clean_failed_deployment_response_with_node_id(driver):
    node = 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    ret = driver.ex_clean_failed_deployment(node)
    assert ret is True


def test_ex_list_customer_images(driver):
    images = driver.ex_list_customer_images()
    assert len(images) == 3
    assert images[0].name == 'ImportedCustomerImage'
    assert images[0].id == '5234e5c7-01de-4411-8b6e-baeb8d91cf5d'
    assert images[0].extra['location'].id == 'NA9'
    assert images[0].extra['cpu'].cpu_count == 4
    assert images[0].extra['OS_displayName'] == 'REDHAT6/64'


def test_create_mcp1_node_optional_param(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    network = driver.ex_list_networks()[0]
    cpu_spec = NttCisServerCpuSpecification(cpu_count='4',
                                            cores_per_socket='2',
                                            performance='STANDARD')
    disks = [NttCisServerDisk(scsi_id='0', speed='HIGHPERFORMANCE')]
    node = driver.create_node(name='test2', image=image, auth=root_pw,
                              ex_description='test2 node',
                              ex_network=network,
                              ex_is_started=False,
                              ex_memory_gb=8,
                              ex_disks=disks,
                              ex_cpu_specification=cpu_spec,
                              ex_primary_dns='10.0.0.5',
                              ex_secondary_dns='10.0.0.6'
                              )
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_mcp1_node_response_no_pass_random_gen(driver):
    image = driver.list_images()[0]
    network = driver.ex_list_networks()[0]
    node = driver.create_node(name='test2', image=image, auth=None,
                              ex_description='test2 node',
                              ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'
    assert 'password' in node.extra


def test_create_mcp1_node_response_no_pass_customer_windows(driver):
    image = driver.ex_list_customer_images()[1]
    network = driver.ex_list_networks()[0]
    node = driver.create_node(name='test2', image=image, auth=None,
                              ex_description='test2 node', ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'
    assert 'password' in node.extra


def test_create_mcp1_node_response_no_pass_customer_windows_STR(driver):
    image = driver.ex_list_customer_images()[1].id
    network = driver.ex_list_networks()[0]
    node = driver.create_node(name='test2', image=image, auth=None,
                              ex_description='test2 node', ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'
    assert'password' in node.extra


def test_create_mcp1_node_response_no_pass_customer_linux(driver):
    image = driver.ex_list_customer_images()[0]
    network = driver.ex_list_networks()[0]
    node = driver.create_node(name='test2', image=image, auth=None,
                              ex_description='test2 node', ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'
    assert 'password' not in node.extra


def test_create_mcp1_node_response_no_pass_customer_linux_STR(driver):
    image = driver.ex_list_customer_images()[0].id
    network = driver.ex_list_networks()[0]
    node = driver.create_node(name='test2', image=image, auth=None,
                              ex_description='test2 node', ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'
    assert 'password' not in node.extra


def test_create_mcp1_node_response_STR(driver):
    rootPw = 'pass123'
    image = driver.list_images()[0].id
    network = driver.ex_list_networks()[0].id
    node = driver.create_node(name='test2', image=image, auth=rootPw,
                              ex_description='test2 node', ex_network=network,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_mcp1_node_no_network(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(InvalidRequestError):
        driver.create_node(name='test2',
                           image=image,
                           auth=rootPw,
                           ex_description='test2 node',
                           ex_network=None,
                           ex_is_started=False)


def test_create_node_mcp1_ipv4(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network='fakenetwork',
                              ex_primary_ipv4='10.0.0.1',
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_mcp1_network(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network='fakenetwork',
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_response_network_domain(driver):
    rootPw = NodeAuthPassword('pass123')
    location = driver.ex_get_location_by_id('NA9')
    image = driver.list_images(location=location)[0]
    network_domain = driver.ex_list_network_domains(location=location)[0]
    vlan = driver.ex_list_vlans(location=location)[0]
    cpu = NttCisServerCpuSpecification(
                                        cpu_count=4,
                                        cores_per_socket=1,
                                        performance='HIGHPERFORMANCE'
                                      )
    node = driver.create_node(name='test2', image=image, auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain=network_domain,
                              ex_vlan=vlan,
                              ex_is_started=False, ex_cpu_specification=cpu,
                              ex_memory_gb=4)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_response_network_domain_STR(driver):
    rootPw = NodeAuthPassword('pass123')
    location = driver.ex_get_location_by_id('NA9')
    image = driver.list_images(location=location)[0]
    network_domain = driver.ex_list_network_domains(location=location)[0].id
    vlan = driver.ex_list_vlans(location=location)[0].id
    cpu = NttCisServerCpuSpecification(
                                        cpu_count=4,
                                        cores_per_socket=1,
                                        performance='HIGHPERFORMANCE'
                                       )
    node = driver.create_node(name='test2', image=image, auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain=network_domain,
                              ex_vlan=vlan,
                              ex_is_started=False, ex_cpu_specification=cpu,
                              ex_memory_gb=4)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_mcp2_vlan(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_vlan='fakevlan',
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_mcp2_ipv4(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_ipv4='10.0.0.1',
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_network_domain_no_vlan_or_ipv4(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(name='test2',
                           image=image,
                           auth=rootPw,
                           ex_description='test2 node',
                           ex_network_domain='fake_network_domain',
                           ex_is_started=False)


def test_create_node_response(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(
                              name='test3',
                              image=image,
                              auth=rootPw,
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_vlan='fakevlan'
                             )
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_ms_time_zone(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(
                              name='test3',
                              image=image,
                              auth=rootPw,
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_vlan='fakevlan',
                              ex_microsoft_time_zone='040'
                            )
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_ambigious_mcps_fail(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(
                           name='test3',
                           image=image,
                           auth=rootPw,
                           ex_network_domain='fakenetworkdomain',
                           ex_network='fakenetwork',
                           ex_primary_nic_vlan='fakevlan'
                         )


def test_create_node_no_network_domain_fail(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(
                           name='test3',
                           image=image,
                           auth=rootPw,
                           ex_primary_nic_vlan='fakevlan'
                          )


def test_create_node_no_primary_nic_fail(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(
                            name='test3',
                            image=image,
                            auth=rootPw,
                            ex_network_domain='fakenetworkdomain'
                          )


def test_create_node_primary_vlan_nic(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(
                              name='test3',
                              image=image,
                              auth=rootPw,
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_vlan='fakevlan',
                              ex_primary_nic_network_adapter='v1000'
                            )
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_primary_ipv4(driver):
    rootPw = 'pass123'
    image = driver.list_images()[0]
    node = driver.create_node(
                              name='test3',
                              image=image,
                              auth=rootPw,
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_private_ipv4='10.0.0.1'
                            )
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_both_primary_nic_and_vlan_fail(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(
                           name='test3',
                           image=image,
                           auth=rootPw,
                           ex_network_domain='fakenetworkdomain',
                           ex_primary_nic_private_ipv4='10.0.0.1',
                           ex_primary_nic_vlan='fakevlan'
                          )


def test_create_node_cpu_specification(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    cpu_spec = NttCisServerCpuSpecification(cpu_count='4',
                                            cores_per_socket='2',
                                            performance='STANDARD')
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_private_ipv4='10.0.0.1',
                              ex_is_started=False,
                              ex_cpu_specification=cpu_spec)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_memory(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]

    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_private_ipv4='10.0.0.1',
                              ex_is_started=False,
                              ex_memory_gb=8)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_disks(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    disks = [NttCisServerDisk(scsi_id='0', speed='HIGHPERFORMANCE')]
    node = driver.create_node(name='test2',
                                   image=image,
                                   auth=rootPw,
                                   ex_description='test2 node',
                                   ex_network_domain='fakenetworkdomain',
                                   ex_primary_nic_private_ipv4='10.0.0.1',
                                   ex_is_started=False,
                                   ex_disks=disks)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_disks_fail(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    disks = 'blah'
    with pytest.raises(TypeError):
        driver.create_node(name='test2',
                           image=image,
                           auth=root_pw,
                           ex_description='test2 node',
                           ex_network_domain='fakenetworkdomain',
                           ex_primary_nic_private_ipv4='10.0.0.1',
                           ex_is_started=False,
                           ex_disks=disks)


def test_create_node_ipv4_gateway(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_private_ipv4='10.0.0.1',
                              ex_is_started=False,
                              ex_ipv4_gateway='10.2.2.2')
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_network_domain_no_vlan_no_ipv4_fail(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(ValueError):
        driver.create_node(name='test2',
                           image=image,
                           auth=rootPw,
                           ex_description='test2 node',
                           ex_network_domain='fake_network_domain',
                           ex_is_started=False)


def test_create_node_mcp2_additional_nics_legacy(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    additional_vlans = ['fakevlan1', 'fakevlan2']
    additional_ipv4 = ['10.0.0.2', '10.0.0.3']
    node = driver.create_node(
                              name='test2',
                              image=image,
                              auth=rootPw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_ipv4='10.0.0.1',
                              ex_additional_nics_vlan=additional_vlans,
                              ex_additional_nics_ipv4=additional_ipv4,
                              ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_bad_additional_nics_ipv4(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(TypeError):
        driver.create_node(name='test2',
                           image=image,
                           auth=rootPw,
                           ex_description='test2 node',
                           ex_network_domain='fake_network_domain',
                           ex_vlan='fake_vlan',
                           ex_additional_nics_ipv4='badstring',
                           ex_is_started=False)


def test_create_node_additional_nics(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    nic1 = NttCisNic(vlan='fake_vlan',
                     network_adapter_name='v1000')
    nic2 = NttCisNic(private_ip_v4='10.1.1.2',
                     network_adapter_name='v1000')
    additional_nics = [nic1, nic2]

    node = driver.create_node(name='test2',
                              image=image,
                              auth=root_pw,
                              ex_description='test2 node',
                              ex_network_domain='fakenetworkdomain',
                              ex_primary_nic_private_ipv4='10.0.0.1',
                              ex_additional_nics=additional_nics,
                              ex_is_started=False)

    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_create_node_additional_nics_vlan_ipv4_coexist_fail(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    nic1 = NttCisNic(private_ip_v4='10.1.1.1', vlan='fake_vlan',
                            network_adapter_name='v1000')
    nic2 = NttCisNic(private_ip_v4='10.1.1.2', vlan='fake_vlan2',
                            network_adapter_name='v1000')
    additional_nics = [nic1, nic2]
    with pytest.raises(ValueError):
        driver.create_node(name='test2',
                                image=image,
                                auth=root_pw,
                                ex_description='test2 node',
                                ex_network_domain='fakenetworkdomain',
                                ex_primary_nic_private_ipv4='10.0.0.1',
                                ex_additional_nics=additional_nics,
                                ex_is_started=False
                                )


def test_create_node_additional_nics_invalid_input_fail(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    additional_nics = 'blah'
    with pytest.raises(TypeError):
        driver.create_node(name='test2',
                                image=image,
                                auth=root_pw,
                                ex_description='test2 node',
                                ex_network_domain='fakenetworkdomain',
                                ex_primary_nic_private_ipv4='10.0.0.1',
                                ex_additional_nics=additional_nics,
                                ex_is_started=False
                                )


def test_create_node_additional_nics_vlan_ipv4_not_exist_fail(driver):
    root_pw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    nic1 = NttCisNic(network_adapter_name='v1000')
    nic2 = NttCisNic(network_adapter_name='v1000')
    additional_nics = [nic1, nic2]
    with pytest.raises(ValueError):
        driver.create_node(name='test2',
                                image=image,
                                auth=root_pw,
                                ex_description='test2 node',
                                ex_network_domain='fakenetworkdomain',
                                ex_primary_nic_private_ipv4='10.0.0.1',
                                ex_additional_nics=additional_nics,
                                ex_is_started=False)


def test_create_node_bad_additional_nics_vlan(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    with pytest.raises(TypeError):
        driver.create_node(name='test2',
                                image=image,
                                auth=rootPw,
                                ex_description='test2 node',
                                ex_network_domain='fake_network_domain',
                                ex_vlan='fake_vlan',
                                ex_additional_nics_vlan='badstring',
                                ex_is_started=False)


def test_create_node_mcp2_indicate_dns(driver):
    rootPw = NodeAuthPassword('pass123')
    image = driver.list_images()[0]
    node = driver.create_node(name='test2',
                                   image=image,
                                   auth=rootPw,
                                   ex_description='test node dns',
                                   ex_network_domain='fakenetworkdomain',
                                   ex_primary_ipv4='10.0.0.1',
                                   ex_primary_dns='8.8.8.8',
                                   ex_secondary_dns='8.8.4.4',
                                   ex_is_started=False)
    assert node.id == 'e75ead52-692f-4314-8725-c8a4f4d13a87'
    assert node.extra['status'].action == 'DEPLOY_SERVER'


def test_ex_shutdown_graceful(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_shutdown_graceful(node)
    assert ret is True


def test_ex_shutdown_graceful_INPROGRESS(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    with pytest.raises(NttCisAPIException):
        driver.ex_shutdown_graceful(node)


def test_ex_start_node(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_start_node(node)
    assert ret is True


def test_ex_start_node_INPROGRESS(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    with pytest.raises(NttCisAPIException):
        driver.ex_start_node(node)


def test_ex_power_off(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_power_off(node)
    assert ret is True


def test_ex_update_vm_tools(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_update_vm_tools(node)
    assert ret is True


def test_ex_power_off_INPROGRESS(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    node = Node(id='11', name=None, state='STOPPING',
                public_ips=None, private_ips=None, driver=driver)

    with pytest.raises(NttCisAPIException):
        driver.ex_power_off(node)


def test_ex_reset(driver):
    node = Node(id='11', name=None, state=None,
                public_ips=None, private_ips=None, driver=driver)
    ret = driver.ex_reset(node)
    assert ret is True


def test_ex_attach_node_to_vlan(driver):
    node = driver.ex_get_node_by_id('e75ead52-692f-4314-8725-c8a4f4d13a87')
    vlan = driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
    ret = driver.ex_attach_node_to_vlan(node, vlan)
    assert ret is True


def test_ex_destroy_nic(driver):
    node = driver.ex_destroy_nic('a202e51b-41c0-4cfc-add0-b1c62fc0ecf6')
    assert node is True


def test_ex_create_network_domain(driver):
    location = driver.ex_get_location_by_id('NA9')
    plan = NetworkDomainServicePlan.ADVANCED
    net = driver.ex_create_network_domain(location=location,
                                          name='test',
                                          description='test',
                                          service_plan=plan)
    assert net.name == 'test'
    assert net.id == 'f14a871f-9a25-470c-aef8-51e13202e1aa'


def test_ex_create_network_domain_NO_DESCRIPTION(driver):
    location = driver.ex_get_location_by_id('NA9')
    plan = NetworkDomainServicePlan.ADVANCED
    net = driver.ex_create_network_domain(location=location,
                                          name='test',
                                          service_plan=plan)
    assert net.name == 'test'
    assert net.id == 'f14a871f-9a25-470c-aef8-51e13202e1aa'


def test_ex_get_network_domain(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    assert net.id == '8cdfd607-f429-4df6-9352-162cfc0891be'
    assert net.description == 'test2'
    assert net.name == 'test'


def test_ex_update_network_domain(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    net.name = 'new name'
    net2 = driver.ex_update_network_domain(net)
    assert net2.name == 'new name'


def test_ex_delete_network_domain(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    result = driver.ex_delete_network_domain(net)
    assert result is True


def test_ex_list_network_domains(driver):
    nets = driver.ex_list_network_domains()
    assert nets[0].name == 'Aurora'
    assert isinstance(nets[0].location, NodeLocation)


def test_ex_list_network_domains_ALLFILTERS(driver):
    NttCisMockHttp.type = 'ALLFILTERS'
    nets = driver.ex_list_network_domains(location='fake_location', name='fake_name',
                                               service_plan='fake_plan', state='fake_state')
    assert nets[0].name == 'Aurora'
    assert isinstance(nets[0].location, NodeLocation)


def test_ex_list_vlans(driver):
    vlans = driver.ex_list_vlans()
    assert vlans[0].name == "Primary"


def test_ex_list_vlans_ALLFILTERS(driver):
    NttCisMockHttp.type = 'ALLFILTERS'
    vlans = driver.ex_list_vlans(location='fake_location', network_domain='fake_network_domain',
                                      name='fake_name', ipv4_address='fake_ipv4', ipv6_address='fake_ipv6', state='fake_state')
    assert vlans[0].name == "Primary"


def test_ex_create_vlan(driver,):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    vlan = driver.ex_create_vlan(network_domain=net,
                                 name='test',
                                 private_ipv4_base_address='10.3.4.0',
                                 private_ipv4_prefix_size='24',
                                 description='test vlan')
    assert vlan.id == '0e56433f-d808-4669-821d-812769517ff8'


def test_ex_create_vlan_NO_DESCRIPTION(driver,):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    vlan = driver.ex_create_vlan(network_domain=net,
                                 name='test',
                                 private_ipv4_base_address='10.3.4.0',
                                 private_ipv4_prefix_size="24")
    assert vlan.id == '0e56433f-d808-4669-821d-812769517ff8'


def test_ex_get_vlan(driver):
    vlan = driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
    assert vlan.id == '0e56433f-d808-4669-821d-812769517ff8'
    assert vlan.description == 'test2'
    assert vlan.status == 'NORMAL'
    assert vlan.name == 'Production VLAN'
    assert vlan.private_ipv4_range_address == '10.0.3.0'
    assert vlan.private_ipv4_range_size == 24
    assert vlan.ipv6_range_size == 64
    assert vlan.ipv6_range_address == '2607:f480:1111:1153:0:0:0:0'
    assert vlan.ipv4_gateway == '10.0.3.1'
    assert vlan.ipv6_gateway == '2607:f480:1111:1153:0:0:0:1'


def test_ex_wait_for_state(driver):
    driver.ex_wait_for_state('NORMAL',
                             driver.ex_get_vlan,
                             vlan_id='0e56433f-d808-4669-821d-812769517ff8',
                             poll_interval=0.1)


def test_ex_wait_for_state_NODE(driver):
    driver.ex_wait_for_state('running',
                             driver.ex_get_node_by_id,
                             id='e75ead52-692f-4314-8725-c8a4f4d13a87',
                             poll_interval=0.1)


def test_ex_wait_for_state_FAIL(driver):
    with pytest.raises(NttCisAPIException) as context:
        driver.ex_wait_for_state('starting',
                                 driver.ex_get_node_by_id,
                                 id='e75ead52-692f-4314-8725-c8a4f4d13a87',
                                 poll_interval=0.1,
                                 timeout=0.1
                                 )
    assert context.value.code == 'running'
    assert 'timed out' in context.value.msg


def test_ex_update_vlan(driver):
    vlan = driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
    vlan.name = 'new name'
    vlan2 = driver.ex_update_vlan(vlan)
    assert vlan2.name == 'new name'


def test_ex_delete_vlan(driver):
    vlan = driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
    result = driver.ex_delete_vlan(vlan)
    assert result is True


def test_ex_expand_vlan(driver):
    vlan = driver.ex_get_vlan('0e56433f-d808-4669-821d-812769517ff8')
    vlan.private_ipv4_range_size = '23'
    vlan = driver.ex_expand_vlan(vlan)
    assert vlan.private_ipv4_range_size == '23'


def test_ex_add_public_ip_block_to_network_domain(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    block = driver.ex_add_public_ip_block_to_network_domain(net)
    assert block.id == '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8'


def test_ex_list_public_ip_blocks(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    blocks = driver.ex_list_public_ip_blocks(net)
    assert blocks[0].base_ip == '168.128.4.18'
    assert blocks[0].size == '2'
    assert blocks[0].id ==  '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8'
    assert blocks[0].location.id == 'NA9'
    assert blocks[0].network_domain.id == net.id


def test_ex_get_public_ip_block(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    block = driver.ex_get_public_ip_block('9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
    assert block.base_ip == '168.128.4.18'
    assert block.size == '2'
    assert block.id == '9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8'
    assert block.location.id ==  'NA9'
    assert block.network_domain.id == net.id


def test_ex_delete_public_ip_block(driver):
    block = driver.ex_get_public_ip_block('9945dc4a-bdce-11e4-8c14-b8ca3a5d9ef8')
    result = driver.ex_delete_public_ip_block(block)
    assert result is True


def test_ex_list_firewall_rules(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    assert rules[0].id == '756cba02-b0bc-48f4-aea5-9445870b6148'
    assert rules[0].network_domain.id == '8cdfd607-f429-4df6-9352-162cfc0891be'
    assert rules[0].name == 'CCDEFAULT.BlockOutboundMailIPv4'
    assert rules[0].action == 'DROP'
    assert rules[0].ip_version, 'IPV4'
    assert rules[0].protocol == 'TCP'
    assert rules[0].source.ip_address == 'ANY'
    assert rules[0].source.any_ip is True
    assert rules[0].destination.any_ip is True


def test_ex_create_firewall_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    rule = driver.ex_create_firewall_rule(net,
                                          rules[0].name,
                                          rules[0].action,
                                          rules[0].ip_version,
                                          rules[0].protocol,
                                          rules[0].source,
                                          rules[0].destination,
                                          'FIRST')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_with_specific_source_ip(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    specific_source_ip_rule = list(filter(lambda x: x.name == 'SpecificSourceIP',
                                          rules))[0]
    rule = driver.ex_create_firewall_rule(net, specific_source_ip_rule.name, specific_source_ip_rule.action,
                                          specific_source_ip_rule.ip_version, specific_source_ip_rule.protocol,
                                          specific_source_ip_rule.source, specific_source_ip_rule.destination,
                                          'FIRST')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_with_source_ip(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    specific_source_ip_rule = \
        list(filter(lambda x: x.name == 'SpecificSourceIP',
                    rules))[0]
    specific_source_ip_rule.source.any_ip = False
    specific_source_ip_rule.source.ip_address = '10.0.0.1'
    specific_source_ip_rule.source.ip_prefix_size = '15'
    rule = driver.ex_create_firewall_rule(net,
                                          specific_source_ip_rule.name,
                                          specific_source_ip_rule.action,
                                          specific_source_ip_rule.ip_version,
                                          specific_source_ip_rule.protocol,
                                          specific_source_ip_rule.source,
                                          specific_source_ip_rule.destination,
                                          'FIRST')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_with_any_ip(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    specific_source_ip_rule = \
        list(filter(lambda x: x.name == 'SpecificSourceIP',
                    rules))[0]
    specific_source_ip_rule.source.any_ip = True
    rule = driver.ex_create_firewall_rule(net,
                                          specific_source_ip_rule.name,
                                          specific_source_ip_rule.action,
                                          specific_source_ip_rule.ip_version,
                                          specific_source_ip_rule.protocol,
                                          specific_source_ip_rule.source,
                                          specific_source_ip_rule.destination,
                                          'FIRST')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_ip_prefix_size(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_list_firewall_rules(net)[0]
    rule.source.address_list_id = None
    rule.source.any_ip = False
    rule.source.ip_address = '10.2.1.1'
    rule.source.ip_prefix_size = '10'
    rule.destination.address_list_id = None
    rule.destination.any_ip = False
    rule.destination.ip_address = '10.0.0.1'
    rule.destination.ip_prefix_size = '20'
    driver.ex_create_firewall_rule(net,
                                   rule.name,
                                   rule.action,
                                   rule.ip_version,
                                   rule.protocol,
                                   rule.source,
                                   rule.destination,
                                   'LAST')


def test_ex_create_firewall_rule_address_list(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_list_firewall_rules(net)[0]
    rule.source.address_list_id = '12345'
    rule.destination.address_list_id = '12345'
    driver.ex_create_firewall_rule(net,
                                   rule.name,
                                   rule.action,
                                   rule.ip_version,
                                   rule.protocol,
                                   rule.source,
                                   rule.destination,
                                   'LAST')


def test_ex_create_firewall_rule_port_list(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_list_firewall_rules(net)[0]
    rule.source.port_list_id = '12345'
    rule.destination.port_list_id = '12345'
    driver.ex_create_firewall_rule(net,
                                   rule.name,
                                   rule.action,
                                   rule.ip_version,
                                   rule.protocol,
                                   rule.source,
                                   rule.destination,
                                   'LAST')


def test_ex_create_firewall_rule_port(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_list_firewall_rules(net)[0]
    rule.source.port_list_id = None
    rule.source.port_begin = '8000'
    rule.source.port_end = '8005'
    rule.destination.port_list_id = None
    rule.destination.port_begin = '7000'
    rule.destination.port_end = '7005'
    driver.ex_create_firewall_rule(net,
                                   rule.name,
                                   rule.action,
                                   rule.ip_version,
                                   rule.protocol,
                                   rule.source,
                                   rule.destination,
                                   'LAST')


def test_ex_create_firewall_rule_ALL_VALUES(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    for rule in rules:
        driver.ex_create_firewall_rule(net,
                                       rule.name,
                                       rule.action,
                                       rule.ip_version,
                                       rule.protocol,
                                       rule.source,
                                       rule.destination,
                                       'LAST')


def test_ex_create_firewall_rule_WITH_POSITION_RULE(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    rule = driver.ex_create_firewall_rule(net,
                                          rules[-2].name,
                                          rules[-2].action,
                                          rules[-2].ip_version,
                                          rules[-2].protocol,
                                          rules[-2].source,
                                          rules[-2].destination,
                                          'BEFORE',
                                          position_relative_to_rule=rules[-1])
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_WITH_POSITION_RULE_STR(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    rule = driver.ex_create_firewall_rule(net,
                                          rules[-2].name,
                                          rules[-2].action,
                                          rules[-2].ip_version,
                                          rules[-2].protocol,
                                          rules[-2].source,
                                          rules[-2].destination,
                                          'BEFORE',
                                          position_relative_to_rule='RULE_WITH_SOURCE_AND_DEST')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_create_firewall_rule_FAIL_POSITION(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    with pytest.raises(ValueError):
        driver.ex_create_firewall_rule(net,
                                       rules[0].name,
                                       rules[0].action,
                                       rules[0].ip_version,
                                       rules[0].protocol,
                                       rules[0].source,
                                       rules[0].destination,
                                       'BEFORE')


def test_ex_create_firewall_rule_FAIL_POSITION_WITH_RULE(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_firewall_rules(net)
    with pytest.raises(ValueError):
        driver.ex_create_firewall_rule(net,
                                       rules[0].name,
                                       rules[0].action,
                                       rules[0].ip_version,
                                       rules[0].protocol,
                                       rules[0].source,
                                       rules[0].destination,
                                       'LAST',
                                       position_relative_to_rule='RULE_WITH_SOURCE_AND_DEST')


def test_ex_get_firewall_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    assert rule.id == 'd0a20f59-77b9-4f28-a63b-e58496b73a6c'


def test_ex_set_firewall_rule_state(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    result = driver.ex_set_firewall_rule_state(rule, False)
    assert result is True


def test_ex_delete_firewall_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    result = driver.ex_delete_firewall_rule(rule)
    assert result is True


def test_ex_edit_firewall_rule(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.source.any_ip = True
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_source_ipaddresslist(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.source.address_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
    rule.source.any_ip = False
    rule.source.ip_address = '10.0.0.1'
    rule.source.ip_prefix_size = 10
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_destination_ipaddresslist(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.destination.address_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
    rule.destination.any_ip = False
    rule.destination.ip_address = '10.0.0.1'
    rule.destination.ip_prefix_size = 10
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_destination_ipaddress(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.source.address_list_id = None
    rule.source.any_ip = False
    rule.source.ip_address = '10.0.0.1'
    rule.source.ip_prefix_size = '10'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_source_ipaddress(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.destination.address_list_id = None
    rule.destination.any_ip = False
    rule.destination.ip_address = '10.0.0.1'
    rule.destination.ip_prefix_size = '10'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_with_relative_rule(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    placement_rule = driver.ex_list_firewall_rules(
        network_domain=net)[-1]
    result = driver.ex_edit_firewall_rule(
        rule=rule, position='BEFORE',
        relative_rule_for_position=placement_rule)
    assert result is True


def test_ex_edit_firewall_rule_with_relative_rule_by_name(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    placement_rule = driver.ex_list_firewall_rules(
        network_domain=net)[-1]
    result = driver.ex_edit_firewall_rule(
        rule=rule, position='BEFORE',
        relative_rule_for_position=placement_rule.name)
    assert result is True


def test_ex_edit_firewall_rule_source_portlist(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.source.port_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_source_port(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.source.port_list_id = None
    rule.source.port_begin = '3'
    rule.source.port_end = '10'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_destination_portlist(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.destination.port_list_id = '802abc9f-45a7-4efb-9d5a-810082368222'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_destination_port(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    rule.destination.port_list_id = None
    rule.destination.port_begin = '3'
    rule.destination.port_end = '10'
    result = driver.ex_edit_firewall_rule(rule=rule, position='LAST')
    assert result is True


def test_ex_edit_firewall_rule_invalid_position_fail(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    with pytest.raises(ValueError):
        driver.ex_edit_firewall_rule(rule=rule, position='BEFORE')


def test_ex_edit_firewall_rule_invalid_position_relative_rule_fail(driver):
    net = driver.ex_get_network_domain(
        '8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_firewall_rule(
        net, 'd0a20f59-77b9-4f28-a63b-e58496b73a6c')
    relative_rule = driver.ex_list_firewall_rules(
        network_domain=net)[-1]
    with pytest.raises(ValueError):
        driver.ex_edit_firewall_rule(rule=rule, position='FIRST',
                                     relative_rule_for_position=relative_rule)


def test_ex_create_nat_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_create_nat_rule(net, '1.2.3.4', '4.3.2.1')
    assert rule.id == 'd31c2db0-be6b-4d50-8744-9a7a534b5fba'


def test_ex_list_nat_rules(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rules = driver.ex_list_nat_rules(net)
    assert rules[0].id == '2187a636-7ebb-49a1-a2ff-5d617f496dce'
    assert rules[0].internal_ip == '10.0.0.15'
    assert rules[0].external_ip == '165.180.12.18'


def test_ex_get_nat_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_nat_rule(net, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
    assert rule.id == '2187a636-7ebb-49a1-a2ff-5d617f496dce'
    assert rule.internal_ip == '10.0.0.16'
    assert rule.external_ip == '165.180.12.19'


def test_ex_delete_nat_rule(driver):
    net = driver.ex_get_network_domain('8cdfd607-f429-4df6-9352-162cfc0891be')
    rule = driver.ex_get_nat_rule(net, '2187a636-7ebb-49a1-a2ff-5d617f496dce')
    result = driver.ex_delete_nat_rule(rule)
    assert result is True


def test_ex_enable_monitoring(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_enable_monitoring(node, "ADVANCED")
    assert result is True


def test_ex_disable_monitoring(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_disable_monitoring(node)
    assert result is True


def test_ex_change_monitoring_plan(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_update_monitoring_plan(node, "ESSENTIALS")
    assert result is True


def test_ex_add_storage_to_node(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_add_storage_to_node(30, node, 'PERFORMANCE')
    assert result is True


def test_ex_remove_storage_from_node(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_remove_storage_from_node(node, 0)
    assert result is True


def test_ex_change_storage_speed(driver):
    result = driver.ex_change_storage_speed("1", 'PERFORMANCE')
    assert result is True


def test_ex_change_storage_size(driver):
    result = driver.ex_change_storage_size("1", 100)
    assert result is True


def test_ex_clone_node_to_image(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_clone_node_to_image(node, 'my image', 'a description')
    assert result is True


def test_ex_edit_metadata(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_edit_metadata(node, 'my new name', 'a description')
    assert result is True


def test_ex_reconfigure_node(driver):
    node = driver.list_nodes()[0]
    result = driver.ex_reconfigure_node(node, 4, 4, 1, 'HIGHPERFORMANCE')
    assert result is True


def test_ex_get_location_by_id(driver):
    location = driver.ex_get_location_by_id('NA9')
    assert location.id == 'NA9'


def test_ex_get_location_by_id_NO_LOCATION(driver):
    location = driver.ex_get_location_by_id(None)
    assert location is None


def test_ex_get_base_image_by_id(driver):
    image_id = driver.list_images()[0].id
    image = driver.ex_get_base_image_by_id(image_id)
    assert image.extra['OS_type'] == 'UNIX'


def test_ex_get_customer_image_by_id(driver):
    image_id = driver.ex_list_customer_images()[1].id
    image = driver.ex_get_customer_image_by_id(image_id)
    assert image.extra['OS_type'] == 'WINDOWS'


def test_ex_get_image_by_id_base_img(driver):
    image_id = driver.list_images()[1].id
    image = driver.ex_get_base_image_by_id(image_id)
    assert image.extra['OS_type'] == 'WINDOWS'


def test_ex_get_image_by_id_customer_img(driver):
    image_id = driver.ex_list_customer_images()[0].id
    image = driver.ex_get_customer_image_by_id(image_id)
    assert image.extra['OS_type'] == 'UNIX'


def test_ex_get_image_by_id_customer_FAIL(driver):
    image_id = 'FAKE_IMAGE_ID'
    with pytest.raises(NttCisAPIException):
        driver.ex_get_base_image_by_id(image_id)


def test_ex_create_anti_affinity_rule(driver):
    node_list = driver.list_nodes()
    success = driver.ex_create_anti_affinity_rule([node_list[0], node_list[1]])
    assert success is True


def test_ex_create_anti_affinity_rule_TUPLE(driver):
    node_list = driver.list_nodes()
    success = driver.ex_create_anti_affinity_rule((node_list[0], node_list[1]))
    assert success is True


def test_ex_create_anti_affinity_rule_TUPLE_STR(driver):
    node_list = driver.list_nodes()
    success = driver.ex_create_anti_affinity_rule((node_list[0].id, node_list[1].id))
    assert success is True


def test_ex_create_anti_affinity_rule_FAIL_STR(driver):
    node_list = 'string'
    with pytest.raises(TypeError):
        driver.ex_create_anti_affinity_rule(node_list)


def test_ex_create_anti_affinity_rule_FAIL_EXISTING(driver):
    node_list = driver.list_nodes()
    NttCisMockHttp.type = 'FAIL_EXISTING'
    with pytest.raises(NttCisAPIException):
        driver.ex_create_anti_affinity_rule((node_list[0], node_list[1]))


def test_ex_delete_anti_affinity_rule(driver):
    net_domain = driver.ex_list_network_domains()[0]
    rule = driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0].id
    success = driver.ex_delete_anti_affinity_rule(rule)
    assert success is True


def test_ex_delete_anti_affinity_rule_STR(driver):
    net_domain = driver.ex_list_network_domains()[0]
    rule = driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0]
    success = driver.ex_delete_anti_affinity_rule(rule.id)
    assert success is True


def test_ex_delete_anti_affinity_rule_FAIL(driver):
    net_domain = driver.ex_list_network_domains()[0]
    rule = driver.ex_list_anti_affinity_rules(network_domain=net_domain)[0]
    NttCisMockHttp.type = 'FAIL'
    with pytest.raises(NttCisAPIException):
        driver.ex_delete_anti_affinity_rule(rule.id)


def test_ex_list_anti_affinity_rules_NETWORK_DOMAIN(driver):
    net_domain = driver.ex_list_network_domains()[0]
    rules = driver.ex_list_anti_affinity_rules(network_domain=net_domain)
    assert isinstance(rules, list)
    assert len(rules) == 2
    assert isinstance(rules[0].id, str)
    assert isinstance(rules[0].node_list, list)


def test_ex_list_anti_affinity_rules_NODE(driver):
    node = driver.list_nodes()[0]
    rules = driver.ex_list_anti_affinity_rules(node=node)
    assert isinstance(rules, list)
    assert len(rules) == 2
    assert isinstance(rules[0].id, str)
    assert isinstance(rules[0].node_list, list)


def test_ex_list_anti_affinity_rules_PAGINATED(driver):
    net_domain = driver.ex_list_network_domains()[0]
    NttCisMockHttp.type = 'PAGINATED'
    rules = driver.ex_list_anti_affinity_rules(network_domain=net_domain)
    assert isinstance(rules, list)
    assert len(rules) == 4
    assert isinstance(rules[0].id, str)
    assert isinstance(rules[0].node_list, list)


def test_ex_list_anti_affinity_rules_ALLFILTERS(driver):
    net_domain = driver.ex_list_network_domains()[0]
    NttCisMockHttp.type = 'ALLFILTERS'
    rules = driver.ex_list_anti_affinity_rules(network_domain=net_domain, filter_id='FAKE_ID', filter_state='FAKE_STATE')
    assert isinstance(rules, list)
    assert len(rules) == 2
    assert isinstance(rules[0].id, str)
    assert isinstance(rules[0].node_list, list)


def test_ex_list_anti_affinity_rules_BAD_ARGS(driver):
    with pytest.raises(ValueError):
        driver.ex_list_anti_affinity_rules(network='fake_network', network_domain='fake_network_domain')


def test_ex_create_tag_key(driver):
    success = driver.ex_create_tag_key('MyTestKey')
    assert success is True


def test_ex_create_tag_key_ALLPARAMS(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'ALLPARAMS'
    success = driver.ex_create_tag_key('MyTestKey', description="Test Key Desc.", value_required=False, display_on_report=False)
    assert success is True


def test_ex_create_tag_key_BADREQUEST(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'BADREQUEST'
    with pytest.raises(NttCisAPIException):
        driver.ex_create_tag_key('MyTestKey')


def test_ex_list_tag_keys(driver):
    tag_keys = driver.ex_list_tag_keys()
    assert isinstance(tag_keys, list)
    assert isinstance(tag_keys[0], NttCisTagKey)
    assert isinstance(tag_keys[0].id, str)


def test_ex_list_tag_keys_ALLFILTERS(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'ALLFILTERS'
    driver.ex_list_tag_keys(id='fake_id', name='fake_name', value_required=False, display_on_report=False)


def test_ex_get_tag_by_id(driver):
    tag = driver.ex_get_tag_key_by_id('d047c609-93d7-4bc5-8fc9-732c85840075')
    assert isinstance(tag, NttCisTagKey)


def test_ex_get_tag_by_id_NOEXIST(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'NOEXIST'
    with pytest.raises(NttCisAPIException):
        driver.ex_get_tag_key_by_id('d047c609-93d7-4bc5-8fc9-732c85840075')


def test_ex_get_tag_by_name(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'SINGLE'
    tag = driver.ex_get_tag_key_by_name('LibcloudTest')
    assert isinstance(tag, NttCisTagKey)


def test_ex_get_tag_by_name_NOEXIST(driver):
    with pytest.raises(ValueError):
        driver.ex_get_tag_key_by_name('LibcloudTest')


def test_ex_modify_tag_key_NAME(driver):
    tag_key = driver.ex_list_tag_keys()[0]
    NttCisMockHttp.type = 'NAME'
    success = driver.ex_modify_tag_key(tag_key, name='NewName')
    assert success is True


def test_ex_modify_tag_key_NOTNAME(driver):
    tag_key = driver.ex_list_tag_keys()[0]
    NttCisMockHttp.type = 'NOTNAME'
    success = driver.ex_modify_tag_key(tag_key, description='NewDesc', value_required=False, display_on_report=True)
    assert success is True


def test_ex_modify_tag_key_NOCHANGE(driver):
    tag_key = driver.ex_list_tag_keys()[0]
    NttCisMockHttp.type = 'NOCHANGE'
    with pytest.raises(NttCisAPIException):
        driver.ex_modify_tag_key(tag_key)


def test_ex_remove_tag_key(driver):
    tag_key = driver.ex_list_tag_keys()[0]
    success = driver.ex_remove_tag_key(tag_key)
    assert success is True


def test_ex_remove_tag_key_NOEXIST(driver):
    tag_key = driver.ex_list_tag_keys()[0]
    NttCisMockHttp.type = 'NOEXIST'
    with pytest.raises(NttCisAPIException):
        driver.ex_remove_tag_key(tag_key)


def test_ex_apply_tag_to_asset(driver):
    node = driver.list_nodes()[0]
    success = driver.ex_apply_tag_to_asset(node, 'TagKeyName', 'FakeValue')
    assert success is True


def test_ex_apply_tag_to_asset_NOVALUE(driver):
    node = driver.list_nodes()[0]
    NttCisMockHttp.type = 'NOVALUE'
    success = driver.ex_apply_tag_to_asset(node, 'TagKeyName')
    assert success is True


def test_ex_apply_tag_to_asset_NOTAGKEY(driver):
    node = driver.list_nodes()[0]
    NttCisMockHttp.type = 'NOTAGKEY'
    with pytest.raises(NttCisAPIException):
        driver.ex_apply_tag_to_asset(node, 'TagKeyNam')


def test_ex_remove_tag_from_asset(driver):
    node = driver.list_nodes()[0]
    success = driver.ex_remove_tag_from_asset(node, 'TagKeyName')
    assert success is True


def test_ex_remove_tag_from_asset_NOTAG(driver):
    node = driver.list_nodes()[0]
    NttCisMockHttp.type = 'NOTAG'
    with pytest.raises(NttCisAPIException):
        driver.ex_remove_tag_from_asset(node, 'TagKeyNam')


def test_ex_list_tags(driver):
    tags = driver.ex_list_tags()
    assert isinstance(tags, list)
    assert isinstance(tags[0], NttCisTag)
    assert len(tags) == 3


def test_ex_list_tags_ALLPARAMS(driver):
    driver.connection._get_orgId()
    NttCisMockHttp.type = 'ALLPARAMS'
    tags = driver.ex_list_tags(asset_id='fake_asset_id', asset_type='fake_asset_type',
                               location='fake_location', tag_key_name='fake_tag_key_name',
                               tag_key_id='fake_tag_key_id', value='fake_value',
                               value_required=False, display_on_report=False)
    assert isinstance(tags, list)
    assert isinstance(tags[0], NttCisTag)
    assert len(tags) == 3


def test_list_consistency_groups(driver):
    cgs = driver.ex_list_consistency_groups()
    assert isinstance(cgs, list)


def test_list_cg_by_src_net_domain(driver):
    nd = "f9d6a249-c922-4fa1-9f0f-de5b452c4026"
    cgs = driver.ex_list_consistency_groups(source_network_domain_id=nd)
    assert cgs[0].name == "sdk_test2_cg"


def test_list_cg_by_name(driver):
    NttCisMockHttp.type = "CG_BY_NAME"
    name = "sdk_test2_cg"
    cg = driver.ex_list_consistency_groups(name=name)
    assert cg[0].id == "195a426b-4559-4c79-849e-f22cdf2bfb6e"


def test_get_consistency_group_by_id(driver):
    NttCisMockHttp.type = None
    cgs = driver.ex_list_consistency_groups()
    cg_id = [i for i in cgs if i.name == "sdk_test2_cg"][0].id
    cg = driver.ex_get_consistency_group(cg_id)
    assert hasattr(cg, 'description')


def test_get_drs_snapshots(driver):
    NttCisMockHttp.type = None
    cgs = driver.ex_list_consistency_groups()
    cg_id = [i for i in cgs if i.name == "sdk_test2_cg"][0].id
    snaps = driver.ex_list_consistency_group_snapshots(cg_id)
    assert hasattr(snaps, 'journalUsageGb')
    assert isinstance(snaps, ClassFactory)


def test_get_drs_snapshots_by_min_max(driver):
    cgs = driver.ex_list_consistency_groups()
    cg_id = [i for i in cgs if i.name == "sdk_test2_cg"][0].id
    snaps = driver.ex_list_consistency_group_snapshots(
        cg_id,
        create_time_min="2018-11-28T00:00:00.000Z",
        create_time_max="2018-11-29T00:00:00.000Z")
    for snap in snaps.snapshot:
        assert "2018-12" not in snap


def test_expand_drs_journal(driver):
    cgs = driver.ex_list_consistency_groups(name="sdk_test2_cg")
    cg_id = cgs[0].id
    expand_by = "100"
    result = driver.ex_expand_journal(cg_id, expand_by)
    assert result is True


def test_start_drs_snapshot_preview(driver):
    cg_id = "195a426b-4559-4c79-849e-f22cdf2bfb6e"
    snapshot_id = "3893"
    result = driver.ex_start_drs_failover_preview(cg_id, snapshot_id)
    assert result is True


def test_stop_drs_snapshot_preivew(driver):
    cg_id = "195a426b-4559-4c79-849e-f22cdf2bfb6e"
    result = driver.ex_stop_drs_failover_preview(cg_id)
    assert result is True


def test_start_drs_failover_invalid_status(driver):
    NttCisMockHttp.type = "INVALID_STATUS"
    cg_id = "195a426b-4559-4c79-849e-f22cdf2bfb6e"
    with pytest.raises(NttCisAPIException) as excinfo:
        result = driver.ex_initiate_drs_failover(cg_id)
    assert "INVALID_STATUS" in excinfo.value.code


def test_initiate_drs_failover(driver):
    cg_id = "195a426b-4559-4c79-849e-f22cdf2bfb6e"
    result = driver.ex_initiate_drs_failover(cg_id)
    assert result is True


def test_create_drs_fail_not_supported(driver):
    NttCisMockHttp.type = "FAIL_NOT_SUPPORTED"
    src_id = "032f3967-00e4-4780-b4ef-8587460f9dd4"
    target_id = "aee58575-38e2-495f-89d3-854e6a886411"
    with pytest.raises(NttCisAPIException) as excinfo:
        result = driver.ex_create_consistency_group(
            "sdk_cg", "100", src_id, target_id, description="A test consistency group")
    exception_msg = excinfo.value.msg
    assert exception_msg == 'DRS is not supported between source Data Center NA9 and target Data Center NA12.'


def test_create_drs_cg_fail_ineligble(driver):
    NttCisMockHttp.type = "FAIL_INELIGIBLE"
    src_id = "032f3967-00e4-4780-b4ef-8587460f9dd4"
    target_id = "aee58575-38e2-495f-89d3-854e6a886411"
    with pytest.raises(NttCisAPIException) as excinfo:
        driver.ex_create_consistency_group(
            "sdk_test2_cg", "100", src_id, target_id, description="A test consistency group")
    exception_msg = excinfo.value.msg
    assert exception_msg == 'The drsEligible flag for target Server aee58575-38e2-495f-89d3-854e6a886411 must be set.'


def test_create_drs_cg(driver):
    src_id = "032f3967-00e4-4780-b4ef-8587460f9dd4"
    target_id = "aee58575-38e2-495f-89d3-854e6a886411"
    result = driver.ex_create_consistency_group(
        "sdk_test2_cg2", "100", src_id, target_id, description="A test consistency group")
    assert result is True


def test_delete_consistency_group(driver):
    cg_id = "fad067be-6ca7-495d-99dc-7921c5f2ca5"
    result = driver.ex_delete_consistency_group(cg_id)
    assert result is True


class InvalidRequestError(Exception):
    def __init__(self, tag):
        super(InvalidRequestError, self).__init__("Invalid Request - %s" % tag)


class NttCisMockHttp(MockHttp):

    fixtures = ComputeFileFixtures('nttcis')

    def _oec_0_9_myaccount_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_PAGINATED(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_ALLFILTERS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_NET_DOMAIN(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_CG_BY_NAME(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_MIN_MAX(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_MIN(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INVALID_STATUS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_FAIL_INELIGIBLE(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_FAIL_NOT_SUPPORTED(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_DYNAMIC(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_networkWithLocation(self, method, url, body, headers):
        body = self.fixtures.load(
            'networkWithLocation.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_deleteServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_deleteServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_rebootServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_rebootServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}rebootServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_rebootServer_RESOURCEBUSY.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server(self, method, url, body, headers):
        if url.endswith('datacenterId=NA3'):
            body = self.fixtures.load(
                'server_server_NA3.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGESIZE50(self, method, url, body, headers):
        if not url.endswith('pageSize=50'):
            raise ValueError("pageSize is not set as expected")
        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_EMPTY(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_paginated_empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGED_THEN_EMPTY(self, method, url, body, headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_server_paginated_empty.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_server_paginated.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGINATED(self, method, url, body, headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_server.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_server_paginated.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_PAGINATEDEMPTY(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_paginated_empty.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_loc'
            elif key == 'networkId':
                assert value == 'fake_network'
            elif key == 'networkDomainId':
                assert value == 'fake_network_domain'
            elif key == 'vlanId':
                assert value == 'fake_vlan'
            elif key == 'ipv6':
                assert value == 'fake_ipv6'
            elif key == 'privateIpv4':
                assert value == 'fake_ipv4'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            elif key == 'started':
                assert value == 'True'
            elif key == 'deployed':
                assert value == 'True'
            elif key == 'sourceImageId':
                assert value == 'fake_image'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_antiAffinityRule_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule_ALLFILTERS(self, method, url, body,
                                                                                          headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'id':
                assert value == 'FAKE_ID'
            elif key == 'state':
                assert value == 'FAKE_STATE'
            elif key == 'pageSize':
                assert value == '250'
            elif key == 'networkDomainId':
                pass
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'server_antiAffinityRule_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_createAntiAffinityRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_createAntiAffinityRule.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_antiAffinityRule_PAGINATED(self, method, url, body,
                                                                                         headers):
        if 'pageNumber=2' in url:
            body = self.fixtures.load(
                'server_antiAffinityRule_list.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            body = self.fixtures.load(
                'server_antiAffinityRule_list_PAGINATED.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_createAntiAffinityRule_FAIL_EXISTING(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_createAntiAffinityRule_FAIL.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteAntiAffinityRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_deleteAntiAffinityRule.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deleteAntiAffinityRule_FAIL(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_createAntiAffinityRule_FAIL.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_snapshotWindow(self, method, url, body, headers):
        body = self.fixtures.load(
            'datacenter_snapshotWindows.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter(self, method, url, body, headers):
        if url.endswith('id=NA9'):
            body = self.fixtures.load(
                'infrastructure_datacenter_NA9.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'infrastructure_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_infrastructure_datacenter_ALLFILTERS(self, method, url, body,
                                                                                            headers):
        if url.endswith('id=NA9'):
            body = self.fixtures.load(
                'infrastructure_datacenter_NA9.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        body = self.fixtures.load(
            'infrastructure_datacenter.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_updateVmwareTools(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}updateVmwareTools":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_updateVmwareTools.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_startServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_startServer_INPROGRESS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}startServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_startServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_shutdownServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_shutdownServer_INPROGRESS(self, method, url, body,
                                                                                        headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}shutdownServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_shutdownServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_resetServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}resetServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_resetServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_powerOffServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_powerOffServer_INPROGRESS(self, method, url, body,
                                                                                        headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}powerOffServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_powerOffServer_INPROGRESS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_11_INPROGRESS(
        self, method, url, body, headers):
        body = self.fixtures.load('server_GetServer.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_networkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_ALLFILTERS(self, method, url, body,
                                                                                        headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'type':
                assert value == 'fake_plan'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'network_networkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_vlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'networkDomainId':
                assert value == 'fake_network_domain'
            elif key == 'ipv6Address':
                assert value == 'fake_ipv6'
            elif key == 'privateIpv4Address':
                assert value == 'fake_ipv4'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'state':
                assert value == 'fake_state'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'network_vlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployServer":
            raise InvalidRequestError(request.tag)

        # Make sure the we either have a network tag with an IP or networkId
        # Or Network info with a primary nic that has privateip or vlanid
        network = request.find(fixxpath('network', TYPES_URN))
        network_info = request.find(fixxpath('networkInfo', TYPES_URN))
        if network is not None:
            if network_info is not None:
                raise InvalidRequestError("Request has both MCP1 and MCP2 values")
            ipv4 = findtext(network, 'privateIpv4', TYPES_URN)
            networkId = findtext(network, 'networkId', TYPES_URN)
            if ipv4 is None and networkId is None:
                raise InvalidRequestError('Invalid request MCP1 requests need privateIpv4 or networkId')
        elif network_info is not None:
            if network is not None:
                raise InvalidRequestError("Request has both MCP1 and MCP2 values")
            primary_nic = network_info.find(fixxpath('primaryNic', TYPES_URN))
            ipv4 = findtext(primary_nic, 'privateIpv4', TYPES_URN)
            vlanId = findtext(primary_nic, 'vlanId', TYPES_URN)
            if ipv4 is None and vlanId is None:
                raise InvalidRequestError('Invalid request MCP2 requests need privateIpv4 or vlanId')
        else:
            raise InvalidRequestError('Invalid request, does not have network or network_info in XML')

        body = self.fixtures.load(
            'server_deployServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87(self, method,
                                                                                                          url, body,
                                                                                                          headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deployNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be(self,
                                                                                                                  method,
                                                                                                                  url,
                                                                                                                  body,
                                                                                                                  headers):
        body = self.fixtures.load(
            'network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be_ALLFILTERS(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'network_networkDomain_8cdfd607_f429_4df6_9352_162cfc0891be.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNetworkDomain(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNetworkDomain":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteNetworkDomain.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deployVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deployVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deployVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_vlan_0e56433f_d808_4669_821d_812769517ff8(self, method,
                                                                                                         url, body,
                                                                                                         headers):
        body = self.fixtures.load(
            'network_vlan_0e56433f_d808_4669_821d_812769517ff8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_expandVlan(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}expandVlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_expandVlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_addPublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addPublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_addPublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba(self,
                                                                                                                  method,
                                                                                                                  url,
                                                                                                                  body,
                                                                                                                  headers):
        body = self.fixtures.load(
            'network_publicIpBlock_4487241a_f0ca_11e3_9315_d4bed9b167ba.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_publicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8(self,
                                                                                                                  method,
                                                                                                                  url,
                                                                                                                  body,
                                                                                                                  headers):
        body = self.fixtures.load(
            'network_publicIpBlock_9945dc4a_bdce_11e4_8c14_b8ca3a5d9ef8.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_removePublicIpBlock(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removePublicIpBlock":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_removePublicIpBlock.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_firewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_createFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c(self,
                                                                                                                 method,
                                                                                                                 url,
                                                                                                                 body,
                                                                                                                 headers):
        body = self.fixtures.load(
            'network_firewallRule_d0a20f59_77b9_4f28_a63b_e58496b73a6c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_editFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteFirewallRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteFirewallRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteFirewallRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_createNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule(self, method, url, body, headers):
        body = self.fixtures.load(
            'network_natRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce(self,
                                                                                                            method, url,
                                                                                                            body,
                                                                                                            headers):
        body = self.fixtures.load(
            'network_natRule_2187a636_7ebb_49a1_a2ff_5d617f496dce.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteNatRule(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteNatRule":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'network_deleteNatRule.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}addNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_addNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeNic(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removeNic":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_removeNic.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_disableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}disableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_disableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_enableServerMonitoring(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}enableServerMonitoring":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_enableServerMonitoring.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeServerMonitoringPlan(self, method, url, body,
                                                                                         headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}changeServerMonitoringPlan":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_changeServerMonitoringPlan.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_c14b1a46_2428_44c1_9c1a_b20e6418d08c(self, method,
                                                                                                          url, body,
                                                                                                          headers):
        body = self.fixtures.load(
            'image_osImage_c14b1a46_2428_44c1_9c1a_b20e6418d08c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_6b4fb0c7_a57b_4f58_b59c_9958f94f971a(self, method,
                                                                                                          url, body,
                                                                                                          headers):
        body = self.fixtures.load(
            'image_osImage_6b4fb0c7_a57b_4f58_b59c_9958f94f971a.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d(self, method,
                                                                                                          url, body,
                                                                                                          headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c(self, method,
                                                                                                          url, body,
                                                                                                          headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_osImage_FAKE_IMAGE_ID(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_osImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage(self, method, url, body, headers):
        body = self.fixtures.load(
            'image_customerImage.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d(self,
                                                                                                                method,
                                                                                                                url,
                                                                                                                body,
                                                                                                                headers):
        body = self.fixtures.load(
            'image_customerImage_5234e5c7_01de_4411_8b6e_baeb8d91cf5d.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c(self,
                                                                                                                method,
                                                                                                                url,
                                                                                                                body,
                                                                                                                headers):
        body = self.fixtures.load(
            'image_customerImage_2ffa36c8_1848_49eb_b4fa_9d908775f68c.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_customerImage_FAKE_IMAGE_ID(self, method, url, body,
                                                                                         headers):
        body = self.fixtures.load(
            'image_customerImage_BAD_REQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_reconfigureServer(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}reconfigureServer":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'server_reconfigureServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_cleanServer(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_cleanServer.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_addDisk(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_addDisk.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeDiskSpeed(self, method, url, body, headers):
        body = self.fixtures.load(
            'change_disk_speed.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_expandDisk(self, method, url, body, headers):
        body = self.fixtures.load(
            'change_disk_size.xml')
        return(httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_removeDisk(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_removeDisk.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_editServerMetadata(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_editServerMetadata.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is not None:
            raise ValueError("Default description for a tag should be blank")
        if value_required is None or value_required != 'true':
            raise ValueError("Default valueRequired should be true")
        if display_on_report is None or display_on_report != 'true':
            raise ValueError("Default displayOnReport should be true")

        body = self.fixtures.load(
            'tag_createTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey_ALLPARAMS(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}createTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is None:
            raise ValueError("Description should have a value")
        if value_required is None or value_required != 'false':
            raise ValueError("valueRequired should be false")
        if display_on_report is None or display_on_report != 'false':
            raise ValueError("displayOnReport should be false")

        body = self.fixtures.load(
            'tag_createTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_createTagKey_BADREQUEST(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_createTagKey_BADREQUEST.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_SINGLE(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tagKey_list_SINGLE.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_ALLFILTERS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'id':
                assert value == 'fake_id'
            elif key == 'name':
                assert value == 'fake_name'
            elif key == 'valueRequired':
                assert value == 'false'
            elif key == 'displayOnReport':
                assert value == 'false'
            elif key == 'pageSize':
                assert value == '250'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'tag_tagKey_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_d047c609_93d7_4bc5_8fc9_732c85840075(self, method,
                                                                                                       url, body,
                                                                                                       headers):
        body = self.fixtures.load(
            'tag_tagKey_5ab77f5f_5aa9_426f_8459_4eab34e03d54.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tagKey_d047c609_93d7_4bc5_8fc9_732c85840075_NOEXIST(self,
                                                                                                               method,
                                                                                                               url,
                                                                                                               body,
                                                                                                               headers):
        body = self.fixtures.load(
            'tag_tagKey_5ab77f5f_5aa9_426f_8459_4eab34e03d54_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NAME(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is None:
            raise ValueError("Name must have a value in the request")
        if description is not None:
            raise ValueError("Description should be empty")
        if value_required is not None:
            raise ValueError("valueRequired should be empty")
        if display_on_report is not None:
            raise ValueError("displayOnReport should be empty")
        body = self.fixtures.load(
            'tag_editTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NOTNAME(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}editTagKey":
            raise InvalidRequestError(request.tag)
        name = findtext(request, 'name', TYPES_URN)
        description = findtext(request, 'description', TYPES_URN)
        value_required = findtext(request, 'valueRequired', TYPES_URN)
        display_on_report = findtext(request, 'displayOnReport', TYPES_URN)
        if name is not None:
            raise ValueError("Name should be empty")
        if description is None:
            raise ValueError("Description should not be empty")
        if value_required is None:
            raise ValueError("valueRequired should not be empty")
        if display_on_report is None:
            raise ValueError("displayOnReport should not be empty")
        body = self.fixtures.load(
            'tag_editTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_editTagKey_NOCHANGE(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_editTagKey_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_deleteTagKey(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}deleteTagKey":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'tag_deleteTagKey.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_deleteTagKey_NOEXIST(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_deleteTagKey_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}applyTags":
            raise InvalidRequestError(request.tag)
        asset_type = findtext(request, 'assetType', TYPES_URN)
        asset_id = findtext(request, 'assetId', TYPES_URN)
        tag = request.find(fixxpath('tag', TYPES_URN))
        tag_key_name = findtext(tag, 'tagKeyName', TYPES_URN)
        value = findtext(tag, 'value', TYPES_URN)
        if asset_type is None:
            raise ValueError("assetType should not be empty")
        if asset_id is None:
            raise ValueError("assetId should not be empty")
        if tag_key_name is None:
            raise ValueError("tagKeyName should not be empty")
        if value is None:
            raise ValueError("value should not be empty")

        body = self.fixtures.load(
            'tag_applyTags.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags_NOVALUE(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}applyTags":
            raise InvalidRequestError(request.tag)
        asset_type = findtext(request, 'assetType', TYPES_URN)
        asset_id = findtext(request, 'assetId', TYPES_URN)
        tag = request.find(fixxpath('tag', TYPES_URN))
        tag_key_name = findtext(tag, 'tagKeyName', TYPES_URN)
        value = findtext(tag, 'value', TYPES_URN)
        if asset_type is None:
            raise ValueError("assetType should not be empty")
        if asset_id is None:
            raise ValueError("assetId should not be empty")
        if tag_key_name is None:
            raise ValueError("tagKeyName should not be empty")
        if value is not None:
            raise ValueError("value should be empty")

        body = self.fixtures.load(
            'tag_applyTags.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_applyTags_NOTAGKEY(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_applyTags_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_removeTags(self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}removeTags":
            raise InvalidRequestError(request.tag)
        body = self.fixtures.load(
            'tag_removeTag.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_removeTags_NOTAG(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_removeTag_BADREQUEST.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tag(self, method, url, body, headers):
        body = self.fixtures.load(
            'tag_tag_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_tag_tag_ALLPARAMS(self, method, url, body, headers):
        (_, params) = url.split('?')
        parameters = params.split('&')
        for parameter in parameters:
            (key, value) = parameter.split('=')
            if key == 'assetId':
                assert value == 'fake_asset_id'
            elif key == 'assetType':
                assert value == 'fake_asset_type'
            elif key == 'valueRequired':
                assert value == 'false'
            elif key == 'displayOnReport':
                assert value == 'false'
            elif key == 'pageSize':
                assert value == '250'
            elif key == 'datacenterId':
                assert value == 'fake_location'
            elif key == 'value':
                assert value == 'fake_value'
            elif key == 'tagKeyName':
                assert value == 'fake_tag_key_name'
            elif key == 'tagKeyId':
                assert value == 'fake_tag_key_id'
            else:
                raise ValueError("Could not find in url parameters {0}:{1}".format(key, value))
        body = self.fixtures.load(
            'tag_tag_list.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_ipAddressList(
        self, method, url, body, headers):
        body = self.fixtures.load('ip_address_lists.xml')
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_ipAddressList_FILTERBYNAME(
        self, method, url, body, headers):
        body = self.fixtures.load('ip_address_lists_FILTERBYNAME.xml')
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createIpAddressList(
        self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "createIpAddressList":
            raise InvalidRequestError(request.tag)

        net_domain = findtext(request, 'networkDomainId', TYPES_URN)
        if net_domain is None:
            raise ValueError("Network Domain should not be empty")

        name = findtext(request, 'name', TYPES_URN)
        if name is None:
            raise ValueError("Name should not be empty")

        ip_version = findtext(request, 'ipVersion', TYPES_URN)
        if ip_version is None:
            raise ValueError("IP Version should not be empty")

        ip_address_col_required = findall(request, 'ipAddress', TYPES_URN)
        child_ip_address_required = findall(request, 'childIpAddressListId',
                                            TYPES_URN)

        if 0 == len(ip_address_col_required) and \
            0 == len(child_ip_address_required):
            raise ValueError("At least one ipAddress element or "
                             "one childIpAddressListId element must be "
                             "provided.")

        if ip_address_col_required[0].get('begin') is None:
            raise ValueError("IP Address should not be empty")

        body = self.fixtures.load(
            'ip_address_list_create.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editIpAddressList(
        self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "editIpAddressList":
            raise InvalidRequestError(request.tag)

        ip_address_list = request.get('id')
        if ip_address_list is None:
            raise ValueError("IpAddressList ID should not be empty")

        name = findtext(request, 'name', TYPES_URN)
        if name is not None:
            raise ValueError("Name should not exists in request")

        ip_version = findtext(request, 'ipVersion', TYPES_URN)
        if ip_version is not None:
            raise ValueError("IP Version should not exists in request")

        ip_address_col_required = findall(request, 'ipAddress', TYPES_URN)
        child_ip_address_required = findall(request, 'childIpAddressListId',
                                            TYPES_URN)

        if 0 == len(ip_address_col_required) and \
            0 == len(child_ip_address_required):
            raise ValueError("At least one ipAddress element or "
                             "one childIpAddressListId element must be "
                             "provided.")

        if ip_address_col_required[0].get('begin') is None:
            raise ValueError("IP Address should not be empty")

        body = self.fixtures.load(
            'ip_address_list_edit.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deleteIpAddressList(
        self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "deleteIpAddressList":
            raise InvalidRequestError(request.tag)

        ip_address_list = request.get('id')
        if ip_address_list is None:
            raise ValueError("IpAddressList ID should not be empty")

        body = self.fixtures.load(
            'ip_address_list_delete.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_portList(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'port_list_lists.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_portList_c8c92ea3_2da8_4d51_8153_f39bec794d69(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'port_list_get.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_createPortList(
        self, method, url, body, headers):

        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "createPortList":
            raise InvalidRequestError(request.tag)

        net_domain = findtext(request, 'networkDomainId', TYPES_URN)
        if net_domain is None:
            raise ValueError("Network Domain should not be empty")

        ports_required = findall(request, 'port', TYPES_URN)
        child_port_list_required = findall(request, 'childPortListId',
                                           TYPES_URN)

        if 0 == len(ports_required) and \
            0 == len(child_port_list_required):
            raise ValueError("At least one port element or one "
                             "childPortListId element must be provided")

        if ports_required[0].get('begin') is None:
            raise ValueError("PORT begin value should not be empty")

        body = self.fixtures.load(
            'port_list_create.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_editPortList(
        self, method, url, body, headers):

        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "editPortList":
            raise InvalidRequestError(request.tag)

        ports_required = findall(request, 'port', TYPES_URN)
        child_port_list_required = findall(request, 'childPortListId',
                                           TYPES_URN)

        if 0 == len(ports_required) and \
            0 == len(child_port_list_required):
            raise ValueError("At least one port element or one "
                             "childPortListId element must be provided")

        if ports_required[0].get('begin') is None:
            raise ValueError("PORT begin value should not be empty")

        body = self.fixtures.load(
            'port_list_edit.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_network_deletePortList(
        self, method, url, body, headers):
        request = ET.fromstring(body)
        if request.tag != "{urn:didata.com:api:cloud:types}" \
                          "deletePortList":
            raise InvalidRequestError(request.tag)

        port_list = request.get('id')
        if port_list is None:
            raise ValueError("Port List ID should not be empty")

        body = self.fixtures.load(
            'ip_address_list_delete.xml'
        )

        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_cloneServer(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'server_clone_response.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_image_importImage(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'import_image_response.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_exchangeNicVlans(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'exchange_nic_vlans_response.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_changeNetworkAdapter(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'change_nic_networkadapter_response.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_deployUncustomizedServer(
        self, method, url, body, headers):
        body = self.fixtures.load(
            'deploy_customised_server.xml'
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_snapshot_snapshot(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "list_server_snapshots.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_snapshot_enableSnapshotService(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "enable_snapshot_service.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_snapshot_initiateManualSnapshot(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "initiate_manual_snapshot.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e1eb7d71_93c9_4b9c_807c_e05932dc8143(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "manual_snapshot_server.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_snapshot_createSnapshotPreviewServer(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "create_preview_server.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_snapshot_disableSnapshotService(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "disable_server_snapshot_service.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "list_consistency_groups.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup_NET_DOMAIN(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "cg_by_src_network_domain.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup_CG_BY_NAME(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "get_cg_by_name_or_id.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup_195a426b_4559_4c79_849e_f22cdf2bfb6e(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "get_cg_by_name_or_id.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_snapshot(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "list_drs_snapshots.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_snapshot_MIN_MAX(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_snap_shots_by_min_max_time.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_snapshot_MIN(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_snap_shots_by_min.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_expandJournal(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_expand_journal.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_startPreviewSnapshot(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_start_failover_preview.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_stopPreviewSnapshot(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_stop_failover_preview.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_initiateFailover_INVALID_STATUS(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_invalid_status.xml"
        )
        return httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_initiateFailover(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_initiate_failover.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_createConsistencyGroup_FAIL_INELIGIBLE(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_fail_create_cg_ineligible.xml"
        )
        return httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_createConsistencyGroup_FAIL_NOT_SUPPORTED(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_fail_create_cg_not_supported.xml"
        )
        return httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_createConsistencyGroup(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_create_cg.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_deleteConsistencyGroup(
        self, method, url, body, headers):
        body = self.fixtures.load(
            "drs_delete_consistency_group.xml"
        )
        return httplib.OK, body, {}, httplib.responses[httplib.OK]


if __name__ == '__main__':
    sys.exit(unittest.main())
