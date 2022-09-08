from libcloud.dns.base import Zone
from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

CREDENTIALS_ZERIGO = ("email", "api key")
ZONE_ID = "example.myzone.com"

Cls = get_driver(Provider.ZERIGO)
driver = Cls(*CREDENTIALS_ZERIGO)

zone = Zone(ZONE_ID, domain=None, type=None, ttl=None, driver=driver)
records = driver.list_records(zone=zone)
