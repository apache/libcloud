from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

RACKSPACE_USER = 'your username'
RACKSPACE_KEY = 'your key'

Driver = get_driver(Provider.RACKSPACE)
conn = Driver(RACKSPACE_USER, RACKSPACE_KEY)

# retrieve available images and sizes
images = conn.list_images()
# [<NodeImage: id=3, name=Gentoo 2008.0, driver=Rackspace  ...>, ...]
sizes = conn.list_sizes()
# [<NodeSize: id=1, name=256 server, ram=256 ... driver=Rackspace ...>, ...]

# create node with first image and first size
node = conn.create_node(name='test', image=images[0], size=sizes[0])
# <Node: uuid=..., name=test, state=3, public_ip=['1.1.1.1'],
#   provider=Rackspace ...>
