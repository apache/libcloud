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
        headers['Authorization'] = \
            self._get_authorization_v4_header(params, headers, now)

        return params, headers

    def _get_authorization_v4_header(self, params, headers, dt):
        assert self.method == 'GET', 'AWS Signature V4 not implemented for ' \
                                     'other methods than GET'

        return 'AWS4-HMAC-SHA256 Credential=%(u)s/%(c)s, ' \
               'SignedHeaders=%(sh)s, Signature=%(s)s' % {
                   'u': self.user_id,
                   'c': self._get_credential_scope(dt),
                   'sh': self._get_signed_headers(headers),
                   's': self._get_signature(params, headers, dt)
               }

    def _get_signature(self, params, headers, dt):
        return _sign(
            self._get_key_to_sign_with(dt),
            self._get_string_to_sign(params, headers, dt),
            hex=True)

    def _get_key_to_sign_with(self, dt):
        return _sign(
            _sign(
                _sign(
                    _sign(('AWS4' + self.key), dt.strftime('%Y%m%d')),
                    self.driver.region_name),
                self.service_name),
            'aws4_request')

    def _get_string_to_sign(self, params, headers, dt):
        return '\n'.join(['AWS4-HMAC-SHA256',
                          dt.strftime('%Y%m%dT%H%M%SZ'),
                          self._get_credential_scope(dt),
                          _hash(self._get_canonical_request(params, headers))])

    def _get_credential_scope(self, dt):
        return '/'.join([dt.strftime('%Y%m%d'),
                         self.driver.region_name,
                         self.service_name,
                         'aws4_request'])

    def _get_signed_headers(self, headers):
        return ';'.join([k.lower() for k in sorted(headers.keys())])

    def _get_canonical_headers(self, headers):
        return '\n'.join([':'.join([k.lower(), v.strip()])
                          for k, v in sorted(headers.items())]) + '\n'

    def _get_payload_hash(self):
        return _hash('')

    def _get_request_params(self, params):
        # For self.method == GET
        return '&'.join(["%s=%s" %
                         (urlquote(k, safe=''), urlquote(str(v), safe='~'))
                         for k, v in sorted(params.items())])

    def _get_canonical_request(self, params, headers):
        return '\n'.join([
            self.method,
            self.action,
            self._get_request_params(params),
            self._get_canonical_headers(headers),
            self._get_signed_headers(headers),
            self._get_payload_hash()
        ])


def _sign(key, msg, hex=False):
    if hex:
        return hmac.new(b(key), b(msg), hashlib.sha256).hexdigest()
    else:
        return hmac.new(b(key), b(msg), hashlib.sha256).digest()


def _hash(msg):
    return hashlib.sha256(b(msg)).hexdigest()


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
