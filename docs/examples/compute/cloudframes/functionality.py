import uuid

from libcloud.compute.types import Provider, NodeState
from libcloud.compute.providers import get_driver

CloudFrames = get_driver(Provider.CLOUDFRAMES)
driver = CloudFrames(url="http://admin:admin@cloudframes:80/appserver/xmlrpc")

# get an available location
location = driver.list_locations()[0]
# and an image
image = driver.list_images()[0]
# as well as a size
size = driver.list_sizes()[0]

# use these to create a node
node = driver.create_node(image=image, name="TEST_%s" % uuid.uuid4(), size=size, location=location)

# snapshot a node, rollback to the snapshot and destroy the snaphost
snapshot = driver.ex_snapshot_node(node)
driver.ex_rollback_node(node, snapshot)
driver.ex_destroy_snapshot(node, snapshot)

# list running nodes
nodes = [n for n in driver.list_nodes() if n.state == NodeState.RUNNING]
# reboot node
driver.reboot_node(node)
# destroy the node
driver.destroy_node(node)
