from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.deployment import ScriptDeployment, SSHKeyDeployment
import os

RACKSPACE_USER = 'your username'
RACKSPACE_KEY = 'your key'

Driver = get_driver(Provider.RACKSPACE)
conn = Driver(RACKSPACE_USER, RACKSPACE_KEY)

# read your public key in
# Note: This key will be added to the authorized keys for the root user
# (/root/.ssh/authorized_keys)
sd = SSHKeyDeployment(open(os.path.expanduser("~/.ssh/id_rsa.pub")).read())
# a simple script to install puppet post boot, can be much more complicated.
script = ScriptDeployment("apt-get -y install puppet")
# a task that first installs the ssh key, and then runs the script
msd = MultiStepDeployment([sd, script])

images = conn.list_images()
sizes = conn.list_sizes()

# deploy_node takes the same base keyword arguments as create_node.
node = conn.deploy_node(name='test', image=images[0], size=sizes[0],
                        deploy=msd)
# <Node: uuid=..., name=test, state=3, public_ip=['1.1.1.1'],
#  provider=Rackspace ...>
# the node is now booted, with your ssh key and puppet installed.
