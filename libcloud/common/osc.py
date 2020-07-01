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

from datetime import datetime
import hashlib
import hmac

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import ET
from libcloud.utils.py3 import _real_unicode
from libcloud.utils.py3 import basestring
from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.common.base import JsonResponse
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.utils.py3 import b, httplib, urlquote
from libcloud.utils.xml import findtext, findall

import logging

__all__ = [
    'OSCBaseResponse',
    'OSCGenericResponse',
    'OSCTokenConnection',
    'SignedOSCConnection',
    'OSCRequestSignerAlgorithmV4',
]

DEFAULT_SIGNATURE_VERSION = '4'
UNSIGNED_PAYLOAD = 'UNSIGNED-PAYLOAD'

PARAMS_NOT_STRING_ERROR_MSG = """
"params" dictionary contains an attribute "%s" which value (%s, %s) is not a
string.

Parameters are sent via query parameters and not via request body and as such,
all the values need to be of a simple type (string, int, bool).

For arrays and other complex types, you should use notation similar to this
one:

params['TagSpecification.1.Tag.Value'] = 'foo'
params['TagSpecification.2.Tag.Value'] = 'bar'

See https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Query-Requests.html
for details.
""".strip()


class OSCBaseResponse(XmlResponse):
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


class OSCGenericResponse(OSCBaseResponse):
    # There are multiple error messages in AWS, but they all have an Error node
    # with Code and Message child nodes. Xpath to select them
    # None if the root node *is* the Error node
    xpath = None

    # This dict maps <Error><Code>CodeName</Code></Error> to a specific
    # exception class that is raised immediately.
    # If a custom exception class is not defined, errors are accumulated and
    # returned from the parse_error method.
    exceptions = {}

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


class OSCTokenConnection(ConnectionUserAndKey):

    def __init__(self, user_id, key, secure=True,
                 host=None, port=None, url=None, timeout=None, proxy_url=None,
                 token=None, retry_delay=None, backoff=None):
        self.token = token
        super(OSCTokenConnection, self).__init__(user_id, key, secure=secure,
                                                 host=host, port=port, url=url,
                                                 timeout=timeout,
                                                 retry_delay=retry_delay,
                                                 backoff=backoff,
                                                 proxy_url=proxy_url)

    def add_default_params(self, params):
        # Even though we are adding it to the headers, we need it here too
        # so that the token is added to the signature.
        if self.token:
            params['x-osc-security-token'] = self.token
        return super(OSCTokenConnection, self).add_default_params(params)

    def add_default_headers(self, headers):
        if self.token:
            headers['x-osc-security-token'] = self.token
        return super(OSCTokenConnection, self).add_default_headers(headers)


class OSCRequestSigner(object):
    """
    Class which handles signing the outgoing AWS requests.
    """

    def __init__(self, access_key, access_secret, version, connection):
        """
        :param access_key: Access key.
        :type access_key: ``str``

        :param access_secret: Access secret.
        :type access_secret: ``str``

        :param version: API version.
        :type version: ``str``

        :param connection: Connection instance.
        :type connection: :class:`Connection`
        """
        self.access_key = access_key
        self.access_secret = access_secret
        self.version = version
        # TODO: Remove cycling dependency between connection and signer
        self.connection = connection


