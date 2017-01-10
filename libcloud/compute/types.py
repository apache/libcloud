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

    "OLD_CONSTANT_TO_NEW_MAPPING"
]


class Type(object):
    @classmethod
    def tostring(cls, value):
        """Return the string representation of the state object attribute
        :param str value: the state object to turn into string
        :return: the uppercase string that represents the state object
        :rtype: str
        """
        return value.upper()

    @classmethod
    def fromstring(cls, value):
        """Return the state object attribute that matches the string
        :param str value: the string to look up
        :return: the state object attribute that matches the string
        :rtype: str
        """
        return getattr(cls, value.upper(), None)


class Provider(Type):
    """
    Defines for each of the supported providers

    Non-Dummy drivers are sorted in alphabetical order. Please preserve this
    ordering when adding new drivers.

    :cvar DUMMY: Example provider
    :cvar ABIQUO: Abiquo driver
    :cvar ALIYUN_ECS: Aliyun ECS driver.
    :cvar AURORACOMPUTE: Aurora Compute driver.
    :cvar AZURE: Azure (classic) driver.
    :cvar AZURE_ARM: Azure Resource Manager (modern) driver.
    :cvar BLUEBOX: Bluebox
    :cvar CLOUDSIGMA: CloudSigma
    :cvar CLOUDSCALE: cloudscale.ch
    :cvar CLOUDSTACK: CloudStack
    :cvar DIMENSIONDATA: Dimension Data Cloud
    :cvar EC2: Amazon AWS.
    :cvar ECP: Enomaly
    :cvar ELASTICHOSTS: ElasticHosts.com
    :cvar EXOSCALE: Exoscale driver.
    :cvar GCE: Google Compute Engine
    :cvar GOGRID: GoGrid
    :cvar GRIDSPOT: Gridspot driver
    :cvar IBM: IBM Developer Cloud
    :cvar IKOULA: Ikoula driver.
    :cvar JOYENT: Joyent driver
    :cvar KTUCLOUD: kt ucloud driver
    :cvar LIBVIRT: Libvirt driver
    :cvar LINODE: Linode.com
    :cvar NEPHOSCALE: NephoScale driver
    :cvar NIMBUS: Nimbus
    :cvar NINEFOLD: Ninefold
    :cvar OPENNEBULA: OpenNebula.org
    :cvar OPSOURCE: Opsource Cloud
    :cvar OUTSCALE_INC: Outscale INC driver.
    :cvar OUTSCALE_SAS: Outscale SAS driver.
    :cvar PROFIT_BRICKS: ProfitBricks driver.
    :cvar RACKSPACE: Rackspace next-gen OpenStack based Cloud Servers
    :cvar RACKSPACE_FIRST_GEN: Rackspace First Gen Cloud Servers
    :cvar RIMUHOSTING: RimuHosting.com
    :cvar TERREMARK: Terremark
    :cvar VCL: VCL driver
    :cvar VCLOUD: vmware vCloud
    :cvar VPSNET: VPS.net
    :cvar VULTR: vultr driver.
    """
    AZURE = 'azure'
    AZURE_ARM = 'azure_arm'
    DUMMY = 'dummy'
    ABIQUO = 'abiquo'
    ALIYUN_ECS = 'aliyun_ecs'
    AURORACOMPUTE = 'aurora_compute'
    AZURE = 'azure'
    BLUEBOX = 'bluebox'
    BRIGHTBOX = 'brightbox'
    BSNL = 'bsnl'
    CISCOCCS = 'ciscoccs'
    CLOUDFRAMES = 'cloudframes'
    CLOUDSIGMA = 'cloudsigma'
    CLOUDSCALE = 'cloudscale'
    CLOUDSTACK = 'cloudstack'
    CLOUDWATT = 'cloudwatt'
    DIGITAL_OCEAN = 'digitalocean'
    DIMENSIONDATA = 'dimensiondata'
    EC2 = 'ec2'
    ECP = 'ecp'
    ELASTICHOSTS = 'elastichosts'
    EUCALYPTUS = 'eucalyptus'
    EXOSCALE = 'exoscale'
    GANDI = 'gandi'
    GCE = 'gce'
    GOGRID = 'gogrid'
    GRIDSPOT = 'gridspot'
    HOSTVIRTUAL = 'hostvirtual'
    IBM = 'ibm'
    IKOULA = 'ikoula'
    INDOSAT = 'indosat'
    INTERNETSOLUTIONS = 'internetsolutions'
    JOYENT = 'joyent'
    KTUCLOUD = 'ktucloud'
    LIBVIRT = 'libvirt'
    LINODE = 'linode'
    MEDONE = 'medone'
    NEPHOSCALE = 'nephoscale'
    NIMBUS = 'nimbus'
    NINEFOLD = 'ninefold'
    NTTA = 'ntta'
    OPENNEBULA = 'opennebula'
    OPENSTACK = 'openstack'
    OPSOURCE = 'opsource'
    OUTSCALE_INC = 'outscale_inc'
    OUTSCALE_SAS = 'outscale_sas'
    OVH = 'ovh'
    PACKET = 'packet'
    PROFIT_BRICKS = 'profitbricks'
    RACKSPACE = 'rackspace'
    RACKSPACE_FIRST_GEN = 'rackspace_first_gen'
    RIMUHOSTING = 'rimuhosting'
    RUNABOVE = 'runabove'
    SERVERLOVE = 'serverlove'
    SKALICLOUD = 'skalicloud'
    SOFTLAYER = 'softlayer'
    TERREMARK = 'terremark'
    VCL = 'vcl'
    VCLOUD = 'vcloud'
    VOXEL = 'voxel'
    VPSNET = 'vpsnet'
    VSPHERE = 'vsphere'
    VULTR = 'vultr'

    # OpenStack based providers
    CLOUDWATT = 'cloudwatt'
    HPCLOUD = 'hpcloud'
    KILI = 'kili'
    ONAPP = 'onapp'

    # Deprecated constants which aren't supported anymore
    RACKSPACE_UK = 'rackspace_uk'
    RACKSPACE_NOVA_BETA = 'rackspace_nova_beta'
    RACKSPACE_NOVA_DFW = 'rackspace_nova_dfw'
    RACKSPACE_NOVA_LON = 'rackspace_nova_lon'
    RACKSPACE_NOVA_ORD = 'rackspace_nova_ord'

    EC2_US_EAST = 'ec2_us_east'
    EC2_US_EAST_OHIO = 'ec2_us_east_ohio'
    EC2_EU = 'ec2_eu_west'  # deprecated name
    EC2_EU_WEST = 'ec2_eu_west'
    EC2_US_WEST = 'ec2_us_west'
    EC2_AP_SOUTHEAST = 'ec2_ap_southeast'
    EC2_AP_NORTHEAST = 'ec2_ap_northeast'
    EC2_AP_NORTHEAST1 = 'ec2_ap_northeast_1'
    EC2_AP_NORTHEAST2 = 'ec2_ap_northeast_2'
    EC2_US_WEST_OREGON = 'ec2_us_west_oregon'
    EC2_SA_EAST = 'ec2_sa_east'
    EC2_AP_SOUTHEAST2 = 'ec2_ap_southeast_2'

    ELASTICHOSTS_UK1 = 'elastichosts_uk1'
    ELASTICHOSTS_UK2 = 'elastichosts_uk2'
    ELASTICHOSTS_US1 = 'elastichosts_us1'
    ELASTICHOSTS_US2 = 'elastichosts_us2'
    ELASTICHOSTS_US3 = 'elastichosts_us3'
    ELASTICHOSTS_CA1 = 'elastichosts_ca1'
    ELASTICHOSTS_AU1 = 'elastichosts_au1'
    ELASTICHOSTS_CN1 = 'elastichosts_cn1'

    CLOUDSIGMA_US = 'cloudsigma_us'

    # Removed
    # SLICEHOST = 'slicehost'


