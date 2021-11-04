from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

node = driver.list_nodes()[0]

tag_names = ["zrh", "database-server", "monited"]

tags = []

# 1. Create necessary tags
for tag_name in tag_names:
    tag = driver.ex_create_tag(name="database-servers")
    tags.append(tag)

# 2. Tag node with the created tags
for tag in tags:
    driver.ex_tag_resource(resource=node, tag=tag)
