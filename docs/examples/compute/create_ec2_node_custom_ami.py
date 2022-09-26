from libcloud.compute.base import NodeImage
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = "your access id"
SECRET_KEY = "your secret key"

# Image with Netflix Asgard available in us-west-1 region
# https://github.com/Answers4AWS/netflixoss-ansible/wiki/AMIs-for-NetflixOSS
AMI_ID = "ami-c8052d8d"

SIZE_ID = "t1.micro"

# 'us-west-1' region is available in Libcloud under EC2_US_WEST provider
# constant
cls = get_driver(Provider.EC2)
driver = cls(ACCESS_ID, SECRET_KEY, region="us-west-1")

# Here we select
sizes = driver.list_sizes()
size = [s for s in sizes if s.id == "t1.micro"][0]
image = NodeImage(id=AMI_ID, name=None, driver=driver)

node = driver.create_node(name="test-node", image=image, size=size)
