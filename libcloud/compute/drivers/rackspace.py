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
Rackspace driver
"""
from libcloud.compute.types import Provider
from libcloud.compute.base import NodeLocation
from libcloud.compute.drivers.openstack import OpenStack_1_0_Connection, OpenStack_1_0_NodeDriver, OpenStack_1_0_Response

from libcloud.common.rackspace import (
    AUTH_URL_US, AUTH_URL_UK)


class RackspaceConnection(OpenStack_1_0_Connection):
    """
    Connection class for the Rackspace driver
    """

    responseCls = OpenStack_1_0_Response
    auth_url = AUTH_URL_US
    XML_NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'


class RackspaceNodeDriver(OpenStack_1_0_NodeDriver):
    name = 'Rackspace'
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    api_name = 'rackspace'

    def list_locations(self):
        """Lists available locations

        Locations cannot be set or retrieved via the API, but currently
        there are two locations, DFW and ORD.
        """
        return [NodeLocation(0, "Rackspace DFW1/ORD1", 'US', self)]


class RackspaceUKConnection(RackspaceConnection):
    """
    Connection class for the Rackspace UK driver
    """
    auth_url = AUTH_URL_UK


class RackspaceUKNodeDriver(RackspaceNodeDriver):
    """Driver for Rackspace in the UK (London)
    """

    name = 'Rackspace (UK)'
    connectionCls = RackspaceUKConnection

    def list_locations(self):
        return [NodeLocation(0, 'Rackspace UK London', 'UK', self)]
