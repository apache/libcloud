# This example shows importing an SSL Domain Certificate

import libcloud


def insert_ssl(lbdriver, compute_driver):
    net_dom_name = "sdk_test_1"
    net_dom = compute_driver.ex_list_network_domains(name=net_dom_name)[0]
    cert = "/home/mraful/client/bob.crt"
    key = "/home/mraful/client/bob.key"
    result = lbdriver.ex_import_ssl_domain_certificate(
        net_dom.id, "bob", cert, key, description="test cert"
    )
    assert result is True


def lbdriver():
    cls = libcloud.get_driver(
        libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS
    )
    driver = cls("mitchgeo-test", "Snmpv2c!", region="eu")
    return driver


def compute_driver():
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.NTTCIS)
    driver = cls("mitchgeo-test", "Snmpv2c!", region="eu")
    return driver


if __name__ == "__main__":
    lb = lbdriver()
    cd = compute_driver()
    insert_ssl(lb, cd)
