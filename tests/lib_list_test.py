import pytest
import libcloud
from libcloud import loadbalancer


def test_list_node_all(compute_driver):
    nodes = compute_driver.list_nodes()
    for node in nodes:
         print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              node.extra['scsi_controller'], node.extra['disks'], node.extra['memoryMb'],
              node.extra['OS_displayName'], node.private_ips, node.extra['ipv6'], node.extra['window'])

    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_location(compute_driver):
    nodes = compute_driver.list_nodes(ex_location='EU6')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_name(compute_driver):
    nodes = compute_driver.list_nodes(ex_name='sdk_server_1')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_ipv6(compute_driver):
    nodes = compute_driver.list_nodes(ex_ipv6='2a00:47c0:111:1331:6140:e432:729b:eef6')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_ipv4(compute_driver):
    nodes = compute_driver.list_nodes(ex_ipv4='10.1.1.6')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_images(compute_driver):
    images = compute_driver.list_images(location='EU6')
    print()
    for image in images:
        print(image.id, image.name)
    assert isinstance(images, list) and len(images) > 0


def test_list_os(compute_driver):
    oss = compute_driver.ex_list_os(location='EU6')


def test_list_node_by_image(compute_driver):
    nodes = compute_driver.list_nodes(ex_image='81a36aa0-555c-4735-b965-4b64fcf0ac8f')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


"""
    requires retrieving vlan Id first
"""

def test_list_node_vlan(compute_driver):
    nodes = compute_driver.list_nodes(ex_vlan='eb05a24e-85a6-46e3-a7c9-f1765737476d')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


"""
Libcloud docs say this works but it is not in our API docs
def test_list_node_image(compute_driver):
    nodes = compute_driver.list_nodes(ex_image='46096745-5a89-472b-9b3b-89a6a07bb60b')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0
"""


def test_list_node_started(compute_driver):
    nodes = compute_driver.list_nodes(ex_started='true')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_deployed(compute_driver):
    nodes = compute_driver.list_nodes(ex_deployed='true')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_state(compute_driver):
    nodes = compute_driver.list_nodes(ex_state='NORMAL')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_network_domain_id(compute_driver):
    nodes = compute_driver.list_nodes(ex_network_domain='6aafcf08-cb0b-432c-9c64-7371265db086')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'],
              node.private_ips, node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_vlans(compute_driver):
    vlans = compute_driver.ex_list_vlans()
    print()
    for vlan in vlans:
        print(vlan.id, vlan.name, vlan.location.id, vlan.ipv4_gateway, vlan.ipv6_gateway, vlan.ipv6_range_address, vlan.ipv6_range_size,
              vlan.private_ipv4_range_address, vlan.private_ipv4_range_size, vlan.status)
    assert isinstance(vlans, list) and len(vlans) > 0


def test_list_vlan(compute_driver):
    vlan = compute_driver.ex_get_vlan('eb05a24e-85a6-46e3-a7c9-f1765737476d')
    print()
    print(vlan.id, vlan.name, vlan.location.id, vlan.ipv4_gateway, vlan.ipv6_gateway, vlan.ipv6_range_address, vlan.ipv6_range_size,
          vlan.private_ipv4_range_address, vlan.private_ipv4_range_size, vlan.status)
    assert vlan.name == 'sdk_vlan1'


def test_list_datacenter_object_creation(compute_driver):
    datacenter = compute_driver.ex_get_datacenter('EU6')


