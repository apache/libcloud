from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

USERNAME = "your account username"
PASSWORD = "your account password"
TENANT_NAME = "project name"

cls = get_driver(Provider.KILI)
driver = cls(USERNAME, PASSWORD, tenant_name=TENANT_NAME)
print(driver.list_nodes())
