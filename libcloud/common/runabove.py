# licensed to the apache software foundation (asf) under one or more
# contributor license agreements.  see the notice file distributed with
# this work for additional information regarding copyright ownership.
# the asf licenses this file to you under the apache license, version 2.0
# (the "license"); you may not use this file except in compliance with
# the license.  you may obtain a copy of the license at
#
#     http://www.apache.org/licenses/license-2.0
#
# unless required by applicable law or agreed to in writing, software
# distributed under the license is distributed on an "as is" basis,
# without warranties or conditions of any kind, either express or implied.
# see the license for the specific language governing permissions and
# limitations under the license.

import hashlib
import time
try:
    import simplejson as json
except ImportError:
    import json
from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.httplib_ssl import LibcloudHTTPSConnection

API_HOST = 'api.runabove.com'
API_ROOT = '/1.0'
LOCATIONS = {
    'SBG-1': {'id': 'SBG-1', 'name': 'Strasbourg 1', 'country': 'FR'},
    'BHS-1': {'id': 'BHS-1', 'name': 'Montreal 1', 'country': 'CA'}
}
DEFAULT_ACCESS_RULES = [
    {"method": "GET", "path": "/*"},
    {"method": "POST", "path": "/*"},
    {"method": "PUT", "path": "/*"},
    {"method": "DELETE", "path": "/*"},
]


class RunAboveException(Exception):
    pass


class RunAboveConnection(ConnectionUserAndKey):
    """
    A connection to the RunAbove API

    Wraps SSL connections to the RunAbove API, automagically injecting the
    parameters that the API needs for each request.
    """
    host = API_HOST
    request_path = API_ROOT
    responseCls = JsonResponse
    timestamp = None
    ua = []
    LOCATIONS = LOCATIONS
    _timedelta = None

    allow_insecure = True

    def __init__(self, user_id, *args, **kwargs):
        self.consumer_key = kwargs.pop('ex_consumer_key', None)
        if self.consumer_key is None:
            consumer_key_json = self.request_consumer_key(user_id)
            msg = "Your consumer key isn't validated, " \
                "go to '{validationUrl}' for valid it. After instantiate " \
                "your driver with \"ex_consumer_key='{consumerKey}'\"."\
                .format(**consumer_key_json)
            raise RunAboveException(msg)
        super(RunAboveConnection, self).__init__(user_id, *args, **kwargs)

    def request_consumer_key(self, user_id):
        action = self.request_path + '/auth/credential'
        data = json.dumps({
            "accessRules": DEFAULT_ACCESS_RULES,
            "redirection": "http://runabove.com",
        })
        headers = {
            'Content-Type': 'application/json',
            'X-Ra-Application': user_id,
        }
        httpcon = LibcloudHTTPSConnection(self.host)
        httpcon.request(method='POST', url=action, body=data, headers=headers)
        response = httpcon.getresponse().read()
        json_response = json.loads(response)
        httpcon.close()
        return json_response

    def get_timestamp(self):
        if not self._timedelta:
            action = API_ROOT + '/auth/time'
            response = self.connection.request('GET', action, headers={})
            timestamp = int(response)
            self._time_delta = timestamp - int(time.time())
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
            "X-Ra-Application": self.user_id,
            "X-Ra-Consumer": self.consumer_key,
            "Content-type": "application/json",
        })
        return headers

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False):
        data = json.dumps(data) if data else None
        timestamp = self.get_timestamp()
        signature = self.make_signature(method, action, data, timestamp)
        headers = headers or {}
        headers.update({
            "X-Ra-Timestamp": timestamp,
            "X-Ra-Signature": signature
        })
        return super(RunAboveConnection, self)\
            .request(action, params=params, data=data, headers=headers,
                     method=method, raw=raw)
