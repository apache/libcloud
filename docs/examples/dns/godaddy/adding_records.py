from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")
zone = driver.get_zone("waffle-machines.com")
record = zone.create_record(name="www", type=RecordType.A, data="127.0.0.1", ttl=5)
