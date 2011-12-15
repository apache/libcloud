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

from libcloud.common.types import LibcloudError, MalformedResponseError
from libcloud.common.types import InvalidCredsError, InvalidCredsException
__all__ = [
    "Provider",
    "NodeState",
    "DeploymentError",
    "DeploymentException",

    # @@TR: should the unused imports below be exported?
    "LibcloudError",
    "MalformedResponseError",
    "InvalidCredsError",
    "InvalidCredsException"
    ]
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
    @cvar NIMBUS: Nimbus
    @cvar BLUEBOX: Bluebox
    @cvar OPSOURCE: Opsource Cloud
    @cvar NINEFOLD: Ninefold
    @cvar TERREMARK: Terremark
    @cvar: EC2_US_WEST_OREGON: Amazon AWS US West 2 (Oregon)
    @cvar CLOUDSTACK: CloudStack
    @cvar CLOUDSIGMA_US: CloudSigma US Las Vegas
    """
    DUMMY = 0
    EC2 = 1  # deprecated name
    EC2_US_EAST = 1
    EC2_EU = 2  # deprecated name
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
    EC2_AP_NORTHEAST = 26
    NIMBUS = 27
    BLUEBOX = 28
    GANDI = 29
    OPSOURCE = 30
    OPENSTACK = 31
    SKALICLOUD = 32
    SERVERLOVE = 33
    NINEFOLD = 34
    TERREMARK = 35
    EC2_US_WEST_OREGON = 36
    CLOUDSTACK = 37
    CLOUDSIGMA_US = 38
    EC2_SA_EAST = 39

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

class Architecture(object):
    """
    Image and size architectures.

    @cvar I386: i386 (32 bt)
    @cvar X86_64: x86_64 (64 bit)
    """
    I386 = 0
    X86_X64 = 1

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
