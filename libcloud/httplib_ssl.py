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
import sys
import socket
import ssl
import base64
import warnings

import libcloud.security
from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import urlunquote
from libcloud.utils.py3 import match_hostname
from libcloud.utils.py3 import CertificateError


__all__ = [
    'LibcloudBaseConnection',
    'LibcloudHTTPConnection',
    'LibcloudHTTPSConnection'
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

    proxy_scheme = None
    proxy_host = None
    proxy_port = None

    proxy_username = None
    proxy_password = None

    http_proxy_used = False

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

        self._setup_http_proxy()

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

    def _setup_http_proxy(self):
        """
        Set up HTTP proxy.

        :param proxy_url: Proxy URL (e.g. http://<host>:3128)
        :type proxy_url: ``str``
        """
        headers = {}

        if self.proxy_username and self.proxy_password:
            # Include authentication header
            user_pass = '%s:%s' % (self.proxy_username, self.proxy_password)
            encoded = base64.encodestring(b(urlunquote(user_pass))).strip()
            auth_header = 'Basic %s' % (encoded.decode('utf-8'))
            headers['Proxy-Authorization'] = auth_header

        if hasattr(self, 'set_tunnel'):
            # Python 2.7 and higher
            # pylint: disable=no-member
            self.set_tunnel(host=self.host, port=self.port, headers=headers)
        elif hasattr(self, '_set_tunnel'):
            # Python 2.6
            # pylint: disable=no-member
            self._set_tunnel(host=self.host, port=self.port, headers=headers)
        else:
            raise ValueError('Unsupported Python version')

        self._set_hostport(host=self.proxy_host, port=self.proxy_port)

    def _activate_http_proxy(self, sock):
        self.sock = sock
        self._tunnel()  # pylint: disable=no-member

    def _set_hostport(self, host, port):
        """
        Backported from Python stdlib so Proxy support also works with
        Python 3.4.
        """
        if port is None:
            i = host.rfind(':')
            j = host.rfind(']')         # ipv6 addresses have [...]
            if i > j:
                try:
                    port = int(host[i + 1:])
                except ValueError:
                    msg = "nonnumeric port: '%s'" % (host[i + 1:])
                    raise httplib.InvalidURL(msg)
                host = host[:i]
            else:
                port = self.default_port  # pylint: disable=no-member
            if host and host[0] == '[' and host[-1] == ']':
                host = host[1:-1]
        self.host = host
        self.port = port


class LibcloudHTTPConnection(httplib.HTTPConnection, LibcloudBaseConnection):
    def __init__(self, *args, **kwargs):
        # Support for HTTP proxy
        proxy_url_env = os.environ.get(HTTP_PROXY_ENV_VARIABLE_NAME, None)
        proxy_url = kwargs.pop('proxy_url', proxy_url_env)

        super(LibcloudHTTPConnection, self).__init__(*args, **kwargs)

        if proxy_url:
            self.set_http_proxy(proxy_url=proxy_url)


class LibcloudHTTPSConnection(httplib.HTTPSConnection, LibcloudBaseConnection):
    """
    LibcloudHTTPSConnection

    Subclass of HTTPSConnection which verifies certificate names
    if and only if CA certificates are available.
    """
    verify = True         # verify by default
    ca_cert = None        # no default CA Certificate

    def __init__(self, *args, **kwargs):
        """
        Constructor
        """
        self._setup_verify()
        # Support for HTTP proxy
        proxy_url_env = os.environ.get(HTTP_PROXY_ENV_VARIABLE_NAME, None)
        proxy_url = kwargs.pop('proxy_url', proxy_url_env)

        super(LibcloudHTTPSConnection, self).__init__(*args, **kwargs)

        if proxy_url:
            self.set_http_proxy(proxy_url=proxy_url)

    def _setup_verify(self):
        """
        Setup Verify SSL or not

        Reads security module's VERIFY_SSL_CERT and toggles whether
        the class overrides the connect() class method or runs the
        inherited httplib.HTTPSConnection connect()
        """
        self.verify = libcloud.security.VERIFY_SSL_CERT

        if self.verify:
            self._setup_ca_cert()
        else:
            warnings.warn(libcloud.security.VERIFY_SSL_DISABLED_MSG)

    def _setup_ca_cert(self):
        """
        Setup CA Certs

        Search in CA_CERTS_PATH for valid candidates and
        return first match.  Otherwise, complain about certs
        not being available.
        """
        if not self.verify:
            return

        ca_certs_available = [cert
                              for cert in libcloud.security.CA_CERTS_PATH
                              if os.path.exists(cert) and os.path.isfile(cert)]
        if ca_certs_available:
            # use first available certificate
            self.ca_cert = ca_certs_available[0]
        else:
            raise RuntimeError(
                libcloud.security.CA_CERTS_UNAVAILABLE_ERROR_MSG)

    def connect(self):
        """
        Connect

        Checks if verification is toggled; if not, just call
        httplib.HTTPSConnection's connect
        """
        if not self.verify:
            return httplib.HTTPSConnection.connect(self)

        # otherwise, create a connection and verify the hostname
        # use socket.create_connection (in 2.6+) if possible
        if getattr(socket, 'create_connection', None):
            sock = socket.create_connection((self.host, self.port),
                                            self.timeout)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))

        # Activate the HTTP proxy
        if self.http_proxy_used:
            self._activate_http_proxy(sock=sock)

        ssl_version = libcloud.security.SSL_VERSION

        # If we support SNI, use SSLContext and tls_context.wrap_socket()
        # else revert to older behaviour with ssl.wrap_socket()
        # Note: This feature is only available in Python 2.7.9 and
        # Python >= 3.2
        has_sni = getattr(ssl, 'HAS_SNI', False)

        if has_sni:
            self.tls_context = ssl.SSLContext(ssl_version)
            self.tls_context.verify_mode = ssl.CERT_REQUIRED

            if self.cert_file and self.key_file:
                self.tls_context.load_cert_chain(
                    certfile=self.cert_file,
                    keyfile=self.key_file,
                    password=None)

            if self.ca_cert:
                self.tls_context.load_verify_locations(cafile=self.ca_cert)

            try:
                self.sock = self.tls_context.wrap_socket(
                    sock,
                    server_hostname=self.host,
                )
            except:
                exc = sys.exc_info()[1]
                exc = get_socket_error_exception(ssl_version=ssl_version,
                                                 exc=exc)
                raise exc
        else:
            # SNI support not available
            try:
                self.sock = ssl.wrap_socket(
                    sock,
                    self.key_file,
                    self.cert_file,
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs=self.ca_cert,
                    ssl_version=ssl_version
                )
            except:
                exc = sys.exc_info()[1]
                exc = get_socket_error_exception(ssl_version=ssl_version,
                                                 exc=exc)
                raise exc

        cert = self.sock.getpeercert()

        # Verify Hostname
        try:
            match_hostname(cert, self.host)
        except CertificateError:
            e = sys.exc_info()[1]
            raise ssl.SSLError('Failed to verify hostname: %s' % (str(e)))


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
