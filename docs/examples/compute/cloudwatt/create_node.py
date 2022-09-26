from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Cloudwatt = get_driver(Provider.CLOUDWATT)
driver = Cloudwatt("your_email", "your_password", "your_tenant_id", tenant_name="your_tenant_name")
image = [i for i in driver.list_images() if i.name == "Debian Wheezy"][0]
size = [s for s in driver.list_sizes() if s.name == "n1.cw.standard-1"][0]
node = driver.create_node(name="yournode", size=size, image=image)