def test_list_firewall_rules(compute_driver):
    rules = compute_driver.ex_list_firewall_rules('6aafcf08-cb0b-432c-9c64-7371265db086')
    print()
    for rule in rules:
        print("id {}, name {}, action {}. location {}, ip ver {}, protocol {}, any ip {}, ip {}, prefix {},"
              " port range {} {} , src address {}, src port list {}, dest. any__ip {}, dest address {}, "
              "dest prefix {}, dest port range {} {}, dest address list id {}"
              ", dest port list id {}".format(
                                              rule.id, rule.name, rule.action,
                                              rule.location.name, rule.ip_version,
                                              rule.protocol, rule.source.any_ip,
                                              rule.source.ip_address,
                                              rule.source.ip_prefix_size,
                                              rule.source.port_begin, rule.source.port_end,
                                              rule.source.address_list_id,
                                              rule.source.port_list_id,
                                              rule.destination.any_ip,
                                              rule.destination.ip_address,
                                              rule.destination.ip_prefix_size,
                                              rule.destination.port_begin,
                                              rule.destination.port_end,
                                              rule.destination.address_list_id,
                                              rule.destination.port_list_id,
                                              ))


def test_list_address_lists(compute_driver):
    address_lists = compute_driver.ex_list_ip_address_list('6aafcf08-cb0b-432c-9c64-7371265db086')
    print()
    for address_list in address_lists:
        print(address_list)
    assert isinstance(address_lists, list) and len(address_lists) > 0


def test_list_port_lists(compute_driver):
    port_lists = compute_driver.ex_list_portlist('6aafcf08-cb0b-432c-9c64-7371265db086')
    print()
    for portlist in port_lists:
        print(portlist)
    assert isinstance(port_lists, list) and len(port_lists) > 0


def test_list_nat_rules(compute_driver):
    nat_rules = compute_driver.ex_list_nat_rules(compute_driver.ex_get_network_domain('6aafcf08-cb0b-432c-9c64-7371265db086'))
    print()
    for nat_rule in nat_rules:
        print(nat_rule, nat_rule.external_ip, nat_rule.internal_ip)
    assert isinstance(nat_rules, list) and len(nat_rules) > 0


def test_list_balancers(lbdriver):
    balancers = lbdriver.list_balancers(ex_network_domain_id="6aafcf08-cb0b-432c-9c64-7371265db086")
    print()
    for balancer in balancers:
        print(balancer.id, balancer.ip, balancer.name, balancer.port)
    assert isinstance(balancers, list)


def test_get_listener(lbdriver):
    listener = lbdriver.get_balancer("59abe126-2bba-48ac-8616-1aba51aabac5")
    print()
    print(listener.ip, listener.name, listener.port)
    assert listener.ip == '168.128.13.127'


def test_vip_nodes(lbdriver):
    vips = lbdriver.ex_get_nodes("6aafcf08-cb0b-432c-9c64-7371265db086")
    print()
    for vip in vips:
        print(vip, vip.ip, vip.name)
    assert isinstance(vips, list) and len(vips) > 0


def test_list_lb_pools(lbdriver):
    pools = lbdriver.ex_get_pools(ex_network_domain_id="6aafcf08-cb0b-432c-9c64-7371265db086")
    print()
    for pool in pools:
        print(pool.id, pool.name, pool.description, pool.health_monitor_id, pool.load_balance_method, pool.slow_ramp_time, pool.status)
    assert isinstance(pools, list)


def test_list_lb_pool_members(lbdriver):
    balancer = lbdriver.get_balancer("59abe126-2bba-48ac-8616-1aba51aabac5")
    pool_members = lbdriver.balancer_list_members(balancer)
    print()
    for pool_member in pool_members:
        print(pool_member)
    assert isinstance(pool_members, list)


def test_get_pool_member(lbdriver):
    pool_member = lbdriver.ex_get_pool_member("9382e488-7f95-4db0-b2de-0b807aab825b")
    print()
    print(pool_member.ip, pool_member.port, pool_member.name)
    assert pool_member.ip == '10.1.1.8'


def test_get_node(lbdriver):
    node = lbdriver.ex_get_node("5c647a74-d181-4ed8-82d3-55ae443a06dd")
    print()
    print(node.name, node.ip, node.connection_limit, node.connection_rate_limit)
    assert isinstance(node, object)


