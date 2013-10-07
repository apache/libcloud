from libcloud.dns.providers import get_driver
from libcloud.dns.types import Provider

CREDENTIALS_ZERIGO = ('email', 'api key')
ZONE_ID = 'example.myzone.com'

Cls = get_driver(Provider.ZERIGO)
driver = Cls(*CREDENTIALS_ZERIGO)

zone = driver.get_zone(zone_id=ZONE_ID)
print(zone.export_to_bind_format())
