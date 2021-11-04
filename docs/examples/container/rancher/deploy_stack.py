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

new_stack = connection.ex_deploy_stack(
    name="GhostBlog", description="Contains services for the" "ghost blog."
)

id_of_new_stack = new_stack["id"]
