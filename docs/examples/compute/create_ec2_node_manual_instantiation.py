from libcloud.compute.base import NodeSize, NodeImage
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = "your access id"
SECRET_KEY = "your secret key"

IMAGE_ID = "ami-c8052d8d"
SIZE_ID = "t1.micro"

cls = get_driver(Provider.EC2)
driver = cls(ACCESS_ID, SECRET_KEY, region="us-west-1")

size = NodeSize(
    id=SIZE_ID,
    name=None,
    ram=None,
    disk=None,
    bandwidth=None,
    price=None,
    driver=driver,
)
image = NodeImage(id=IMAGE_ID, name=None, driver=driver)

node = driver.create_node(name="test-node", image=image, size=size)
