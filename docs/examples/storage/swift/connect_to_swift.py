from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

cls = get_driver(Provider.OPENSTACK_SWIFT)

driver = cls('username', 'api key',
             region='ord',
             ex_force_auth_url='http://192.168.1.101:5000',
             ex_force_service_type='object-store',
             ex_force_service_name='Object Storage Service')

print(driver.list_containers())
