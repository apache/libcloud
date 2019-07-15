from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeSize
from libcloud.compute.type import Provider

driver = get_driver(Provider.GRIDSCALE)

driver = driver('USER-UUID', 'API-TOKEN')

# We don't feature packages containing a fix size so you will have to
# built your own size object. Make sure to use a multiple of 1024MB when
# asigning RAM
name = 'my-node-size'
size = NodeSize(id=0, bandwidth=0, price=0, name=name, ram=10240,
                driver=driver, extra={'cores': 2})

ssh_key = driver.list_key_pairs()[0]
ssh_key_uuid = ssh_key.fingerprint
name = 'MyServer'
location = driver.list_locations()[0]
image = driver.list_images()[0]

node = driver.create_node(name, size, location, ex_ssh_key_ids=ssh_key)
