from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls("customer_id", "api_key", "api_secret")

record = driver.get_record("waffle-machines.com", "www:A")
record = driver.update_record(record=record, name="www", type=RecordType.A, data="50.63.202.22")
