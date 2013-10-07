from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2_ACCESS_ID = 'your access id'
EC2_SECRET_KEY = 'your secret key'

cls = get_driver(Provider.EC2)
driver = cls(EC2_ACCESS_ID, EC2_SECRET_KEY)
sizes = driver.list_sizes()

# >>> sizes[:2]
# [<NodeSize: id=t1.micro, name=Micro Instance, ram=613 disk=15 bandwidth=None
#   price=0.02 driver=Amazon EC2 ...>,
# <NodeSize: id=m1.small, name=Small Instance, ram=1740 disk=160 bandwidth=None
#  price=0.065 driver=Amazon EC2 ...>,
# >>> sizes[0].price
# 0.02
# >>>
