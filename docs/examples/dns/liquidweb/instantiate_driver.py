from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.LIQUIDWEB)
driver = cls(user_id="user", key="api_key")
