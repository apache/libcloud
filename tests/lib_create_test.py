from pprint import pprint
import pytest
import libcloud

from libcloud.compute.drivers.nttcis import NttCisPort, NttCisIpAddress, NttCisPublicIpBlock, NttCisNatRule
from libcloud.common.nttcis import NttCisFirewallRule, NttCisVlan, NttCisFirewallAddress


def test_deploy_vlan(compute_driver, vlan_name='sdk_test2', network_domain_name='sdk_test_1', base_ipv4_addr='10.1.2.0'):
    # Default network size is 24 bits. Interval and polling times default to 2 and 60.
    interval = 3
    timeout = 60
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    result = compute_driver.ex_create_vlan(network_domain, vlan_name, base_ipv4_addr)
    assert isinstance(result, NttCisVlan)
    compute_driver.ex_wait_for_state('normal', compute_driver.ex_get_vlan, interval, timeout, result.id)
    return result


def test_deploy_vlan_2(compute_driver, vlan_name='sdk_test_3', network_domain_name='sdk_test_1',
                     base_ipv4_addr='10.2.0.0', private_ipv4_prefix_size=24):
    # Default network size is 24 bits. Interval and polling times default to 2 and 60.
    interval = 3
    timeout = 60
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    result = compute_driver.ex_create_vlan(network_domain, vlan_name, base_ipv4_addr,
                                           private_ipv4_prefix_size=private_ipv4_prefix_size)
    assert isinstance(result, NttCisVlan)
    compute_driver.ex_wait_for_state('normal', compute_driver.ex_get_vlan, interval, timeout, result.id)
    return result


def test_create_nat_rule(compute_driver):
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    result = compute_driver.ex_create_nat_rule(network_domain, '10.1.1.7', '168.128.13.126')
    assert isinstance(result, NttCisNatRule)


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


