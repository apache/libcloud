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
Base types used by other parts of libcloud
"""

class Provider(object):
    """
    Defines for each of the supported providers

    @cvar DUMMY: Example provider
    @cvar EC2_US_EAST: Amazon AWS US N. Virgina
    @cvar EC2_US_WEST: Amazon AWS US N. California
    @cvar EC2_EU_WEST: Amazon AWS EU Ireland
    @cvar RACKSPACE: Rackspace Cloud Servers
    @cvar RACKSPACE_UK: Rackspace UK Cloud Servers
    @cvar SLICEHOST: Slicehost.com
    @cvar GOGRID: GoGrid
    @cvar VPSNET: VPS.net
    @cvar LINODE: Linode.com
    @cvar VCLOUD: vmware vCloud
    @cvar RIMUHOSTING: RimuHosting.com
    @cvar ECP: Enomaly
    @cvar IBM: IBM Developer Cloud
    @cvar OPENNEBULA: OpenNebula.org
    @cvar DREAMHOST: DreamHost Private Server
    @cvar CLOUDSIGMA: CloudSigma
    """
    DUMMY = 0
    EC2 = 1  # deprecated name
    EC2_US_EAST = 1
    EC2_EU = 2 # deprecated name
    EC2_EU_WEST = 2
    RACKSPACE = 3
    SLICEHOST = 4
    GOGRID = 5
    VPSNET = 6
    LINODE = 7
    VCLOUD = 8
    RIMUHOSTING = 9
    EC2_US_WEST = 10
    VOXEL = 11
    SOFTLAYER = 12
    EUCALYPTUS = 13
    ECP = 14
    IBM = 15
    OPENNEBULA = 16
    DREAMHOST = 17
    ELASTICHOSTS = 18
    ELASTICHOSTS_UK1 = 19
    ELASTICHOSTS_UK2 = 20
    ELASTICHOSTS_US1 = 21
    EC2_AP_SOUTHEAST = 22
    RACKSPACE_UK = 23
    BRIGHTBOX = 24
    CLOUDSIGMA = 25

class NodeState(object):
    """
    Standard states for a node

    @cvar RUNNING: Node is running
    @cvar REBOOTING: Node is rebooting
    @cvar TERMINATED: Node is terminated
    @cvar PENDING: Node is pending
    @cvar UNKNOWN: Node state is unknown
    """
    RUNNING = 0
    REBOOTING = 1
    TERMINATED = 2
    PENDING = 3
    UNKNOWN = 4

class LibcloudError(Exception):
    """The base class for other libcloud exceptions"""
    def __init__(self, value, driver=None):
        self.value = value
        self.driver = driver

class MalformedResponseError(LibcloudError):
    """Exception for the cases when a provider returns a malformed
    response, e.g. you request JSON and provider returns 
    '<h3>something</h3>' due to some error on their side."""
    def __init__(self, value, body=None, driver=None):
      self.value = value
      self.driver = driver
      self.body = body
    def __str__(self):
        return "<MalformedResponseException in "+ repr(self.driver) +" "+ repr(self.value) +">: "+ repr(self.body)

class InvalidCredsError(LibcloudError):
    """Exception used when invalid credentials are used on a provider."""
    def __init__(self, value='Invalid credentials with the provider', driver=None):
        self.value = value
        self.driver = driver
    def __str__(self):
        return repr(self.value)
"""Deprecated alias of L{InvalidCredsError}"""
InvalidCredsException = InvalidCredsError

class DeploymentError(LibcloudError):
    """
    Exception used when a Deployment Task failed.

    @ivar node: L{Node} on which this exception happened, you might want to call L{Node.destroy}
    """
    def __init__(self, node, original_exception=None):
        self.node = node
        self.value = original_exception
    def __str__(self):
        return repr(self.value)

"""Deprecated alias of L{DeploymentException}"""
DeploymentException = DeploymentError
