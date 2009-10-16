# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
from libcloud.types import Provider
from libcloud.drivers.linode import LinodeNodeDriver as Linode
from libcloud.drivers.slicehost import SlicehostNodeDriver as Slicehost
from libcloud.drivers.rackspace import RackspaceNodeDriver as Rackspace

DRIVERS = {
#    Provider.DUMMY:
#        ('libcloud.drivers.dummy', 'DummyNodeDriver'),
    Provider.EC2:
        ('libcloud.drivers.ec2', 'EC2NodeDriver'),
    Provider.EC2_EU:
        ('libcloud.drivers.ec2', 'EC2EUNodeDriver'),
#    Provider.GOGRID:
#        ('libcloud.drivers.gogrid', 'GoGridNodeDriver'),
    Provider.RACKSPACE:
        ('libcloud.drivers.rackspace', 'RackspaceNodeDriver'),
    Provider.SLICEHOST:
        ('libcloud.drivers.slicehost', 'SlicehostNodeDriver'),
    Provider.VPSNET:
        ('libcloud.drivers.vpsnet', 'VPSNetNodeDriver'),
    Provider.LINODE:
        ('libcloud.drivers.linode', 'LinodeNodeDriver'),
    Provider.RIMUHOSTING:
        ('libcloud.drivers.rimuhosting', 'RimuHostingNodeDriver')
}

def get_driver(provider):
    if provider in DRIVERS:
        mod_name, driver_name = DRIVERS[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)
