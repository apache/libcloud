from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Gandi = get_driver(Provider.GANDI)
driver = Gandi("api_key")

image = [i for i in driver.list_images() if "Debian 8 64" in i.name][0]
size = [s for s in driver.list_sizes() if s.name == "Medium instance"][0]
location = [loc for loc in driver.list_locations() if loc.name == "FR-SD2"][0]

node = driver.create_node(
    name="yournode",
    size=size,
    image=image,
    location=location,
    login="youruser",
    password="pass",
)
