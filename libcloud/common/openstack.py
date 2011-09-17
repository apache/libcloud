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
Common utilities for OpenStack
"""
import httplib
from urllib2 import urlparse
from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.compute.types import LibcloudError, InvalidCredsError, MalformedResponseError

try:
    import simplejson as json
except ImportError:
    import json

AUTH_API_VERSION = 'v1.0'

__all__ = [
    "OpenStackBaseConnection",
    "OpenStackAuthConnection",
    ]


# @TODO: Refactor for re-use by other openstack drivers
class OpenStackAuthResponse(Response):
    def success(self):
        return True

    def parse_body(self):
        if not self.body:
            return None

        if 'content-type' in self.headers:
            key = 'content-type'
        elif 'Content-Type' in self.headers:
            key = 'Content-Type'
        else:
            raise LibcloudError('Missing content-type header', driver=OpenStackAuthConnection)

        content_type = self.headers[key]
        if content_type.find(';') != -1:
            content_type = content_type.split(';')[0]

        if content_type == 'application/json':
            try:
                data = json.loads(self.body)
            except:
                raise MalformedResponseError('Failed to parse JSON',
                                             body=self.body,
                                             driver=OpenStackAuthConnection)
        elif content_type == 'text/plain':
            data = self.body
        else:
            data = self.body

        return data

class OpenStackAuthConnection(ConnectionUserAndKey):

    responseCls = OpenStackAuthResponse
    name = 'OpenStack Auth'

    def __init__(self, parent_conn, auth_url, user_id, key):
        self.parent_conn = parent_conn
        # enable tests to use the same mock connection classes.
        self.conn_classes = parent_conn.conn_classes

        super(OpenStackAuthConnection, self).__init__(
            user_id, key, url=auth_url)

        self.auth_url = auth_url
        self.urls = {}
        self.driver = self.parent_conn.driver

    def add_default_headers(self, headers):
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json; charset=UTF-8'
        return headers

    def authenticate(self):
        reqbody = json.dumps({'credentials': {'username': self.user_id, 'key': self.key}})
        resp = self.request("/auth",
                    data=reqbody,
                    headers={
                        'X-Auth-User': self.user_id,
                        'X-Auth-Key': self.key,
                    },
                    method='POST')

        if resp.status == httplib.UNAUTHORIZED:
            # HTTP UNAUTHORIZED (401): auth failed
            raise InvalidCredsError()
        elif resp.status != httplib.OK:
            raise MalformedResponseError('Malformed response',
                    body='code: %s body:%s' % (resp.status, resp.body),
                    driver=self.driver)
        else:
            try:
                body = json.loads(resp.body)
            except Exception, e:
                raise MalformedResponseError('Failed to parse JSON', e)
            try:
                self.auth_token = body['auth']['token']['id']
                self.urls = body['auth']['serviceCatalog']
            except KeyError, e:
                raise MalformedResponseError('Auth JSON response is missing required elements', e)

class OpenStackBaseConnection(ConnectionUserAndKey):

    auth_url = None

    def __init__(self, user_id, key, secure=True,
                 host=None, port=None, ex_force_base_url=None):
        self.server_url = None
        self.cdn_management_url = None
        self.storage_url = None
        self.lb_url = None
        self.auth_token = None
        self._force_base_url = ex_force_base_url
        super(OpenStackBaseConnection, self).__init__(
            user_id, key)

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.auth_token
        headers['Accept'] = self.accept_format
        return headers

    def morph_action(self, action):
        key = self._url_key

        value = getattr(self, key, None)
        if not value:
            self._populate_hosts_and_request_paths()

        request_path = getattr(self, '__request_path_%s' % (key), '')
        action = request_path + action
        return action

    @property
    def base_url(self):
        return self._get_base_url(url_key=self._url_key)

    def _get_base_url(self, url_key):
        value = getattr(self, url_key, None)
        if not value:
            self._populate_hosts_and_request_paths()
            value = getattr(self, url_key, None)
        if self._force_base_url != None:
            value = self._force_base_url
        return value

    def _get_default_region(self, arr):
        if len(arr):
            for i in arr:
                if i.get('v1Default', False):
                    return i['publicURL']
            # uber lame
            return arr[0]
        return None

    def request(self, **kwargs):
        self._populate_hosts_and_request_paths()
        return super(OpenStackBaseConnection, self).request(**kwargs)

    def _populate_hosts_and_request_paths(self):
        """
        OpenStack uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.
        """
        if not self.auth_token:
            if self.auth_url == None:
                raise LibcloudError('OpenStack instance must have auth_url set')

            osa = OpenStackAuthConnection(self, self.auth_url, self.user_id, self.key)

            # may throw InvalidCreds, etc
            osa.authenticate()

            self.auth_token = osa.auth_token

            # TODO: Multi-region support
            self.server_url = self._get_default_region(osa.urls.get('cloudServers', []))
            self.cdn_management_url = self._get_default_region(osa.urls.get('cloudFilesCDN', []))
            self.storage_url = self._get_default_region(osa.urls.get('cloudFiles', []))
            # TODO: this is even more broken, the service catalog does NOT show load
            # balanacers :(  You must hard code in the Rackspace Load balancer URLs...
            self.lb_url = self.server_url.replace("servers", "ord.loadbalancers")

            for key in ['server_url', 'storage_url', 'cdn_management_url',
                        'lb_url']:
                base_url = None
                if self._force_base_url != None:
                    base_url = self._force_base_url
                else:
                    base_url = getattr(self, key)

                scheme, server, request_path, param, query, fragment = (
                    urlparse.urlparse(base_url))
                # Set host to where we want to make further requests to
                setattr(self, '__%s' % (key), server)
                setattr(self, '__request_path_%s' % (key), request_path)

            (self.host, self.port, self.secure, self.request_path) = self._tuple_from_url(self.base_url)