class OSCRequestSignerAlgorithmV4(OSCRequestSigner):
    def get_request_headers(self, service_name, region, action,
                            data=None):
        date = datetime.utcnow()
        host = "{}.{}.outscale.com".format(service_name, region)
        headers = {
            'Content-Type': "application/json; charset=utf-8",
            'X-Osc-Date': date.strftime('%Y%m%dT%H%M%SZ'),
            'Host': host,
        }
        path = "/{}/{}/{}".format(self.connection.service_name, self.version, action)
        sig = self._get_authorization_v4_header(
            headers=headers,
            dt=date,
            method='POST',
            path=path,
            data=data
        )
        headers.update({'Authorization': sig})
        return headers

    def _get_authorization_v4_header(self, headers, dt, method='GET',
                                     path='/', data=None):
        credentials_scope = self._get_credential_scope(dt=dt)
        signed_headers = self._get_signed_headers(headers=headers)
        signature = self._get_signature(headers=headers,dt=dt,
                                        method=method, path=path,
                                        data=data)
        return 'OSC4-HMAC-SHA256 Credential=%(u)s/%(c)s, ' \
               'SignedHeaders=%(sh)s, Signature=%(s)s' % {
                   'u': self.access_key,
                   'c': credentials_scope,
                   'sh': signed_headers,
                   's': signature
               }

    def _get_signature(self, headers, dt, method, path, data):
        string_to_sign = self._get_string_to_sign(headers=headers, dt=dt,
                                                  method=method, path=path,
                                                  data=data)
        signing_key = self._get_key_to_sign_with(self.access_secret, dt)
        return hmac.new(signing_key, string_to_sign.encode('utf-8'),
                        hashlib.sha256).hexdigest()

    @staticmethod
    def sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_key_to_sign_with(self, key, dt):
        dt = dt.strftime('%Y%m%d')
        k_date = self.sign(('OSC4' + key).encode('utf-8'), dt)
        k_region = self.sign(k_date, self.connection.region_name)
        k_service = self.sign(k_region, self.connection.service_name)
        return self.sign(k_service, 'osc4_request')

    def _get_string_to_sign(self, headers, dt, method, path, data):
        canonical_request = self._get_canonical_request(headers=headers,
                                                        method=method,
                                                        path=path,
                                                        data=data)
        return 'OSC4-HMAC-SHA256' + '\n' \
                        + dt.strftime('%Y%m%dT%H%M%SZ') + '\n' \
                        + self._get_credential_scope(dt) + '\n' \
                        + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    def _get_credential_scope(self, dt):
        return '/'.join([dt.strftime('%Y%m%d'),
                         self.connection.region_name,
                         self.connection.service_name,
                         'osc4_request'])

    @staticmethod
    def _get_signed_headers(headers):
        return ';'.join([k.lower() for k in sorted(headers.keys())])

    @staticmethod
    def _get_canonical_headers(headers):
        return '\n'.join([':'.join([k.lower(), str(v).strip()])
                          for k, v in sorted(headers.items())]) + '\n'

    @staticmethod
    def _get_request_params(params):
        return '&'.join(["%s=%s" %
                         (urlquote(k, safe=''), urlquote(str(v), safe='~'))
                         for k, v in sorted(params.items())])

    def _get_canonical_request(self, headers, method, path, data="{}"):
        data = data if data else "{}"
        return '\n'.join([
            method,
            path,
            self._get_request_params({}),
            self._get_canonical_headers(headers),
            self._get_signed_headers(headers),
            hashlib.sha256(data.encode('utf-8')).hexdigest()
        ])


class SignedOSCConnection(OSCTokenConnection):
    version = None

    def __init__(self, user_id, key, secure=True, host=None, port=None,
                 url=None, timeout=None, proxy_url=None, token=None,
                 retry_delay=None, backoff=None,
                 signature_version=DEFAULT_SIGNATURE_VERSION):
        super(SignedOSCConnection, self).__init__(user_id=user_id, key=key,
                                                  secure=secure, host=host,
                                                  port=port, url=url,
                                                  timeout=timeout, token=token,
                                                  retry_delay=retry_delay,
                                                  backoff=backoff,
                                                  proxy_url=proxy_url)
        self.signature_version = str(signature_version)

        if self.signature_version == '4':
            signer_cls = OSCRequestSignerAlgorithmV4
        else:
            raise ValueError('Unsupported signature_version: %s' %
                             (signature_version))

        self.signer = signer_cls(access_key=self.user_id,
                                 access_secret=self.key,
                                 version=self.version,
                                 connection=self)

    def add_default_params(self, params):
        for key, value in params.items():
            if not isinstance(value, (_real_unicode, basestring, int, bool)):
                msg = PARAMS_NOT_STRING_ERROR_MSG % (key, value, type(value))
                raise ValueError(msg)
        return params


class OSCJsonResponse(JsonResponse):
    """
    Amazon ECS response class.
    ECS API uses JSON unlike the s3, elb drivers
    """
    def parse_error(self):
        response = json.loads(self.body)
        code = response['__type']
        message = response.get('Message', response['message'])
        return ('%s: %s' % (code, message))