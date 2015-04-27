from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PACKET)

driver = cls('your API auth token')

nodes = driver.list_nodes('project-id')
for node in nodes:
    print(node)
