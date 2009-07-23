from libcloud.providers import connect
from libcloud.types import Provider

conn = connect(Provider.EC2, 'access key id', 'secret key')
print conn.list_nodes()
conn = connect(Provider.DUMMY, 'blah')
print conn.list_nodes()
