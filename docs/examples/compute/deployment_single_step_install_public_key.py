import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.deployment import SSHKeyDeployment

# Path to the private SSH key file used to authenticate
PRIVATE_SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")

# Path to the public key you would like to install
KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

RACKSPACE_USER = "your username"
RACKSPACE_KEY = "your key"

Driver = get_driver(Provider.RACKSPACE)
conn = Driver(RACKSPACE_USER, RACKSPACE_KEY)

with open(KEY_PATH) as fp:
    content = fp.read()

# Note: This key will be added to the authorized keys for the root user
# (/root/.ssh/authorized_keys)
step = SSHKeyDeployment(content)

images = conn.list_images()
sizes = conn.list_sizes()

# deploy_node takes the same base keyword arguments as create_node.
node = conn.deploy_node(
    name="test",
    image=images[0],
    size=sizes[0],
    deploy=step,
    ssh_key=PRIVATE_SSH_KEY_PATH,
)
