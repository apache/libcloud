from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2_ACCESS_ID = 'your access id'
EC2_SECRET_KEY = 'your secret key'
RACKSPACE_USER = 'your username'
RACKSPACE_KEY = 'your key'

EC2Driver = get_driver(Provider.EC2)
RackspaceDriver = get_driver(Provider.RACKSPACE)

drivers = [EC2Driver(EC2_ACCESS_ID, EC2_SECRET_KEY),
           RackspaceDriver(RACKSPACE_USER, RACKSPACE_KEY)]

nodes = []
for driver in drivers:
    nodes += driver.list_nodes()
print nodes
# [ <Node: provider=Amazon, status=RUNNING, name=bob, ip=1.2.3.4.5>,
#   <Node: provider=Rackspace, status=REBOOT, name=korine, ip=6.7.8.9>, ... ]

# Reboot all nodes named 'test'
[node.reboot() for node in nodes if node.name == 'test']
