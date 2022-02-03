from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")
