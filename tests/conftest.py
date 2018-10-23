import pytest
import libcloud


@pytest.fixture(scope="module")
def compute_driver():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    compute_driver = cls('mitchgeo-test', 'Snmpv2c!', region='eu')
    return compute_driver


@pytest.fixture(scope="module")
def compute_driver_na():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    compute_driver = cls('mitchgeo-test', 'Snmpv2c!', region='na')
    return compute_driver


@pytest.fixture(scope="module")
def lbdriver():
    cd = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    compute_driver = cd('mitchgeo-test', 'Snmpv2c!', region='eu')
    net_domain_name = 'sdk_test_1'
    net_domains = compute_driver.ex_list_network_domains(location='EU6')
    net_domain_id = [d for d in net_domains if d.name == net_domain_name][0].id
    cls = libcloud.get_driver(libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS)
    lbdriver = cls('mitchgeo-test', net_domain_id, 'Snmpv2c!', region='eu')
    return lbdriver


@pytest.fixture(scope="module")
def drs_driver():
    drs = libcloud.get_driver(libcloud.DriverType.DRS, libcloud.DriverType.DRS.NTTCIS)
    drsdriver = drs('mitchgeo-test', 'Snmpv2c!', region='eu')
    return drsdriver
