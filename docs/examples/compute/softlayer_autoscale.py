from pprint import pprint

from libcloud.compute.types import Provider, AutoScaleAdjustmentType,\
    AutoScaleMetric, AutoScaleOperator, AutoScaleTerminationPolicy
from libcloud.compute.providers import get_driver

USER_NAME = 'your user name'
SECRET_KEY = 'your secret key'

cls = get_driver(Provider.SOFTLAYER)
driver = cls(USER_NAME, SECRET_KEY)

size = driver.list_sizes()[0]

# Dallas 5 datacenter
location = driver.list_locations()[4]

# Use default image (e.g. DEBIAN_LATEST)
group = driver.create_auto_scale_group(
    name='libcloud-group', min_size=1, max_size=5, cooldown=300,
    termination_policies=AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE,
    size=size, location=location, ex_region='na-usa-central-1')
pprint(group)

policy = driver.create_auto_scale_policy(
    group=group, name='libcloud-policy',
    adjustment_type=AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
    scaling_adjustment=1)

pprint(policy)

alarm = driver.create_auto_scale_alarm(name='libcloud-alarm',
                                       policy=policy,
                                       metric_name=AutoScaleMetric.CPU_UTIL,
                                       operator=AutoScaleOperator.GT,
                                       threshold=80,
                                       period=120)
pprint(alarm)

import time
time.sleep(60)

nodes = driver.list_auto_scale_group_members(group=group)
pprint(nodes)

driver.delete_auto_scale_group(group=group)
