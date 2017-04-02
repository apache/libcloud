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
import warnings
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

import libcloud.security
from libcloud.utils.py3 import urlparse, PY3


__all__ = [
    'LibcloudBaseConnection',
    'LibcloudConnection'
]

ALLOW_REDIRECTS = 1

HTTP_PROXY_ENV_VARIABLE_NAME = 'http_proxy'


class SignedX509Adapter(HTTPAdapter):
    def __init__(self, cert_file=None, key_file=None):
        self.cert_file = cert_file
        self.key_file = key_file

    def init_poolmanager(self, *args, **kwargs):
        self.tls_context = create_urllib3_context()
        kwargs['ssl_context'] = self.tls_context
        
        has_sni = getattr(ssl, 'HAS_SNI', False)

        if has_sni:
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
        
        return super(HTTPAdapter, self).init_poolmanager(*args, **kwargs)


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

    ca_cert = None

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

    def _setup_verify(self):
        self.verify = libcloud.security.VERIFY_SSL_CERT

    def _setup_ca_cert(self):
        if self.verify is False:
            pass
        else:
            if isinstance(libcloud.security.CA_CERTS_PATH, list):
                if len(libcloud.security.CA_CERTS_PATH) > 1:
                    warnings.warn('Only 1 certificate path is supported')
                self.ca_cert = libcloud.security.CA_CERTS_PATH[0]
            else:
                self.ca_cert = libcloud.security.CA_CERTS_PATH

    def _setup_signing(self, cert_file=None, key_file=None):
        """
        Setup request signing by mounting a signing
        adapter to the session
        """
        self.session.mount("https", SignedX509Adapter(cert_file, key_file))


class LibcloudConnection(LibcloudBaseConnection):
    timeout = None
    host = None
    response = None

    def __init__(self, host, port, secure=None, **kwargs):
        scheme = 'https' if secure is not None and secure else 'http'
        self.host = '{0}://{1}{2}'.format(
            'https' if port == 443 else scheme,
            host,
            ":{0}".format(port) if port not in (80, 443) else ""
        )
        # Support for HTTP proxy
        proxy_url_env = os.environ.get(HTTP_PROXY_ENV_VARIABLE_NAME, None)
        proxy_url = kwargs.pop('proxy_url', proxy_url_env)

        self._setup_verify()
        self._setup_ca_cert()
        
        LibcloudBaseConnection.__init__(self)
        
        if 'cert_file' in kwargs or 'key_file' in kwargs:
            self._setup_signing(**kwargs)
        if proxy_url:
            self.set_http_proxy(proxy_url=proxy_url)
        self.session.timeout = kwargs.get('timeout', 60)

    @property
    def verification(self):
        """
        The option for SSL verification given to underlying requests
        """
        return self.ca_cert if self.ca_cert is not None else self.verify

    def request(self, method, url, body=None, headers=None, raw=False,
                stream=False):
        url = urlparse.urljoin(self.host, url)
        self.response = self.session.request(
            method=method.lower(),
            url=url,
            data=body,
            headers=headers,
            allow_redirects=ALLOW_REDIRECTS,
            stream=stream,
            verify=self.verification
        )

    def prepared_request(self, method, url, body=None,
                         headers=None, raw=False, stream=False):
        req = requests.Request(method, ''.join([self.host, url]),
                               data=body, headers=headers)

        prepped = self.session.prepare_request(req)

        prepped.body = body

        self.response = self.session.send(
            prepped,
            stream=raw,
            verify=self.ca_cert if self.ca_cert is not None else self.verify)

    def getresponse(self):
        return self.response

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


class HttpLibResponseProxy(object):
    """
    Provides a proxy pattern around the :class:`requests.Reponse`
    object to a :class:`httplib.HTTPResponse` object
    """
    def __init__(self, response):
        self._response = response

    def read(self, amt=None):
        return self._response.text

    def getheader(self, name, default=None):
        """
        Get the contents of the header name, or default
        if there is no matching header.
        """
        if name in self._response.headers.keys():
            return self._response.headers[name]
        else:
            return default

    def getheaders(self):
        """
        Return a list of (header, value) tuples.
        """
        if PY3:
            return list(self._response.headers.items())
        else:
            return self._response.headers.items()

    @property
    def status(self):
        return self._response.status_code

    @property
    def reason(self):
        return self._response.reason

    @property
    def version(self):
        # requests doesn't expose this
        return '11'
