from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

driver = get_driver(Provider.RANCHER)

connection = driver(
    "MYRANCHERACCESSKEY",
    "MYRANCHERSECRETKEY",
    host="172.30.22.1",
    port=8080,
    secure=False,
)

search_results = connection.ex_search_containers(
    search_params={"imageUuid": "docker:mysql", "state": "running"}
)

id_of_first_result = search_results[0]["id"]
