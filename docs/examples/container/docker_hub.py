from libcloud.container.types import Provider
from libcloud.container.providers import get_driver
from libcloud.container.utils.docker import HubClient

cls = get_driver(Provider.ECS)

conn = cls(
    access_id="SDHFISJDIFJSIDFJ",
    secret="THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H",
    region="ap-southeast-2",
)
hub = HubClient()

image = hub.get_image("ubuntu", "latest")

for cluster in conn.list_clusters():
    print(cluster.name)
    if cluster.name == "default":
        container = conn.deploy_container(cluster=cluster, name="my-simple-app", image=image)
