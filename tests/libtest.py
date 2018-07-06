import pytest
import libcloud


def test_connection():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.DIMENSIONDATA)
    driver = cls('mitchgeo-test', 'Snmpv2c!', region='dd-eu')
    nodes = driver.list_nodes()
    assert isinstance(nodes, list)


