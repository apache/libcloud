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


# This example performs several tasks on Google Compute Engine.  It can be run
# directly or can be imported into an interactive python session.  This can
# also serve as an integration test for the GCE Node Driver.
#
# To run interactively:
#    - Make sure you have valid values in secrets.py
#      (For more information about setting up your credentials, see the
#      libcloud/common/google.py docstring)
#    - Run 'python' in this directory, then:
#        import gce_demo
#        gce = gce_demo.get_gce_driver()
#        gce.list_nodes()
#        etc.
#    - Or, to run the full demo from the interactive python shell:
#        import gce_demo
#        gce_demo.CLEANUP = False               # optional
#        gce_demo.MAX_NODES = 4                 # optional
#        gce_demo.DATACENTER = 'us-central1-a'  # optional
#        gce_demo.main()

import os.path
import sys

try:
    import secrets
except ImportError:
    print('"demos/secrets.py" not found.\n\n'
          'Please copy secrets.py-dist to secrets.py and update the GCE* '
          'values with appropriate authentication information.\n'
          'Additional information about setting these values can be found '
          'in the docstring for:\n'
          'libcloud/common/google.py\n')
    sys.exit(1)

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

# Add datacenter to kwargs for Python 2.5 compatibility
kwargs = kwargs.copy()
kwargs['datacenter'] = DATACENTER


# ==== HELPER FUNCTIONS ====
def get_gce_driver():
    driver = get_driver(Provider.GCE)(*args, **kwargs)
    return driver


def display(title, resource_list):
    """
    Display a list of resources.

    :param  title: String to be printed at the heading of the list.
    :type   title: ``str``

    :param  resource_list: List of resources to display
    :type   resource_list: Any ``object`` with a C{name} attribute
    """
    print('%s:' % title)
    for item in resource_list[:10]:
        print('   %s' % item.name)


def clean_up(gce, base_name, node_list=None, resource_list=None):
    """
    Destroy all resources that have a name beginning with 'base_name'.

    :param  base_name: String with the first part of the name of resources
                       to destroy
    :type   base_name: ``str``

    :keyword  node_list: List of nodes to consider for deletion
    :type     node_list: ``list`` of :class:`Node`

    :keyword  resource_list: List of resources to consider for deletion
    :type     resource_list: ``list`` of I{Resource Objects}
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
def main():
    gce = get_gce_driver()
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

    all_volumes = gce.list_volumes(ex_zone='all')
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

    snapshots = gce.ex_list_snapshots()
    display('Snapshots', snapshots)

    # == Clean up any old demo resources ==
    print('Cleaning up any "%s" resources:' % DEMO_BASE_NAME)
    clean_up(gce, DEMO_BASE_NAME, all_nodes,
             all_addresses + all_volumes + firewalls + networks + snapshots)

    # == Create Node with disk auto-created ==
    if MAX_NODES > 1:
        print('Creating Node with auto-created SSD:')
        name = '%s-np-node' % DEMO_BASE_NAME
        node_1 = gce.create_node(name, 'n1-standard-1', 'debian-7',
                                 ex_tags=['libcloud'], ex_disk_type='pd-ssd')
        print('   Node %s created' % name)

        # == Create, and attach a disk ==
        print('Creating a new disk:')
        disk_name = '%s-attach-disk' % DEMO_BASE_NAME
        volume = gce.create_volume(10, disk_name)
        if volume.attach(node_1):
            print ('   Attached %s to %s' % (volume.name, node_1.name))

        if CLEANUP:
            # == Detach the disk ==
            if gce.detach_volume(volume, ex_node=node_1):
                print('   Detached %s from %s' % (volume.name, node_1.name))

    # == Create Snapshot ==
    print('Creating a snapshot from existing disk:')
    # Create a disk to snapshot
    vol_name = '%s-snap-template' % DEMO_BASE_NAME
    image = gce.ex_get_image('debian-7')
    vol = gce.create_volume(None, vol_name, image=image)
    print('   Created disk %s to shapshot' % DEMO_BASE_NAME)
    # Snapshot volume
    snapshot = vol.snapshot('%s-snapshot' % DEMO_BASE_NAME)
    print('   Snapshot %s created' % snapshot.name)

    # == Create Node with existing disk ==
    print('Creating Node with existing disk:')
    name = '%s-persist-node' % DEMO_BASE_NAME
    # Use objects this time instead of names
    # Get latest Debian 7 image
    image = gce.ex_get_image('debian-7')
    # Get Machine Size
    size = gce.ex_get_size('n1-standard-1')
    # Create Disk from Snapshot created above
    volume_name = '%s-boot-disk' % DEMO_BASE_NAME
    volume = gce.create_volume(None, volume_name, snapshot=snapshot)
    print('   Created %s from snapshot' % volume.name)
    # Create Node with Disk
    node_2 = gce.create_node(name, size, image, ex_tags=['libcloud'],
                             ex_boot_disk=volume)
    print('   Node %s created with attached disk %s' % (node_2.name,
                                                        volume.name))

    # == Update Tags for Node ==
    print('Updating Tags for %s' % node_2.name)
    tags = node_2.extra['tags']
    tags.append('newtag')
    if gce.ex_set_node_tags(node_2, tags):
        print('   Tags updated for %s' % node_2.name)
    check_node = gce.ex_get_node(node_2.name)
    print('   New tags: %s' % check_node.extra['tags'])

    # == Create Multiple nodes at once ==
    base_name = '%s-multiple-nodes' % DEMO_BASE_NAME
    number = MAX_NODES - 2
    if number > 0:
        print('Creating Multiple Nodes (%s):' % number)
        multi_nodes = gce.ex_create_multiple_nodes(base_name, size, image,
                                                   number,
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
    print('   Address %s created with IP %s' % (address_1.name,
                                                address_1.address))

    # == List Updated Resources in current zone/region ==
    print('Updated Resources in current zone/region:')
    nodes = gce.list_nodes()
    display('Nodes', nodes)

    addresses = gce.ex_list_addresses()
    display('Addresses', addresses)

    volumes = gce.list_volumes()
    display('Volumes', volumes)

    firewalls = gce.ex_list_firewalls()
    display('Firewalls', firewalls)

    networks = gce.ex_list_networks()
    display('Networks', networks)

    snapshots = gce.ex_list_snapshots()
    display('Snapshots', snapshots)

    if CLEANUP:
        print('Cleaning up %s resources created.' % DEMO_BASE_NAME)
        clean_up(gce, DEMO_BASE_NAME, nodes,
                 addresses + volumes + firewalls + networks + snapshots)

if __name__ == '__main__':
    main()
