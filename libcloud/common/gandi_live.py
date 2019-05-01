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
Gandi Live driver base classes
"""

from libcloud.common.base import ConnectionKey, JsonResponse

__all__ = [
    'API_HOST',
    'GandiLiveException',
    'GandiLiveResponse',
    'BaseGandiLiveDriver',
]

API_HOST = 'dns.api.gandi.net'

class GandiLiveException(Exception):
    """
    Exception class for Gandi Live driver
    """
    def __str__(self):
        return '(%u) %s' % (self.args[0], self.args[1])

    def __repr__(self):
        return '<GandiLiveException code %u "%s">' % (self.args[0], self.args[1])


class GandiLiveResponse(JsonResponse):
    """
    A Base Gandi Live Response class to derive from.
    """


class GandiLiveConnection(ConnectionKey):
    """
    Connection class for the Gandi Live driver
    """

    responseCls = GandiLiveResponse
    host = API_HOST
    endpoint = '/api/v5/'

    def add_default_headers(self, headers):
        """
        Returns default headers as a dictionary.
        """
        headers["Content-Type"] = 'application/json'
        headers["X-Api-Key"] = self.key
        return headers


class BaseGandiLiveDriver(object):
    """
    Gandi Live base driver
    """
    connectionCls = GandiLiveConnection
    name = 'GandiLive'
