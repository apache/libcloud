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
import hmac
import time
from hashlib import sha256

from libcloud.utils.py3 import b, urlquote
from libcloud.common.base import ConnectionUserAndKey, XmlResponse


class AWSBaseResponse(XmlResponse):
    pass


class SignedAWSConnection(ConnectionUserAndKey):

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = self.version
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key,
                                                       self.action)
        return params

    def _get_aws_auth_param(self, params, secret_key, path='/'):
        """
        Creates the signature required for AWS, per
        http://bit.ly/aR7GaQ [docs.amazonwebservices.com]:

        StringToSign = HTTPVerb + "\n" +
                       ValueOfHostHeaderInLowercase + "\n" +
                       HTTPRequestURI + "\n" +
                       CanonicalizedQueryString <from the preceding step>
        """
        keys = list(params.keys())
        keys.sort()
        pairs = []
        for key in keys:
            pairs.append(urlquote(key, safe='') + '=' +
                         urlquote(params[key], safe='-_~'))

        qs = '&'.join(pairs)

        hostname = self.host
        if (self.secure and self.port != 443) or \
           (not self.secure and self.port != 80):
            hostname += ":" + str(self.port)

        string_to_sign = '\n'.join(('GET', hostname, path, qs))

        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key), b(string_to_sign),
                     digestmod=sha256).digest()
        )
        return b64_hmac.decode('utf-8')

