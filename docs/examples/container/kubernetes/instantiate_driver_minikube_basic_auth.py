import libcloud.security
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

# Disable cert vertification when running minikube locally using self signed
# cert
libcloud.security.VERIFY_SSL_CERT = False

cls = get_driver(Provider.KUBERNETES)

# You can retrieve cluster ip by running "minikube ip" command
conn = cls(key="user1", secret="pass123", host="192.168.99.100", port=8443, secure=True)

for container in conn.list_containers():
    print(container.name)

for cluster in conn.list_clusters():
    print(cluster.name)
