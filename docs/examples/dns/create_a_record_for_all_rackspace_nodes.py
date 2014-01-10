from pprint import pprint

from libcloud.compute.providers import get_driver as get_compute_driver
from libcloud.compute.types import Provider as ComputeProvider
from libcloud.dns.providers import get_driver as get_dns_driver
from libcloud.dns.types import Provider as DNSProvider
from libcloud.dns.types import RecordType

CREDENTIALS_RACKSPACE = ('username', 'api key')
CREDENTIALS_ZERIGO = ('email', 'api key')

cls = get_compute_driver(ComputeProvider.RACKSPACE)
compute_driver = cls(*CREDENTIALS_RACKSPACE)

cls = get_dns_driver(DNSProvider.ZERIGO)
dns_driver = cls(*CREDENTIALS_ZERIGO)

# Retrieve all the nodes
nodes = compute_driver.list_nodes()

# Create a new zone
zone = dns_driver.create_zone(domain='mydomain2.com')

created = []

for node in nodes:
    name = node.name

    ip = node.public_ips[0] if node.public_ips else None

    if not ip:
        continue

    print('Creating %s record (data=%s) for node %s' % ('A', ip, name))
    record = zone.create_record(name=name, type=RecordType.A, data=ip)
    created.append(record)

print 'Done, created %d records' % (len(created))
pprint(created)
