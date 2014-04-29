from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

import libcloud.security

# At the time this example was written, https://nova-api.trystack.org:5443
# was using a certificate issued by a Certificate Authority (CA) which is
# not included in the default Ubuntu certificates bundle (ca-certificates).
# Note: Code like this poses a security risk (MITM attack) and that's the
# reason why you should never use it for anything else besides testing. You
# have been warned.
libcloud.security.VERIFY_SSL_CERT = False

OpenStack = get_driver(Provider.OPENSTACK)

driver = OpenStack('your username', 'your password',
                   ex_force_auth_url='https://nova-api.trystack.org:5443',
                   ex_force_auth_version='2.0_password')

nodes = driver.list_nodes()

images = driver.list_images()
sizes = driver.list_sizes()
size = [s for s in sizes if s.ram == 512][0]
image = [i for i in images if i.name == 'natty-server-cloudimg-amd64'][0]

node = driver.create_node(name='test node', image=image, size=size)
