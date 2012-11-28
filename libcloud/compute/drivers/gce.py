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

"""
Libcloud driver for Google Compute Engine.

Google Compute Engine home page:
cloud.google.com/products/compute-engine.html

Google Compute Engine documentation:
developers.google.com/compute/docs
"""

import getpass
import os
import paramiko
import sys

from gcelib import gce, gce_util, shortcuts

from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import NodeSize
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState


class GoogleComputeEngineNodeDriver(NodeDriver):
    """
    Google Compute Engine Node Driver
    """
    api_name = 'gce'
    type = Provider.GCE
    name = 'GoogleComputeEngine'

    NODE_STATE_MAP = {
        "PROVISIONING": NodeState.PENDING,
        "STAGING": NodeState.PENDING,
        "RUNNING": NodeState.RUNNING,
        "STOPPED": NodeState.TERMINATED,
        "TERMINATED": NodeState.TERMINATED
    }

    def __init__(self, ssh_username=None, ssh_private_key_file=None,
                 project=None, key=None):
        """
        @param      ssh_username: The username that can be used to log into
        Google Compute Engine nodes in a cluster (required).
        @type       ssh_username: C{str}

        @param      ssh_private_key_file: The fully qualified path to the ssh
        private key file (required).
        @type       ssh_private_key_file: C{str}

        @param      project: The name of the Google Compute Engine project
        (required).
        @type       project: C{str}

        @rtype: None
        """
        super(GoogleComputeEngineNodeDriver, self).__init__(key)
        self.credentials = gce_util.get_credentials()

        if project:
            self.project = project
        else:
            print "Please specify the project in your Driver's constructor."
            sys.exit(1)

        if ssh_username:
            self.ssh_username = ssh_username
        else:
            print "Please specify your ssh username in your Driver's \
                constructor."
            sys.exit(1)

        if ssh_private_key_file:
            self.ssh_private_key_file = ssh_private_key_file
        else:
            print "Please specify your ssh private key file in your Driver's \
            constructor."
            sys.exit(1)

        self.default_zone = 'us-central1-a'
        self.default_image = 'projects/google/images/ubuntu-12-04-v20120621'
        self.default_machine_type = 'n1-standard-1'

        self.SSHClient = paramiko.SSHClient()
        self.gcelib_instance = gce.get_api(self.credentials,
                                           default_project=self.project,
                                           default_zone=self.default_zone,
                                           default_image=self.default_image,
                                           default_machine_type=
                                           self.default_machine_type)

    def list_nodes(self):
        """
        List all Google Compute Engine nodes associated with the current
        project.

        @rtype: C{list} of L{Node}
        """
        list_nodes = []

        for instance in self.gcelib_instance.all_instances():
            node = self._to_node(instance)
            list_nodes.append(node)

        return list_nodes

    def list_images(self):
        """
        List all available Google Compute Engine distribution images.

        @rtype: C{list} of L{NodeImage}
        """
        list_images = []

        for img in self.gcelib_instance.list_images(project='google'):
            image = self._to_node_image(img)
            list_images.append(image)

        return list_images

    def list_sizes(self, location=None):
        """
        List all available Google Compute Engine node sizes (machine types).

        @keyword location: The location at which to list sizes (optional).
        @type    location: L{NodeLocation}

        @rtype: C{list} of L{NodeSize}
        """
        list_sizes = []

        for machine_type in self.gcelib_instance.list_machine_types():
            size = self._to_node_size(machine_type)
            list_sizes.append(size)

        return list_sizes

    def list_locations(self):
        """
        List all available Google Compute Engine zones.

        @rtype: C{list} of L{NodeLocation}
        """
        list_locations = []

        for zone in self.gcelib_instance.list_zones():
            location = self._to_node_location(zone)
            list_locations.append(location)

        return list_locations

    def create_node(self, name, size, image, location):
        """
        Create a new Google Compute Engine node.

        @param      name: The name of the new Google Compute Engine node
        (required).
        @type       name: C{str}

        @param      size: The size of resources allocated to this node
        (required).
        @type       size: L{NodeSize}

        @param      image: The OS Image to boot on this node (required).
        @type       image: L{NodeImage}

        @param      location: The zone in which to create this node
        (required).
        @type       location: L{NodeLocation}

        @rtype: L{Node}
        """
        self.gcelib_instance.insert_instance(name=name, machineType=size.name,
                                             image=image.name,
                                             zone=location.name,
                                             project=self.project,
                                             metadata=None)

        return self._get_node(name)

    def reboot_node(self, node):
        """
        Reboot the given Google Compute Engine node.

        @param      node: The Google Compute Engine node to reboot (required).
        @type       node: L{Node}

        @rtype: C{bool}
        """
        ssh_username = self.ssh_username
        ssh_private_key = self.ssh_private_key_file
        ssh_host = node.private_ips[0]

        ssh_private_key_file = os.path.expanduser(ssh_private_key)
        ssh_private_key_pass = ""

        try:
            pkey = paramiko.RSAKey.from_private_key_file(ssh_private_key_file,
                                                         ssh_private_key_pass)
        except paramiko.SSHException:
            prompt = 'Enter passphrase for key \'' + ssh_private_key_file + \
                '\': '
            ssh_private_key_pass = getpass.getpass(prompt=prompt)
            pkey = paramiko.RSAKey.from_private_key_file(ssh_private_key_file,
                                                         ssh_private_key_pass)
        try:
            ssh_client = self.SSHClient
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(ssh_host, username=ssh_username, pkey=pkey)
            ssh_client.exec_command('sudo reboot')
            ssh_client.close()
            return True
        except Exception:
            return False

    def destroy_node(self, node):
        """
        Destroy the given Google Compute Engine node.

        @param      node: The Google Compute Engine node to destroy (required).
        @type       node: L{Node}

        @rtype: C{bool}
        """
        try:
            self.gcelib_instance.delete_instance(node.name)
            return True
        except Exception:
            return False

    def deploy_node(self, name, size, image, location, script):
        """
        Create a new Google Compute Engine node, and run a startup script on
        initialization

        @param      name: The name of the new Google Compute Engine node
        (required).
        @type       name: C{str}

        @param      size: The size of resources allocated to this node
        (required).
        @type       size: L{NodeSize}

        @param      image: The OS Image to boot on this node (required).
        @type       image: L{NodeImage}

        @param      location: The zone in which to create this node
        (required).
        @type       location: L{NodeLocation}

        @param      script: The fully qualified local path to the startup
        script to run on node initialization (required).
        @type       script: C{string}

        @rtype: L{Node}
        """
        startup_script = shortcuts.metadata({'startup-script':
                                             open(script).read()})

        self.gcelib_instance.insert_instance(name=name, machineType=size.name,
                                             image=image.name,
                                             zone=location.name,
                                             project=self.project,
                                             metadata=startup_script)

        return self._get_node(name)

    def _get_node(self, name):
        """
        Get the Google Compute Engine node associated with name.

        @param      name: The name of the Google Compute Engine node to be
        returned (required).
        @type       name: C{str}

        @rtype: L{Node}
        """
        gcelib_instance = self.gcelib_instance.get_instance(name)
        if gcelib_instance is None:
            return gcelib_instance
        else:
            return self._to_node(gcelib_instance)

    def _to_node(self, node):
        """
        Convert the gcelib node into a Node.

        @param      node: The gcelib node to be converted into a Node
        (required).
        @type       node: C{gcelib node}

        @rtype: L{Node}
        """
        public_ips = []
        private_ips = []
        extra = {}

        extra['status'] = node.status
        extra['machine_type'] = node.machineType
        extra['description'] = node.description
        extra['zone'] = node.zone
        extra['image'] = node.image
        extra['disks'] = node.disks
        extra['networkInterfaces'] = node.networkInterfaces
        extra['id'] = node.id
        extra['selfLink'] = node.selfLink
        extra['name'] = node.name
        extra['metadata'] = node.metadata

        for network_interface in node.networkInterfaces:
            public_ips.append(network_interface.networkIP)
            for access_config in network_interface.accessConfigs:
                private_ips.append(access_config.natIP)

        return Node(id=node.id, name=node.name,
                    state=self.NODE_STATE_MAP[node.status],
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, size=node.machineType, image=node.image,
                    extra=extra)

    def _to_node_image(self, image):
        """
        Convert the gcelib image into a NodeImage.

        @param      node: The gcelib image to be converted into a NodeImage.
        @type       node: C{gcelib image}

        @rtype: L{NodeImage}
        """
        extra = {}
        extra['preferredKernel'] = image.preferredKernel
        extra['description'] = image.description
        extra['creationTimestamp'] = image.creationTimestamp

        return NodeImage(id=image.id, name=image.selfLink, driver=self,
                         extra=extra)

    def _to_node_location(self, location):
        """
        Convert the gcelib location into a NodeLocation.

        @param      node: The gcelib location to be converted into a
        NodeLocation (required).
        @type       node: C{gcelib location}

        @rtype: L{NodeLocation}
        """
        return NodeLocation(id=location.id, name=location.name, country='US',
                            driver=self)

    def _to_node_size(self, machine_type):
        """
        Convert the gcelib machine type into a NodeSize.

        @param      node: The gcelib machine type to be converted into a
        NodeSize (required).
        @type       node: C{gcelib machine type}

        @rtype: L{NodeSize}
        """
        try:
            price = self._get_size_price(size_id=machine_type.name)
        except KeyError:
            price = None

        return NodeSize(id=machine_type.id, name=machine_type.name,
                        ram=machine_type.memoryMb,
                        disk=machine_type.imageSpaceGb, bandwidth=0,
                        price=price, driver=self)
