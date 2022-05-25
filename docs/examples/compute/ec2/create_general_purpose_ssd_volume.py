from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EC2)
driver = cls("access key", "secret key", region="us-east-i1")

volume = driver.create_volume(size=100, name="Test GP volume", ex_volume_type="gp2")
