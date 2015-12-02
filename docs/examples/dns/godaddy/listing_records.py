from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.GODADDY)
driver = cls('customer_id', 'api_key', 'api_secret')

zone = driver.get_zone('wazzle-flooble.com')
records = driver.list_records(zone)
for record in records:
    print("Type : %s" % record.type)
    print("Data: %s" % record.data)
    print("TTL: %s" % record.ttl)
