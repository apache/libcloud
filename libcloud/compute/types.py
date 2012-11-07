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
    "InvalidCredsException",
    "DEPRECATED_RACKSPACE_PROVIDERS",
    "OLD_CONSTANT_TO_NEW_MAPPING"
    ]


class Provider(object):
    """
    Defines for each of the supported providers

    @cvar DUMMY: Example provider
    @cvar EC2_US_EAST: Amazon AWS US N. Virgina
    @cvar EC2_US_WEST: Amazon AWS US N. California
    @cvar EC2_EU_WEST: Amazon AWS EU Ireland
    @cvar RACKSPACE: Rackspace next-gen OpenStack based Cloud Servers
    @cvar RACKSPACE_FIRST_GEN: Rackspace First Gen Cloud Servers
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
    @cvar EC2_US_WEST_OREGON: Amazon AWS US West 2 (Oregon)
    @cvar CLOUDSTACK: CloudStack
    @cvar CLOUDSIGMA_US: CloudSigma US Las Vegas
    @cvar LIBVIRT: Libvirt driver
    @cvar JOYENT: Joyent driver
    @cvar VCL: VCL driver
    @cvar KTUCLOUD: kt ucloud driver
    @cvar GRIDSPOT: Gridspot driver
    """
    DUMMY = 'dummy'
    EC2 = 'ec2'  # deprecated name
    EC2_US_EAST = 'ec2_us_east'
    EC2_EU = 'ec2_eu'  # deprecated name
    EC2_EU_WEST = 'ec2_eu_west'
    RACKSPACE = 'rackspace'
    SLICEHOST = 'slicehost'
    GOGRID = 'gogrid'
    VPSNET = 'vpsnet'
    LINODE = 'linode'
    VCLOUD = 'vcloud'
    RIMUHOSTING = 'rimuhosting'
    EC2_US_WEST = 'ec2_us_west'
    VOXEL = 'voxel'
    SOFTLAYER = 'softlayer'
    EUCALYPTUS = 'eucalyptus'
    ECP = 'ecp'
    IBM = 'ibm'
    OPENNEBULA = 'opennebula'
    DREAMHOST = 'dreamhost'
    ELASTICHOSTS = 'elastichosts'
    ELASTICHOSTS_UK1 = 'elastichosts_uk1'
    ELASTICHOSTS_UK2 = 'elastichosts_uk2'
    ELASTICHOSTS_US1 = 'elastichosts_us1'
    EC2_AP_SOUTHEAST = 'ec2_ap_southeast'
    BRIGHTBOX = 'brightbox'
    CLOUDSIGMA = 'cloudsigma'
    EC2_AP_NORTHEAST = 'ec2_ap_northeast'
    NIMBUS = 'nimbus'
    BLUEBOX = 'bluebox'
    GANDI = 'gandi'
    OPSOURCE = 'opsource'
    OPENSTACK = 'openstack'
    SKALICLOUD = 'skalicloud'
    SERVERLOVE = 'serverlove'
    NINEFOLD = 'ninefold'
    TERREMARK = 'terremark'
    EC2_US_WEST_OREGON = 'ec2_us_west_oregon'
    CLOUDSTACK = 'cloudstack'
    CLOUDSIGMA_US = 'cloudsigma_us'
    EC2_SA_EAST = 'ec2_sa_east'
    LIBVIRT = 'libvirt'
    ELASTICHOSTS_US2 = 'elastichosts_us2'
    ELASTICHOSTS_CA1 = 'elastichosts_ca1'
    JOYENT = 'joyent'
    VCL = 'vcl'
    KTUCLOUD = 'ktucloud'
    GRIDSPOT = 'gridspot'
    RACKSPACE_FIRST_GEN = 'rackspace_first_gen'

    # Deprecated constants
    RACKSPACE_UK = 23
    RACKSPACE_NOVA_BETA = 40
    RACKSPACE_NOVA_DFW = 41
    RACKSPACE_NOVA_LON = 48
    RACKSPACE_NOVA_ORD = 50


DEPRECATED_RACKSPACE_PROVIDERS = [Provider.RACKSPACE_UK,
                                  Provider.RACKSPACE_NOVA_BETA,
                                  Provider.RACKSPACE_NOVA_DFW,
                                  Provider.RACKSPACE_NOVA_LON,
                                  Provider.RACKSPACE_NOVA_ORD]
OLD_CONSTANT_TO_NEW_MAPPING = {
    Provider.RACKSPACE: Provider.RACKSPACE_FIRST_GEN,
    Provider.RACKSPACE_UK: Provider.RACKSPACE_FIRST_GEN,

    Provider.RACKSPACE_NOVA_BETA: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_DFW: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_LON: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_ORD: Provider.RACKSPACE
}


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
    def __init__(self, node, original_exception=None, driver=None):
        self.node = node
        self.value = original_exception
        self.driver = driver

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return (('<DeploymentError: node=%s, error=%s, driver=%s>'
                % (self.node.id, str(self.value), str(self.driver))))


"""Deprecated alias of L{DeploymentException}"""
DeploymentException = DeploymentError
