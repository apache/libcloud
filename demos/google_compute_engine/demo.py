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

import libcloud.test.secrets as secrets

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from pprint import pprint

# Set up your compute driver
GoogleComputeEngine = get_driver(Provider.GCE)

# Instantiate your compute driver with the required credentials. For Google
# Compute Engine, these are (ssh_username, ssh_private_key_file, project).
ssh_username, ssh_private_key_file, project = getattr(secrets,
                                                      'GCE_PARAMS',
                                                      ())
driver = GoogleComputeEngine(ssh_username, ssh_private_key_file, project)

# Get the list of available images.
images = driver.list_images()
print "List of images:"
pprint(images)
print "\n"

# Get the list of available sizes (machine types).
sizes = driver.list_sizes()
print "List of sizes (machine types):"
pprint(sizes)
print "\n"

# Get the list of available locations.
locations = driver.list_locations()
print "List of locations:"
pprint(locations)
print "\n"

# Create a new node, 'new_node_name', using a machine type, image, and location
# from the list of available machine types, images, and locations.
image = images[-1]
size = sizes[0]
location = locations[0]
new_node_name = 'my-new-node'
node = driver.create_node(new_node_name, size, image, location)
print "Creating a new node:", node.name
pprint(node)
print "\n"

# Print metadata for node. This will contain a script if bootstrapping node
# with a startup script.
print "Metadata for:", node.name
pprint(node.extra['metadata'])
print "\n"

# Get the list of nodes in your cluster.
nodes = driver.list_nodes()
print "List of nodes:"
pprint(nodes)
print "\n"

# To see the following command take effect, ssh into 'new_node_name'.
# Restarting 'new_node_name'.
ret = driver.reboot_node(node)
if ret:
    print "Successfully rebooted:", node.name
else:
    print "Unsuccessful in rebooting:", node.name
pprint(node)
print "\n"

# To see the following command take effect, ssh into 'new_node_name'.
# Deleting 'new_node_name'.
ret = driver.destroy_node(node)
if ret:
    print "Successfully deleted:", node.name
else:
    print "Unsuccessful in deleting:", node.name
pprint(node)
print "\n"

# Create a new node, 'new_node_name', using a machine type, image, and location
# from the list of available machine types, images, and locations.
# The node will be bootstrapped by running a desired script on first
# initialization.
script = ''  # Full path to your bootstrap script.
node = driver.deploy_node(node.name, size, image, location, script)
print "Creating a new node:", node.name, " and deploying it with script \
from", script
pprint(node)
print "\n"

# Print metadata for node.
print "Metadata for:", node.name
pprint(node.extra['metadata'])
print "\n"

# Delete all nodes in cluster.
print "Deleting all nodes in cluster.\n"
for node in driver.list_nodes():
    node.destroy()

# Get the list of nodes in your cluster. This should return an empty list.
nodes = driver.list_nodes()
print "List of nodes:"
pprint(nodes)
print "\n"
