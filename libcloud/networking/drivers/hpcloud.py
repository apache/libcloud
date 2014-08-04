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
HP Changed enough superficial pieces of OpenStack that we have to override most
bits just to use a different name here and there.
"""

from libcloud.networking.types import Provider
from libcloud.networking.drivers.openstack import OpenStackNeutronConnection
from libcloud.networking.drivers.openstack import \
    OpenStackNeutronNetworkingDriver

__all__ = [
    'HPCloudConnection',
    'HPCloudNetworkingDriver'
]


class HPCloudConnection(OpenStackNeutronConnection):
    """
    Connection class for network API for HPCloud - based on Neutron
    """
    service_name = 'Networking'


class HPCloudNetworkingDriver(OpenStackNeutronNetworkingDriver):
    """
    OpenStack network driver for HPCloud - based on Neutron
    """
    api_name = 'hpcloud_neutron'
    name = 'HPCloud Neutron'
    website = 'https://docs.hpcloud.com/api/'

    connectionCls = HPCloudConnection
    type = Provider.HPCLOUD
