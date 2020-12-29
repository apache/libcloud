from libcloud.dns.providers import get_driver
from libcloud.dns.types import Provider, RecordType

CREDENTIALS_ZERIGO = ('email', 'api key')

cls = get_driver(Provider.ZERIGO)
driver = cls(*CREDENTIALS_ZERIGO)

zone = [z for z in driver.list_zones() if z.domain == 'example.com'][0]

extra = {'ttl': 900}
record = zone.create_record(name='www', type=RecordType.A, data='127.0.0.1',
                            extra=extra)
