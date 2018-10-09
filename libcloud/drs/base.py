
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

from libcloud.common.base import ConnectionKey, BaseDriver
from libcloud.common.types import LibcloudError


class DRSConsistencyGroup(object):
    """
    Provide a common interface for handling DRS.
    """

    def __init__(self, id, name, description, journalSizeGB,  serverPairSourceServerId, serverPairtargetServerId,
                 driver, extra=None):
        """
        :param id: Load balancer ID.
        :type id: ``str``

        :param name: Load balancer name.
        :type name: ``str``

        :param state: State this loadbalancer is in.
        :type state: :class:`libcloud.loadbalancer.types.State`

        :param ip: IP address of this loadbalancer.
        :type ip: ``str``

        :param port: Port of this loadbalancer.
        :type port: ``int``

        :param driver: Driver this loadbalancer belongs to.
        :type driver: :class:`.Driver`

        :param extra: Provider specific attributes. (optional)
        :type extra: ``dict``
        """
        self.id = str(id) if id else None
        self.name = name
        self.description = description
        self.journalSizeGB = journalSizeGB

        self.serverPairSourceServerId = serverPairSourceServerId
        self.serverPairtargetServerId = serverPairtargetServerId
        self.driver = driver
        self.extra = extra or {}


class Driver(BaseDriver):
    """
    A base Driver class to derive from

    This class is always subclassed by a specific driver.
    """

    name = None
    website = None

    connectionCls = ConnectionKey

    def __init__(self, key, secret=None, secure=True, host=None,
                 port=None, **kwargs):
        super(Driver, self).__init__(key=key, secret=secret, secure=secure,
                                     host=host, port=port, **kwargs)
