from pprint import pprint

from libcloud.compute.types import Provider as compute_provider
from libcloud.compute.providers import get_driver \
    as compute_get_driver

from libcloud.autoscale.types import Provider, AutoScaleAdjustmentType,\
    AutoScaleMetric, AutoScaleOperator, AutoScaleTerminationPolicy
from libcloud.autoscale.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

IMAGE_ID = 'ami-1ecae776'
SIZE_ID = 't2.small'

ec2_driver = compute_get_driver(compute_provider.EC2)(ACCESS_ID, SECRET_KEY)

as_driver = get_driver(Provider.AWS_AUTOSCALE)(ACCESS_ID, SECRET_KEY)

cw_driver = get_driver(Provider.AWS_CLOUDWATCH)(ACCESS_ID, SECRET_KEY)

# Get image and size for autoscale member template
images = ec2_driver.list_images()
image = [i for i in images if i.id == IMAGE_ID][0]

sizes = ec2_driver.list_sizes()
size = [s for s in sizes if s.id == SIZE_ID][0]

location = ec2_driver.list_locations()[0]
group = as_driver.create_auto_scale_group(
    group_name='libcloud-group', min_size=2, max_size=5,
    cooldown=300,
    termination_policies=[AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE],
    name='inst-name', image=image, size=size, location=location)

pprint(group)
# create scale up policy
policy_scale_up = as_driver.create_auto_scale_policy(
    group=group, name='policy-scale-up',
    adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
    scaling_adjustment=1)

pprint(policy_scale_up)

# and associate it with cpu>80 alarm
alarm_high_cpu = cw_driver.create_auto_scale_alarm(
    name='cpu-high', policy=policy_scale_up,
    metric_name=AutoScaleMetric.CPU_UTIL,
    operator=AutoScaleOperator.GT, threshold=80,
    period=120)

pprint(alarm_high_cpu)

# create scale down policy
policy_scale_down = as_driver.create_auto_scale_policy(
    group=group, name='policy-scale-down',
    adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
    scaling_adjustment=-1)

pprint(policy_scale_down)

# associate policy with a cpu<30 alarm
alarm_low_cpu = cw_driver.create_auto_scale_alarm(
    name='cpu-low', policy=policy_scale_down,
    metric_name=AutoScaleMetric.CPU_UTIL,
    operator=AutoScaleOperator.LT, threshold=30,
    period=120)

pprint(alarm_low_cpu)

import time
time.sleep(60)

nodes = as_driver.list_auto_scale_group_members(group=group)
pprint(nodes)

# delete group completely with all of its resources
# (members, policies, alarms)
as_driver.delete_auto_scale_group(group=group)
