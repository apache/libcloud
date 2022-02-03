from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.ECS)

conn = cls(
    access_id="SDHFISJDIFJSIDFJ",
    secret="THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H",
    region="ap-southeast-2",
)

for container in conn.list_containers():
    print(container.name)

for cluster in conn.list_clusters():
    print(cluster.name)
