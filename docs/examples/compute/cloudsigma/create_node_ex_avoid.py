from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls('username', 'password', region='zrh', api_version='2.0')

name = 'test node avoid mode'
size = driver.list_sizes()[0]
image = driver.list_images()[0]

existing_nodes = driver.list_nodes()
existing_node_uuids = [node.id for node in existing_nodes]


node = driver.create_node(name=name, size=size, image=image,
                          ex_avoid=existing_node_uuids)
print(node)
