from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

tags = driver.ex_list_tags()
tag = [tag for tag in tags if tag.name == "database-server"][0]

nodes = driver.list_nodes(ex_tag=tag)
policy = driver.ex_list_firewall_policies()[0]

for node in nodes:
    driver.ex_attach_firewall_policy(policy=policy, node=node)
