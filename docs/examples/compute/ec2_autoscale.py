from pprint import pprint

from libcloud.compute.types import Provider, AutoScaleAdjustmentType,\
    AutoScaleMetric, AutoScaleOperator, AutoScaleTerminationPolicy
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

IMAGE_ID = 'ami-5c120b19'
SIZE_ID = 't2.small'

cls = get_driver(Provider.EC2_US_WEST)
driver = cls(ACCESS_ID, SECRET_KEY)

as_cls = get_driver(Provider.AWS_AUTOSCALE_US_WEST)
as_driver = as_cls(ACCESS_ID, SECRET_KEY)

cw_cls = get_driver(Provider.AWS_CLOUDWATCH_US_WEST)
cw_driver = cw_cls(ACCESS_ID, SECRET_KEY)

# Here we select image
images = driver.list_images()
image = [i for i in images if i.id == IMAGE_ID][0]

sizes = driver.list_sizes()
size = [s for s in sizes if s.id == SIZE_ID][0]

location = driver.list_locations()[1]
group = as_driver.create_auto_scale_group(
    name='libcloud-group', min_size=2, max_size=5, cooldown=300,
    termination_policies=[AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE],
    image=image, size=size, location=location, ex_instance_name='test-node')

pprint(group)

policy = as_driver.create_auto_scale_policy(
    group=group, name='libcloud-policy',
    adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
    scaling_adjustment=1)

pprint(policy)

alarm = cw_driver.create_auto_scale_alarm(name='libcloud-alarm',
                                          policy=policy,
                                          metric_name=AutoScaleMetric.CPU_UTIL,
                                          operator=AutoScaleOperator.GT,
                                          threshold=80,
                                          period=120)
pprint(alarm)

import time
time.sleep(60)

nodes = as_driver.list_auto_scale_group_members(group=group)
pprint(nodes)

as_driver.delete_auto_scale_group(group=group)
