import pytest
import libcloud


@pytest.fixture(scope="module")
def driver():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    driver = cls('mitchgeo-test', 'Snmpv2c!', region='dd-eu')
    return driver

