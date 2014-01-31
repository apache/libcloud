from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

HPCLOUD_AUTH_URL = \
    'https://region-a.geo-1.identity.hpcloudsvc.com:35357/v2.0/tokens'
OpenStack = get_driver(Provider.OPENSTACK)

#HP Cloud US West AZ 1
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_version='2.0_password',
                   ex_force_auth_url=HPCLOUD_AUTH_URL,
                   ex_tenant_name='your_tenant_name',
                   ex_force_service_region='az-1.region-a.geo-1',
                   ex_force_service_name='Compute')

#HP Cloud US West AZ 2
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_version='2.0_password',
                   ex_force_auth_url=HPCLOUD_AUTH_URL,
                   ex_tenant_name='your_tenant_name',
                   ex_force_service_region='az-2.region-a.geo-1',
                   ex_force_service_name='Compute')


#HP Cloud US West AZ 3
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_version='2.0_password',
                   ex_force_auth_url=HPCLOUD_AUTH_URL,
                   ex_tenant_name='your_tenant_name',
                   ex_force_service_region='az-3.region-a.geo-1',
                   ex_force_service_name='Compute')


#HP Cloud US East
driver = OpenStack('your_auth_username', 'your_auth_password',
                   ex_force_auth_version='2.0_password',
                   ex_force_auth_url=HPCLOUD_AUTH_URL,
                   ex_tenant_name='your_tenant_name',
                   ex_force_service_region='region-b.geo-1',
                   ex_force_service_name='Compute')
