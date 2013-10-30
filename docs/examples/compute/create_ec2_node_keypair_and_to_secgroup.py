from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

SIZE_ID = 't1.micro'

# Name of the existing keypair you want to use
KEYPAIR_NAME = 'keypairname'

# A list of security groups you want this node to be added to
SECURITY_GROUP_NAMES = ['secgroup1', 'secgroup2']

cls = get_driver(Provider.EC2)
driver = cls(ACCESS_ID, SECRET_KEY)

sizes = driver.list_sizes()
images = driver.list_images()
size = [s for s in sizes if s.id == 't1.micro'][0]
image = images[0]

node = driver.create_node(name='test-node-1', image=image, size=size,
                          ex_keyname=KEYPAIR_NAME,
                          ex_securitygroup=SECURITY_GROUP_NAMES)
