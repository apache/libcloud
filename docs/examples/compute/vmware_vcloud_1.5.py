import libcloud.security
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Skip this step if you are launching nodes on an official vCloud
# provider. It is intended only for self signed SSL certs in
# vanilla vCloud Director v1.5 test deployments.
# Note: Code like this poses a security risk (MITM attack) and
# that's the reason why you should never use it for anything else
# besides testing. You have been warned.
libcloud.security.VERIFY_SSL_CERT = False

vcloud = get_driver(Provider.VCLOUD)

driver = vcloud(
    "you username@organisation", "your password", host="vcloud.local", api_version="1.5"
)

# List all instantiated vApps
nodes = driver.list_nodes()
# List all VMs within the first vApp instance
print(nodes[0].extra["vms"])

# List all available vApp Templates
images = driver.list_images()
image = [i for i in images if i.name == "natty-server-cloudimg-amd64"][0]

# Create node with minimum set of parameters
node = driver.create_node(name="test node 1", image=image)
# Destroy the node
driver.destroy_node(node)

# Create node without deploying and powering it on
node = driver.create_node(name="test node 2", image=image, ex_deploy=False)

# Create node with custom CPU & Memory values
node = driver.create_node(name="test node 3", image=image, ex_vm_cpu=3, ex_vm_memory=1024)

# Create node with customised networking parameters (eg. for OVF
# imported images)
node = driver.create_node(
    name="test node 4",
    image=image,
    ex_vm_network="your vm net name",
    ex_network="your org net name",
    ex_vm_fence="bridged",
    ex_vm_ipmode="DHCP",
)

# Create node in a custom virtual data center
node = driver.create_node(name="test node 4", image=image, ex_vdc="your vdc name")

# Create node with guest OS customisation script to be run at first boot
node = driver.create_node(
    name="test node 5", image=image, ex_vm_script="filesystem path to your script"
)
