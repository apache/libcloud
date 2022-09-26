import os

from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PROFIT_BRICKS)

# Get ProfitBricks credentials from environment variables
pb_username = os.environ.get("PROFITBRICKS_USERNAME")
pb_password = os.environ.get("PROFITBRICKS_PASSWORD")

driver = cls(pb_username, pb_password)

# List available sizes
sizes = driver.list_sizes()

# Medium-size instance
my_size = sizes[1]

datacenters = driver.ex_list_datacenters()
# Looks for existing data centers named 'demo-dc'
desired_dc = [dc for dc in datacenters if dc.name == "demo-dc"]

# Get available HDD public images
images = driver.list_images("HDD")

my_image = None
# Let's choose Ubuntu-16.04 image in us/las region
for img in images:
    if "Ubuntu-16.04-LTS-server" in img.name and "us/las" == img.extra["location"]:
        my_image = img
        break

node_key = None
# Read SSH key from file
# Specify correct path
with open("/home/user/.ssh/id_rsa.pub") as f:
    node_key = NodeAuthSSHKey(f.read())
f.close()

node = driver.create_node(
    name="demo-node",
    size=my_size,
    ex_cpu_family="INTEL_XEON",
    image=my_image,
    ex_datacenter=desired_dc[0],
    ex_ssh_keys=[node_key],
)
print(node)
