from libcloud.compute.base import NodeImage, NodeSize
from libcloud.compute.types import Provider, AutoScaleTerminationPolicy
from libcloud.compute.providers import get_driver

from libcloud.loadbalancer.base import Algorithm
from libcloud.loadbalancer.types import Provider as lb_provider
from libcloud.loadbalancer.providers import get_driver as lb_get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

IMAGE_ID = 'ami-5c120b19'
SIZE_ID = 't2.small'

REGION = 'us-west-1'

# auto scale driver
cls = get_driver(Provider.AWS_AUTOSCALE_US_WEST)
as_driver = cls(ACCESS_ID, SECRET_KEY)

# loadbalancer driver
lb_cls = lb_get_driver(lb_provider.ELB)
lb_driver = lb_cls(ACCESS_ID, SECRET_KEY, REGION)

# image for the auto scale members
image = NodeImage(IMAGE_ID, None, None)

size = NodeSize(SIZE_ID, 'Small Instance', None, None, None, None,
                None)

# create a balancer
balancer = lb_driver.create_balancer(
    name='MyLB',
    algorithm=Algorithm.ROUND_ROBIN,
    port=80,
    protocol='http',
    members=[])

print(balancer)

# create scale group with balancer (group and balancer are
# in same availability zone)
group = as_driver.create_auto_scale_group(
    name='libcloud-balancer-group', min_size=2, max_size=5,
    cooldown=300,
    termination_policies=[AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE],
    balancer=balancer, image=image,
    size=size,
    ex_instance_name='test-node')

print(group)

import time
time.sleep(120)

nodes = as_driver.list_auto_scale_group_members(group=group)
print(nodes)

as_driver.delete_auto_scale_group(group=group)
balancer.destroy()
