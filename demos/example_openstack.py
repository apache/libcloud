from pprint import pprint

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

Openstack = get_driver(Provider.OPENSTACK)

con = Openstack(
    'admin', 'password',
    ex_force_auth_url='http://23.12.198.36/identity/v3/auth/tokens',
    ex_force_base_url='http://23.12.198.36:8774/v2.1',
    api_version='2.0',
    ex_tenant_name='demo')

pprint(con.list_locations())
pprint(con.list_images())
pprint(con.list_nodes())
