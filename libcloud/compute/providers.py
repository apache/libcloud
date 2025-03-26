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
Provider related utilities
"""


from types import ModuleType
from typing import TYPE_CHECKING, Type, Union

from libcloud.compute.types import OLD_CONSTANT_TO_NEW_MAPPING, Provider
from libcloud.common.providers import get_driver as _get_provider_driver
from libcloud.common.providers import set_driver as _set_provider_driver
from libcloud.compute.deprecated import DEPRECATED_DRIVERS

if TYPE_CHECKING:
    # NOTE: This is needed to avoid having setup.py depend on requests
    from libcloud.compute.base import NodeDriver

__all__ = ["Provider", "DRIVERS", "get_driver"]

DRIVERS = {
    Provider.ABIQUO: ("libcloud.compute.drivers.abiquo", "AbiquoNodeDriver"),
    Provider.ALIYUN_ECS: ("libcloud.compute.drivers.ecs", "ECSDriver"),
    Provider.AZURE: ("libcloud.compute.drivers.azure", "AzureNodeDriver"),
    Provider.AZURE_ARM: ("libcloud.compute.drivers.azure_arm", "AzureNodeDriver"),
    Provider.BRIGHTBOX: ("libcloud.compute.drivers.brightbox", "BrightboxNodeDriver"),
    Provider.CLOUDSCALE: ("libcloud.compute.drivers.cloudscale", "CloudscaleNodeDriver"),
    Provider.CLOUDSIGMA: ("libcloud.compute.drivers.cloudsigma", "CloudSigmaNodeDriver"),
    Provider.CLOUDSTACK: ("libcloud.compute.drivers.cloudstack", "CloudStackNodeDriver"),
    Provider.DIGITAL_OCEAN: ("libcloud.compute.drivers.digitalocean", "DigitalOceanNodeDriver"),
    Provider.DIMENSIONDATA: ("libcloud.compute.drivers.dimensiondata", "DimensionDataNodeDriver"),
    Provider.DUMMY: ("libcloud.compute.drivers.dummy", "DummyNodeDriver"),
    Provider.EC2: ("libcloud.compute.drivers.ec2", "EC2NodeDriver"),
    Provider.EQUINIXMETAL: ("libcloud.compute.drivers.equinixmetal", "EquinixMetalNodeDriver"),
    Provider.EUCALYPTUS: ("libcloud.compute.drivers.ec2", "EucNodeDriver"),
    Provider.EXOSCALE: ("libcloud.compute.drivers.exoscale", "ExoscaleNodeDriver"),
    Provider.GANDI: ("libcloud.compute.drivers.gandi", "GandiNodeDriver"),
    Provider.GCE: ("libcloud.compute.drivers.gce", "GCENodeDriver"),
    Provider.GIG_G8: ("libcloud.compute.drivers.gig_g8", "G8NodeDriver"),
    Provider.GRIDSCALE: ("libcloud.compute.drivers.gridscale", "GridscaleNodeDriver"),
    Provider.IKOULA: ("libcloud.compute.drivers.ikoula", "IkoulaNodeDriver"),
    Provider.KAMATERA: ("libcloud.compute.drivers.kamatera", "KamateraNodeDriver"),
    Provider.KTUCLOUD: ("libcloud.compute.drivers.ktucloud", "KTUCloudNodeDriver"),
    Provider.KUBEVIRT: ("libcloud.compute.drivers.kubevirt", "KubeVirtNodeDriver"),
    Provider.LIBVIRT: ("libcloud.compute.drivers.libvirt_driver", "LibvirtNodeDriver"),
    Provider.LINODE: ("libcloud.compute.drivers.linode", "LinodeNodeDriver"),
    Provider.MAXIHOST: ("libcloud.compute.drivers.maxihost", "MaxihostNodeDriver"),
    Provider.NIMBUS: ("libcloud.compute.drivers.ec2", "NimbusNodeDriver"),
    Provider.NTTA: ("libcloud.compute.drivers.ntta", "NTTAmericaNodeDriver"),
    Provider.NTTCIS: ("libcloud.compute.drivers.nttcis", "NttCisNodeDriver"),
    Provider.ONAPP: ("libcloud.compute.drivers.onapp", "OnAppNodeDriver"),
    Provider.OPENNEBULA: ("libcloud.compute.drivers.opennebula", "OpenNebulaNodeDriver"),
    Provider.OPENSTACK: ("libcloud.compute.drivers.openstack", "OpenStackNodeDriver"),
    Provider.OUTSCALE: ("libcloud.compute.drivers.outscale", "OutscaleNodeDriver"),
    Provider.OUTSCALE_INC: ("libcloud.compute.drivers.ec2", "OutscaleINCNodeDriver"),
    Provider.OUTSCALE_SAS: ("libcloud.compute.drivers.ec2", "OutscaleSASNodeDriver"),
    Provider.OVH: ("libcloud.compute.drivers.ovh", "OvhNodeDriver"),
    Provider.RACKSPACE: ("libcloud.compute.drivers.rackspace", "RackspaceNodeDriver"),
    Provider.RACKSPACE_FIRST_GEN: ("libcloud.compute.drivers.rackspace", "RackspaceFirstGenNodeDriver"),
    Provider.RIMUHOSTING: ("libcloud.compute.drivers.rimuhosting", "RimuHostingNodeDriver"),
    Provider.SCALEWAY: ("libcloud.compute.drivers.scaleway", "ScalewayNodeDriver"),
    Provider.TERREMARK: ("libcloud.compute.drivers.vcloud", "TerremarkDriver"),
    Provider.UPCLOUD: ("libcloud.compute.drivers.upcloud", "UpcloudDriver"),
    Provider.VCL: ("libcloud.compute.drivers.vcl", "VCLNodeDriver"),
    Provider.VCLOUD: ("libcloud.compute.drivers.vcloud", "VCloudNodeDriver"),
    Provider.VPSNET: ("libcloud.compute.drivers.vpsnet", "VPSNetNodeDriver"),
    Provider.VSPHERE: ("libcloud.compute.drivers.vsphere", "VSphereNodeDriver"),
    Provider.VULTR: ("libcloud.compute.drivers.vultr", "VultrNodeDriver"),
}


def get_driver(provider):
    # type: (Union[Provider, str]) -> Type[NodeDriver]
    deprecated_constants = OLD_CONSTANT_TO_NEW_MAPPING
    return _get_provider_driver(
        drivers=DRIVERS,
        provider=provider,
        deprecated_providers=DEPRECATED_DRIVERS,
        deprecated_constants=deprecated_constants,
    )


def set_driver(provider, module, klass):
    # type: (Union[Provider, str], ModuleType, type) -> Type[NodeDriver]
    return _set_provider_driver(drivers=DRIVERS, provider=provider, module=module, klass=klass)
