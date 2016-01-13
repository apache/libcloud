from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.KUBERNETES)

conn = cls(key='my_username',
           secret='THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H',
           host='126.32.21.4')

for container in conn.list_containers():
    print(container.name)

for cluster in conn.list_clusters():
    print(cluster.name)
