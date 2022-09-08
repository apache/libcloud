from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Import the deployment specific modules
from libcloud.compute.deployment import ScriptDeployment, MultiStepDeployment

cls = get_driver(Provider.EXOSCALE)
driver = cls("api key", "api secret key")

image = driver.list_images()[0]
size = driver.list_sizes()[0]

# Define the scripts that you want to run during deployment
script = ScriptDeployment("/bin/date")
msd = MultiStepDeployment([script])

node = driver.deploy_node(
    name="test",
    image=image,
    size=size,
    ssh_key="~/.ssh/id_rsa_test",
    ex_keyname="test-keypair",
    deploy=msd,
)

# The stdout of the deployment can be checked on the `script` object
pprint(script.stdout)
