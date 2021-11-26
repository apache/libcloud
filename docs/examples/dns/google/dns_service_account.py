from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

DNSDriver = get_driver(Provider.GOOGLE)
driver = DNSDriver("service account email", "keyfile location", project="project ID")
