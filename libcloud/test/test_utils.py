# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more§
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
import pytest
import socket
import codecs
import unittest
import warnings
import os.path
import requests_mock
from itertools import chain

# In Python > 2.7 DeprecationWarnings are disabled by default
warnings.simplefilter('default')

import libcloud.utils.files

from libcloud.utils.misc import get_driver, set_driver

from libcloud.utils.py3 import PY3
from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import b
from libcloud.utils.py3 import bchr
from libcloud.utils.py3 import hexadigits
from libcloud.utils.py3 import urlquote
from libcloud.compute.types import Provider
from libcloud.compute.providers import DRIVERS
from libcloud.compute.drivers.dummy import DummyNodeDriver
from libcloud.utils.misc import get_secure_random_string
from libcloud.utils.networking import is_public_subnet
from libcloud.utils.networking import is_private_subnet
from libcloud.utils.networking import is_valid_ip_address
from libcloud.utils.networking import join_ipv4_segments
from libcloud.utils.networking import increment_ipv4_segments
from libcloud.utils.decorators import wrap_non_libcloud_exceptions
from libcloud.utils.connection import get_response_object
from libcloud.utils.publickey import (
    get_pubkey_openssh_fingerprint,
    get_pubkey_ssh2_fingerprint,
)
from libcloud.common.types import LibcloudError
from libcloud.storage.drivers.dummy import DummyIterator


WARNINGS_BUFFER = []

if PY3:
    from io import FileIO as file


def show_warning(msg, cat, fname, lno, file=None, line=None):
    WARNINGS_BUFFER.append((msg, cat, fname, lno))

original_func = warnings.showwarning


