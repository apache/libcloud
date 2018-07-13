import pytest
import libcloud


def test_list_node_all(driver):
    nodes = driver.list_nodes()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'], node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_location(driver):
    nodes = driver.list_nodes(ex_location='EU7')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'], node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_list_node_started(driver):
    nodes = driver.list_nodes(ex_started='true')
    print()
    for node in nodes:
        print(node.extra['networkDomainId'], node.extra['datacenterId'], node.uuid, node.state, node.name, node.extra['cpu'],
              [disk for disk in node.extra['disks']], node.extra['memoryMb'], node.extra['OS_displayName'], node.extra['ipv6'])
    assert isinstance(nodes, list) and len(nodes) > 0


def test_images(driver):
    images = driver.list_images()
    print()
    print(images)
    assert isinstance(images, list) and len(images) > 0

