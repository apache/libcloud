import pytest
import libcloud


@pytest.fixture(scope="module")
def compute_driver():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    compute_driver = cls('mitchgeo-test', 'Snmpv2c!', region='dd-eu')
    return compute_driver


@pytest.fixture(scope="module")
def lbdriver():
    cls = libcloud.get_driver(libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS)
    lbdriver = cls('mitchgeo-test', 'Snmpv2c!', region='dd-eu')
    return lbdriver