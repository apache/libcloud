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

import base64
import hashlib
import hmac
import time
import urllib

try:
    import simplejson as json
except:
    import json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.common.types import MalformedResponseError

class CloudStackResponse(Response):
    def parse_body(self):
        try:
            body = json.loads(self.body)
        except:
            raise MalformedResponseError(
                "Failed to parse JSON",
                body=self.body,
                driver=self.connection.driver)
        return body

    parse_error = parse_body

class CloudStackConnection(ConnectionUserAndKey):
    responseCls = CloudStackResponse

    ASYNC_PENDING = 0
    ASYNC_SUCCESS = 1
    ASYNC_FAILURE = 2

    def _make_signature(self, params):
        signature = [(k.lower(), v) for k, v in params.items()]
        signature.sort(key=lambda x: x[0])
        signature = urllib.urlencode(signature)
        signature = signature.lower().replace('+', '%20')
        signature = hmac.new(self.key, msg=signature, digestmod=hashlib.sha1)
        return base64.b64encode(signature.digest())

    def add_default_params(self, params):
        params['apiKey'] = self.user_id
        params['response'] = 'json'

        return params

    def pre_connect_hook(self, params, headers):
        params['signature'] = self._make_signature(params)

        return params, headers

    def _sync_request(self, command, **kwargs):
        """This method handles synchronous calls which are generally fast
           information retrieval requests and thus return 'quickly'."""

        kwargs['command'] = command
        result = self.request(self.driver.path, params=kwargs)
        command = command.lower() + 'response'
        if command not in result.object:
            raise MalformedResponseError(
                "Unknown response format",
                body=result.body,
                driver=self.driver)
        result = result.object[command]
        return result

    def _async_request(self, command, **kwargs):
        """This method handles asynchronous calls which are generally
           requests for the system to do something and can thus take time.

           In these cases the initial call will either fail fast and return
           an error, or it can return a job ID.  We then poll for the status
           of the job ID which can either be pending, successful or failed."""

        result = self._sync_request(command, **kwargs)
        job_id = result['jobid']
        success = True

        while True:
            result = self._sync_request('queryAsyncJobResult', jobid=job_id)
            status = result.get('jobstatus', self.ASYNC_PENDING)
            if status != self.ASYNC_PENDING:
                break
            time.sleep(self.driver.async_poll_frequency)

        if result['jobstatus'] == self.ASYNC_FAILURE:
            raise Exception(result)

        return result['jobresult']

class CloudStackDriverMixIn(object):
    host = None
    path = None
    async_poll_frequency = 1

    connectionCls = CloudStackConnection

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        host = host or self.host
        super(CloudStackDriverMixIn, self).__init__(key, secret, secure, host,
                                                    port)

    def _sync_request(self, command, **kwargs):
        return self.connection._sync_request(command, **kwargs)

    def _async_request(self, command, **kwargs):
        return self.connection._async_request(command, **kwargs)
