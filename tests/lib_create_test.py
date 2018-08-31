import pytest
import libcloud
from libcloud import loadbalancer
from libcloud.common.nttcis import NttCisAPIException, NttCisVlan


def test_deploy_vlan(compute_driver, vlan_name, network_domain_id, base_ipv4_addr):
    network_domain = compute_driver.ex_get_network_domain(network_domain_id)
    result = compute_driver.ex_create_vlan(network_domain, vlan_name, base_ipv4_addr)
    assert isinstance(result, NttCisVlan)
    compute_driver.ex_wait_for_state('normal', compute_driver.ex_get_vlan, 2, 60, result.id)
    return result


def test_deploy_server(compute_driver):
    image_id = "81a36aa0-555c-4735-b965-4b64fcf0ac8f"
    images = compute_driver.list_images(location='EU6')
    image = [i for i in images if i.id == image_id]
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    psswd = 'Snmpv2c!'
    vlan_name = "sdk_vlan1"
    vlans = compute_driver.ex_list_vlans()
    vlan = [v for v in vlans if v.name == vlan_name]
    new_node = compute_driver.create_node("ubuntu", image[0], psswd, ex_description="auto_created_server",
                                         ex_network_domain=net_domain[0], ex_primary_nic_vlan=vlan[0])
    compute_driver.ex_wait_for_state('running', compute_driver.ex_get_node_by_id, 2, 300, new_node.id)
    assert new_node.state == 'running'


def test_delete_server(compute_driver):
    server = compute_driver.list_nodes(ex_name="ubuntu")[0]
    shut_result = compute_driver.ex_shutdown_graceful(server)
    assert shut_result is True
    compute_driver.ex_wait_for_state('stopped', compute_driver.ex_get_node_by_id, 2, 45, server.id)
    result = compute_driver.destroy_node(server)
    assert result is True
    compute_driver.ex_wait_for_state('terminated', compute_driver.ex_get_node_by_id, 2, 240, server.id)


def test_deploy_firewall_rule