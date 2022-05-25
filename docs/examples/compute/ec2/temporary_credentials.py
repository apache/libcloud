from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EC2)
driver = cls(
    "temporary access key",
    "temporary secret key",
    token="temporary session token",
    region="us-west-1",
)
