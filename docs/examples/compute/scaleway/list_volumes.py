from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.SCALEWAY)
driver = cls("SCALEWAY_ACCESS_KEY", "SCALEWAY_SECRET_TOKEN")

volumes = driver.list_volumes()
for volume in volumes:
    print(volume)
    snapshots = driver.list_volume_snapshots(volume)
    for snapshot in snapshots:
        print("  snapshot-%s" % snapshot)
