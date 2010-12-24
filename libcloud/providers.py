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

from libcloud.types import Provider

DRIVERS = {
    Provider.DUMMY:
        ('libcloud.drivers.dummy', 'DummyNodeDriver'),
    Provider.EC2_US_EAST:
        ('libcloud.drivers.ec2', 'EC2NodeDriver'),
    Provider.EC2_EU_WEST:
        ('libcloud.drivers.ec2', 'EC2EUNodeDriver'),
    Provider.EC2_US_WEST:
        ('libcloud.drivers.ec2', 'EC2USWestNodeDriver'),
    Provider.EC2_AP_SOUTHEAST:
        ('libcloud.drivers.ec2', 'EC2APSENodeDriver'),
    Provider.ECP:
        ('libcloud.drivers.ecp', 'ECPNodeDriver'),
    Provider.ELASTICHOSTS_UK1:
        ('libcloud.drivers.elastichosts', 'ElasticHostsUK1NodeDriver'),
    Provider.ELASTICHOSTS_UK2:
        ('libcloud.drivers.elastichosts', 'ElasticHostsUK2NodeDriver'),
    Provider.ELASTICHOSTS_US1:
        ('libcloud.drivers.elastichosts', 'ElasticHostsUS1NodeDriver'),
    Provider.CLOUDSIGMA:
        ('libcloud.drivers.cloudsigma', 'CloudSigmaZrhNodeDriver'),
    Provider.GOGRID:
        ('libcloud.drivers.gogrid', 'GoGridNodeDriver'),
    Provider.RACKSPACE:
        ('libcloud.drivers.rackspace', 'RackspaceNodeDriver'),
    Provider.RACKSPACE_UK:
        ('libcloud.drivers.rackspace', 'RackspaceUKNodeDriver'),
    Provider.SLICEHOST:
        ('libcloud.drivers.slicehost', 'SlicehostNodeDriver'),
    Provider.VPSNET:
        ('libcloud.drivers.vpsnet', 'VPSNetNodeDriver'),
    Provider.LINODE:
        ('libcloud.drivers.linode', 'LinodeNodeDriver'),
    Provider.RIMUHOSTING:
        ('libcloud.drivers.rimuhosting', 'RimuHostingNodeDriver'),
    Provider.VOXEL:
        ('libcloud.drivers.voxel', 'VoxelNodeDriver'),
    Provider.SOFTLAYER:
        ('libcloud.drivers.softlayer', 'SoftLayerNodeDriver'),
    Provider.EUCALYPTUS:
        ('libcloud.drivers.ec2', 'EucNodeDriver'),
    Provider.IBM:
        ('libcloud.drivers.ibm_sbc', 'IBMNodeDriver'),
    Provider.OPENNEBULA:
        ('libcloud.drivers.opennebula', 'OpenNebulaNodeDriver'),
    Provider.DREAMHOST:
        ('libcloud.drivers.dreamhost', 'DreamhostNodeDriver'),
    Provider.BRIGHTBOX:
        ('libcloud.drivers.brightbox', 'BrightboxNodeDriver'),
}

def get_driver(provider):
    """Gets a driver
    @param provider: Id of provider to get driver
    @type provider: L{libcloud.types.Provider}
    """
    if provider in DRIVERS:
        mod_name, driver_name = DRIVERS[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)
