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

import sys
import unittest
import os.path

import libcloud.security
from libcloud.httplib_ssl import LibcloudHTTPSConnection

class TestHttpLibSSLTests(unittest.TestCase):

    def setUp(self):
        libcloud.security.VERIFY_SSL_CERT = False
        self.httplib_object = LibcloudHTTPSConnection('foo.bar')

    def test_verify_hostname(self):
        cert1 = {'notAfter': 'Feb 16 16:54:50 2013 GMT',
         'subject': ((('countryName', 'US'),),
                     (('stateOrProvinceName', 'Delaware'),),
                     (('localityName', 'Wilmington'),),
                     (('organizationName', 'Python Software Foundation'),),
                     (('organizationalUnitName', 'SSL'),),
                     (('commonName', 'somemachine.python.org'),))}

        cert2 = {'notAfter': 'Feb 16 16:54:50 2013 GMT',
         'subject': ((('countryName', 'US'),),
                     (('stateOrProvinceName', 'Delaware'),),
                     (('localityName', 'Wilmington'),),
                     (('organizationName', 'Python Software Foundation'),),
                     (('organizationalUnitName', 'SSL'),),
                     (('commonName', 'somemachine.python.org'),)),
         'subjectAltName': ((('DNS', 'foo.alt.name')),
                           (('DNS', 'foo.alt.name.1')))}

        self.assertFalse(self.httplib_object._verify_hostname(
                         hostname='invalid', cert=cert1))
        self.assertTrue(self.httplib_object._verify_hostname(
                        hostname='somemachine.python.org', cert=cert1))

        self.assertFalse(self.httplib_object._verify_hostname(
                         hostname='invalid', cert=cert2))
        self.assertTrue(self.httplib_object._verify_hostname(
                        hostname='foo.alt.name.1', cert=cert2))

    def test_get_subject_alt_names(self):
        cert1 = {'notAfter': 'Feb 16 16:54:50 2013 GMT',
         'subject': ((('countryName', 'US'),),
                     (('stateOrProvinceName', 'Delaware'),),
                     (('localityName', 'Wilmington'),),
                     (('organizationName', 'Python Software Foundation'),),
                     (('organizationalUnitName', 'SSL'),),
                     (('commonName', 'somemachine.python.org'),))}

        cert2 = {'notAfter': 'Feb 16 16:54:50 2013 GMT',
         'subject': ((('countryName', 'US'),),
                     (('stateOrProvinceName', 'Delaware'),),
                     (('localityName', 'Wilmington'),),
                     (('organizationName', 'Python Software Foundation'),),
                     (('organizationalUnitName', 'SSL'),),
                     (('commonName', 'somemachine.python.org'),)),
         'subjectAltName': ((('DNS', 'foo.alt.name')),
                           (('DNS', 'foo.alt.name.1')))}

        self.assertEqual(self.httplib_object._get_subject_alt_names(cert=cert1),
                         [])

        alt_names = self.httplib_object._get_subject_alt_names(cert=cert2)
        self.assertEqual(len(alt_names), 2)
        self.assertTrue('foo.alt.name' in alt_names)
        self.assertTrue('foo.alt.name.1' in alt_names)

    def test_get_common_name(self):
        cert = {'notAfter': 'Feb 16 16:54:50 2013 GMT',
         'subject': ((('countryName', 'US'),),
                     (('stateOrProvinceName', 'Delaware'),),
                     (('localityName', 'Wilmington'),),
                     (('organizationName', 'Python Software Foundation'),),
                     (('organizationalUnitName', 'SSL'),),
                     (('commonName', 'somemachine.python.org'),))}

        self.assertEqual(self.httplib_object._get_common_name(cert)[0],
                         'somemachine.python.org')
        self.assertEqual(self.httplib_object._get_common_name({}),
                         None)

    def test_setup_verify(self):
        # @TODO: catch warnings
        # non-strict mode,s hould just emit a warning
        libcloud.security.VERIFY_SSL_CERT = True
        libcloud.security.VERIFY_SSL_CERT_STRICT = False
        self.httplib_object._setup_verify()

        # strict mode, should throw a runtime error
        libcloud.security.VERIFY_SSL_CERT = True
        libcloud.security.VERIFY_SSL_CERT_STRICT = True
        try:
            self.httplib_object._setup_verify()
        except:
            pass
        else:
            self.fail('Exception not thrown')

        libcloud.security.VERIFY_SSL_CERT = False
        libcloud.security.VERIFY_SSL_CERT_STRICT = False
        self.httplib_object._setup_verify()

    def test_setup_ca_cert(self):
        # @TODO: catch warnings
        self.httplib_object.verify = False
        self.httplib_object.strict = False
        self.httplib_object._setup_ca_cert()

        self.assertEqual(self.httplib_object.ca_cert, None)

        self.httplib_object.verify = True

        libcloud.security.CA_CERTS_PATH = [os.path.abspath(__file__)]
        self.httplib_object._setup_ca_cert()
        self.assertTrue(self.httplib_object.ca_cert is not None)

        libcloud.security.CA_CERTS_PATH = []
        self.httplib_object._setup_ca_cert()
        self.assertFalse(self.httplib_object.ca_cert)
        self.assertFalse(self.httplib_object.verify)

if __name__ == '__main__':
    sys.exit(unittest.main())
