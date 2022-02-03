from libcloud.container.base import ContainerImage
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.ECS)

conn = cls(
    access_id="SDHFISJDIFJSIDFJ",
    secret="THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H",
    region="ap-southeast-2",
)

for cluster in conn.list_clusters():
    print(cluster.name)
    if cluster.name == "my-cluster":
        conn.list_containers(cluster=cluster)
        container = conn.deploy_container(
            name="my-simple-app",
            image=ContainerImage(
                id=None, name="simple-app", path="simple-app", version=None, driver=conn
            ),
            cluster=cluster,
        )
