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

from libcloud.utils.py3 import urlencode
from libcloud.utils.py3 import b

from libcloud.common.base import ConnectionUserAndKey, PollingConnection
from libcloud.common.base import JsonResponse
from libcloud.common.types import MalformedResponseError


class CloudStackResponse(JsonResponse):
    pass


class CloudStackConnection(ConnectionUserAndKey, PollingConnection):
    responseCls = CloudStackResponse
    poll_interval = 1
    request_method = '_sync_request'
    timeout = 600

    ASYNC_PENDING = 0
    ASYNC_SUCCESS = 1
    ASYNC_FAILURE = 2

    def _make_signature(self, params):
        signature = [(k.lower(), v) for k, v in list(params.items())]
        signature.sort(key=lambda x: x[0])
        signature = urlencode(signature)
        signature = signature.lower().replace('+', '%20')
        signature = hmac.new(b(self.key), msg=b(signature), digestmod=hashlib.sha1)
        return base64.b64encode(b(signature.digest()))

    def add_default_params(self, params):
        params['apiKey'] = self.user_id
        params['response'] = 'json'

        return params

    def pre_connect_hook(self, params, headers):
        params['signature'] = self._make_signature(params)

        return params, headers

    def _async_request(self, command, **kwargs):
        context = {'command': command}
        context.update(kwargs)
        result = super(CloudStackConnection, self).async_request(action=None,
                                                               params=None,
                                                               data=None,
                                                               headers=None,
                                                               method=None,
                                                               context=context)
        return result['jobresult']

    def get_request_kwargs(self, action, params=None, data='', headers=None,
                           method='GET', context=None):
        return context

    def get_poll_request_kwargs(self, response, context, request_kwargs):
        job_id = response['jobid']
        kwargs = {'command': 'queryAsyncJobResult', 'jobid': job_id}
        return kwargs

    def has_completed(self, response):
        status = response.get('jobstatus', self.ASYNC_PENDING)

        if status == self.ASYNC_FAILURE:
            raise Exception(status)

        return status == self.ASYNC_SUCCESS

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


class CloudStackDriverMixIn(object):
    host = None
    path = None

    connectionCls = CloudStackConnection

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
        host = host or self.host
        super(CloudStackDriverMixIn, self).__init__(key, secret, secure, host,
                                                    port)

    def _sync_request(self, command, **kwargs):
        return self.connection._sync_request(command, **kwargs)

    def _async_request(self, command, **kwargs):
        return self.connection._async_request(command, **kwargs)
