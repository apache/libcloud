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
import sys
import unittest

class BackwardCompatibilityTests(unittest.TestCase):
    def test_all_the_old_paths_works(self):
        # Common
        from libcloud.types import InvalidCredsError
        from libcloud.base import Node, NodeImage, NodeSize, NodeLocation
        from libcloud.types import NodeState
        from libcloud.types import LibcloudError

        from libcloud.base import Response
        from libcloud.base import ConnectionKey, ConnectionUserAndKey
        from libcloud.base import NodeAuthPassword

        # Driver specific
        from libcloud.drivers.brightbox import BrightboxNodeDriver
        from libcloud.drivers.cloudsigma import CloudSigmaZrhNodeDriver
        from libcloud.drivers.rimuhosting import RimuHostingNodeDriver
        from libcloud.drivers.elastichosts import ElasticHostsBaseNodeDriver
        from libcloud.drivers.gogrid import GoGridNodeDriver
        from libcloud.common.gogrid import GoGridIpAddress
        from libcloud.drivers.linode import LinodeNodeDriver
        from libcloud.drivers.vpsnet import VPSNetNodeDriver
        from libcloud.drivers.opennebula import OpenNebulaNodeDriver
        from libcloud.drivers.ibm_sbc import IBMNodeDriver as IBM
        from libcloud.drivers.rackspace import RackspaceNodeDriver as Rackspace
        from libcloud.drivers.ec2 import EC2NodeDriver, EC2APSENodeDriver
        from libcloud.drivers.ec2 import EC2APNENodeDriver, IdempotentParamError
        from libcloud.drivers.voxel import VoxelNodeDriver as Voxel
        from libcloud.drivers.vcloud import TerremarkDriver
        from libcloud.drivers.vcloud import VCloudNodeDriver
        from libcloud.drivers.slicehost import SlicehostNodeDriver as Slicehost
        from libcloud.drivers.softlayer import SoftLayerNodeDriver as SoftLayer
        from libcloud.drivers.ecp import ECPNodeDriver

        from libcloud.drivers.cloudsigma import str2dicts, str2list, dict2str

if __name__ == '__main__':
    sys.exit(unittest.main())
