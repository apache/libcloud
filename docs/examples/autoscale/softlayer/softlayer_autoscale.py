from pprint import pprint

from libcloud.compute.types import Provider as compute_provider
from libcloud.compute.providers import get_driver \
    as compute_get_driver

from libcloud.autoscale.types import Provider, AutoScaleAdjustmentType,\
    AutoScaleMetric, AutoScaleOperator, AutoScaleTerminationPolicy
from libcloud.autoscale.providers import get_driver

USER_NAME = 'your access id'
SECRET_KEY = 'your secret key'

sl_driver = compute_get_driver(compute_provider.SOFTLAYER)(
    USER_NAME, SECRET_KEY)

as_driver = get_driver(Provider.SOFTLAYER)(USER_NAME, SECRET_KEY)

image = sl_driver.list_images()[0]
size = sl_driver.list_sizes()[0]

# Dallas 5 datacenter
location = sl_driver.list_locations()[4]

group = as_driver.create_auto_scale_group(
    name='libcloud-group', min_size=2, max_size=5,
    cooldown=300,
    termination_policies=[AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE],
    image=image, size=size, location=location,
    ex_region='na-usa-central-1')

pprint(group)
# create scale up policy
policy_scale_up = as_driver.create_auto_scale_policy(
    group=group, name='policy-scale-up',
    adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
    scaling_adjustment=1)

pprint(policy_scale_up)

# and associate it with cpu>80 alarm
alarm_high_cpu = as_driver.create_auto_scale_alarm(
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
alarm_low_cpu = as_driver.create_auto_scale_alarm(
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
