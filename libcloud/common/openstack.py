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
from libcloud.compute.types import InvalidCredsError, MalformedResponseError

AUTH_API_VERSION = 'v1.0'

__all__ = [
    "OpenstackBaseConnection",
    ]

class OpenstackBaseConnection(ConnectionUserAndKey):
    def __init__(self, user_id, key, secure):
        self.auth_token = None
        self.__host = None
        super(OpenstackBaseConnection, self).__init__(
            user_id, key, secure=secure)

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.auth_token
        headers['Accept'] = self.accept_format
        return headers

    @property
    def request_path(self):
        return self._get_request_path(url_key=self._url_key)

    @property
    def host(self):
        # Default to server_host
        return self._get_host(url_key=self._url_key)

    def _get_request_path(self, url_key):
        value_key = '__request_path_%s' % (url_key)
        value = getattr(self, value_key, None)

        if not value:
            self._populate_hosts_and_request_paths()
            value = getattr(self, value_key, None)

        return value

    def _get_host(self, url_key):
        value_key = '__%s' % (url_key)
        value = getattr(self, value_key, None)

        if not value:
            self._populate_hosts_and_request_paths()
            value = getattr(self, value_key, None)

        return value

    def _populate_hosts_and_request_paths(self):
        """
        Openstack uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.
        """
        if not self.auth_token:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](
                self.auth_host, self.port[self.secure])
            conn.request(
                method='GET',
                url='/%s' % (AUTH_API_VERSION),
                headers={
                    'X-Auth-User': self.user_id,
                    'X-Auth-Key': self.key
                }
            )

            resp = conn.getresponse()
            if resp.status == httplib.NO_CONTENT:
                # HTTP NO CONTENT (204): auth successful
                headers = dict(resp.getheaders())
                try:
                    self.auth_token = headers['x-auth-token']
                    for class_key, response_key in self.auth_headers_keys.iteritems():
                        if getattr(self, class_key, False) is False:
                            setattr(self, class_key, headers[response_key])
                except KeyError, e:
                    # Returned 204 but has missing information in the header, something is wrong
                    raise MalformedResponseError('Malformed response',
                                                 body='Missing header: %s' % (str(e)),
                                                 driver=self.driver)
            elif resp.status == httplib.UNAUTHORIZED:
                # HTTP UNAUTHORIZED (401): auth failed
                raise InvalidCredsError()
            else:
                # Any response code != 401 or 204, something is wrong
                raise MalformedResponseError('Malformed response',
                        body='code: %s body:%s' % (resp.status, ''.join(resp.body.readlines())),
                        driver=self.driver)

            for key in self.auth_headers_keys.keys():
                print getattr(self,key)
                scheme, server, request_path, param, query, fragment = (
                    urlparse.urlparse(getattr(self, key)))
                # Set host to where we want to make further requests to
                setattr(self, '__%s' % (key), server)
                setattr(self, '__request_path_%s' % (key), request_path)

            conn.close()
