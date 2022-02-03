from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.LUADNS)
driver = cls(user="user", key="api_key")
