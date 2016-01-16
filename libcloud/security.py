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
Security (SSL) Settings

Usage:
    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = True

    # Optional
    libcloud.security.CA_CERTS_PATH.append('/path/to/cacert.txt')

    # Use a custom SSL / TLS version
    libcloud.security.SSL_VERSION = ssl.PROTOCOL_TLSv1_2
"""

import os
import ssl

from libcloud.utils.py3 import PY2_post_279
from libcloud.utils.py3 import PY3_post_34

__all__ = [
    'VERIFY_SSL_CERT',
    'SSL_VERSION',
    'CA_CERTS_PATH',

    'get_ssl_version'
]

VERIFY_SSL_CERT = True

# Default SSL version which is used if one is not explicitli specified
DEFAULT_SSL_VERSION = ssl.PROTOCOL_TLSv1

# SSL version to be used as specified by the user
SSL_VERSION = None


# File containing one or more PEM-encoded CA certificates
# concatenated together.
CA_CERTS_PATH = [
    # centos/fedora: openssl
    '/etc/pki/tls/certs/ca-bundle.crt',

    # debian/ubuntu/arch/gentoo: ca-certificates
    '/etc/ssl/certs/ca-certificates.crt',

    # freebsd: ca_root_nss
    '/usr/local/share/certs/ca-root-nss.crt',

    # macports: curl-ca-bundle
    '/opt/local/share/curl/curl-ca-bundle.crt',

    # homebrew: openssl
    '/usr/local/etc/openssl/cert.pem',

    # homebrew: curl-ca-bundle (backward compatibility)
    '/usr/local/opt/curl-ca-bundle/share/ca-bundle.crt',
]

# Allow user to explicitly specify which CA bundle to use, using an environment
# variable
environment_cert_file = os.getenv('SSL_CERT_FILE', None)
if environment_cert_file is not None:
    # Make sure the file exists
    if not os.path.exists(environment_cert_file):
        raise ValueError('Certificate file %s doesn\'t exist' %
                         (environment_cert_file))

    if not os.path.isfile(environment_cert_file):
        raise ValueError('Certificate file can\'t be a directory')

    # If a provided file exists we ignore other common paths because we
    # don't want to fall-back to a potentially less restrictive bundle
    CA_CERTS_PATH = [environment_cert_file]

CA_CERTS_UNAVAILABLE_ERROR_MSG = (
    'No CA Certificates were found in CA_CERTS_PATH. For information on '
    'how to get required certificate files, please visit '
    'https://libcloud.readthedocs.org/en/latest/other/'
    'ssl-certificate-validation.html'
)

VERIFY_SSL_DISABLED_MSG = (
    'SSL certificate verification is disabled, this can pose a '
    'security risk. For more information how to enable the SSL '
    'certificate verification, please visit the libcloud '
    'documentation.'
)


def get_ssl_version():
    """
    Return SSL / TLS version which is to be used when establishing SSL / TLS
    connection.

    The return value depends on the Python version and
    libcloud.security.SSL_VERSION setting value.

    :rtype: ``int``
    """
    ssl_version = DEFAULT_SSL_VERSION

    # In Python >= 2.7.9 and >= 3.4 unsecure SSL v3.0 is disabled by default
    # so it's safe to use PROTOCOL_SSLv23.
    if PY2_post_279 or PY3_post_34:
        ssl_version = ssl.PROTOCOL_SSLv23

    # libcloud.security.SSL_VERSION has precedence over dynamicaly obtained
    # values
    if SSL_VERSION:
        ssl_version = SSL_VERSION

    return ssl_version
