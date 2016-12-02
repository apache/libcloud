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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib

from libcloud.common.types import InvalidCredsError
from libcloud.compute.types import Provider
from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.base import BaseDriver

API_HOST = 'api.ctl.io'

__all__ = [
    "CLCResponse",
    "CLCConnection",
    "CLCBaseDriver",
]

class CLCResponse(JsonResponse):
    """
    Response class for the CLC driver
    """
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def __init__(self, *args, **kwargs):
        self.driver = CLCBaseDriver
        super(CLCResponse, self).__init__(*args, **kwargs)

    def parse_error(self):
        error = 'HTTP %s' % self.status
        body = self.parse_body()
        if isinstance(body, dict):
            error = body.get('message', error)
        return error

    def success(self):
        return self.status in self.valid_response_codes


class CLCConnection(ConnectionUserAndKey):
    """
    Connection class for the CLC driver
    """

    host = API_HOST
    responseCls = CLCResponse

    def __init__(self, *args, **kw):
        self._token = kw.get('token')
        self._alias = kw.get('alias')
        # monkey-patch self.request to get a token
        self._request = self.request
        self.request = self.request_authenticated
        super(CLCConnection, self).__init__(*args, **kw)

    def authenticate(self):
        """
        Authenticate with login credentials
        """
        creds = dict(username=self.user_id, password=self.key)
        resp = self._request(
            '/v2/authentication/login',
            data=json.dumps(creds),
            method='POST')
        if not resp.success():
            raise InvalidCredsError(resp.body)
        resp = resp.parse_body()
        self._alias = self._alias or resp['accountAlias']
        self._token = resp['bearerToken']
        return resp

    def request_authenticated(self, *args, **kw):
        """
        Lazy authenticating wrapper for :attr:`request`
        """
        if not self._token:
            self.authenticate()
        return self._request(*args, **kw)

    def add_default_headers(self, headers):
        """
        Adds vendor headers:
        - authorization header when token present
        - api client
        """
        if self._token:
            headers['Authorization'] = 'Bearer %s' % (self._token)
        headers['Content-Type'] = 'application/json'
        headers['Api-Client'] = self._user_agent()
        return headers



class CLCBaseDriver(BaseDriver):
    """
    CLC BaseDriver
    """
    connectionCls = CLCConnection
    type = Provider.CLC
    host = API_HOST
    api_name = 'clc'
    name = 'CLC'
    website = 'https://www.ctl.io'

    def __init__(self, *args, **kw):
        super(CLCBaseDriver, self).__init__(*args, **kw)
        self.connection._token = kw.get('token')
        self.connection._alias = kw.get('alias')

    @property
    def alias(self):
        """
        Returns account alias. If this instance was

        :rtype: ``str``
        """
        if not self.connection._alias:
            self.connection.authenticate()
        return self.connection._alias

    def get_links(self, tag, links):
        """
        Return matching links for rel=`tag`

        :param tag: rel tag of link
        :type tag: ``str``

        :param links: list of links
        :type links: ``list``

        :rtype: ``list``
        """
        ret = []
        for l in links:
            if l['rel'] != tag:
                continue
            href = l.get('href')
            if href:
                ret.append(href)
            else:
                ret.append(id)
        return ret