DEPRECATED_RACKSPACE_PROVIDERS = [Provider.RACKSPACE_UK,
                                  Provider.RACKSPACE_NOVA_BETA,
                                  Provider.RACKSPACE_NOVA_DFW,
                                  Provider.RACKSPACE_NOVA_LON,
                                  Provider.RACKSPACE_NOVA_ORD]
OLD_CONSTANT_TO_NEW_MAPPING = {
    # Rackspace
    Provider.RACKSPACE_UK: Provider.RACKSPACE_FIRST_GEN,

    Provider.RACKSPACE_NOVA_BETA: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_DFW: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_LON: Provider.RACKSPACE,
    Provider.RACKSPACE_NOVA_ORD: Provider.RACKSPACE,

    # AWS
    Provider.EC2_US_EAST: Provider.EC2,
    Provider.EC2_US_EAST_OHIO: Provider.EC2,
    Provider.EC2_EU: Provider.EC2,
    Provider.EC2_EU_WEST: Provider.EC2,
    Provider.EC2_US_WEST: Provider.EC2,
    Provider.EC2_AP_SOUTHEAST: Provider.EC2,
    Provider.EC2_AP_SOUTHEAST2: Provider.EC2,
    Provider.EC2_AP_NORTHEAST: Provider.EC2,
    Provider.EC2_AP_NORTHEAST1: Provider.EC2,
    Provider.EC2_AP_NORTHEAST2: Provider.EC2,
    Provider.EC2_US_WEST_OREGON: Provider.EC2,
    Provider.EC2_SA_EAST: Provider.EC2,
    Provider.EC2_AP_SOUTHEAST: Provider.EC2,

    # ElasticHosts
    Provider.ELASTICHOSTS_UK1: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_UK2: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_US1: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_US2: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_US3: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_CA1: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_AU1: Provider.ELASTICHOSTS,
    Provider.ELASTICHOSTS_CN1: Provider.ELASTICHOSTS,
}


