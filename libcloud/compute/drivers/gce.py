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

import json
import getpass
import os
import paramiko
import sys

import httplib2
from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build

from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import NodeSize
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState


GCE_SCOPE = 'https://www.googleapis.com/auth/compute'
GCE_AUTH_VERSION = 'v1beta14'

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

    def __init__(self, account, key, project, ssh_username=None, ssh_private_key_file=None, zone='us-central1-a'):
        """
        @param      account: The google service account name
        @type       account: C{str}

        @param      key: Private key for access to GCE
        @type       key: file

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
        self.account = account
        with open(key, 'r') as key:
            self.key = key.read()
        credentials = SignedJwtAssertionCredentials(self.account, self.key, scope=GCE_SCOPE)
        http = httplib2.Http()
        auth = credentials.authorize(http)
        self.request = build('compute', GCE_AUTH_VERSION, http=auth)

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

        self.default_zone = zone
        self.default_image = 'projects/google/images/ubuntu-12-04-v20120621'
        self.default_machine_type = 'n1-standard-1'
        self.default_network_interfaces = 'default'


    def list_nodes(self):
        """
        List all Google Compute Engine nodes associated with the current
        project.

        @rtype: C{list} of L{Node}
        """
        list_nodes = []
        req = self.request.instances().list(project=self.project, zone=self.default_zone).execute()
        items = req['items'] if 'items' in req else []
        for instance in items:
            node = self._to_node(instance)
            list_nodes.append(node)

        return list_nodes

    def list_images(self, project=None):
        """
        List all available Google Compute Engine distribution images.

        @rtype: C{list} of L{NodeImage}
        """
        list_images = []
        if project is None:
            project = 'google'
        for img in self.request.images().list(project=project).execute()['items']:
            image = self._to_node_image(img)
            list_images.append(image)

        return list_images

    def list_sizes(self, project=None):
        """
        List all available Google Compute Engine node sizes (machine types).

        @keyword location: The location at which to list sizes (optional).
        @type    location: L{NodeLocation}

        @rtype: C{list} of L{NodeSize}
        """
        list_sizes = []
        if project is None:
            project = 'google'
        for machine_type in self.request.machineTypes().list(project=project).execute()['items']:
            size = self._to_node_size(machine_type)
            list_sizes.append(size)

        return list_sizes

    def list_locations(self, project=None):
        """
        List all available Google Compute Engine zones.

        @rtype: C{list} of L{NodeLocation}
        """
        list_locations = []
        if project is None:
            project = 'google'
        for zone in self.request.zones().list(project=project).execute()['items']:
            location = self._to_node_location(zone)
            list_locations.append(location)

        return list_locations

    def create_node(self, name, size, image, location=None, project=None, metadata={}, **kwargs):
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

        @param      metadata: Metadata to start node
        @type       location: L{dict}

        @rtype: L{Node}
        """
        if project is None:
            project = self.project
        if location is None:
            location = self.default_zone
        #TODO: Add metadata usage
        node = self.request.instances().insert(project=project, zone=location, body={
            'machineType': size.extra['selfLink'],
            'name': name,
            'network': self.default_network_interfaces,
            'metadata': [],
            'image': image.name,

        }).execute()

        return self._get_node(name, project, location)

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
            prompt = 'Enter passphrase for key \'' + ssh_private_key_file +\
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

    def destroy_node(self, node, project=None, location=None):
        """
        Destroy the given Google Compute Engine node.

        @param      node: The Google Compute Engine node to destroy (required).
        @type       node: L{Node}

        @rtype: C{bool}
        """
        if project is None:
            project = self.project
        if location is None:
            location = self.default_zone
        try:
            self.request.instances().delete(project=project, zone=location, instance=node.name).execute()
            return True
        except Exception:
            return False


    def _get_node(self, name, project=None, location=None):
        """
        Get the Google Compute Engine node associated with name.

        @param      name: The name of the Google Compute Engine node to be
        returned (required).
        @type       name: C{str}

        @rtype: L{Node}
        """
        if project is None:
            project = self.project
        if location is None:
            location = self.default_zone
        new_node = self.request.instances().get(project=project, zone=location, instance=name)
        if 'items' in new_node:
            return self._to_node(new_node['items'][0])

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

        extra['status'] = node['status']
        extra['machine_type'] = node['machineType']
        extra['description'] = node['description']
        extra['zone'] = node['zone']
        extra['image'] = node['image']
        extra['disks'] = node['disks']
        extra['networkInterfaces'] = node['networkInterfaces']
        extra['id'] = node['id']
        extra['selfLink'] = node['selfLink']
        extra['name'] = node['name']
        extra['metadata'] = node['metadata']

        for network_interface in node.networkInterfaces:
            private_ips.append(network_interface.networkIP)
            for access_config in network_interface.accessConfigs:
                public_ips.append(access_config.natIP)

        return Node(id=node['id'], name=node['name'],
                    state=self.NODE_STATE_MAP[node['status']],
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, size=node['machineType'], image=node['image'],
                    extra=extra)

    def _to_node_image(self, image):
        """
        Convert the gcelib image into a NodeImage.

        @param      node: The gcelib image to be converted into a NodeImage.
        @type       node: C{gcelib image}

        @rtype: L{NodeImage}
        """
        extra = {}
        extra['preferredKernel'] = image['preferredKernel']
        extra['description'] = image['description']
        extra['creationTimestamp'] = image['creationTimestamp']

        return NodeImage(id=image['id'], name=image['selfLink'], driver=self,
                         extra=extra)

    def _to_node_location(self, location):
        """
        Convert the gcelib location into a NodeLocation.

        @param      node: The gcelib location to be converted into a
        NodeLocation (required).
        @type       node: C{gcelib location}

        @rtype: L{NodeLocation}
        """
        return NodeLocation(id=location['id'], name=location['name'], country='US',
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
            price = self._get_size_price(size_id=machine_type['name'])
        except KeyError:
            price = None

        extra = {'url': machine_type['selfLink'],
                 'description': machine_type['description']}
        size = NodeSize(id=machine_type['id'], name=machine_type['name'],
                        ram=machine_type['memoryMb'],
                        disk=machine_type['imageSpaceGb'], bandwidth=0,
                        price=price, driver=self)
        size.extra = extra
        return size

