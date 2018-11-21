import pytest
import libcloud
from libcloud import loadbalancer
from libcloud.compute.drivers.nttcis import NttCisPort
from libcloud.common.nttcis import NttCisIpAddress, NttCisVlan, NttCisVIPNode
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


def test_edit_vlan(compute_driver):
    vlan = compute_driver.ex_list_vlans(name='sdk_test2')[0]
    vlan.name = 'sdk_test_2'
    vlan.description = "Second test Vlan"
    result = compute_driver.ex_update_vlan(vlan)
    assert isinstance(result, NttCisVlan)


def test_expand_vlan(compute_driver):
    vlan = compute_driver.ex_list_vlans(name='sdk_test_3')[0]
    vlan.private_ipv4_range_size = '23'
    result = compute_driver.ex_expand_vlan(vlan)
    assert isinstance(result, NttCisVlan)


def test_delete_vlan(compute_driver):
    vlan = compute_driver.ex_list_vlans(name='sdk_test_3')[0]
    result = compute_driver.ex_delete_vlan(vlan)
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


def test_edit_firewall_rule(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    rule_name = 'sdk_test_firewall_rule_2'
    rules = compute_driver.ex_list_firewall_rules(net_domain[0])
    rule = [rule for rule in rules if rule.name == rule_name]
    rule[0].destination.port_end = None
    result = compute_driver.ex_edit_firewall_rule(rule[0])
    print(compute_driver.ex_get_firewall_rule(net_domain[0].id, rule[0].id))
    assert result is True


def test_delete_firewall_rule(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    rule_name = 'sdk_test_firewall_rule_2'
    rules = compute_driver.ex_list_firewall_rules(net_domain[0])
    rule = [rule for rule in rules if rule.name == rule_name]
    result = compute_driver.ex_delete_firewall_rule(rule[0])
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


def test_delete_port_list(compute_driver):
    portlists = compute_driver.ex_list_portlist('6aafcf08-cb0b-432c-9c64-7371265db086')
    port_list_to_delete = [plist for plist in portlists if plist.name == 'sdk_test_port_list']
    result = compute_driver.ex_delete_portlist(port_list_to_delete[0])
    assert result is True


def test_edit_address_list(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name][0]
    addr_list = compute_driver.ex_get_ip_address_list(net_domain, 'sdk_test_address_list')
    assert addr_list[0].ip_version == 'IPV4'
    ip_address_1 = NttCisIpAddress(begin='190.2.2.100')
    ip_address_2 = NttCisIpAddress(begin='190.2.2.106', end='190.2.2.108')
    ip_address_3 = NttCisIpAddress(begin='190.2.2.0', prefix_size='24')
    ip_address_4 = NttCisIpAddress(begin='10.2.0.0', prefix_size='24')
    ip_address_collection = [ip_address_1, ip_address_2, ip_address_3, ip_address_4]

    result = compute_driver.ex_edit_ip_address_list("d32aa8d4-831b-4fd6-95da-c639768834f0",
                                                    ip_address_collection=ip_address_collection)
    assert result is True


def test_delete_public_ip_block(compute_driver):
    block = compute_driver.ex_get_public_ip_block("813b87a8-18e1-11e5-8d4f-180373fb68df")
    result = compute_driver.ex_delete_public_ip_block(block)
    assert result is True


def test_edit_address_list_2(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name][0]
    # An ip address list object can be used as an argument or the id of the address list
    addr_list = compute_driver.ex_get_ip_address_list(net_domain, 'sdk_test_address_list')

    result = compute_driver.ex_edit_ip_address_list("d32aa8d4-831b-4fd6-95da-c639768834f0",
                                                    description='nil')
    assert result is True


def test_delete_address_list(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name][0]
    addresslist_to_delete = compute_driver.ex_get_ip_address_list(net_domain, 'sdk_test_address_list')
    print(addresslist_to_delete)


def test_edit_port_list_1(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    port_list_name = 'sdk_test_port_list'
    port_lists = compute_driver.ex_list_portlist(net_domain[0])
    port_list = [port for port in port_lists if port.name == port_list_name][0]
    port_collection = [NttCisPort(begin='8000', end='8080'), NttCisPort(begin='9000')]
    result = compute_driver.ex_edit_portlist(port_list.id, port_collection=port_collection)
    assert result is True


def test_unreserve_ip_address(compute_driver):
    vlan_name = 'sdk_vlan1'
    vlan = compute_driver.ex_list_vlans(name=vlan_name)[0]
    ip = '2a00:47c0:111:1331:7df0:9beb:43c9:5c'
    result = compute_driver.ex_unreserve_ip_addresses(vlan, ip)
    assert result is True


def test_list_locations(compute_driver):
    locations = compute_driver.list_locations()
    for location in locations:
        print(location)


def test_delete_nat_rule(compute_driver):
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    rule = compute_driver.ex_get_nat_rule(network_domain, '74f0897f-5536-4c17-84b0-d52b1fb3aea6')
    result = compute_driver.ex_delete_nat_rule(rule)
    assert result is True


def test_update_health_monitor(compute_driver, lbdriver):
    pool_name = 'sdk_test_balancer'
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    pools = lbdriver.ex_get_pools(ex_network_domain_id=network_domain.id)
    pool = [p for p in pools if p.name == pool_name][0]
    pool.health_monitor_id = '9f79487a-1b6d-11e5-8d4f-180373fb68df'
    result = lbdriver.ex_update_pool(pool)
    assert result is True


def test_update_node_monitor(compute_driver, lbdriver):
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    nodes = lbdriver.ex_get_nodes(ex_network_domain_id=network_domain.id)
    #pool = [p for p in pools if p.name == pool_name][0]
    health_monitor_id = '9f79a126-1b6d-11e5-8d4f-180373fb68df'
    for node in nodes:
        node.health_monitor_id = health_monitor_id
        result = lbdriver.ex_update_node(node)
        assert isinstance(result, NttCisVIPNode)


def test_remove_node(compute_driver, lbdriver):
    node_name = 'web1'
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    nodes = lbdriver.ex_get_nodes(ex_network_domain_id=network_domain.id)
    node = [n for n in nodes if n.name == node_name][0]
    pool_name = "sdk_test_balancer"
    pools = lbdriver.ex_get_pools(ex_network_domain_id=network_domain.id)
    pool = [p for p in pools if p.name == pool_name][0]
    pool_members = lbdriver.ex_get_pool_members(pool.id)
    pool_member = [pm for pm in pool_members if pm.node_id == node.id][0]
    result = lbdriver.ex_destroy_pool_member(pool_member)
    assert result is True


def test_delete_node(compute_driver, lbdriver):
    node_name = 'web1'
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    nodes = lbdriver.ex_get_nodes(ex_network_domain_id=network_domain.id)
    node = [n for n in nodes if n.name == node_name][0]
    result = lbdriver.ex_destroy_node(node.id)
    assert result is True


def test_remove_pool(compute_driver, lbdriver):
    listener_name = "sdk_test_balancer"
    listeners = lbdriver.list_balancers(ex_network_domain_id=lbdriver.network_domain_id)
    listener = [l for l in listeners if l.name == listener_name][0]
    pool_id = None
    result = lbdriver.ex_update_listener(listener, poolId=pool_id)
    assert result is True


def test_delete_pool(compute_driver, lbdriver):
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    pool_name = "sdk_test_balancer"
    pools = lbdriver.ex_get_pools(ex_network_domain_id=network_domain.id)
    pool = [p for p in pools if p.name == pool_name][0]
    result = lbdriver.ex_destroy_pool(pool)
    assert result is True


def test_delete_listener(compute_driver, lbdriver):
    listener_name = "sdk_test_balancer"
    listeners = lbdriver.list_balancers(ex_network_domain_id=lbdriver.network_domain_id)
    listener = [l for l in listeners if l.name == listener_name][0]
    result = lbdriver.destroy_balancer(listener)
    assert result is True


def test_expand_journal(drsdriver):
    cgs = drsdriver.list_consistency_groups(name="sdk_test2_cg")
    cg_id = cgs[0].id
    expand_by = "100"
    result = drsdriver.expand_journal(cg_id, expand_by)
    assert result is True


def test_delete_consistency_group(drsdriver):
    cg_name = "sdk_test2_cg"
    cg = drsdriver.list_consistency_groups(name=cg_name)
    cg_id = cg[0].id
    result = drsdriver.delete_consistency_group(cg_id)
    assert result is True


def test_edit_ssl_offload_profile(lbdriver):
    profile_name = "ssl_offload"
    datacenter_id = "EU6"
    profile = lbdriver.ex_list_ssl_offload_profiles(name=profile_name, datacenter_id=datacenter_id)[0]
    result = lbdriver.ex_edit_ssl_offload_profile(profile.id, profile.name,
                                                  profile.sslDomainCertificate.id,
                                                  ciphers=profile.ciphers,
                                                  description="A test edit of an offload profile")
    assert result is True