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
Common utilities for Rackspace Cloud Servers and Cloud Files
"""
import httplib
from urllib2 import urlparse
from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.openstack import OpenstackBaseConnection
from libcloud.compute.types import InvalidCredsError, MalformedResponseError

AUTH_HOST_US='auth.api.rackspacecloud.com'
AUTH_HOST_UK='lon.auth.api.rackspacecloud.com'
AUTH_API_VERSION = 'v1.0'

__all__ = [
    "RackspaceBaseConnection",
    "AUTH_HOST_US",
    "AUTH_HOST_UK"
    ]

class RackspaceBaseConnection(OpenstackBaseConnection):
    def __init__(self, user_id, key, secure):
        self.cdn_management_url = None
        self.storage_url = None
        self.auth_token = None
        self.__host = None
        super(RackspaceBaseConnection, self).__init__(
            user_id, key, secure=secure)
