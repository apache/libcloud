from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EC2)
driver = cls("access key", "secret key", region="us-east-i1")

volume = driver.create_volume(size=100, name="Test IOPS volume", ex_volume_type="io1", ex_iops=1000)
