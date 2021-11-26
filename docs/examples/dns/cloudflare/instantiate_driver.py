from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.CLOUDFLARE)
driver = cls("<email address>", "<api key>")
