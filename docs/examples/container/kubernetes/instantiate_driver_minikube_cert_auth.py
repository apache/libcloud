import libcloud.security
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

# Disable cert vertification when running minikube locally using self signed
# cert
libcloud.security.VERIFY_SSL_CERT = False

cls = get_driver(Provider.KUBERNETES)

# You can retrieve cluster ip by running "minikube ip" command
conn = cls(
    host="192.168.99.103",
    port=8443,
    secure=True,
    key_file="/home/user/.minikube/client.key",
    cert_file="/home/user/.minikube/client.crt",
    ca_cert="/home/user/.minikube/ca.crt",
)

for container in conn.list_containers():
    print(container.name)

for cluster in conn.list_clusters():
    print(cluster.name)