def test_deploy_firewall_rule_1(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    address_list_name = 'sdk_test_address_list'
    address_lists = compute_driver.ex_list_ip_address_list('6aafcf08-cb0b-432c-9c64-7371265db086')
    # using lambda with filter

    # address_list = list(filter(lambda x: address_list_name, address_lists))
    # address_list_id = address_list[0].id

    # using list comprehension to filter

    address_list = [a for a in address_lists if a.name == address_list_name]
    address_list_id = address_list[0].id

    port_list_name = 'sdk_test_port_list'
    port_lists = compute_driver.ex_list_portlist('6aafcf08-cb0b-432c-9c64-7371265db086')
    port_list = [p for p in port_lists if p.name == port_list_name]
    port_list_id = port_list[0].id
    dest_firewall_address = NttCisFirewallAddress(address_list_id=address_list_id, port_list_id=port_list_id)
    source_firewall_address = NttCisFirewallAddress(any_ip='ANY')
    rule = compute_driver.ex_create_firewall_rule(net_domain[0], 'sdk_test_firewall_rule_1', 'ACCEPT_DECISIVELY',
                                                  'IPV4', 'TCP', source_firewall_address, dest_firewall_address, 'LAST')
    print(rule)
    assert isinstance(rule, NttCisFirewallRule)


def test_deploy_firewall_rule_2(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    source_firewall_address = NttCisFirewallAddress(any_ip='ANY')
    dest_firewall_address = NttCisFirewallAddress(ip_address='10.2.0.0', ip_prefix_size='16',
                                                  port_begin='8000', port_end='8080')

    rule = compute_driver.ex_create_firewall_rule(net_domain[0], 'sdk_test_firewall_rule_2', 'ACCEPT_DECISIVELY',
                                                  'IPV4', 'TCP', source_firewall_address, dest_firewall_address, 'LAST')
    print(rule)
    assert isinstance(rule, NttCisFirewallRule)


def test_deploy_firewall_rule_3(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    source_firewall_address = NttCisFirewallAddress(any_ip='ANY')
    dest_firewall_address = NttCisFirewallAddress(ip_address='10.2.0.0', ip_prefix_size='16',
                                                  port_begin='25')
    rule_name = 'sdk_test_firewall_rule_2'
    rules = compute_driver.ex_list_firewall_rules(net_domain[0])
    rule = [rule for rule in rules if rule.name == rule_name]
    relative_to = compute_driver.ex_get_firewall_rule(net_domain[0], rule[0].id)
    rule = compute_driver.ex_create_firewall_rule(net_domain[0], 'sdk_test_firewall_rule_3', 'ACCEPT_DECISIVELY',
                                                  'IPV4', 'TCP', source_firewall_address, dest_firewall_address,
                                                  'BEFORE', position_relative_to_rule=relative_to)
    print(rule)
    assert isinstance(rule, NttCisFirewallRule)


def test_create_port_list(compute_driver):
    """
    An optional named argument, child_portlist_list, which takes the id of an existing
    port list to include in this port list.
    """
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    port_list_name = 'sdk_test_port_list'
    description = 'A test port list'
    port_list = [NttCisPort(begin='8000', end='8080')]
    result = compute_driver.ex_create_portlist(net_domain[0], port_list_name, description, port_list)
    assert result is True


def test_create_address_list(compute_driver):
    """
        An optional named argument, child_ip_address_list, which takes the id of an existing
        port list to include in this port list.
        """
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name]
    address_list_name = 'sdk_test_address_list'
    description = 'A test address list'
    ip_version = 'IPV4'
    # An optional prefix list can be specified as a named argument, prefix_size=
    address_list = [NttCisIpAddress('10.2.0.1', end='10.2.0.11')]

    result = compute_driver.ex_create_ip_address_list(net_domain[0], address_list_name,
                                  description,
                                  ip_version, address_list)
    assert result is True


def test_create_public_ip_block(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name][0]
    ip_block = compute_driver.ex_add_public_ip_block_to_network_domain(net_domain)
    assert isinstance(ip_block, NttCisPublicIpBlock)
    print(ip_block)


def test_create_private_ipv4_address(compute_driver):
    vlan_name = 'sdk_vlan1'
    vlan = compute_driver.ex_list_vlans(name=vlan_name)[0]
    ip = '10.1.1.20'
    description = 'A test reserved ipv4 address'
    result = compute_driver.ex_reserve_ip(vlan, ip, description)
    assert result is True


def test_create_ipv6_addresss(compute_driver):
    vlan_name = 'sdk_vlan1'
    vlan = compute_driver.ex_list_vlans(name=vlan_name)[0]
    ipv6 = '2a00:47c0:111:1331:7df0:9beb:43c9:5c'
    result = compute_driver.ex_reserve_ip(vlan, ipv6)
    assert result is True


def test_import_customer_image(compute_driver):
    package_name = "bitnami-couchdb-2.1.2-1-r35-linux-centos-7-x86_64.mf"
    name = "bitnami-couchdb-2.1.2-1-r35-linux-centos-7-x86_64"
    datacenter_id = 'EU6'
    is_guest_os_customization = 'false'
    result = compute_driver.import_image(package_name, name, datacenter_id=datacenter_id,
                                         is_guest_os_customization=is_guest_os_customization)
    assert result is True


def test_create_load_balancer(lbdriver, compute_driver):
    member1 = compute_driver.list_nodes(ex_name='web1')[0]
    member2 = compute_driver.list_nodes(ex_name='web2')[0]
    members = [member1, member2]
    name = 'sdk_test_balancer'
    port = '80'
    listener_port = '8000'
    protocol = 'TCP'
    algorithm = 'LEAST_CONNECTIONS'
    members = [m for m in members]
    ex_listener_ip_address = "168.128.13.127"
    lb = lbdriver.create_balancer(name, listener_port=listener_port, port=port, protocol=protocol,
                                  algorithm=algorithm, members=members, optimization_profile='TCP',
                                  ex_listener_ip_address=ex_listener_ip_address)



def test_create_pool(lbdriver):
    pass

