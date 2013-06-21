#!/usr/bin/env python
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


# This example performs several tasks on Google Compute Engine.  It should be
# run directly. This can also serve as an integration test for the GCE
# Node Driver.

import os.path
import sys

try:
    import secrets
except ImportError:
    secrets = None

# Add parent dir of this file's dir to sys.path (OS-agnostically)
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__),
                                 os.path.pardir)))

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# Maximum number of 1-CPU nodes to allow to run simultaneously
MAX_NODES = 5

# String that all resource names created by the demo will start with
# WARNING: Any resource that has a matching name will be destroyed.
DEMO_BASE_NAME = 'libcloud-demo'

# Datacenter to create resources in
DATACENTER = 'us-central1-a'

# Clean up resources at the end (can be set to false in order to
# inspect resources at the end of the run). Resources will be cleaned
# at the beginning regardless.
CLEANUP = True

args = getattr(secrets, 'GCE_PARAMS', ())
kwargs = getattr(secrets, 'GCE_KEYWORD_PARAMS', {})

gce = get_driver(Provider.GCE)(*args,
                               datacenter=DATACENTER,
                               **kwargs)


# ==== HELPER FUNCTIONS ====
def display(title, resource_list):
    """
    Display a list of resources.

    @param  title: String to be printed at the heading of the list.
    @type   title: C{str}

    @param  resource_list: List of resources to display
    @type   resource_list: Any C{object} with a C{name} attribute
    """
    print('%s:' % title)
    for item in resource_list[:10]:
        print('   %s' % item.name)


def clean_up(base_name, node_list=None, resource_list=None):
    """
    Destroy all resources that have a name beginning with 'base_name'.

    @param  base_name: String with the first part of the name of resources
                       to destroy
    @type   base_name: C{str}

    @keyword  node_list: List of nodes to consider for deletion
    @type     node_list: C{list} of L{Node}

    @keyword  resource_list: List of resources to consider for deletion
    @type     resource_list: C{list} of I{Resource Objects}
    """
    if node_list is None:
        node_list = []
    if resource_list is None:
        resource_list = []
    # Use ex_destroy_multiple_nodes to destroy nodes
    del_nodes = []
    for node in node_list:
        if node.name.startswith(base_name):
            del_nodes.append(node)

    result = gce.ex_destroy_multiple_nodes(del_nodes)
    for i, success in enumerate(result):
        if success:
            print('   Deleted %s' % del_nodes[i].name)
        else:
            print('   Failed to delete %s' % del_nodes[i].name)

    # Destroy everything else with just the destroy method
    for resource in resource_list:
        if resource.name.startswith(base_name):
            if resource.destroy():
                print('   Deleted %s' % resource.name)
            else:
                print('   Failed to Delete %s' % resource.name)

# ==== DEMO CODE STARTS HERE ====

# Get project info and print name
project = gce.ex_get_project()
print('Project: %s' % project.name)

# == Get Lists of Everything and Display the lists (up to 10) ==
# These can either just return values for the current datacenter (zone)
# or for everything.
all_nodes = gce.list_nodes(ex_zone='all')
display('Nodes', all_nodes)

all_addresses = gce.ex_list_addresses(region='all')
display('Addresses', all_addresses)

all_volumes = gce.ex_list_volumes(ex_zone='all')
display('Volumes', all_volumes)

# This can return everything, but there is a large amount of overlap,
# so we'll just get the sizes from the current zone.
sizes = gce.list_sizes()
display('Sizes', sizes)

# These are global
firewalls = gce.ex_list_firewalls()
display('Firewalls', firewalls)

networks = gce.ex_list_networks()
display('Networks', networks)

images = gce.list_images()
display('Images', images)

locations = gce.list_locations()
display('Locations', locations)

zones = gce.ex_list_zones()
display('Zones', zones)

# == Clean up any old demo resources ==
print('Cleaning up any "%s" resources:' % DEMO_BASE_NAME)
clean_up(DEMO_BASE_NAME, all_nodes,
         all_addresses + all_volumes + firewalls + networks)

# == Create Node with non-persistent disk ==
if MAX_NODES > 1:
    print('Creating Node with non-persistent disk:')
    name = '%s-np-node' % DEMO_BASE_NAME
    node_1 = gce.create_node(name, 'n1-standard-1', 'debian-7',
                             ex_tags=['libcloud'])
    print('   Node %s created' % name)

# == Create Node with persistent disk ==
print('Creating Node with Persistent disk:')
name = '%s-persist-node' % DEMO_BASE_NAME
# Use objects this time instead of names
# Get latest Debian 7 image
image = gce.ex_get_image('debian-7')
# Get Machine Size
size = gce.ex_get_size('n1-standard-1')
# Create Disk.  Size is None to just take default of image
volume_name = '%s-boot-disk' % DEMO_BASE_NAME
volume = gce.create_volume(None, volume_name, image=image)
# Create Node with Disk
node_2 = gce.create_node(name, size, image, ex_tags=['libcloud'],
                         ex_boot_disk=volume)
print('   Node %s created with attached disk %s' % (node_2.name, volume.name))

# == Create Multiple nodes at once ==
base_name = '%s-muliple-nodes' % DEMO_BASE_NAME
number = MAX_NODES - 2
if number > 0:
    print('Creating Multiple Nodes (%s):' % number)
    multi_nodes = gce.ex_create_multiple_nodes(base_name, size, image, number,
                                               ex_tags=['libcloud'])
    for node in multi_nodes:
        print('   Node %s created.' % node.name)

# == Create a Network ==
print('Creating Network:')
name = '%s-network' % DEMO_BASE_NAME
cidr = '10.10.0.0/16'
network_1 = gce.ex_create_network(name, cidr)
print('   Network %s created' % network_1.name)

# == Create a Firewall ==
print('Creating a Firewall:')
name = '%s-firewall' % DEMO_BASE_NAME
allowed = [{'IPProtocol': 'tcp',
            'ports': ['3141']}]
firewall_1 = gce.ex_create_firewall(name, allowed, network=network_1,
                                    source_tags=['libcloud'])
print('   Firewall %s created' % firewall_1.name)

# == Create a Static Address ==
print('Creating an Address:')
name = '%s-address' % DEMO_BASE_NAME
address_1 = gce.ex_create_address(name)
print('   Address %s created with IP %s' % (address_1.name, address_1.address))

# == List Updated Resources in current zone/region ==
print('Updated Resources in current zone/region:')
nodes = gce.list_nodes()
display('Nodes', nodes)

addresses = gce.ex_list_addresses()
display('Addresses', addresses)

volumes = gce.ex_list_volumes()
display('Volumes', volumes)

firewalls = gce.ex_list_firewalls()
display('Firewalls', firewalls)

networks = gce.ex_list_networks()
display('Networks', networks)


if CLEANUP:
    print('Cleaning up %s resources created.' % DEMO_BASE_NAME)
    clean_up(DEMO_BASE_NAME, nodes,
             addresses + volumes + firewalls + networks)
