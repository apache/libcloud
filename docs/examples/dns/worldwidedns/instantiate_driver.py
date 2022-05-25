from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.WORLDWIDEDNS)

# Normal account
driver = cls("username", "apikey")

# Reseller account
driver = cls("username", "apikey", reseller_id="reseller_id")