class NodeState(Type):
    """
    Standard states for a node

    :cvar RUNNING: Node is running.
    :cvar STARTING: Node is starting up.
    :cvar REBOOTING: Node is rebooting.
    :cvar TERMINATED: Node is terminated. This node can't be started later on.
    :cvar STOPPING: Node is currently trying to stop.
    :cvar STOPPED: Node is stopped. This node can be started later on.
    :cvar PENDING: Node is pending.
    :cvar SUSPENDED: Node is suspended.
    :cvar ERROR: Node is an error state. Usually no operations can be performed
                 on the node once it ends up in the error state.
    :cvar PAUSED: Node is paused.
    :cvar RECONFIGURING: Node is being reconfigured.
    :cvar UNKNOWN: Node state is unknown.
    """
    RUNNING = 'running'
    STARTING = 'starting'
    REBOOTING = 'rebooting'
    TERMINATED = 'terminated'
    PENDING = 'pending'
    UNKNOWN = 'unknown'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    SUSPENDED = 'suspended'
    ERROR = 'error'
    PAUSED = 'paused'
    RECONFIGURING = 'reconfiguring'
    MIGRATING = 'migrating'
    NORMAL = 'normal'


class StorageVolumeState(Type):
    """
    Standard states of a StorageVolume
    """
    AVAILABLE = 'available'
    ERROR = 'error'
    INUSE = 'inuse'
    CREATING = 'creating'
    DELETING = 'deleting'
    DELETED = 'deleted'
    BACKUP = 'backup'
    ATTACHING = 'attaching'
    UNKNOWN = 'unknown'
    MIGRATING = 'migrating'


class VolumeSnapshotState(Type):
    """
    Standard states of VolumeSnapshots
    """
    AVAILABLE = 'available'
    ERROR = 'error'
    CREATING = 'creating'
    DELETING = 'deleting'
    RESTORING = 'restoring'
    UNKNOWN = 'unknown'


class Architecture(object):
    """
    Image and size architectures.

    :cvar I386: i386 (32 bt)
    :cvar X86_64: x86_64 (64 bit)
    """
    I386 = 0
    X86_X64 = 1


class DeploymentError(LibcloudError):
    """
    Exception used when a Deployment Task failed.

    :ivar node: :class:`Node` on which this exception happened, you might want
                to call :func:`Node.destroy`
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


class KeyPairError(LibcloudError):
    error_type = 'KeyPairError'

    def __init__(self, name, driver):
        self.name = name
        self.value = 'Key pair with name %s does not exist' % (name)
        super(KeyPairError, self).__init__(value=self.value, driver=driver)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s name=%s, value=%s, driver=%s>' %
                (self.error_type, self.name, self.value, self.driver.name))


class KeyPairDoesNotExistError(KeyPairError):
    error_type = 'KeyPairDoesNotExistError'


"""Deprecated alias of :class:`DeploymentException`"""
DeploymentException = DeploymentError
