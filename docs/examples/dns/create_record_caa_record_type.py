from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver

CREDENTIALS = ("email", "api key")

cls = get_driver(Provider.CLOUDFLARE)
driver = cls(*CREDENTIALS)

zone = [z for z in driver.list_zones() if z.domain == "example.com"][0]

# 1. issue tag
print(zone.create_record(name="www", type=RecordType.CAA, data="0 issue caa.domain.com"))

# 2. issuewild tag
print(zone.create_record(name="www", type=RecordType.CAA, data="0 issuewild caa.domain.com"))

# 3. iodef tag
print(zone.create_record(name="www", type=RecordType.CAA, data="0 iodef caa.domain.com/report"))
