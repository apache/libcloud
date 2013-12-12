from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Import the deployment specific modules
from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment

cls = get_driver(Provider.EXOSCALE)
driver = cls('api key', 'api secret key')

# Define the scripts that you want to run during deployment
script = ScriptDeployment("/bin/date")
msd = MultiStepDeployment([script])

node = conn.deploy_node(name='test', image=image, size=size,
                        ssh_key='~/.ssh/id_rsa_test',
                        ex_keyname='test-keypair',
                        deploy=msd)

# The stdout of the deployment can be checked on the `script` object
script.stdout
