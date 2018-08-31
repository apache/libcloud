import pytest
import libcloud
from libcloud import loadbalancer
from libcloud.common.nttcis import NttCisAPIException, NttCisVlan
from tests.lib_create_test import test_deploy_vlan


def test_disable_node_snapshot(compute_driver):
    node = '040fefdb-78be-4b17-8ef9-86820bad67d9'
    assert compute_driver.ex_disable_snapshots(node) is True


def test_list_windows(compute_driver):
    loc = 'EU6'
    service_plan = 'ADVANCED'
    windows = compute_driver.list_snapshot_windows(loc, service_plan)
    for window in windows:
       print(window)
       assert 'day_of_week' in window


def test_enable_snapshot(compute_driver):
    """
    This will enable a snapshot window and create an initial
    snapshot when it has done so. A node object and a window id are required
    :param compute_driver: The driver object for compute nodes.
    :return: True or False
    :rtype: ``bool``
    """
    window_id = 'ea646520-4272-11e8-838c-180373fb68df'
    node = '040fefdb-78be-4b17-8ef9-86820bad67d9'
    result = compute_driver.ex_enable_snapshots(node, window_id)
    assert result is True


def test_initiate_manual_snapshot_warn(compute_driver):
    with pytest.raises(RuntimeError, match=r'Found more than one server Id .*'):
        compute_driver.ex_initiate_manual_snapshot('sdk_server_1', 'dc637783-2bb2-4b92-838a-99a899b5e29b')


def test_initiate_manual_snapshot(compute_driver):
    compute_driver.ex_initiate_manual_snapshot('sdk_server_1', 'dc637783-2bb2-4b92-838a-99a899b5e29b')


def test_shutdown_server_1(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9 ')
    result = compute_driver.ex_shutdown_graceful(node)
    assert result is True


def test_start_server_1(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9 ')
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_shutdown_server_2(compute_driver):
    nodes = compute_driver.list_nodes(ex_name='sdk_server_1')
    for node in nodes:
        result = compute_driver.ex_shutdown_graceful(node)
        assert result is True


def test_start_server_2(compute_driver):
    nodes = compute_driver.list_nodes(ex_name='sdk_server_1')
    for node in nodes:
        result = compute_driver.ex_start_node(node)
        assert result is True


def test_edit_metadata(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9 ')
    description = 'SDK  Test server'
    name = 'sdk_server_1'
    result = compute_driver.ex_edit_metadata(node, name=name, description=description)
    assert result is True


def test_edit_metadata_fails(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9 ')
    description = 'Test server'
    ip_address = 'EU6 Ubuntu'
    with pytest.raises(TypeError):
        result = compute_driver.ex_edit_metadata(node, ip_address=ip_address, description=description)


def test_reconfigure_node(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9')
    cpu_performance = 'HIGHPERFORMANCE'
    result = compute_driver.ex_reconfigure_node(node, cpu_performance=cpu_performance)
    assert result is True


def test_add_disk_by_node(compute_driver):
    """
    Speeds can be specified based on DataCenter
    :param compute_driver: libcloud.DriverType.COMPUTE.NTTCIS
    :return: NA
    """
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_add_storage_to_node(20, node)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 180, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_add_disk_by_controller_id(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_add_storage_to_node(20, controller_id=node.extra['scsi_controller'][0].id)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 180, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_changing_diskspeed(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    disk_id = 'f8a01c24-4768-46be-af75-9fe877f8c588'
    result = compute_driver.ex_change_storage_speed(disk_id, 'HIGHPERFORMANCE')
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_changing_diskspeed_iops(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    disk_id = 'f8a01c24-4768-46be-af75-9fe877f8c588'
    result = compute_driver.ex_change_storage_speed(disk_id, 'PROVISIONEDIOPS', iops=60)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_add_scsi_controller(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    adapter_type = 'VMWARE_PARAVIRTUAL'
    result = compute_driver.ex_add_scsi_controller_to_node(node.id, adapter_type)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_remove_scsi_controller(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_remove_scsi_controller('f1126751-c6d5-4d64-893c-8902b8481f90')
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_update_vmware_tools(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    result = compute_driver.ex_update_vm_tools(node)
    assert result is True
    compute_driver.ex_wait_for_state('running', compute_driver.ex_get_node_by_id, 2, 240, node.id)


def test_add_node_to_vlan(compute_driver):
    vlan = test_deploy_vlan(compute_driver, "test_vlan_create", "6aafcf08-cb0b-432c-9c64-7371265db086", "10.0.2.0")
    assert isinstance(vlan, NttCisVlan)
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_attach_node_to_vlan(node, vlan=vlan)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_remove_nic(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_disable_snapshots(node.id)
    assert result is True
    result = compute_driver.ex_destroy_nic("e9cdea1b-c4f2-4769-93a8-57e24248abdd")
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True

""""
No wayt to get nic id's via libcloud
def test_exchange_nic_vlans(compute_driver):
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    print(node.extra)
"""


def test_change_nic_type(compute_driver):
    nic_id = "7a27b2b1-7b20-404f-be53-4695023c2734"
    nic_type = 'VMXNET3'
    node = compute_driver.ex_get_node_by_id('803e5e00-b22a-450a-8827-066ff15ec977')
    shut_result = compute_driver.ex_shutdown_graceful(node)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, node.id)
    result = compute_driver.ex_change_nic_network_adapter(nic_id, nic_type)
    assert result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 240, node.id)
    result = compute_driver.ex_start_node(node)
    assert result is True


def test_create_anti_affinity_rule(compute_driver):
    server1 = compute_driver.ex_get_node_by_id("d0425097-202f-4bba-b268-c7a73b8da129")
    server2 = compute_driver.ex_get_node_by_id("803e5e00-b22a-450a-8827-066ff15ec977")
    servers = [server1, server2]
    result = compute_driver.ex_create_anti_affinity_rule(servers)
    assert isinstance(result, )


def test_delete_anti_affinity_rule(compute_driver):
    anti_affinity_rule = "40d83160-0fa2-418d-a73e-5f15fe1354fc"
    result = compute_driver.ex_delete_anti_affinity_rule(anti_affinity_rule)
    assert result is True





def test_list_locations(compute_driver):
    locations = compute_driver.list_locations()
    for location in locations:
        print(location)

