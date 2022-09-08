from libcloud.container.base import ContainerImage
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

driver = get_driver(Provider.RANCHER)

connection = driver(
    "MYRANCHERACCESSKEY",
    "MYRANCHERSECRETKEY",
    host="172.30.0.100",
    port=8080,
    secure=False,
)

image = ContainerImage("hastebin", "hastebin", "rlister/hastebin", "latest", driver=None)

new_container = connection.deploy_container(
    name="awesomecontainer", image=image, networkMode="managed"
)
