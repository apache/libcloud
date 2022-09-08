from libcloud.container.base import ContainerImage
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

driver = get_driver(Provider.RANCHER)

connection = driver("MYRANCHERACCESSKEY", "MYRANCHERSECRETKEY", host="17.23.66.4", port=443)

image = ContainerImage("hastebin", "hastebin", "rlister/hastebin", "latest", driver=None)

new_service = connection.ex_deploy_service(
    name="excitingservice",
    image=image,
    environmentid="1e2",
    environment={"STORAGE_TYPE": "file"},
)
