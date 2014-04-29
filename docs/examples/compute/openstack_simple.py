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
                   ex_force_auth_url='http://192.168.1.101:5000',
                   ex_force_auth_version='2.0_password')
