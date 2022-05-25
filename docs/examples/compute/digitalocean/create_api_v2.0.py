from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.DIGITAL_OCEAN)

driver = cls("access token", api_version="v2")

options = {"backups": True, "private_networking": True, "ssh_keys": [123456, 123457]}

name = "test.domain.tld"
size = driver.list_sizes()[0]
image = driver.list_images()[0]
location = driver.list_locations()[0]

node = driver.create_node(name, size, image, location, ex_create_attr=options)
