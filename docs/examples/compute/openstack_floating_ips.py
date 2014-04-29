from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

import libcloud.security

# This assumes you don't have SSL set up.
# Note: Code like this poses a security risk (MITM attack) and
# that's the reason why you should never use it for anything else
# besides testing. You have been warned.
libcloud.security.VERIFY_SSL_CERT = False

OpenStack = get_driver(Provider.OPENSTACK)
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_url='http://10.0.4.1:5000',
                   ex_force_auth_version='2.0_password',
                   ex_tenant_name='your_tenant')

# get the first pool - public by default
pool = driver.ex_list_floating_ip_pools()[0]

# create an ip in the pool
floating_ip = pool.create_floating_ip()

# get the node, note: change the node id to the some id you have
node = driver.ex_get_node_details('922a4381-a18c-487f-b816-cc31c9060853')

# attach the ip to the node
driver.ex_attach_floating_ip_to_node(node, floating_ip)

# remove it from the node
driver.ex_detach_floating_ip_from_node(node, floating_ip)

# delete the ip
floating_ip.delete()
