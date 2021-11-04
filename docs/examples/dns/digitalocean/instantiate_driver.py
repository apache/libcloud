from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.DIGITAL_OCEAN)
driver = cls(key="access token")
