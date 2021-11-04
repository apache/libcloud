import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

locations = drv.list_locations()

desired_location = [loc for loc in locations if loc.name == "ES"]

try:
    shared_storage = drv.ex_create_shared_storage(
        name="Test Shared Storage",
        size=50,
        datacenter_id=desired_location[0].id,
        description=None,
    )
    print(shared_storage)
except Exception as e:
    print(e)
