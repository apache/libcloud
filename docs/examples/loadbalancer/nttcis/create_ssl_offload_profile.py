# Create an SSL Offload Profile

import libcloud


def create_ssl_profile(lbdriver):
    # Identify the network domain to insert the profile into
    net_domain_id = "6aafcf08-cb0b-432c-9c64-7371265db086"
    name = "ssl_offload"
    # Retrieve the domain certificate to be used int the profile
    domain_cert = lbdriver.ex_list_ssl_domain_certs(name="alice")[0]
    result = lbdriver.ex_create_ssl_offload_profile(
        net_domain_id, name, domain_cert.id, ciphers="!ECDHE+AES-GCM:"
    )
    assert result is True


def lbdriver():
    cls = libcloud.get_driver(
        libcloud.DriverType.LOADBALANCER, libcloud.DriverType.LOADBALANCER.NTTCIS
    )
    driver = cls("mitchgeo-test", "Snmpv2c!", region="eu")
    return driver


if __name__ == "__main__":
    lb = lbdriver()
    create_ssl_profile(lb)
