from libcloud.providers import connect
from libcloud.types import Provider

ec2 = connect(Provider.EC2, 'access key id', 'secret key')
slicehost = connect(Provider.SLICEHOST, 'api key')
rackspace = connect(Provider.RACKSPACE, 'username', 'api key')

all_servers = []
for provider in [ ec2, slicehost, rackspace ]:
    all_servers.extend(provider.list_nodes())

# all_servers now has a list of node objects 
# from ec2, slicehost, and rackspace
print all_servers
