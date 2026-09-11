from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.LINODE)
driver = cls("your access token")

nodes = driver.list_nodes()
print(nodes)
