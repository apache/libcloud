from libcloud.dns.base import Zone
from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

CREDENTIALS_CLOUDFLARE = ("api token",)
ZONE_ID = "your Cloudflare zone ID"
ZONE_NAME = "example.myzone.com"

Cls = get_driver(Provider.CLOUDFLARE)
driver = Cls(*CREDENTIALS_CLOUDFLARE)

zone = Zone(ZONE_ID, domain=ZONE_NAME, type="master", ttl=3600, driver=driver)
records = driver.list_records(zone=zone)
