from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

DNSDriver = get_driver(Provider.GOOGLE)
driver = DNSDriver("client ID", "client secret", project="project ID")
