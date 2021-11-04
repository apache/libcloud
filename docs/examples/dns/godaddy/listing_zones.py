from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")

zones = driver.list_zones()
for zone in zones:
    print("Domain : {}".format(zone.domain))
    print("Expires: {}".format(zone.extra["expires"]))
