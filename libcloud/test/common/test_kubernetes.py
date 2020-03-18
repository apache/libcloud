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


__all__ = [
    'KubernetesAuthTestCaseMixin'
]

import os
import base64

from libcloud.utils.py3 import b

from libcloud.common.kubernetes import KubernetesBasicAuthConnection
from libcloud.common.kubernetes import KubernetesTLSAuthConnection
from libcloud.common.kubernetes import KubernetesTokenAuthConnection

KEY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '../compute/fixtures/azure/libcloud.pem'))
CERT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                            '../loadbalancer/fixtures/nttcis/denis.crt'))
CA_CERT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                               '../loadbalancer/fixtures/nttcis/chain.crt'))


class KubernetesAuthTestCaseMixin(object):
    """
    Test class mixin which tests different type of Kubernetes authentication
    mechanisms (client cert, token, basic auth).

    It's to be used with all the drivers which inherit from KubernetesDriverMixin.
    """

    def test_http_basic_auth(self):
        driver = self.driver_cls(key='username', secret='password')
        self.assertEqual(driver.connectionCls, KubernetesBasicAuthConnection)
        self.assertEqual(driver.connection.user_id, 'username')
        self.assertEqual(driver.connection.key, 'password')

        auth_string = base64.b64encode(b('%s:%s' % ('username', 'password'))).decode('utf-8')

        headers = driver.connection.add_default_headers({})
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Authorization'], 'Basic %s' % (auth_string))

    def test_cert_auth(self):
        # key_file provided, but not cert_file
        expected_msg = 'Both key and certificate files are needed'
        self.assertRaisesRegex(ValueError, expected_msg, self.driver_cls,
                               key_file=KEY_FILE, ca_cert=CA_CERT_FILE)

        # cert_file provided, but not key_file
        expected_msg = 'Both key and certificate files are needed'
        self.assertRaisesRegex(ValueError, expected_msg, self.driver_cls,
                               cert_file=CERT_FILE, ca_cert=CA_CERT_FILE)

        # ca_cert argument specified
        driver = self.driver_cls(key_file=KEY_FILE, cert_file=CERT_FILE,
                                 ca_cert=CA_CERT_FILE)
        self.assertEqual(driver.connectionCls, KubernetesTLSAuthConnection)
        self.assertEqual(driver.connection.key_file, KEY_FILE)
        self.assertEqual(driver.connection.cert_file, CERT_FILE)
        self.assertEqual(driver.connection.connection.ca_cert, CA_CERT_FILE)

        headers = driver.connection.add_default_headers({})
        self.assertEqual(headers['Content-Type'], 'application/json')

        # ca_cert argument not specified
        driver = self.driver_cls(key_file=KEY_FILE, cert_file=CERT_FILE,
                                 ca_cert=None)
        self.assertEqual(driver.connectionCls, KubernetesTLSAuthConnection)
        self.assertEqual(driver.connection.key_file, KEY_FILE)
        self.assertEqual(driver.connection.cert_file, CERT_FILE)
        self.assertEqual(driver.connection.connection.ca_cert, False)

        headers = driver.connection.add_default_headers({})
        self.assertEqual(headers['Content-Type'], 'application/json')

    def test_bearer_token_auth(self):
        driver = self.driver_cls(ex_token_bearer_auth=True, key='foobar')
        self.assertEqual(driver.connectionCls, KubernetesTokenAuthConnection)
        self.assertEqual(driver.connection.key, 'foobar')

        headers = driver.connection.add_default_headers({})
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Authorization'], 'Bearer %s' % ('foobar'))

    def test_host_sanitization(self):
        driver = self.driver_cls(host='example.com')
        self.assertEqual(driver.connection.host, 'example.com')

        driver = self.driver_cls(host='http://example.com')
        self.assertEqual(driver.connection.host, 'example.com')

        driver = self.driver_cls(host='https://example.com')
        self.assertEqual(driver.connection.host, 'example.com')
