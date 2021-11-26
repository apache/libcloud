from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = "your access id"
SECRET_KEY = "your secret key"
HOST = "hostname or ip address of your management server"
PATH = "path to the api endpoint, e.g: /client/api"

SIZE_ID = "id of the computer offering you want to use"
IMAGE_ID = "id of the template you want to use"

# Name of the existing keypair you want to use
KEYPAIR_NAME = "keypairname"

# The security groups you want this node to be added to
SECURITY_GROUP_NAMES = ["secgroup1", "secgroup2"]

cls = get_driver(Provider.CLOUDSTACK)
driver = cls(key=ACCESS_ID, secret=SECRET_KEY, secure=True, host=HOST, path=PATH)

sizes = driver.list_sizes()
images = driver.list_images()
size = [s for s in sizes if s.id == SIZE_ID][0]
image = [i for i in images if i.id == IMAGE_ID][0]

node = driver.create_node(
    name="test-node-1",
    image=image,
    size=size,
    ex_security_groups=SECURITY_GROUP_NAMES,
    ex_keyname=KEYPAIR_NAME,
)
