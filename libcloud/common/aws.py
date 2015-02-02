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
from datetime import datetime
import hashlib
import hmac
import time
from hashlib import sha256

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.common.base import ConnectionUserAndKey, XmlResponse, BaseDriver
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.utils.py3 import b, httplib, urlquote
from libcloud.utils.xml import findtext, findall


class AWSBaseResponse(XmlResponse):
    namespace = None

    def _parse_error_details(self, element):
        """
        Parse code and message from the provided error element.

        :return: ``tuple`` with two elements: (code, message)
        :rtype: ``tuple``
        """
        code = findtext(element=element, xpath='Code',
                        namespace=self.namespace)
        message = findtext(element=element, xpath='Message',
                           namespace=self.namespace)

        return code, message


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
            code, message = self._parse_error_details(element=err)
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


class AWSTokenConnection(ConnectionUserAndKey):
    def __init__(self, user_id, key, secure=True,
                 host=None, port=None, url=None, timeout=None, token=None):
        self.token = token
        super(AWSTokenConnection, self).__init__(user_id, key, secure=secure,
                                                 host=host, port=port, url=url,
                                                 timeout=timeout)

    def add_default_params(self, params):
        # Even though we are adding it to the headers, we need it here too
        # so that the token is added to the signature.
        if self.token:
            params['x-amz-security-token'] = self.token
        return super(AWSTokenConnection, self).add_default_params(params)

    def add_default_headers(self, headers):
        if self.token:
            headers['x-amz-security-token'] = self.token
        return super(AWSTokenConnection, self).add_default_headers(headers)


class SignedAWSConnection(AWSTokenConnection):

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


class V4SignedAWSConnection(AWSTokenConnection):

    def add_default_params(self, params):
        params['Version'] = self.version
        return params

    def pre_connect_hook(self, params, headers):
        now = datetime.utcnow()
        headers['X-AMZ-Date'] = now.strftime('%Y%m%dT%H%M%SZ')
        headers['Authorization'] = self._get_authorization_v4_header(params, headers, now)

        return params, headers

    def _get_authorization_v4_header(self, params, headers, dt):
        # TODO: according to AWS spec (and RFC 2616 Section 4.2.) excess whitespace
        # from inside non-quoted strings should be stripped. Now we only strip the
        # start and end of the string. See http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        canonical_headers = '\n'.join([':'.join([k.lower(), v.strip()])
                                       for k, v in sorted(headers.items())])
        canonical_headers += '\n'

        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])

        # For self.method == GET
        request_params = '&'.join(["%s=%s" % (urlquote(k, safe=''), urlquote(v, safe='-_~'))
                                   for k, v in sorted(params.items())])
        payload_hash = hashlib.sha256('').hexdigest()

        canonical_request = '\n'.join([self.method,
                                       self.action,
                                       request_params,
                                       canonical_headers,
                                       signed_headers,
                                       payload_hash])

        credential_scope = '/'.join([dt.strftime('%Y%m%d'),
                                     self.driver.region_name,
                                     self.service_name,
                                     'aws4_request'])
        string_to_sign = '\n'.join(['AWS4-HMAC-SHA256',
                                    dt.strftime('%Y%m%dT%H%M%SZ'),
                                    credential_scope,
                                    hashlib.sha256(canonical_request).hexdigest()])

        # Key derivation functions. See:
        # http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
        def getSignatureKey(key, date_stamp, regionName, serviceName):
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

            signed_date = sign(('AWS4' + key).encode('utf-8'), date_stamp)
            signed_region = sign(signed_date, regionName)
            signed_service = sign(signed_region, serviceName)
            return sign(signed_service, 'aws4_request')

        signing_key = getSignatureKey(self.key, dt.strftime('%Y%m%d'), self.driver.region_name, self.service_name)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        return 'AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s' % \
               (self.user_id, credential_scope, signed_headers, signature)


class AWSDriver(BaseDriver):
    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=None, token=None, **kwargs):
        self.token = token
        super(AWSDriver, self).__init__(key, secret=secret, secure=secure,
                                        host=host, port=port,
                                        api_version=api_version, region=region,
                                        token=token, **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = super(AWSDriver, self)._ex_connection_class_kwargs()
        kwargs['token'] = self.token
        return kwargs
