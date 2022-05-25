from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.OUTSCALE)
driver = cls(key="my_key", secret="my_secret", region="my_region", service="my_service")
