import os

from libcloud.compute.drivers.scaleway import ScalewayNodeDriver

driver = ScalewayNodeDriver(key=os.environ["SCW_ACCESS_KEY"], secret=os.environ["SCW_TOKEN"])

images = [
    x for x in driver.list_images(region="par1") if x.id == "89457135-d446-41ba-a8df-d53e5bb54710"
]
sizes = [x for x in driver.list_sizes() if x.name == "C2S"]

# We create the node
driver.create_node("foobar", size=sizes[0], image=images[0], region="par1")

# We delete it right after
driver.destroy_node("foobar")
