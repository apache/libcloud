# This script lists the snapshots in a consistency group
# filtered by a minimum and maximum create time

import libcloud


def get_snapshots_by_min_max(drsdriver):
    cgs = drsdriver.list_consistency_groups()
    cg_id = [i for i in cgs if i.name == "sdk_test2_cg"][0].id
    snaps = drsdriver.list_consistency_group_snapshots(
        cg_id,
        create_time_min="2018-11-06T00:00:00.000Z",
        create_time_max="2018-11-07T00:00:00.000Z")
    return snaps


if __name__ == "__main__":
    cls = libcloud.get_driver(libcloud.DriverType.DRS,
                              libcloud.DriverType.DRS.NTTCIS)
    drsdriver = cls('my_user', 'my_pass', region='na')
    objs = get_snapshots_by_min_max(drsdriver)
    for obj in objs.snapshot:
        print(obj)