class TestUtils(unittest.TestCase):
    def setUp(self):
        global WARNINGS_BUFFER
        WARNINGS_BUFFER = []

    def tearDown(self):
        global WARNINGS_BUFFER
        WARNINGS_BUFFER = []
        warnings.showwarning = original_func

    def test_guess_file_mime_type(self):
        file_path = os.path.abspath(__file__)
        mimetype, encoding = libcloud.utils.files.guess_file_mime_type(
            file_path=file_path)

        self.assertTrue(mimetype.find('python') != -1)

    def test_get_driver(self):
        driver = get_driver(drivers=DRIVERS, provider=Provider.DUMMY)
        self.assertTrue(driver is not None)

        try:
            driver = get_driver(drivers=DRIVERS, provider='fooba')
        except AttributeError:
            pass
        else:
            self.fail('Invalid provider, but an exception was not thrown')

    def test_get_driver_string_and_enum_notation(self):
        driver = get_driver(drivers=DRIVERS, provider=Provider.DUMMY)
        self.assertEqual(driver, DummyNodeDriver)

        driver = get_driver(drivers=DRIVERS, provider='dummy')
        self.assertEqual(driver, DummyNodeDriver)

        driver = get_driver(drivers=DRIVERS, provider='DUMMY')
        self.assertEqual(driver, DummyNodeDriver)

    def test_set_driver(self):
        # Set an existing driver
        try:
            driver = set_driver(DRIVERS, Provider.DUMMY,
                                'libcloud.storage.drivers.dummy',
                                'DummyStorageDriver')
        except AttributeError:
            pass

        # Register a new driver
        driver = set_driver(DRIVERS, 'testingset',
                            'libcloud.storage.drivers.dummy',
                            'DummyStorageDriver')

        self.assertTrue(driver is not None)

        # Register it again
        try:
            set_driver(DRIVERS, 'testingset',
                       'libcloud.storage.drivers.dummy',
                       'DummyStorageDriver')
        except AttributeError:
            pass

        # Register an invalid module
        try:
            set_driver(DRIVERS, 'testingnew',
                       'libcloud.storage.drivers.dummy1',
                       'DummyStorageDriver')
        except ImportError:
            pass

        # Register an invalid class
        try:
            set_driver(DRIVERS, 'testingnew',
                       'libcloud.storage.drivers.dummy',
                       'DummyStorageDriver1')
        except AttributeError:
            pass

    def test_deprecated_warning(self):
        warnings.showwarning = show_warning

        libcloud.utils.SHOW_DEPRECATION_WARNING = False
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.deprecated_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 0)

        libcloud.utils.SHOW_DEPRECATION_WARNING = True
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.deprecated_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 1)

    def test_in_development_warning(self):
        warnings.showwarning = show_warning

        libcloud.utils.SHOW_IN_DEVELOPMENT_WARNING = False
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.in_development_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 0)

        libcloud.utils.SHOW_IN_DEVELOPMENT_WARNING = True
        self.assertEqual(len(WARNINGS_BUFFER), 0)
        libcloud.utils.in_development_warning('test_module')
        self.assertEqual(len(WARNINGS_BUFFER), 1)

    def test_read_in_chunks_iterator_no_data(self):
        iterator = DummyIterator()
        generator1 = libcloud.utils.files.read_in_chunks(iterator=iterator,
                                                         yield_empty=False)
        generator2 = libcloud.utils.files.read_in_chunks(iterator=iterator,
                                                         yield_empty=True)

        # yield_empty=False
        count = 0
        for data in generator1:
            count += 1
            self.assertEqual(data, b(''))

        self.assertEqual(count, 0)

        # yield_empty=True
        count = 0
        for data in generator2:
            count += 1
            self.assertEqual(data, b(''))

        self.assertEqual(count, 1)

    def test_read_in_chunks_iterator(self):
        def iterator():
            for x in range(0, 1000):
                yield 'aa'

        for result in libcloud.utils.files.read_in_chunks(iterator(),
                                                          chunk_size=10,
                                                          fill_size=False):
            self.assertEqual(result, b('aa'))

        for result in libcloud.utils.files.read_in_chunks(iterator(), chunk_size=10,
                                                          fill_size=True):
            self.assertEqual(result, b('aaaaaaaaaa'))

    def test_read_in_chunks_filelike(self):
            class FakeFile(file):
                def __init__(self):
                    self.remaining = 500

                def read(self, size):
                    self.remaining -= 1
                    if self.remaining == 0:
                        return ''
                    return 'b' * (size + 1)

            for index, result in enumerate(libcloud.utils.files.read_in_chunks(
                                           FakeFile(), chunk_size=10,
                                           fill_size=False)):
                self.assertEqual(result, b('b' * 11))

            self.assertEqual(index, 498)

            for index, result in enumerate(libcloud.utils.files.read_in_chunks(
                                           FakeFile(), chunk_size=10,
                                           fill_size=True)):
                if index != 548:
                    self.assertEqual(result, b('b' * 10))
                else:
                    self.assertEqual(result, b('b' * 9))

            self.assertEqual(index, 548)

    def test_exhaust_iterator(self):
        def iterator_func():
            for x in range(0, 1000):
                yield 'aa'

        data = b('aa' * 1000)
        iterator = libcloud.utils.files.read_in_chunks(iterator=iterator_func())
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, data)

        result = libcloud.utils.files.exhaust_iterator(iterator=iterator_func())
        self.assertEqual(result, data)

        data = '12345678990'
        iterator = StringIO(data)
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, b(data))

    def test_exhaust_iterator_empty_iterator(self):
        data = ''
        iterator = StringIO(data)
        result = libcloud.utils.files.exhaust_iterator(iterator=iterator)
        self.assertEqual(result, b(data))

    def test_unicode_urlquote(self):
        # Regression tests for LIBCLOUD-429
        if PY3:
            # Note: this is a unicode literal
            val = '\xe9'
        else:
            val = codecs.unicode_escape_decode('\xe9')[0]

        uri = urlquote(val)
        self.assertEqual(b(uri), b('%C3%A9'))

        # Unicode without unicode characters
        uri = urlquote('v=1')
        self.assertEqual(b(uri), b('v%3D1'))

        # Already-encoded bytestring without unicode characters
        uri = urlquote(b('v=1'))
        self.assertEqual(b(uri), b('v%3D1'))

    def test_get_secure_random_string(self):
        for i in range(1, 500):
            value = get_secure_random_string(size=i)
            self.assertEqual(len(value), i)

    def test_hexadigits(self):
        self.assertEqual(hexadigits(b('')), [])
        self.assertEqual(hexadigits(b('a')), ['61'])
        self.assertEqual(hexadigits(b('AZaz09-')),
                         ['41', '5a', '61', '7a', '30', '39', '2d'])

    def test_bchr(self):
        if PY3:
            self.assertEqual(bchr(0), b'\x00')
            self.assertEqual(bchr(97), b'a')
        else:
            self.assertEqual(bchr(0), '\x00')
            self.assertEqual(bchr(97), 'a')


