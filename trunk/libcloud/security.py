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

    # optional
    libcloud.security.CA_CERTS_PATH.append("/path/to/cacert.txt")
"""

VERIFY_SSL_CERT = True
VERIFY_SSL_CERT_STRICT = True

# File containing one or more PEM-encoded CA certificates
# concatenated together
CA_CERTS_PATH = [
    # centos/fedora: openssl
    '/etc/pki/tls/certs/ca-bundle.crt',

    # debian/ubuntu/arch/gentoo: ca-certificates
    '/etc/ssl/certs/ca-certificates.crt',

    # freebsd: ca_root_nss
    '/usr/local/share/certs/ca-root-nss.crt',

    # macports: curl-ca-bundle
    '/opt/local/share/curl/curl-ca-bundle.crt',
]

CA_CERTS_UNAVAILABLE_WARNING_MSG = (
    'Warning: No CA Certificates were found in CA_CERTS_PATH. '
    'Toggling VERIFY_SSL_CERT to False.'
)

CA_CERTS_UNAVAILABLE_ERROR_MSG = (
    'No CA Certificates were found in CA_CERTS_PATH. '
)

VERIFY_SSL_DISABLED_MSG = (
    'SSL certificate verification is disabled, this can pose a '
    'security risk. For more information how to enable the SSL '
    'certificate verification, please visit the libcloud '
    'documentation.'
)
