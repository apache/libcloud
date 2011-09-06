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
from xml.etree import ElementTree as ET

from libcloud.common.types import MalformedResponseError
from libcloud.compute.types import Provider
from libcloud.compute.base import NodeLocation
from libcloud.compute.drivers.openstack import OpenStackConnection, OpenStackNodeDriver, OpenStackResponse

from libcloud.common.rackspace import (
    AUTH_HOST_US, AUTH_HOST_UK)


# Is RackspaceResponse needed? parse_body seems enough like parent.
class RackspaceResponse(OpenStackResponse):

    def parse_body(self):
        if not self.body:
            return None
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError(
                "Failed to parse XML",
                body=self.body,
                driver=RackspaceNodeDriver)
        return body


class RackspaceConnection(OpenStackConnection):
    """
    Connection class for the Rackspace driver
    """

    responseCls = RackspaceResponse
    auth_host = AUTH_HOST_US


class RackspaceNodeDriver(OpenStackNodeDriver):
    name = 'Rackspace'
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE

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
    auth_host = AUTH_HOST_UK


class RackspaceUKNodeDriver(RackspaceNodeDriver):
    """Driver for Rackspace in the UK (London)
    """

    name = 'Rackspace (UK)'
    connectionCls = RackspaceUKConnection

    def list_locations(self):
        return [NodeLocation(0, 'Rackspace UK London', 'UK', self)]
