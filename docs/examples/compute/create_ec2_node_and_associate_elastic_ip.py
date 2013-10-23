from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

IMAGE_ID = 'ami-c8052d8d'
SIZE_ID = 't1.micro'

cls = get_driver(Provider.EC2_US_WEST)
driver = cls(ACCESS_ID, SECRET_KEY)

sizes = driver.list_sizes()
images = driver.list_images()

size = [s for s in sizes if s.id == SIZE_ID][0]
image = [i for i in images if i.id == IMAGE_ID][0]

node = driver.create_node(name='test-node', image=image, size=size)

# Here we allocate and associate an elastic IP
elastic_ip = driver.ex_allocate_address()
driver.ex_associate_address_with_node(node, elastic_ip)

# When we are done with our elastic IP, we can disassociate from our
# node, and release it
driver.ex_disassociate_address(elastic_ip)
driver.ex_release_address(elastic_ip)
