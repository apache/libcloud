from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.SCALEWAY)
driver = cls("SCALEWAY_ACCESS_KEY", "SCALEWAY_SECRET_TOKEN")

nodes = driver.list_nodes()
for node in nodes:
    print(node)
