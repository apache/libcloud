from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.KUBERNETES)

# 1. Client side cert auth
conn = cls(
    host="192.168.99.103",
    port=8443,
    secure=True,
    key_file="/home/user/.minikube/client.key",
    cert_file="/home/user/.minikube/client.crt",
    ca_cert="/home/user/.minikube/ca.crt",
)

# 2. Bearer bootstrap token auth
conn = cls(key="my_token", host="126.32.21.4", ex_token_bearer_auth=True)

# 3. Basic auth
conn = cls(key="my_username", secret="THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H", host="126.32.21.4")

for container in conn.list_containers():
    print(container.name)

for cluster in conn.list_clusters():
    print(cluster.name)
