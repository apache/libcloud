from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

servers_groups = driver.ex_list_servers_availability_groups()
drives_groups = driver.ex_list_drives_availability_groups()

print(servers_groups)
print(drives_groups)
