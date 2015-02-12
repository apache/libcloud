from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


OpenStack = get_driver(Provider.OPENSTACK)
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_tenant_name='mytenant',
                   ex_force_auth_url='http://192.168.1.101:5000',
                   ex_force_auth_version='2.0_password')
