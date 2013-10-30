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


# This example performs several tasks on Google Compute Engine and the GCE
# Load Balancer.  It can be run directly or can be imported into an
# interactive python session.  This can also serve as an integration test for
# the GCE Load Balancer Driver.
#
# To run interactively:
#    - Make sure you have valid values in secrets.py
#      (For more information about setting up your credentials, see the
#      libcloud/common/google.py docstring)
#    - Run 'python' in this directory, then:
#        import gce_lb_demo
#        gcelb = gce_lb_demo.get_gcelb_driver()
#        gcelb.list_balancers()
#        etc.
#    - Or, to run the full demo from the interactive python shell:
#        import gce_lb_demo
#        gce_lb_demo.CLEANUP = False               # optional
#        gce_lb_demo.MAX_NODES = 4                 # optional
#        gce_lb_demo.DATACENTER = 'us-central1-a'  # optional
#        gce_lb_demo.main()

import os.path
import sys
import time

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

from libcloud.utils.py3 import PY3
if PY3:
    import urllib.request as url_req
else:
    import urllib2 as url_req

# This demo uses both the Compute driver and the LoadBalancer driver
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.loadbalancer.types import Provider as Provider_lb
from libcloud.loadbalancer.providers import get_driver as get_driver_lb

# String that all resource names created by the demo will start with
# WARNING: Any resource that has a matching name will be destroyed.
DEMO_BASE_NAME = 'libcloud-lb-demo'

# Datacenter to create resources in
DATACENTER = 'us-central1-b'

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
    # same authentication information so the the LB driver can get its own
    # Compute driver.
    if gce_driver:
        driver = get_driver_lb(Provider_lb.GCE)(gce_driver=gce_driver)
    else:
        driver = get_driver_lb(Provider_lb.GCE)(*args, **kwargs)
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
    gcelb = get_gcelb_driver(gce)

    # Existing Balancers
    balancers = gcelb.list_balancers()
    display('Load Balancers', balancers)

    # Protocols
    protocols = gcelb.list_protocols()
    print('Protocols:')
    for p in protocols:
        print('   %s' % p)

    # Healthchecks
    healthchecks = gcelb.ex_list_healthchecks()
    display('Health Checks', healthchecks)

    # This demo is based on the GCE Load Balancing Quickstart described here:
    # https://developers.google.com/compute/docs/load-balancing/lb-quickstart

    # == Clean-up and existing demo resources ==
    all_nodes = gce.list_nodes(ex_zone='all')
    firewalls = gce.ex_list_firewalls()
    print('Cleaning up any "%s" resources:' % DEMO_BASE_NAME)
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
    metadata = {'items': [{'key': 'startup-script',
                           'value': startup_script}]}
    lb_nodes = gce.ex_create_multiple_nodes(base_name, size, image,
                                            number, ex_tags=[tag],
                                            ex_metadata=metadata)
    display('Created Nodes', lb_nodes)

    # == Create a Firewall for instances ==
    print('Creating a Firewall:')
    name = '%s-firewall' % DEMO_BASE_NAME
    allowed = [{'IPProtocol': 'tcp',
                'ports': ['80']}]
    firewall = gce.ex_create_firewall(name, allowed, source_tags=[tag])
    print('   Firewall %s created' % firewall.name)

    # == Create a Health Check ==
    print('Creating a HealthCheck:')
    name = '%s-healthcheck' % DEMO_BASE_NAME

    # These are all the default values, but listed here as an example.  To
    # create a healthcheck with the defaults, only name is required.
    hc = gcelb.ex_create_healthcheck(name, host=None, path='/', port='80',
                                     interval=5, timeout=5,
                                     unhealthy_threshold=2,
                                     healthy_threshold=2)
    print('   Healthcheck %s created' % hc.name)

    # == Create Load Balancer ==
    print('Creating Load Balancer')
    name = '%s-lb' % DEMO_BASE_NAME
    port = 80
    protocol = 'tcp'
    algorithm = None
    members = lb_nodes[:2]  # Only attach the first two initially
    healthchecks = [hc]
    balancer = gcelb.create_balancer(name, port, protocol, algorithm, members,
                                     ex_healthchecks=healthchecks)
    print('   Load Balancer %s created' % balancer.name)

    # == Attach third Node ==
    print('Attaching additional node to Load Balancer:')
    member = balancer.attach_compute_node(lb_nodes[2])
    print('   Attached %s to %s' % (member.id, balancer.name))

    # == Show Balancer Members ==
    members = balancer.list_members()
    print('Load Balancer Members:')
    for member in members:
        print('   ID: %s IP: %s' % (member.id, member.ip))

    # == Remove a Member ==
    print('Removing a Member:')
    detached = members[0]
    detach = balancer.detach_member(detached)
    if detach:
        print('   Member %s detached from %s' % (detached.id, balancer.name))

    # == Show Updated Balancer Members ==
    members = balancer.list_members()
    print('Updated Load Balancer Members:')
    for member in members:
        print('   ID: %s IP: %s' % (member.id, member.ip))

    # == Reattach Member ==
    print('Reattaching Member:')
    member = balancer.attach_member(detached)
    print('   Member %s attached to %s' % (member.id, balancer.name))

    # == Test Load Balancer by connecting to it multiple times ==
    print('Sleeping for 10 seconds to stabilize the balancer...')
    time.sleep(10)
    rounds = 200
    url = 'http://%s/' % balancer.ip
    line_length = 75
    print('Connecting to %s %s times:' % (url, rounds))
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
    print('')

    if CLEANUP:
        balancers = gcelb.list_balancers()
        healthchecks = gcelb.ex_list_healthchecks()
        nodes = gce.list_nodes(ex_zone='all')
        firewalls = gce.ex_list_firewalls()

        print('Cleaning up %s resources created.' % DEMO_BASE_NAME)
        clean_up(DEMO_BASE_NAME, nodes, balancers + healthchecks + firewalls)

if __name__ == '__main__':
    main()
