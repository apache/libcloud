# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeAuthPassword

ECSDriver = get_driver(Provider.ALIYUN_ECS)

region = 'cn-hangzhou'

your_access_key_id = ''
your_access_key_secret = ''
ecs = ECSDriver(your_access_key_id, your_access_key_secret, region=region)

sizes = ecs.list_sizes()
small = sizes[1]

locations = ecs.list_locations()
location = None
for each in locations:
    if each.id == region:
        location = each
        break
if location is None:
    print('could not find cn-qingdao location')
    sys.exit(-1)
print(location.name)

images = ecs.list_images()
print('Found %d images' % len(images))
for each in images:
    if 'ubuntu' in each.id.lower():
        image = each
        break
else:
    image = images[0]
print('Use image %s' % image)

sgs = ecs.ex_list_security_groups()
print('Found %d security groups' % len(sgs))
if len(sgs) == 0:
    sg = ecs.ex_create_security_group(description='test')
    print('Create security group %s' % sg)
else:
    sg = sgs[0].id
    print('Use security group %s' % sg)

nodes = ecs.list_nodes()
print('Found %d nodes' % len(nodes))
if len(nodes) == 0:
    print('Starting create a new node')
    data_disk = {
        'size': 5,
        'category': ecs.disk_categories.CLOUD,
        'disk_name': 'data_disk1',
        'delete_with_instance': True}

    auth = NodeAuthPassword('P@$$w0rd')

    ex_internet_charge_type = ecs.internet_charge_types.BY_TRAFFIC
    node = ecs.create_node(image=image, size=small, name='test',
                           ex_security_group_id=sg,
                           ex_internet_charge_type=ex_internet_charge_type,
                           ex_internet_max_bandwidth_out=1,
                           ex_data_disk=data_disk,
                           auth=auth)
    print('Created node %s' % node)
    nodes = ecs.list_nodes()

for each in nodes:
    print('Found node %s' % each)
