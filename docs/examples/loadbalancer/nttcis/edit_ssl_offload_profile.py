# This script demonstrates how to edit a profile

import libcloud


def edit_ssl_offload_profile(lbdriver):
    # Identify the wich profile by name to be edited
    profile_name = "ssl_offload"
    datacenter_id = "EU6"
    profile = lbdriver.ex_list_ssl_offload_profiles(name=profile_name, datacenter_id=datacenter_id)[
        0
    ]
    # All elements must be passed to the edit method that
    #  would be required in creating a profile as well as what currently exists
    # such as the current ciphers, unless ciphers were to be changed.
    # Here a new description is being added.
    result = lbdriver.ex_edit_ssl_offload_profile(
        profile.id,
        profile.name,
        profile.sslDomainCertificate.id,
        ciphers=profile.ciphers,
        description="A test edit of an offload profile",
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
    edit_ssl_offload_profile(lb)
