from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.NFSN)
driver = cls("<account name>", "<api key>")
