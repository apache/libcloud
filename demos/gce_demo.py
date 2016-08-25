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

# This example performs several tasks on Google Compute Platform.  It can be
# run directly or can be imported into an interactive python session.  This
# can also serve as live integration tests.
#
# To run directly, use python 2.7 or greater:
#    - $ python gce_demo.py --help    # to see the help screen
#    - $ python gce_demo.py           # to run all demos / tests
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
#        gce_demo.main_compute()                # 'compute' only demo
#        gce_demo.main_load_balancer()          # 'load_balancer' only demo
#        gce_demo.main_dns()                    # 'dns only demo
#        gce_demo.main()                        # all demos / tests

import os.path
import sys
import datetime
import time

try:
    import argparse
except:
    print('This script uses the python "argparse" module. Please use Python '
          '2.7 or greater.')
    raise

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
sys.path.append(
    os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.common.google import ResourceNotFoundError
from libcloud.loadbalancer.types import Provider as Provider_lb
from libcloud.loadbalancer.providers import get_driver as get_driver_lb
from libcloud.dns.types import Provider as Provider_dns
from libcloud.dns.providers import get_driver as get_driver_dns
from libcloud.dns.base import Record, Zone
from libcloud.utils.py3 import PY3
if PY3:
    import urllib.request as url_req  # pylint: disable=no-name-in-module
else:
    import urllib2 as url_req

# Maximum number of 1-CPU nodes to allow to run simultaneously
MAX_NODES = 5

# String that all resource names created by the demo will start with
# WARNING: Any resource that has a matching name will be destroyed.
DEMO_BASE_NAME = 'lct'

# Datacenter to create resources in
DATACENTER = 'us-central1-f'
BACKUP_DATACENTER = 'us-east1-c'

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


def get_gcelb_driver(gce_driver=None):
    # The GCE Load Balancer driver uses the GCE Compute driver for all of its
    # API calls.  You can either provide the driver directly, or provide the
    # same authentication information so the LB driver can get its own
    # Compute driver.
    if gce_driver:
        driver = get_driver_lb(Provider_lb.GCE)(gce_driver=gce_driver)
    else:
        driver = get_driver_lb(Provider_lb.GCE)(*args, **kwargs)
    return driver


def get_dns_driver(gce_driver=None):
    # The Google DNS driver uses the GCE Compute driver for all of its
    # API calls.  You can either provide the driver directly, or provide the
    # same authentication information so the LB driver can get its own
    # Compute driver.
    if gce_driver:
        driver = get_driver_dns(Provider_dns.GOOGLE)(gce_driver=gce_driver)
    else:
        driver = get_driver_dns(Provider_dns.GOOGLE)(*args, **kwargs)
    return driver


def create_mig(gce, mig_base_name, zone, template, postfix, num_instances=2):
    """
    Creates MIG, sets named ports, modifies various text with 'postfix'.

    :param  gce: An initalized GCE driver.
    :type   gce: :class`GCENodeDriver`

    :param  zone: Zone to create Managed Instance Group in.
    :type   zone: :class:`GCEZone` or ``str``

    :param  template: Instance Template to use in creating MIG.
    :type   template: :class:`GCEInstanceTemplate`

    :param  postfix: string to append to mig name, etc.  Example: 'east',
                     'central'
    :type   postfix: ``str``

    :param  num_instances: number of instances to create in MIG.  Default is 2.
    :type   num_instances: ``int``

    :returns: initialized Managed Instance Group.
    :rtype: :class:`GCEInstanceGroupManager`
    """
    mig_name = '%s-%s' % (mig_base_name, postfix)
    mig = gce.ex_create_instancegroupmanager(
        mig_name, zone, template, num_instances, base_instance_name=mig_name,
        description='Demo for %s' % postfix)
    display('    Managed Instance Group [%s] "%s" created' % (postfix.upper(),
                                                              mig.name))
    display('    ... MIG instances created: %s' %
            ','.join([x['name'] for x in mig.list_managed_instances()]))

    # set the named_ports on the Instance Group.
    named_ports = [{'name': '%s-http' % DEMO_BASE_NAME, 'port': 80}]
    mig.set_named_ports(named_ports=named_ports)
    display('    ... MIG ports set: %s' % named_ports)

    return mig


def display(title, resource_list=[]):
    """
    Display a list of resources.

    :param  title: String to be printed at the heading of the list.
    :type   title: ``str``

    :param  resource_list: List of resources to display
    :type   resource_list: Any ``object`` with a C{name} attribute
    """
    print('=> %s' % title)
    for item in resource_list:
        if isinstance(item, Record):
            if item.name.startswith(DEMO_BASE_NAME):
                print('=>   name=%s, type=%s' % (item.name, item.type))
            else:
                print('     name=%s, type=%s' % (item.name, item.type))
        elif isinstance(item, Zone):
            if item.domain.startswith(DEMO_BASE_NAME):
                print('=>   name=%s, dnsname=%s' % (item.id, item.domain))
            else:
                print('     name=%s, dnsname=%s' % (item.id, item.domain))
        elif hasattr(item, 'name'):
            if item.name.startswith(DEMO_BASE_NAME):
                print('=>   %s' % item.name)
            else:
                print('     %s' % item.name)
        else:
            if item.startswith(DEMO_BASE_NAME):
                print('=>   %s' % item)
            else:
                print('     %s' % item)


def cleanup_only():
    start_time = datetime.datetime.now()
    display('Clean-up start time: %s' % str(start_time))
    gce = get_gce_driver()
    # Get project info and print name
    project = gce.ex_get_project()
    display('Project: %s' % project.name)

    # == Get Lists of Everything and Display the lists (up to 10) ==
    # These can either just return values for the current datacenter (zone)
    # or for everything.
    all_nodes = gce.list_nodes(ex_zone='all')
    display('Nodes:', all_nodes)

    all_addresses = gce.ex_list_addresses(region='all')
    display('Addresses:', all_addresses)

    all_volumes = gce.list_volumes(ex_zone='all')
    display('Volumes:', all_volumes)

    # This can return everything, but there is a large amount of overlap,
    # so we'll just get the sizes from the current zone.
    sizes = gce.list_sizes()
    display('Sizes:', sizes)

    # These are global
    firewalls = gce.ex_list_firewalls()
    display('Firewalls:', firewalls)

    networks = gce.ex_list_networks()
    display('Networks:', networks)

    images = gce.list_images()
    display('Images:', images)

    locations = gce.list_locations()
    display('Locations:', locations)

    zones = gce.ex_list_zones()
    display('Zones:', zones)

    snapshots = gce.ex_list_snapshots()
    display('Snapshots:', snapshots)

    gfrs = gce.ex_list_forwarding_rules(global_rules=True)
    display("Global Forwarding Rules", gfrs)
    targetproxies = gce.ex_list_targethttpproxies()
    display("Target HTTP Proxies", targetproxies)
    urlmaps = gce.ex_list_urlmaps()
    display("URLMaps", urlmaps)
    bes = gce.ex_list_backendservices()
    display("Backend Services", bes)
    migs = gce.ex_list_instancegroupmanagers(zone='all')
    display("Instance Group Managers", migs)
    its = gce.ex_list_instancetemplates()
    display("Instance Templates", its)
    hcs = gce.ex_list_healthchecks()
    display("Health Checks", hcs)

    # == Clean up any old demo resources ==
    display('Cleaning up any "%s" resources' % DEMO_BASE_NAME)
    clean_up(gce, DEMO_BASE_NAME, None,
             gfrs + targetproxies + urlmaps + bes + hcs + migs + its)

    # == Pause to let cleanup occur and repopulate volume and node lists ==
    if len(migs):
        time.sleep(10)
        all_volumes = gce.list_volumes(ex_zone='all')
        all_nodes = gce.list_nodes(ex_zone='all')

    clean_up(gce, DEMO_BASE_NAME, all_nodes,
             all_addresses + all_volumes + firewalls + networks + snapshots)
    volumes = gce.list_volumes()
    clean_up(gce, DEMO_BASE_NAME, None, volumes)
    end_time = datetime.datetime.now()
    display('Total runtime: %s' % str(end_time - start_time))


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
            display('   Deleted %s' % del_nodes[i].name)
        else:
            display('   Failed to delete %s' % del_nodes[i].name)

    # Destroy everything else with just the destroy method
    for resrc in resource_list:
        if resrc.name.startswith(base_name):
            try:
                resrc.destroy()
                class_name = resrc.__class__.__name__
                display('   Deleted %s (%s)' % (resrc.name, class_name))
            except ResourceNotFoundError:
                display('   Not found: %s (%s)' % (resrc.name,
                                                   resrc.__class__.__name__))
            except:
                class_name = resrc.__class__.__name__
                display('   Failed to Delete %s (%s)' % (resrc.name,
                                                         class_name))
                raise


def main_compute():
    start_time = datetime.datetime.now()
    display('Compute demo/test start time: %s' % str(start_time))
    gce = get_gce_driver()
    # Get project info and print name
    project = gce.ex_get_project()
    display('Project: %s' % project.name)

    # == Get Lists of Everything and Display the lists (up to 10) ==
    # These can either just return values for the current datacenter (zone)
    # or for everything.
    all_nodes = gce.list_nodes(ex_zone='all')
    display('Nodes:', all_nodes)

    all_addresses = gce.ex_list_addresses(region='all')
    display('Addresses:', all_addresses)

    all_volumes = gce.list_volumes(ex_zone='all')
    display('Volumes:', all_volumes)

    # This can return everything, but there is a large amount of overlap,
    # so we'll just get the sizes from the current zone.
    sizes = gce.list_sizes()
    display('Sizes:', sizes)

    # These are global
    firewalls = gce.ex_list_firewalls()
    display('Firewalls:', firewalls)

    subnetworks = gce.ex_list_subnetworks()
    display('Subnetworks:', subnetworks)

    networks = gce.ex_list_networks()
    display('Networks:', networks)

    images = gce.list_images()
    display('Images:', images)

    locations = gce.list_locations()
    display('Locations:', locations)

    zones = gce.ex_list_zones()
    display('Zones:', zones)

    snapshots = gce.ex_list_snapshots()
    display('Snapshots:', snapshots)

    # == Clean up any old demo resources ==
    display('Cleaning up any "%s" resources' % DEMO_BASE_NAME)
    # Delete subnetworks first, networks last
    clean_up(gce, DEMO_BASE_NAME, None, subnetworks)
    clean_up(gce, DEMO_BASE_NAME, all_nodes,
             all_addresses + all_volumes + firewalls + snapshots + networks)

    # == Create a Legacy Network ==
    display('Creating Legacy Network:')
    name = '%s-legacy-network' % DEMO_BASE_NAME
    cidr = '10.10.0.0/16'
    network_legacy = gce.ex_create_network(name, cidr)
    display('  Network %s created' % name)

    # == Delete the Legacy Network ==
    display('Delete Legacy Network:')
    network_legacy.destroy()
    display('  Network %s delete' % name)

    # == Create an auto network ==
    display('Creating Auto Network:')
    name = '%s-auto-network' % DEMO_BASE_NAME
    network_auto = gce.ex_create_network(name, cidr=None, mode='auto')
    display('  AutoNetwork %s created' % network_auto.name)

    # == Display subnetworks from the auto network ==
    subnets = []
    for sn in network_auto.subnetworks:
        subnets.append(gce.ex_get_subnetwork(sn))
    display('Display subnetworks:', subnets)

    # == Delete the auto network ==
    display('Delete Auto Network:')
    network_auto.destroy()
    display('  AutoNetwork %s deleted' % name)

    # == Create an custom network ==
    display('Creating Custom Network:')
    name = '%s-custom-network' % DEMO_BASE_NAME
    network_custom = gce.ex_create_network(name, cidr=None, mode='custom')
    display('  Custom Network %s created' % network_custom.name)

    # == Create a subnetwork ==
    display('Creating Subnetwork:')
    sname = '%s-subnetwork' % DEMO_BASE_NAME
    region = 'us-central1'
    cidr = '192.168.17.0/24'
    subnet = gce.ex_create_subnetwork(sname, cidr, network_custom, region)
    display('  Subnetwork %s created' % subnet.name)
    # Refresh object, now that it has a subnet
    network_custom = gce.ex_get_network(name)

    # == Display subnetworks from the auto network ==
    subnets = []
    for sn in network_custom.subnetworks:
        subnets.append(gce.ex_get_subnetwork(sn))
    display('Display custom subnetworks:', subnets)

    # == Launch instance in custom subnetwork ==
    display('Creating Node in custom subnetwork:')
    name = '%s-subnet-node' % DEMO_BASE_NAME
    node_1 = gce.create_node(name, 'g1-small', 'debian-8',
                             ex_disk_auto_delete=True,
                             ex_network=network_custom, ex_subnetwork=subnet)
    display('  Node %s created' % name)

    # == Destroy instance in custom subnetwork ==
    display('Destroying Node in custom subnetwork:')
    node_1.destroy()
    display('  Node %s destroyed' % name)

    # == Delete an subnetwork ==
    display('Delete Custom Subnetwork:')
    subnet.destroy()
    display('  Custom Subnetwork %s deleted' % sname)
    is_deleted = False
    while not is_deleted:
        time.sleep(3)
        try:
            subnet = gce.ex_get_subnetwork(sname, region)
        except ResourceNotFoundError:
            is_deleted = True

    # == Delete the auto network ==
    display('Delete Custom Network:')
    network_custom.destroy()
    display('  Custom Network %s deleted' % name)

    # == Create Node with disk auto-created ==
    if MAX_NODES > 1:
        display('Creating a node with boot/local-ssd using GCE structure:')
        name = '%s-gstruct' % DEMO_BASE_NAME
        img_url = "projects/debian-cloud/global/images/"
        img_url += "backports-debian-7-wheezy-v20141205"
        disk_type_url = "projects/%s/zones/us-central1-f/" % project.name
        disk_type_url += "diskTypes/local-ssd"
        gce_disk_struct = [
            {
                "type": "PERSISTENT",
                "deviceName": '%s-gstruct' % DEMO_BASE_NAME,
                "initializeParams": {
                    "diskName": '%s-gstruct' % DEMO_BASE_NAME,
                    "sourceImage": img_url
                },
                "boot": True,
                "autoDelete": True
            }, {
                "type": "SCRATCH",
                "deviceName": '%s-gstruct-lssd' % DEMO_BASE_NAME,
                "initializeParams": {
                    "diskType": disk_type_url
                },
                "autoDelete": True
            }
        ]
        node_gstruct = gce.create_node(name, 'n1-standard-1', None,
                                       'us-central1-f',
                                       ex_disks_gce_struct=gce_disk_struct)
        num_disks = len(node_gstruct.extra['disks'])
        display('  Node %s created with %d disks' % (node_gstruct.name,
                                                     num_disks))

        display('Creating Node with auto-created SSD:')
        name = '%s-np-node' % DEMO_BASE_NAME
        node_1 = gce.create_node(name, 'n1-standard-1', 'debian-7',
                                 ex_tags=['libcloud'], ex_disk_type='pd-ssd',
                                 ex_disk_auto_delete=False)
        display('  Node %s created' % name)

        # Stop the node and change to a custom machine type (e.g. size)
        display('Stopping node, setting custom size, starting node:')
        name = '%s-np-node' % DEMO_BASE_NAME
        gce.ex_stop_node(node_1)
        gce.ex_set_machine_type(node_1, 'custom-2-4096')  # 2 vCPU, 4GB RAM
        gce.ex_start_node(node_1)
        node_1 = gce.ex_get_node(name)
        display('  %s: state=%s, size=%s' % (name, node_1.extra['status'],
                                             node_1.size))

        # == Create, and attach a disk ==
        display('Creating a new disk:')
        disk_name = '%s-attach-disk' % DEMO_BASE_NAME
        volume = gce.create_volume(10, disk_name)
        if gce.attach_volume(node_1, volume, ex_auto_delete=True):
            display('  Attached %s to %s' % (volume.name, node_1.name))
        display('  Disabled auto-delete for %s on %s' % (volume.name,
                                                         node_1.name))
        gce.ex_set_volume_auto_delete(volume, node_1, auto_delete=False)

        if CLEANUP:
            # == Detach the disk ==
            if gce.detach_volume(volume, ex_node=node_1):
                display('  Detached %s from %s' % (volume.name, node_1.name))

    # == Create Snapshot ==
    display('Creating a snapshot from existing disk:')
    # Create a disk to snapshot
    vol_name = '%s-snap-template' % DEMO_BASE_NAME
    image = gce.ex_get_image('debian-7')
    vol = gce.create_volume(None, vol_name, image=image)
    display('Created disk %s to shapshot:' % DEMO_BASE_NAME)
    # Snapshot volume
    snapshot = vol.snapshot('%s-snapshot' % DEMO_BASE_NAME)
    display('  Snapshot %s created' % snapshot.name)

    # == Create Node with existing disk ==
    display('Creating Node with existing disk:')
    name = '%s-persist-node' % DEMO_BASE_NAME
    # Use objects this time instead of names
    # Get latest Debian 7 image
    image = gce.ex_get_image('debian-7')
    # Get Machine Size
    size = gce.ex_get_size('n1-standard-1')
    # Create Disk from Snapshot created above
    volume_name = '%s-boot-disk' % DEMO_BASE_NAME
    volume = gce.create_volume(None, volume_name, snapshot=snapshot)
    display('  Created %s from snapshot' % volume.name)
    # Create Node with Disk
    node_2 = gce.create_node(name, size, image, ex_tags=['libcloud'],
                             ex_boot_disk=volume, ex_disk_auto_delete=False)
    display('  Node %s created with attached disk %s' % (node_2.name,
                                                         volume.name))

    # == Update Tags for Node ==
    display('Updating Tags for %s:' % node_2.name)
    tags = node_2.extra['tags']
    tags.append('newtag')
    if gce.ex_set_node_tags(node_2, tags):
        display('  Tags updated for %s' % node_2.name)
    check_node = gce.ex_get_node(node_2.name)
    display('  New tags: %s' % check_node.extra['tags'])

    # == Setting Metadata for Node ==
    display('Setting Metadata for %s:' % node_2.name)
    if gce.ex_set_node_metadata(node_2, {'foo': 'bar', 'baz': 'foobarbaz'}):
        display('  Metadata updated for %s' % node_2.name)
    check_node = gce.ex_get_node(node_2.name)
    display('  New Metadata: %s' % check_node.extra['metadata'])

    # == Create Multiple nodes at once ==
    base_name = '%s-multiple-nodes' % DEMO_BASE_NAME
    number = MAX_NODES - 2
    if number > 0:
        display('Creating Multiple Nodes (%s):' % number)
        multi_nodes = gce.ex_create_multiple_nodes(
            base_name, size, image, number, ex_tags=['libcloud'],
            ex_disk_auto_delete=True)
        for node in multi_nodes:
            display('  Node %s created' % node.name)

    # == Create a Network ==
    display('Creating Network:')
    name = '%s-network' % DEMO_BASE_NAME
    cidr = '10.10.0.0/16'
    network_1 = gce.ex_create_network(name, cidr)
    display('  Network %s created' % network_1.name)

    # == Create a Firewall ==
    display('Creating a Firewall:')
    name = '%s-firewall' % DEMO_BASE_NAME
    allowed = [{'IPProtocol': 'tcp', 'ports': ['3141']}]
    firewall_1 = gce.ex_create_firewall(name, allowed, network=network_1,
                                        source_tags=['libcloud'])
    display('  Firewall %s created' % firewall_1.name)

    # == Create a Static Address ==
    display('Creating an Address:')
    name = '%s-address' % DEMO_BASE_NAME
    address_1 = gce.ex_create_address(name)
    display('  Address %s created with IP %s' % (address_1.name,
                                                 address_1.address))

    # == List Updated Resources in current zone/region ==
    display('Updated Resources in current zone/region')
    nodes = gce.list_nodes()
    display('Nodes:', nodes)

    addresses = gce.ex_list_addresses()
    display('Addresses:', addresses)

    firewalls = gce.ex_list_firewalls()
    display('Firewalls:', firewalls)

    subnetworks = gce.ex_list_subnetworks()
    display('Subnetworks:', subnetworks)

    networks = gce.ex_list_networks()
    display('Networks:', networks)

    snapshots = gce.ex_list_snapshots()
    display('Snapshots:', snapshots)

    if CLEANUP:
        display('Cleaning up %s resources created' % DEMO_BASE_NAME)
        clean_up(gce, DEMO_BASE_NAME, None, subnetworks)
        clean_up(gce, DEMO_BASE_NAME, nodes,
                 addresses + firewalls + snapshots + networks)
        volumes = gce.list_volumes()
        clean_up(gce, DEMO_BASE_NAME, None, volumes)
    end_time = datetime.datetime.now()
    display('Total runtime: %s' % str(end_time - start_time))


# ==== LOAD BALANCER CODE STARTS HERE ====
def main_load_balancer():
    start_time = datetime.datetime.now()
    display('Load-balancer demo/test start time: %s' % str(start_time))
    gce = get_gce_driver()
    gcelb = get_gcelb_driver(gce)

    # Get project info and print name
    project = gce.ex_get_project()
    display('Project: %s' % project.name)

    # Existing Balancers
    balancers = gcelb.list_balancers()
    display('Load Balancers', balancers)

    # Protocols
    protocols = gcelb.list_protocols()
    display('Protocols', protocols)

    # Healthchecks
    healthchecks = gcelb.ex_list_healthchecks()
    display('Health Checks', healthchecks)

    # This demo is based on the GCE Load Balancing Quickstart described here:
    # https://developers.google.com/compute/docs/load-balancing/lb-quickstart

    # == Clean-up and existing demo resources ==
    all_nodes = gce.list_nodes(ex_zone='all')
    firewalls = gce.ex_list_firewalls()
    display('Cleaning up any "%s" resources' % DEMO_BASE_NAME)
    clean_up(gce, DEMO_BASE_NAME, all_nodes,
             balancers + healthchecks + firewalls)

    # == Create 3 nodes to balance between ==
    startup_script = ('apt-get -y update && '
                      'apt-get -y install apache2 && '
                      'hostname > /var/www/index.html')
    tag = '%s-www' % DEMO_BASE_NAME
    base_name = '%s-www' % DEMO_BASE_NAME
    image = gce.ex_get_image('debian-7')
    size = gce.ex_get_size('n1-standard-1')
    number = 3
    display('Creating %d nodes' % number)
    metadata = {'items': [{'key': 'startup-script', 'value': startup_script}]}
    lb_nodes = gce.ex_create_multiple_nodes(
        base_name, size, image, number, ex_tags=[tag], ex_metadata=metadata,
        ex_disk_auto_delete=True, ignore_errors=False)
    display('Created Nodes', lb_nodes)

    # == Create a Firewall for instances ==
    display('Creating a Firewall')
    name = '%s-firewall' % DEMO_BASE_NAME
    allowed = [{'IPProtocol': 'tcp', 'ports': ['80']}]
    firewall = gce.ex_create_firewall(name, allowed, target_tags=[tag])
    display('    Firewall %s created' % firewall.name)

    # == Create a Health Check ==
    display('Creating a HealthCheck')
    name = '%s-healthcheck' % DEMO_BASE_NAME

    # These are all the default values, but listed here as an example.  To
    # create a healthcheck with the defaults, only name is required.
    hc = gcelb.ex_create_healthcheck(
        name, host=None, path='/', port='80', interval=5, timeout=5,
        unhealthy_threshold=2, healthy_threshold=2)
    display('Healthcheck %s created' % hc.name)

    # == Create Load Balancer ==
    display('Creating Load Balancer')
    name = '%s-lb' % DEMO_BASE_NAME
    port = 80
    protocol = 'tcp'
    algorithm = None
    members = lb_nodes[:2]  # Only attach the first two initially
    healthchecks = [hc]
    balancer = gcelb.create_balancer(name, port, protocol, algorithm, members,
                                     ex_healthchecks=healthchecks)
    display('    Load Balancer %s created' % balancer.name)

    # == Attach third Node ==
    display('Attaching additional node to Load Balancer')
    member = balancer.attach_compute_node(lb_nodes[2])
    display('      Attached %s to %s' % (member.id, balancer.name))

    # == Show Balancer Members ==
    members = balancer.list_members()
    display('Load Balancer Members')
    for member in members:
        display('      ID: %s IP: %s' % (member.id, member.ip))

    # == Remove a Member ==
    display('Removing a Member')
    detached = members[0]
    detach = balancer.detach_member(detached)
    if detach:
        display('      Member %s detached from %s' % (detached.id,
                                                      balancer.name))

    # == Show Updated Balancer Members ==
    members = balancer.list_members()
    display('Updated Load Balancer Members')
    for member in members:
        display('      ID: %s IP: %s' % (member.id, member.ip))

    # == Reattach Member ==
    display('Reattaching Member')
    member = balancer.attach_member(detached)
    display('      Member %s attached to %s' % (member.id, balancer.name))

    # == Test Load Balancer by connecting to it multiple times ==
    PAUSE = 60
    display('Sleeping for %d seconds for LB members to serve...' % PAUSE)
    time.sleep(PAUSE)
    rounds = 200
    url = 'http://%s/' % balancer.ip
    line_length = 75
    display('Connecting to %s %s times' % (url, rounds))
    for x in range(rounds):
        response = url_req.urlopen(url)
        if PY3:
            output = str(response.read(), encoding='utf-8').strip()
        else:
            output = response.read().strip()
        if 'www-001' in output:
            padded_output = output.center(line_length)
        elif 'www-002' in output:
            padded_output = output.rjust(line_length)
        else:
            padded_output = output.ljust(line_length)
        sys.stdout.write('\r%s' % padded_output)
        sys.stdout.flush()
        time.sleep(.25)

    print('')
    if CLEANUP:
        balancers = gcelb.list_balancers()
        healthchecks = gcelb.ex_list_healthchecks()
        nodes = gce.list_nodes(ex_zone='all')
        firewalls = gce.ex_list_firewalls()

        display('Cleaning up %s resources created' % DEMO_BASE_NAME)
        clean_up(gce, DEMO_BASE_NAME, nodes,
                 balancers + healthchecks + firewalls)

    end_time = datetime.datetime.now()
    display('Total runtime: %s' % str(end_time - start_time))


# ==== BACKEND SERVICE LOAD BALANCER CODE STARTS HERE ====
def main_backend_service():
    start_time = datetime.datetime.now()
    display('Backend Service w/Global Forwarding Rule demo/test start time: %s'
            % str(start_time))
    gce = get_gce_driver()
    # Get project info and print name
    project = gce.ex_get_project()
    display('Project: %s' % project.name)

    # Based on the instructions at:
    # https://cloud.google.com/compute/docs/load-balancing/http/#overview

    zone_central = DATACENTER
    zone_east = BACKUP_DATACENTER
    it_name = '%s-instancetemplate' % DEMO_BASE_NAME
    mig_name = '%s-mig' % DEMO_BASE_NAME
    hc_name = '%s-healthcheck' % DEMO_BASE_NAME
    bes_name = '%s-bes' % DEMO_BASE_NAME
    urlmap_name = '%s-urlmap' % DEMO_BASE_NAME
    targethttpproxy_name = '%s-httptargetproxy' % DEMO_BASE_NAME
    address_name = '%s-address' % DEMO_BASE_NAME
    gfr_name = '%s-gfr' % DEMO_BASE_NAME
    firewall_name = '%s-firewall' % DEMO_BASE_NAME

    startup_script = ('apt-get -y update && '
                      'apt-get -y install apache2 && '
                      'echo "$(hostname)" > /var/www/html/index.html')
    tag = '%s-mig-www' % DEMO_BASE_NAME
    metadata = {'items': [{'key': 'startup-script', 'value': startup_script}]}

    mig_central = None
    mig_east = None
    bes = None
    urlmap = None
    tp = None
    address = None
    gfr = None
    firewall = None

    display('Create a BackendService')
    # == Create an Instance Template ==
    it = gce.ex_create_instancetemplate(it_name, size='n1-standard-1',
                                        image='debian-8', network='default',
                                        metadata=metadata, tags=[tag])
    display('    InstanceTemplate "%s" created' % it.name)

    # == Create a MIG ==
    mig_central = create_mig(gce, mig_name, zone_central, it, 'central')
    mig_east = create_mig(gce, mig_name, zone_east, it, 'east')

    # == Create a Health Check ==
    hc = gce.ex_create_healthcheck(hc_name, host=None, path='/', port='80',
                                   interval=30, timeout=10,
                                   unhealthy_threshold=10, healthy_threshold=1)
    display('    Healthcheck %s created' % hc.name)

    # == Create a Backend Service ==
    be_central = gce.ex_create_backend(
        instance_group=mig_central.instance_group)
    be_east = gce.ex_create_backend(instance_group=mig_east.instance_group)
    bes = gce.ex_create_backendservice(
        bes_name, [hc], backends=[be_central, be_east], port_name='%s-http' %
        DEMO_BASE_NAME, protocol='HTTP', description='%s bes desc' %
        DEMO_BASE_NAME, timeout_sec=60, enable_cdn=False)
    display('    Backend Service "%s" created' % bes.name)

    # == Create a URLMap ==
    urlmap = gce.ex_create_urlmap(urlmap_name, default_service=bes)
    display('    URLMap "%s" created' % urlmap.name)

    # == Create a Target (HTTP) Proxy ==
    tp = gce.ex_create_targethttpproxy(targethttpproxy_name, urlmap)
    display('    TargetProxy "%s" created' % tp.name)

    # == Create a Static Address ==
    address = gce.ex_create_address(address_name, region='global')
    display('    Address "%s" created with IP "%s"' % (address.name,
                                                       address.address))
    # == Create a Global Forwarding Rule ==
    gfr = gce.ex_create_forwarding_rule(
        gfr_name, target=tp, address=address, port_range='80',
        description='%s libcloud forwarding rule http test' % DEMO_BASE_NAME,
        global_rule=True)
    display('    Global Forwarding Rule "%s" created' % (gfr.name))

    # == Create a Firewall for instances ==
    allowed = [{'IPProtocol': 'tcp', 'ports': ['80']}]
    firewall = gce.ex_create_firewall(firewall_name, allowed,
                                      target_tags=[tag])
    display('    Firewall %s created' % firewall.name)

    # TODO(supertom): launch instances to demostrate that it works
    # take backends out of service.  Adding in this functionality
    # will also add 10-15 minutes to the demo.
    #    display("Sleeping for 10 minutes, starting at %s" %
    #            str(datetime.datetime.now()))
    #    time.sleep(600)

    if CLEANUP:
        display('Cleaning up %s resources created' % DEMO_BASE_NAME)
        clean_up(gce, DEMO_BASE_NAME, None,
                 resource_list=[firewall, gfr, address, tp, urlmap, bes, hc,
                                mig_central, mig_east, it])
    end_time = datetime.datetime.now()
    display('Total runtime: %s' % str(end_time - start_time))


# ==== GOOGLE DNS CODE STARTS HERE ====
def main_dns():
    start_time = datetime.datetime.now()
    display('DNS demo/test start time: %s' % str(start_time))
    gce = get_gce_driver()
    gdns = get_dns_driver()
    # Get project info and print name
    project = gce.ex_get_project()
    display('Project: %s' % project.name)

    # Get list of managed zones
    zones = gdns.iterate_zones()
    display('Zones', zones)

    # Get list of records
    zones = gdns.iterate_zones()
    for z in zones:
        records = gdns.iterate_records(z)
        display('Records for managed zone "%s"' % z.id, records)

    # TODO(erjohnso): Finish this DNS section. Challenging in that you need to
    # own a domain, so testing will require user customization. Perhaps a new
    # command-line required flag unless --skip-dns is supplied. Also, real
    # e2e testing should try to do DNS lookups on new records, but DNS TTL
    # and propagation delays will introduce limits on what can be tested.

    end_time = datetime.datetime.now()
    display('Total runtime: %s' % str(end_time - start_time))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Google Cloud Platform Demo / Live Test Script')
    parser.add_argument("--compute", help="perform compute demo / live tests",
                        dest="compute", action="store_true")
    parser.add_argument("--load-balancer",
                        help="perform load-balancer demo / live tests",
                        dest="lb", action="store_true")
    parser.add_argument("--backend-service",
                        help="perform backend-service demo / live tests",
                        dest="bes", action="store_true")
    parser.add_argument("--dns", help="perform DNS demo / live tests",
                        dest="dns", action="store_true")
    parser.add_argument("--cleanup-only",
                        help="perform clean-up (skips all tests)",
                        dest="cleanup", action="store_true")
    cl_args = parser.parse_args()

    if cl_args.cleanup:
        cleanup_only()
    else:
        if cl_args.compute:
            main_compute()
        if cl_args.lb:
            main_load_balancer()
        if cl_args.dns:
            main_dns()
        if cl_args.bes:
            main_backend_service()
