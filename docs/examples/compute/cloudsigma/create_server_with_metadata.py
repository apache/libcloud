from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls('username', 'password', region='zrh', api_version='2.0')

name = 'test node sizeth metadata'
size = driver.list_sizes()[0]
image = driver.list_images()[0]

metadata = {'ssh_public_key': 'my public key', 'role': 'database server',
            'region': 'zrh'}

node = driver.create_node(name=name, size=size, image=image,
                          ex_metadata=metadata)
print(node)
