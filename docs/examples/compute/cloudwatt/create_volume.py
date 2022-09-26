from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Cloudwatt = get_driver(Provider.CLOUDWATT)
driver = Cloudwatt("your_email", "your_password", "your_tenant_id", tenant_name="your_tenant_name")
node = driver.list_nodes()[0]
volume = driver.create_volume(10, "your_volume")
driver.attach_volume(node, volume)