class NetworkingUtilsTestCase(unittest.TestCase):
    def test_is_public_and_is_private_subnet(self):
        public_ips = [
            '213.151.0.8',
            '86.87.86.1',
            '8.8.8.8',
            '8.8.4.4'
        ]

        private_ips = [
            '192.168.1.100',
            '10.0.0.1',
            '172.16.0.0'
        ]

        for address in public_ips:
            is_public = is_public_subnet(ip=address)
            is_private = is_private_subnet(ip=address)

            self.assertTrue(is_public)
            self.assertFalse(is_private)

        for address in private_ips:
            is_public = is_public_subnet(ip=address)
            is_private = is_private_subnet(ip=address)

            self.assertFalse(is_public)
            self.assertTrue(is_private)

    def test_is_valid_ip_address(self):
        valid_ipv4_addresses = [
            '192.168.1.100',
            '10.0.0.1',
            '213.151.0.8',
            '77.77.77.77'
        ]

        invalid_ipv4_addresses = [
            '10.1',
            '256.256.256.256',
            '0.567.567.567',
            '192.168.0.257'
        ]

        valid_ipv6_addresses = [
            'fe80::200:5aee:feaa:20a2',
            '2607:f0d0:1002:51::4',
            '2607:f0d0:1002:0051:0000:0000:0000:0004',
            '::1'
        ]

        invalid_ipv6_addresses = [
            '2607:f0d',
            '2607:f0d0:0004',
        ]

        for address in valid_ipv4_addresses:
            status = is_valid_ip_address(address=address,
                                         family=socket.AF_INET)
            self.assertTrue(status)

        for address in valid_ipv6_addresses:
            status = is_valid_ip_address(address=address,
                                         family=socket.AF_INET6)
            self.assertTrue(status)

        for address in chain(invalid_ipv4_addresses, invalid_ipv6_addresses):
            status = is_valid_ip_address(address=address,
                                         family=socket.AF_INET)
            self.assertFalse(status)

        for address in chain(invalid_ipv4_addresses, invalid_ipv6_addresses):
            status = is_valid_ip_address(address=address,
                                         family=socket.AF_INET6)
            self.assertFalse(status)

    def test_join_ipv4_segments(self):
        values = [
            (('127', '0', '0', '1'), '127.0.0.1'),
            (('255', '255', '255', '0'), '255.255.255.0'),
        ]

        for segments, joined_ip in values:
            result = join_ipv4_segments(segments=segments)
            self.assertEqual(result, joined_ip)

    def test_increment_ipv4_segments(self):
        values = [
            (('127', '0', '0', '1'), '127.0.0.2'),
            (('255', '255', '255', '0'), '255.255.255.1'),
            (('254', '255', '255', '255'), '255.0.0.0'),
            (('100', '1', '0', '255'), '100.1.1.0'),
        ]

        for segments, incremented_ip in values:
            result = increment_ipv4_segments(segments=segments)
            result = join_ipv4_segments(segments=result)
            self.assertEqual(result, incremented_ip)


class TestPublicKeyUtils(unittest.TestCase):

    PUBKEY = (
        'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDOfbWSXOlqvYjZmRO84/lIoV4gvuX+'
        'P1lLg50MMg6jZjLZIlYY081XPRmuom0xY0+BO++J2KgLl7gxJ6xMsKK2VQ+TakdfAH20'
        'XfMcTohd/zVCeWsbqZQvEhVXBo4hPIktcfNz0u9Ez3EtInO+kb7raLcRhOVi9QmOkOrC'
        'WtQU9mS71AWJuqI9H0YAnTiI8Hs5bn2tpMIqmTXT3g2bwywC25x1Nx9Hy0/FP+KUL6Ag'
        'vDXv47l+TgSDfTBEkvq+IF1ITrnaOG+nRE02oZC6cwHYTifM/IOollkujxIQmi2Z+j66'
        'OHSrjnEQugr0FqGJF2ygKfIh/i2u3fVLM60qE2NN user@example'
    )

    def test_pubkey_openssh_fingerprint(self):
        fp = get_pubkey_openssh_fingerprint(self.PUBKEY)
        self.assertEqual(fp, '35:22:13:5b:82:e2:5d:e1:90:8c:73:74:9f:ef:3b:d8')

    def test_pubkey_ssh2_fingerprint(self):
        fp = get_pubkey_ssh2_fingerprint(self.PUBKEY)
        self.assertEqual(fp, '11:ad:5d:4c:5b:99:c9:80:7e:81:03:76:5a:25:9d:8c')


def test_decorator():

    @wrap_non_libcloud_exceptions
    def foo():
        raise Exception("bork")

    with pytest.raises(LibcloudError):
        foo()


def test_get_response_object():
    with requests_mock.mock() as m:
        m.get('http://test.com/test', text='data')
        response = get_response_object('http://test.com/test')
        assert response.body == 'data'

if __name__ == '__main__':
    sys.exit(unittest.main())
