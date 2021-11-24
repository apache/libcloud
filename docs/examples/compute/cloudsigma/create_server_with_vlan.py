from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

name = "test node with vlan"
size = driver.list_sizes()[0]
image = driver.list_images()[0]

# 1. Create a VLAN. VLANs are created by purchasing a subscription.
subscription = driver.ex_create_subscription(
    amount=1, period="1 month", resource="vlan", auto_renew=True
)
vlan_uuid = subscription.subscribed_object

# 2. Create a node with a VLAN
node = driver.create_node(name=name, size=size, image=image, ex_vlan=vlan_uuid)
print(node)
