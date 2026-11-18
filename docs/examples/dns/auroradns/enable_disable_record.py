from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.AURORADNS)

driver = cls("myapikey", "mysecret")

zone = driver.get_zone("auroradns.eu")

record = zone.create_record(
    name="www", type=RecordType.AAAA, data="2a00:f10:452::1", ex_disabled=True
)
record.update(ex_disabled=False)
