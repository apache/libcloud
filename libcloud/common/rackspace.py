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
from libcloud.compute.types import InvalidCredsError

AUTH_HOST_US='auth.api.rackspacecloud.com'
AUTH_HOST_UK='lon.auth.api.rackspacecloud.com'
AUTH_API_VERSION = 'v1.0'

class RackspaceBaseConnection(ConnectionUserAndKey):
    def __init__(self, user_id, key, secure):
        self.cdn_management_url = None
        self.storage_url = None
        self.auth_token = None
        self.request_path = None
        self.__host = None
        super(RackspaceBaseConnection, self).__init__(user_id, key, secure=secure)

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.auth_token
        headers['Accept'] = self.accept_format
        return headers

    @property
    def host(self):
        """
        Rackspace uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.
        """
        if not self.__host:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](self.auth_host, self.port[self.secure])
            conn.request(
                method='GET',
                url='/%s' % (AUTH_API_VERSION),
                headers={
                    'X-Auth-User': self.user_id,
                    'X-Auth-Key': self.key
                }
            )

            resp = conn.getresponse()

            if resp.status != httplib.NO_CONTENT:
                raise InvalidCredsError()

            headers = dict(resp.getheaders())

            try:
                self.server_url = headers['x-server-management-url']
                self.storage_url = headers['x-storage-url']
                self.cdn_management_url = headers['x-cdn-management-url']
                self.auth_token = headers['x-auth-token']
            except KeyError:
                raise InvalidCredsError()

            scheme, server, self.request_path, param, query, fragment = (
                urlparse.urlparse(getattr(self, self._url_key))
            )

            if scheme is "https" and self.secure is not True:
                raise InvalidCredsError()

            # Set host to where we want to make further requests to;
            self.__host = server
            conn.close()

        return self.__host
