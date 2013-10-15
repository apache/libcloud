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
from xml.etree import ElementTree as ET

from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.utils.py3 import b, httplib, urlquote
from libcloud.utils.xml import findtext, findall


class AWSBaseResponse(XmlResponse):
    pass


class AWSGenericResponse(AWSBaseResponse):
    # There are multiple error messages in AWS, but they all have an Error node
    # with Code and Message child nodes. Xpath to select them
    # None if the root node *is* the Error node
    xpath = None

    # This dict maps <Error><Code>CodeName</Code></Error> to a specific
    # exception class that is raised immediately.
    # If a custom exception class is not defined, errors are accumulated and
    # returned from the parse_error method.
    expections = {}

    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_error(self):
        context = self.connection.context
        status = int(self.status)

        # FIXME: Probably ditch this as the forbidden message will have
        # corresponding XML.
        if status == httplib.FORBIDDEN:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)

        try:
            body = ET.XML(self.body)
        except Exception:
            raise MalformedResponseError('Failed to parse XML',
                                         body=self.body,
                                         driver=self.connection.driver)

        if self.xpath:
            errs = findall(element=body, xpath=self.xpath,
                           namespace=self.namespace)
        else:
            errs = [body]

        msgs = []
        for err in errs:
            code = findtext(element=err, xpath='Code',
                            namespace=self.namespace)
            message = findtext(element=err, xpath='Message',
                               namespace=self.namespace)

            exceptionCls = self.exceptions.get(code, None)

            if exceptionCls is None:
                msgs.append('%s: %s' % (code, message))
                continue

            # Custom exception class is defined, immediately throw an exception
            params = {}
            if hasattr(exceptionCls, 'kwargs'):
                for key in exceptionCls.kwargs:
                    if key in context:
                        params[key] = context[key]

            raise exceptionCls(value=message, driver=self.connection.driver,
                               **params)

        return "\n".join(msgs)


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
            value = str(params[key])
            pairs.append(urlquote(key, safe='') + '=' +
                         urlquote(value, safe='-_~'))

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
