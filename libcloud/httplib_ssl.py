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
"""
Subclass for httplib.HTTPSConnection with optional certificate name
verification, depending on libcloud.security settings.
"""
import os
import socket

import requests

from libcloud.utils.py3 import urlparse


__all__ = [
    'LibcloudBaseConnection',
    'LibcloudConnection'
]

HTTP_PROXY_ENV_VARIABLE_NAME = 'http_proxy'

# Error message which is thrown when establishing SSL / TLS connection fails
UNSUPPORTED_TLS_VERSION_ERROR_MSG = """
Failed to establish SSL / TLS connection (%s). It is possible that the server \
doesn't support requested SSL / TLS version (%s).
For information on how to work around this issue, please see \
https://libcloud.readthedocs.org/en/latest/other/\
ssl-certificate-validation.html#changing-used-ssl-tls-version
""".strip()

# Maps ssl.PROTOCOL_* constant to the actual SSL / TLS version name
SSL_CONSTANT_TO_TLS_VERSION_MAP = {
    0: 'SSL v2',
    2: 'SSLv3, TLS v1.0, TLS v1.1, TLS v1.2',
    3: 'TLS v1.0',
    4: 'TLS v1.1',
    5: 'TLS v1.2'
}


class LibcloudBaseConnection(object):
    """
    Base connection class to inherit from.

    Note: This class should not be instantiated directly.
    """

    session = None

    proxy_scheme = None
    proxy_host = None
    proxy_port = None

    proxy_username = None
    proxy_password = None

    http_proxy_used = False

    def __init__(self):
        self.session = requests.Session()

    def set_http_proxy(self, proxy_url):
        """
        Set a HTTP proxy which will be used with this connection.

        :param proxy_url: Proxy URL (e.g. http://<hostname>:<port> without
                          authentication and
                          http://<username>:<password>@<hostname>:<port> for
                          basic auth authentication information.
        :type proxy_url: ``str``
        """
        result = self._parse_proxy_url(proxy_url=proxy_url)
        scheme = result[0]
        host = result[1]
        port = result[2]
        username = result[3]
        password = result[4]

        self.proxy_scheme = scheme
        self.proxy_host = host
        self.proxy_port = port
        self.proxy_username = username
        self.proxy_password = password
        self.http_proxy_used = True

        self.session.proxies = {
            self.proxy_scheme: proxy_url
        }

    def _parse_proxy_url(self, proxy_url):
        """
        Parse and validate a proxy URL.

        :param proxy_url: Proxy URL (e.g. http://hostname:3128)
        :type proxy_url: ``str``

        :rtype: ``tuple`` (``scheme``, ``hostname``, ``port``)
        """
        parsed = urlparse.urlparse(proxy_url)

        if parsed.scheme != 'http':
            raise ValueError('Only http proxies are supported')

        if not parsed.hostname or not parsed.port:
            raise ValueError('proxy_url must be in the following format: '
                             'http://<proxy host>:<proxy port>')

        proxy_scheme = parsed.scheme
        proxy_host, proxy_port = parsed.hostname, parsed.port

        netloc = parsed.netloc

        if '@' in netloc:
            username_password = netloc.split('@', 1)[0]
            split = username_password.split(':', 1)

            if len(split) < 2:
                raise ValueError('URL is in an invalid format')

            proxy_username, proxy_password = split[0], split[1]
        else:
            proxy_username = None
            proxy_password = None

        return (proxy_scheme, proxy_host, proxy_port, proxy_username,
                proxy_password)


class LibcloudConnection(LibcloudBaseConnection):
    timeout = None
    host = None
    response = None

    def __init__(self, host, port, **kwargs):
        self.host = '{}://{}'.format(
            'https' if port == 443 else 'http',
            host
        )
        # Support for HTTP proxy
        proxy_url_env = os.environ.get(HTTP_PROXY_ENV_VARIABLE_NAME, None)
        proxy_url = kwargs.pop('proxy_url', proxy_url_env)

        super(LibcloudConnection, self).__init__()

        if proxy_url:
            self.set_http_proxy(proxy_url=proxy_url)
        self.session.timeout = kwargs.get('timeout', 60)

    def request(self, method, url, body=None, headers=None, raw=False):
        self.response = self.session.request(
            method=method.lower(),
            url=''.join([self.host, url]),
            data=body,
            headers=headers,
            allow_redirects=1,
            stream=raw
        )

    def getresponse(self):
        return self

    def getheaders(self):
        # urlib decoded response body, libcloud has a bug
        # and will not check if content is gzipped, so let's
        # remove headers indicating compressed content.
        if 'content-encoding' in self.response.headers:
            del self.response.headers['content-encoding']
        return self.response.headers

    @property
    def status(self):
        return self.response.status_code

    @property
    def reason(self):
        return None if self.response.status_code > 400 else self.response.text

    def connect(self):  # pragma: no cover
        pass

    def read(self):
        return self.response.content

    def close(self):  # pragma: no cover
        # return connection back to pool
        self.response.close()


def get_socket_error_exception(ssl_version, exc):
    """
    Function which intercepts socket.error exceptions and re-throws an
    exception with a more user-friendly message in case server doesn't support
    requested SSL version.
    """
    exc_msg = str(exc)

    # Re-throw an exception with a more friendly error message
    if 'connection reset by peer' in exc_msg.lower():
        ssl_version_name = SSL_CONSTANT_TO_TLS_VERSION_MAP[ssl_version]
        msg = (UNSUPPORTED_TLS_VERSION_ERROR_MSG %
               (exc_msg, ssl_version_name))

        # Note: In some cases arguments are (errno, message) and in
        # other it's just (message,)
        exc_args = getattr(exc, 'args', [])

        if len(exc_args) == 2:
            new_exc_args = [exc.args[0], msg]
        else:
            new_exc_args = [msg]

        new_exc = socket.error(*new_exc_args)
        new_exc.original_exc = exc
        return new_exc
    else:
        return exc
