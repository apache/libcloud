import base64
import hashlib
import hmac
import time
import urllib

try:
    import json
except:
    import simplejson as json

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

class CloudStackConnection(ConnectionUserAndKey):
    responseCls = CloudStackResponse

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
        "Make a synchronous API request. These return immediately."

        kwargs['command'] = command
        result = self.request(self.driver.path, params=kwargs).object
        command = command.lower() + 'response'
        if command not in result:
            raise MalformedResponseError(
                "Unknown response format",
                body=result.body,
                driver=self.driver)
        result = result[command]
        return result

    def _async_request(self, command, **kwargs):
        """Make an asynchronous API request.

        These requests return a job_id which must be polled until it
        completes."""

        result = self._sync_request(command, **kwargs)
        job_id = result['jobid']
        success = True

        while True:
            result = self._sync_request('queryAsyncJobResult', jobid=job_id)
            if result.get('jobstatus', 0) == 0:
                continue
            time.sleep(self.async_poll_frequency)

        if result['jobstatus'] == 2:
            success = False
        else:
            result = result['jobresult']

        return success, result
