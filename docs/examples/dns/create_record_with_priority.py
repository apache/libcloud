from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver

CREDENTIALS_CLOUDFLARE = ("api token",)

cls = get_driver(Provider.CLOUDFLARE)
driver = cls(*CREDENTIALS_CLOUDFLARE)

zone = [z for z in driver.list_zones() if z.domain == "example.com"][0]

extra = {"priority": 10}
record = zone.create_record(name=None, type=RecordType.MX, data="aspmx.l.google.com", extra=extra)
