from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.DNSIMPLE)

driver = cls("username", "apikey")
