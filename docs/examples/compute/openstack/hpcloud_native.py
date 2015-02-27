from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


USERNAME = 'your account username'
PASSWORD = 'your account password'
TENANT_NAME = 'project name'
REGION = 'region-b.geo-1'

cls = get_driver(Provider.HPCLOUD)
driver = cls(USERNAME, PASSWORD, tenant_name=TENANT_NAME,
             region=REGION)
print(driver.list_nodes())
