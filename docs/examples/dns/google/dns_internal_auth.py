from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

# This example assumes you are running an instance within Google Compute Engine
# in which case you only need to provide the project ID.
DNSDriver = get_driver(Provider.GOOGLE)
driver = DNSDriver("", "", project="project ID")
