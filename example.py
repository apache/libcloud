from libcloud.drivers import EC2, Slicehost, Rackspace

ec2 = EC2('access key id', 'secret key')
slicehost = Slicehost('api key')
rackspace = Rackspace('username', 'api key')

all_nodes = []
for provider in [ ec2, slicehost, rackspace ]:
  all_nodes.extend(provider.node.list())

print all_nodes
"""
[ <Node: provider=Amazon, status=RUNNING, name=bob, ip=1.2.3.4.5>,
<Node: provider=Slicehost, status=REBOOT, name=korine, ip=6.7.8.9.10>, ... ]
"""

node = all_nodes[0]
print node.destroy()
# <Node: provider=Amazon, status=TERMINATED, name=bob, ip=1.2.3.4.5>,

print slicehost.node.create(from=node)
# <Node: provider=Slicehost, status=PENDING, name=bob, ip=None>,
