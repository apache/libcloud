from libcloud.dns.types import Provider, RecordType
from libcloud.dns.providers import get_driver
from libcloud.dns.drivers.auroradns import AuroraDNSHealthCheckType

cls = get_driver(Provider.AURORADNS)

driver = cls("myapikey", "mysecret")

zone = driver.get_zone("auroradns.eu")

health_check = driver.ex_create_healthcheck(
    zone=zone,
    type=AuroraDNSHealthCheckType.HTTP,
    hostname="web01.auroradns.eu",
    path="/",
    port=80,
    interval=10,
    threshold=5,
)

record = zone.create_record(
    name="www",
    type=RecordType.AAAA,
    data="2a00:f10:452::1",
    extra={"health_check_id": health_check.id},
)
