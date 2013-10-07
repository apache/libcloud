from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'
IAM_PROFILE = 'your IAM profile arn or IAM profile name'

IMAGE_ID = 'ami-c8052d8d'
SIZE_ID = 't1.micro'
cls = get_driver(Provider.EC2_US_WEST)
driver = cls(ACCESS_ID, SECRET_KEY)

# Here we select size and image
sizes = driver.list_sizes()
images = driver.list_images()

size = [s for s in sizes if s.id == SIZE_ID][0]
image = [i for i in images if i.id == IMAGE_ID][0]

node = driver.create_node(name='test-node', image=image, size=size,
                          ex_iamprofile=IAM_PROFILE)
