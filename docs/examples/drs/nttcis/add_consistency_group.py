# This script creates a consistency group

import libcloud


def create_drs(compute_driver, drs_driver):
    nodes = compute_driver.list_nodes(ex_name='src-sdk-test')
    src_id = nodes[0].id
    nodes = compute_driver.list_nodes(ex_name="tgt-sdk-test")
    target_id = nodes[0].id
    consistency_group_name = "sdk_test_cg"
    journal_size_gb = "100"
    result = drs_driver.create_consistency_group(
        consistency_group_name, journal_size_gb, src_id, target_id,
        description="A test consistency group")
    assert result is True


if __name__ == "__main__":
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE,
                              libcloud.DriverType.COMPUTE.NTTCIS)
    computedriver = cls('my_user', 'my_pass', region='na')

    cls = libcloud.get_driver(libcloud.DriverType.DRS,
                              libcloud.DriverType.DRS.NTTCIS)
    drsdriver = cls('my_user', 'my_pass', region='na')
    create_drs(computedriver, drsdriver)