def test_list_snapshots(compute_driver):
    snapshots = compute_driver.list_snapshots('web1')
    for snapshot in snapshots:
        print(snapshot)
        assert 'expiry_time' in snapshot


def test_list_nics(compute_driver):
    result = compute_driver.ex_list_


def test_list_vlans(compute_driver):
    vlans = compute_driver.ex_list_vlans()
    print(vlans)
    assert isinstance(vlans, list)


def test_list_anti_affinity_rules(compute_driver):
    # Could use network domain or node but not both
    # net_domain = compute_driver.ex_get_network_domain('6aafcf08-cb0b-432c-9c64-7371265db086')
    node = compute_driver.ex_get_node_by_id("803e5e00-b22a-450a-8827-066ff15ec977")
    anti_affinity_rules = compute_driver.ex_list_anti_affinity_rules(node=node)
    assert len(anti_affinity_rules) > 1


def test_list_no_anti_affinity_rules(compute_driver):
    # Could use network domain or node but not both
    # net_domain = compute_driver.ex_get_network_domain('6aafcf08-cb0b-432c-9c64-7371265db086')
    node = compute_driver.ex_get_node_by_id("803e5e00-b22a-450a-8827-066ff15ec977")
    anti_affinity_rules = compute_driver.ex_list_anti_affinity_rules(node=node)
    assert len(anti_affinity_rules) == 0


def test_list_locations(compute_driver):
    locations = compute_driver.list_locations()
    for location in locations:
        print(location)


"""
def test_list_sizes(compute_driver):
    properties = compute_driver.list_locations()
    for property in properties:
        print(property)
"""


def test_images(compute_driver):
    images = compute_driver.list_images()
    print()
    print(images)
    assert isinstance(images, list) and len(images) > 0


def test_list_public_ip_blocks(compute_driver):
    domain_name = 'sdk_test_1'
    domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain = [d for d in domains if d.name == domain_name][0]
    blocks = compute_driver.ex_list_public_ip_blocks(net_domain)
    print(blocks)


def test_list_private_ipv4_addresses_vlan(compute_driver):
    vlan_name = 'sdk_vlan1'
    vlan = compute_driver.ex_list_vlans(name=vlan_name)[0]
    ip_addresses = compute_driver.ex_list_reserved_ipv4(vlan=vlan)
    for ip_address in ip_addresses:
        print(ip_address)


def test_list_private_ipv4_addresses_datacenter(compute_driver):
    datacenter_id = 'EU8'
    ip_addresses = compute_driver.ex_list_reserved_ipv4(datacenter_id=datacenter_id)
    for ip_address in ip_addresses:
        print(ip_address)


def test_list_private_ipv4_addresses_all(compute_driver):
    ip_addresses = compute_driver.ex_list_reserved_ipv4()
    for ip_address in ip_addresses:
        print(ip_address)


def test_list_reserved_ipv6_address_vlan(compute_driver):
    vlan_name = 'sdk_vlan1'
    vlan = compute_driver.ex_list_vlans(name=vlan_name)[0]
    ip_addresses = compute_driver.ex_list_reserved_ipv6(vlan=vlan)
    for ip_address in ip_addresses:
        print(ip_address)


def test_list_nat_rules(compute_driver):
    network_domain_name = "sdk_test_1"
    network_domains = compute_driver.ex_list_network_domains(location='EU6')
    network_domain = [nd for nd in network_domains if nd.name == network_domain_name][0]
    rules = compute_driver.ex_list_nat_rules(network_domain)
    for rule in rules:
        print(rule)


def test_list_customer_images(compute_driver):
    location = 'EU6'
    images = compute_driver.ex_list_customer_images(location)
    for image in images:
        print(image, image.extra)


def test_get_customer_image(compute_driver):
    imagee_id = '84da095f-c8c7-4ace-9fb6-eceb1047027c'
    image = compute_driver.ex_get_image_by_id(imagee_id)
    print(image, image.extra)

