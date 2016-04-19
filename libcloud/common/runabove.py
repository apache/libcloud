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


import hashlib
import time

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.connection import get_response_object
from libcloud.common.types import InvalidCredsError
from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.httplib_ssl import LibcloudHTTPSConnection

__all__ = [
    'RunAboveResponse',
    'RunAboveConnection'
]

API_HOST = 'api.runabove.com'
API_ROOT = '/1.0'
LOCATIONS = {
    'SBG-1': {'id': 'SBG-1', 'name': 'Strasbourg 1', 'country': 'FR'},
    'BHS-1': {'id': 'BHS-1', 'name': 'Montreal 1', 'country': 'CA'}
}
DEFAULT_ACCESS_RULES = [
    {'method': 'GET', 'path': '/*'},
    {'method': 'POST', 'path': '/*'},
    {'method': 'PUT', 'path': '/*'},
    {'method': 'DELETE', 'path': '/*'},
]


class RunAboveException(Exception):
    pass


class RunAboveResponse(JsonResponse):
    def parse_error(self):
        response = super(RunAboveResponse, self).parse_body()
        response = response or {}

        if response.get('errorCode', None) == 'INVALID_SIGNATURE':
            raise InvalidCredsError('Signature validation failed, probably '
                                    'using invalid credentials')

        return self.body


class RunAboveConnection(ConnectionUserAndKey):
    """
    A connection to the RunAbove API

    Wraps SSL connections to the RunAbove API, automagically injecting the
    parameters that the API needs for each request.
    """
    host = API_HOST
    request_path = API_ROOT
    responseCls = RunAboveResponse
    timestamp = None
    ua = []
    LOCATIONS = LOCATIONS
    _timedelta = None

    allow_insecure = True

    def __init__(self, user_id, *args, **kwargs):
        self.consumer_key = kwargs.pop('ex_consumer_key', None)
        if self.consumer_key is None:
            consumer_key_json = self.request_consumer_key(user_id)
            msg = ("Your consumer key isn't validated, "
                   "go to '%(validationUrl)s' for valid it. After instantiate "
                   "your driver with \"ex_consumer_key='%(consumerKey)s'\"." %
                   consumer_key_json)
            raise RunAboveException(msg)
        super(RunAboveConnection, self).__init__(user_id, *args, **kwargs)

    def request_consumer_key(self, user_id):
        action = self.request_path + '/auth/credential'
        data = json.dumps({
            'accessRules': DEFAULT_ACCESS_RULES,
            'redirection': 'http://runabove.com',
        })
        headers = {
            'Content-Type': 'application/json',
            'X-Ra-Application': user_id,
        }
        httpcon = LibcloudHTTPSConnection(self.host)
        httpcon.request(method='POST', url=action, body=data, headers=headers)
        response = httpcon.getresponse()

        if response.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError()

        body = response.read()
        json_response = json.loads(body)
        httpcon.close()
        return json_response

    def get_timestamp(self):
        if not self._timedelta:
            url = 'https://%s/%s/auth/time' % (API_HOST, API_ROOT)
            response = get_response_object(url=url, method='GET', headers={})
            if not response or not response.body:
                raise Exception('Failed to get current time from RunAbove API')

            timestamp = int(response.body)
            self._timedelta = timestamp - int(time.time())
        return int(time.time()) + self._timedelta

    def make_signature(self, method, action, data, timestamp):
        full_url = 'https://%s%s' % (API_HOST, action)
        sha1 = hashlib.sha1()
        base_signature = "+".join([
            self.key,
            self.consumer_key,
            method.upper(),
            full_url,
            data if data else '',
            str(timestamp),
        ])
        sha1.update(base_signature.encode())
        signature = '$1$' + sha1.hexdigest()
        return signature

    def add_default_params(self, params):
        return params

    def add_default_headers(self, headers):
        headers.update({
            'X-Ra-Application': self.user_id,
            'X-Ra-Consumer': self.consumer_key,
            'Content-type': 'application/json',
        })
        return headers

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False):
        data = json.dumps(data) if data else None
        timestamp = self.get_timestamp()
        signature = self.make_signature(method, action, data, timestamp)
        headers = headers or {}
        headers.update({
            'X-Ra-Timestamp': timestamp,
            'X-Ra-Signature': signature
        })
        return super(RunAboveConnection, self)\
            .request(action, params=params, data=data, headers=headers,
                     method=method, raw=raw)
