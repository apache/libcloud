from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

CREDENTIALS_CLOUDFLARE = ("api token",)
ZONE_NAME = "example.myzone.com"

Cls = get_driver(Provider.CLOUDFLARE)
driver = Cls(*CREDENTIALS_CLOUDFLARE)

zone = [zone for zone in driver.list_zones() if zone.domain == ZONE_NAME][0]
records = driver.list_records(zone=zone)
