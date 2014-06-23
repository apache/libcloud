from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = 'your api key'
secretkey = 'your secret key'

Driver = get_driver(Provider.IKOULA)
driver = Driver(key=apikey, secret=secretkey)

# This returns a list of CloudStackNetwork objects
nets = driver.ex_list_networks()

# List the images/templates available
# This returns a list of NodeImage objects
images = driver.list_images()

# List the instance types
# This returns a list of NodeSize objects
sizes = driver.list_sizes()

# Create the node
# This returns a Node object
node = driver.create_node(name='libcloud', image=images[0],
                          size=sizes[0], networks=[nets[0]])

# The node has a private IP in the guest network used
# No public IPs and no rules
pprint(node.extra)
pprint(node.private_ips)
