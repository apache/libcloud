from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = "mykey"
secretkey = "mysecret"

Driver = get_driver(Provider.AURORACOMPUTE)
driver = Driver(key=apikey, secret=secretkey)

images = driver.list_images()
sizes = driver.list_sizes()

# Find a Agile Offering with 2GB of Memory
size = [s for s in sizes if s.ram == 2048 and s.name.startswith("Agile")][0]

# Search for the Ubuntu 16.04 image
image = [i for i in images if i.name == "Ubuntu 16.04"][0]

# Create the new Virtual Machine
node = driver.create_node(image=image, size=size)

print(node)
