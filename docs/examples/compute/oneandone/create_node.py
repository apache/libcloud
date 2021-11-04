import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

# First we need to get all avaliable sizes
sizes = drv.list_sizes()

# Then we select one we want to use to create a node. We pick 'S' as small.
desired_size = [size for size in sizes if size.name == "S"]

# Let's get all available images
images = drv.list_images("IMAGE")

# Now we select an image we want to install on to the node.
# We pick Ubuntu 14.04
desired_image = [img for img in images if "ubuntu1404-64min" in img.name.lower()]

# This step is optional.
# Then we get the list of available datacenters (locations)
locations = drv.list_locations()

# And we pick one in this case Spain (ES)
desired_location = [loc for loc in locations if loc.name == "ES"]

# Now let's create that node:
node = drv.create_node(
    name="Libcloud Test Node2",
    image=desired_image[0],
    ex_fixed_instance_size_id=desired_size[0].id,
    location=desired_location[0],
)

print(node)
