from pprint import pprint

from libcloud.compute.providers import get_driver as get_compute_driver
from libcloud.compute.types import Provider as ComputeProvider
from libcloud.dns.providers import get_driver as get_dns_driver
from libcloud.dns.types import Provider as DNSProvider, RecordType

CREDENTIALS_RACKSPACE = ('username', 'api key')
CREDENTIALS_ZERIGO = ('email', 'api key')

Cls = get_compute_driver(ComputeProvider.RACKSPACE)
compute_driver = Cls(*CREDENTIALS_RACKSPACE)

Cls = get_dns_driver(DNSProvider.ZERIGO)
dns_driver = Cls(*CREDENTIALS_ZERIGO)

# Retrieve all the nodes
nodes = compute_driver.list_nodes()

# Create a new zone
zone = dns_driver.create_zone(domain='mydomain2.com')

created = []
for node in nodes:
    name = node.name

    ips = node.public_ip

    if not ips:
        continue

    ip = ips[0]

    print 'Creating %s record (data=%s) for node %s' % ('A', ip, name)
    record = zone.create_record(name=name, type=RecordType.A, data=ip)
    created.append(record)

print 'Done, created %d records' % (len(created))
pprint(created)
