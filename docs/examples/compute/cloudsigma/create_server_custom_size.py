from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.drivers.cloudsigma import CloudSigmaNodeSize

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

name = "test node custom size"
image = driver.list_images()[0]

# Custom node size with 56 GB of ram, 5000 MHz CPU and 200 GB SSD drive
size = CloudSigmaNodeSize(
    id=1,
    name="my size",
    cpu=5000,
    ram=5600,
    disk=200,
    bandwidth=None,
    price=0,
    driver=driver,
)
node = driver.create_node(name=name, size=size, image=image)
print(node)
