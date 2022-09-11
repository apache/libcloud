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

import os
import ssl
import sys
import socket
from unittest import mock
from unittest.mock import Mock, patch

import requests_mock
from requests.exceptions import ConnectTimeout

import libcloud.common.base
from libcloud.http import LibcloudConnection, SignedHTTPSAdapter, LibcloudBaseConnection
from libcloud.test import unittest, no_internet
from libcloud.utils.py3 import assertRaisesRegex
from libcloud.common.base import Response, Connection, CertificateConnection
from libcloud.utils.retry import RETRY_EXCEPTIONS, Retry, RetryForeverOnRateLimitError
from libcloud.common.exceptions import RateLimitReachedError


class BaseConnectionClassTestCase(unittest.TestCase):
    def setUp(self):
        self.orig_http_proxy = os.environ.pop("http_proxy", None)
        self.orig_https_proxy = os.environ.pop("https_proxy", None)

    def tearDown(self):
        if self.orig_http_proxy:
            os.environ["http_proxy"] = self.orig_http_proxy
        elif "http_proxy" in os.environ:
            del os.environ["http_proxy"]

        if self.orig_https_proxy:
            os.environ["https_proxy"] = self.orig_https_proxy
        elif "https_proxy" in os.environ:
            del os.environ["https_proxy"]

        libcloud.common.base.ALLOW_PATH_DOUBLE_SLASHES = False

    def test_parse_proxy_url(self):
        conn = LibcloudBaseConnection()

        proxy_url = "http://127.0.0.1:3128"
        result = conn._parse_proxy_url(proxy_url=proxy_url)
        self.assertEqual(result[0], "http")
        self.assertEqual(result[1], "127.0.0.1")
        self.assertEqual(result[2], 3128)
        self.assertIsNone(result[3])
        self.assertIsNone(result[4])

        proxy_url = "https://127.0.0.2:3129"
        result = conn._parse_proxy_url(proxy_url=proxy_url)
        self.assertEqual(result[0], "https")
        self.assertEqual(result[1], "127.0.0.2")
        self.assertEqual(result[2], 3129)
        self.assertIsNone(result[3])
        self.assertIsNone(result[4])

        proxy_url = "http://user1:pass1@127.0.0.1:3128"
        result = conn._parse_proxy_url(proxy_url=proxy_url)
        self.assertEqual(result[0], "http")
        self.assertEqual(result[1], "127.0.0.1")
        self.assertEqual(result[2], 3128)
        self.assertEqual(result[3], "user1")
        self.assertEqual(result[4], "pass1")

        proxy_url = "https://user1:pass1@127.0.0.2:3129"
        result = conn._parse_proxy_url(proxy_url=proxy_url)
        self.assertEqual(result[0], "https")
        self.assertEqual(result[1], "127.0.0.2")
        self.assertEqual(result[2], 3129)
        self.assertEqual(result[3], "user1")
        self.assertEqual(result[4], "pass1")

        proxy_url = "http://127.0.0.1"
        expected_msg = "proxy_url must be in the following format"
        assertRaisesRegex(
            self, ValueError, expected_msg, conn._parse_proxy_url, proxy_url=proxy_url
        )

        proxy_url = "http://@127.0.0.1:3128"
        expected_msg = "URL is in an invalid format"
        assertRaisesRegex(
            self, ValueError, expected_msg, conn._parse_proxy_url, proxy_url=proxy_url
        )

        proxy_url = "http://user@127.0.0.1:3128"
        expected_msg = "URL is in an invalid format"
        assertRaisesRegex(
            self, ValueError, expected_msg, conn._parse_proxy_url, proxy_url=proxy_url
        )

    def test_constructor(self):
        proxy_url = "http://127.0.0.2:3128"
        os.environ["http_proxy"] = proxy_url
        conn = LibcloudConnection(host="localhost", port=80)
        self.assertEqual(conn.proxy_scheme, "http")
        self.assertEqual(conn.proxy_host, "127.0.0.2")
        self.assertEqual(conn.proxy_port, 3128)
        self.assertEqual(
            conn.session.proxies,
            {"http": "http://127.0.0.2:3128", "https": "http://127.0.0.2:3128"},
        )

        _ = os.environ.pop("http_proxy", None)
        conn = LibcloudConnection(host="localhost", port=80)
        self.assertIsNone(conn.proxy_scheme)
        self.assertIsNone(conn.proxy_host)
        self.assertIsNone(conn.proxy_port)

        proxy_url = "http://127.0.0.3:3128"
        conn.set_http_proxy(proxy_url=proxy_url)
        self.assertEqual(conn.proxy_scheme, "http")
        self.assertEqual(conn.proxy_host, "127.0.0.3")
        self.assertEqual(conn.proxy_port, 3128)
        self.assertEqual(
            conn.session.proxies,
            {"http": "http://127.0.0.3:3128", "https": "http://127.0.0.3:3128"},
        )

        proxy_url = "http://127.0.0.4:3128"
        conn = LibcloudConnection(host="localhost", port=80, proxy_url=proxy_url)
        self.assertEqual(conn.proxy_scheme, "http")
        self.assertEqual(conn.proxy_host, "127.0.0.4")
        self.assertEqual(conn.proxy_port, 3128)
        self.assertEqual(
            conn.session.proxies,
            {"http": "http://127.0.0.4:3128", "https": "http://127.0.0.4:3128"},
        )

        os.environ["http_proxy"] = proxy_url
        proxy_url = "http://127.0.0.5:3128"
        conn = LibcloudConnection(host="localhost", port=80, proxy_url=proxy_url)
        self.assertEqual(conn.proxy_scheme, "http")
        self.assertEqual(conn.proxy_host, "127.0.0.5")
        self.assertEqual(conn.proxy_port, 3128)
        self.assertEqual(
            conn.session.proxies,
            {"http": "http://127.0.0.5:3128", "https": "http://127.0.0.5:3128"},
        )

        os.environ["http_proxy"] = proxy_url
        proxy_url = "https://127.0.0.6:3129"
        conn = LibcloudConnection(host="localhost", port=80, proxy_url=proxy_url)
        self.assertEqual(conn.proxy_scheme, "https")
        self.assertEqual(conn.proxy_host, "127.0.0.6")
        self.assertEqual(conn.proxy_port, 3129)
        self.assertEqual(
            conn.session.proxies,
            {"http": "https://127.0.0.6:3129", "https": "https://127.0.0.6:3129"},
        )

    def test_connection_to_unusual_port(self):
        conn = LibcloudConnection(host="localhost", port=8080)
        self.assertIsNone(conn.proxy_scheme)
        self.assertIsNone(conn.proxy_host)
        self.assertIsNone(conn.proxy_port)
        self.assertEqual(conn.host, "http://localhost:8080")

        conn = LibcloudConnection(host="localhost", port=80)
        self.assertEqual(conn.host, "http://localhost")

    def test_connection_session_timeout(self):
        """
        Test that the connection timeout attribute is set correctly
        """
        conn = LibcloudConnection(host="localhost", port=8080)
        self.assertEqual(conn.session.timeout, 60)

        conn = LibcloudConnection(host="localhost", port=8080, timeout=10)
        self.assertEqual(conn.session.timeout, 10)

    @unittest.skipIf(no_internet(), "Internet is not reachable")
    def test_connection_timeout_raised(self):
        """
        Test that the connection times out
        """
        conn = LibcloudConnection(host="localhost", port=8080, timeout=0.1)
        # use a not-routable address to test that the connection timeouts
        host = "http://10.255.255.1"
        with self.assertRaises(ConnectTimeout):
            conn.request("GET", host)

    def test_connection_url_merging(self):
        """
        Test that the connection class will parse URLs correctly
        """
        conn = Connection(url="http://test.com/")
        conn.connect()
        self.assertEqual(conn.connection.host, "http://test.com")
        with requests_mock.mock() as m:
            m.get("http://test.com/test", text="data")
            response = conn.request("/test")
        self.assertEqual(response.body, "data")

    def test_morph_action_hook(self):
        conn = Connection(url="http://test.com")

        conn.request_path = ""
        self.assertEqual(conn.morph_action_hook("/test"), "/test")
        self.assertEqual(conn.morph_action_hook("test"), "/test")

        conn.request_path = "/v1"
        self.assertEqual(conn.morph_action_hook("/test"), "/v1/test")
        self.assertEqual(conn.morph_action_hook("test"), "/v1/test")

        conn.request_path = "/v1"
        self.assertEqual(conn.morph_action_hook("/test"), "/v1/test")
        self.assertEqual(conn.morph_action_hook("test"), "/v1/test")

        conn.request_path = "v1"
        self.assertEqual(conn.morph_action_hook("/test"), "/v1/test")
        self.assertEqual(conn.morph_action_hook("test"), "/v1/test")

        conn.request_path = "v1/"
        self.assertEqual(conn.morph_action_hook("/test"), "/v1/test")
        self.assertEqual(conn.morph_action_hook("test"), "/v1/test")

        conn.request_path = "/a"
        self.assertEqual(conn.morph_action_hook("//b/c.txt"), "/a/b/c.txt")

        conn.request_path = "/b"
        self.assertEqual(conn.morph_action_hook("/foo//"), "/b/foo/")

        libcloud.common.base.ALLOW_PATH_DOUBLE_SLASHES = True

        conn.request_path = "/"
        self.assertEqual(conn.morph_action_hook("/"), "//")

        conn.request_path = ""
        self.assertEqual(conn.morph_action_hook("/"), "/")

        conn.request_path = "/a"
        self.assertEqual(conn.morph_action_hook("//b/c.txt"), "/a//b/c.txt")

        conn.request_path = "/b"
        self.assertEqual(conn.morph_action_hook("/foo//"), "/b/foo//")

    def test_connect_with_prefix(self):
        """
        Test that a connection with a base path (e.g. /v1/) will
        add the base path to requests
        """
        conn = Connection(url="http://test.com/")
        conn.connect()
        conn.request_path = "/v1"
        self.assertEqual(conn.connection.host, "http://test.com")
        with requests_mock.mock() as m:
            m.get("http://test.com/v1/test", text="data")
            response = conn.request("/test")
        self.assertEqual(response.body, "data")

    def test_secure_connection_unusual_port(self):
        """
        Test that the connection class will default to secure (https) even
        when the port is an unusual (non 443, 80) number
        """
        conn = Connection(secure=True, host="localhost", port=8081)
        conn.connect()
        self.assertEqual(conn.connection.host, "https://localhost:8081")

        conn2 = Connection(url="https://localhost:8081")
        conn2.connect()
        self.assertEqual(conn2.connection.host, "https://localhost:8081")

    def test_secure_by_default(self):
        """
        Test that the connection class will default to secure (https)
        """
        conn = Connection(host="localhost", port=8081)
        conn.connect()
        self.assertEqual(conn.connection.host, "https://localhost:8081")

    def test_implicit_port(self):
        """
        Test that the port is not included in the URL if the protocol implies
        the port, e.g. http implies 80
        """
        conn = Connection(secure=True, host="localhost", port=443)
        conn.connect()
        self.assertEqual(conn.connection.host, "https://localhost")

        conn2 = Connection(secure=False, host="localhost", port=80)
        conn2.connect()
        self.assertEqual(conn2.connection.host, "http://localhost")

    def test_insecure_connection_unusual_port(self):
        """
        Test that the connection will allow unusual ports and insecure
        schemes
        """
        conn = Connection(secure=False, host="localhost", port=8081)
        conn.connect()
        self.assertEqual(conn.connection.host, "http://localhost:8081")

        conn2 = Connection(url="http://localhost:8081")
        conn2.connect()
        self.assertEqual(conn2.connection.host, "http://localhost:8081")


class ConnectionClassTestCase(unittest.TestCase):
    def setUp(self):
        self.originalConnect = Connection.connect
        self.originalResponseCls = Connection.responseCls

        Connection.connect = Mock()
        Connection.responseCls = Mock()
        Connection.allow_insecure = True

    def tearDown(self):
        Connection.connect = self.originalConnect
        Connection.responseCls = Connection.responseCls
        Connection.allow_insecure = True

    def test_dont_allow_insecure(self):
        Connection.allow_insecure = True
        Connection(secure=False)

        Connection.allow_insecure = False

        expected_msg = r"Non https connections are not allowed \(use " r"secure=True\)"
        assertRaisesRegex(self, ValueError, expected_msg, Connection, secure=False)

    def test_cache_busting(self):
        params1 = {"foo1": "bar1", "foo2": "bar2"}
        params2 = [("foo1", "bar1"), ("foo2", "bar2")]

        con = Connection()
        con.connection = Mock()
        con.pre_connect_hook = Mock()
        con.pre_connect_hook.return_value = {}, {}
        con.cache_busting = False

        con.request(action="/path", params=params1)
        args, kwargs = con.pre_connect_hook.call_args
        self.assertFalse("cache-busting" in args[0])
        self.assertEqual(args[0], params1)

        con.request(action="/path", params=params2)
        args, kwargs = con.pre_connect_hook.call_args
        self.assertFalse("cache-busting" in args[0])
        self.assertEqual(args[0], params2)

        con.cache_busting = True

        con.request(action="/path", params=params1)
        args, kwargs = con.pre_connect_hook.call_args
        self.assertTrue("cache-busting" in args[0])

        con.request(action="/path", params=params2)
        args, kwargs = con.pre_connect_hook.call_args
        self.assertTrue("cache-busting" in args[0][len(params2)])

    def test_context_is_reset_after_request_has_finished(self):
        context = {"foo": "bar"}

        def responseCls(connection, response) -> mock.MagicMock:
            connection.called = True
            self.assertEqual(connection.context, context)
            return mock.MagicMock(spec=Response)

        con = Connection()
        con.called = False
        con.connection = Mock()
        con.responseCls = responseCls

        con.set_context(context)
        self.assertEqual(con.context, context)

        con.request("/")

        # Context should have been reset
        self.assertTrue(con.called)
        self.assertEqual(con.context, {})

        # Context should also be reset if a method inside request throws
        con = Connection(timeout=1, retry_delay=0.1)
        con.connection = Mock()

        con.set_context(context)
        self.assertEqual(con.context, context)
        con.connection.request = Mock(side_effect=ssl.SSLError())

        try:
            con.request("/")
        except ssl.SSLError:
            pass

        self.assertEqual(con.context, {})

        con.connection = Mock()
        con.set_context(context)
        self.assertEqual(con.context, context)

        con.responseCls = Mock(side_effect=ValueError())

        try:
            con.request("/")
        except ValueError:
            pass

        self.assertEqual(con.context, {})

    def _raise_socket_error(self):
        raise socket.gaierror("")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_with_sleep(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        mock_connect.side_effect = socket.gaierror("")
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        self.assertRaises(socket.gaierror, retry_request(con.request), action="/")

        self.assertGreater(mock_connect.call_count, 1, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_with_timeout(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        mock_connect.side_effect = socket.gaierror("")
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        self.assertRaises(socket.gaierror, retry_request(con.request), action="/")

        self.assertGreater(mock_connect.call_count, 1, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_with_backoff(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        mock_connect.side_effect = socket.gaierror("")
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        self.assertRaises(socket.gaierror, retry_request(con.request), action="/")
        self.assertGreater(mock_connect.call_count, 1, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_rate_limit_error_timeout(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        mock_connect.__name__ = "mock_connect"
        headers = {"retry-after": 0.2}
        mock_connect.side_effect = RateLimitReachedError(headers=headers)
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        self.assertRaises(RateLimitReachedError, retry_request(con.request), action="/")
        self.assertGreater(mock_connect.call_count, 1, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_rate_limit_error_forever_with_old_retry_class(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        self.retry_counter = 0

        def mock_connect_side_effect(*args, **kwargs):
            self.retry_counter += 1

            if self.retry_counter < 4:
                headers = {"retry-after": 0.1}
                raise RateLimitReachedError(headers=headers)

            return "success"

        mock_connect.__name__ = "mock_connect"
        mock_connect.side_effect = mock_connect_side_effect
        retry_request = RetryForeverOnRateLimitError(timeout=1, retry_delay=0.1, backoff=1)
        retry_request(con.request)(action="/")

        # We have waited longer the timeout but continue to retry
        result = retry_request(con.request)(action="/")
        self.assertEqual(result, "success")

        self.assertEqual(mock_connect.call_count, 5, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_should_not_retry_on_non_defined_exception(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        self.retry_counter = 0

        mock_connect.__name__ = "mock_connect"
        mock_connect.side_effect = ValueError("should not retry this " "error")
        retry_request = Retry(timeout=5, retry_delay=0.1, backoff=1)

        self.assertRaisesRegex(
            ValueError,
            "should not retry this error",
            retry_request(con.request),
            action="/",
        )
        self.assertEqual(mock_connect.call_count, 1, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_rate_limit_error_success_on_second_attempt(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        self.retry_counter = 0

        def mock_connect_side_effect(*args, **kwargs):
            self.retry_counter += 1

            if self.retry_counter < 2:
                headers = {"retry-after": 0.2}
                raise RateLimitReachedError(headers=headers)

            return "success"

        mock_connect.__name__ = "mock_connect"
        mock_connect.side_effect = mock_connect_side_effect
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        result = retry_request(con.request)(action="/")
        self.assertEqual(result, "success")

        self.assertEqual(mock_connect.call_count, 2, "Retry logic failed")

    @patch("libcloud.common.base.Connection.request")
    def test_retry_on_all_default_retry_exception_classes(self, mock_connect):
        con = Connection()
        con.connection = Mock()

        self.retry_counter = 0

        def mock_connect_side_effect(*args, **kwargs):
            self.retry_counter += 1

            if self.retry_counter < len(RETRY_EXCEPTIONS):
                raise RETRY_EXCEPTIONS[self.retry_counter]

            return "success"

        mock_connect.__name__ = "mock_connect"
        mock_connect.side_effect = mock_connect_side_effect
        retry_request = Retry(timeout=1, retry_delay=0.1, backoff=1)
        result = retry_request(con.request)(action="/")
        self.assertEqual(result, "success")

        self.assertEqual(mock_connect.call_count, len(RETRY_EXCEPTIONS), "Retry logic failed")

    def test_request_parses_errors(self):
        class ThrowingResponse(Response):
            def __init__(self, *_, **__):
                super().__init__(mock.MagicMock(), mock.MagicMock())

            def parse_body(self):
                return super().parse_body()

            def parse_error(self):
                raise RateLimitReachedError()

            def success(self):
                return False

        con = Connection()
        con.connection = Mock()
        con.responseCls = ThrowingResponse

        with self.assertRaises(RateLimitReachedError):
            con.request(action="/")

    def test_parse_errors_can_be_retried(self):
        class RetryableThrowingError(Response):
            parse_error_counter: int = 0
            success_counter: int = 0

            def __init__(self, *_, **__):
                super().__init__(mock.MagicMock(), mock.MagicMock())

            def parse_body(self):
                return super().parse_body()

            def parse_error(self):
                RetryableThrowingError.parse_error_counter += 1
                if RetryableThrowingError.parse_error_counter > 1:
                    return "success"
                else:
                    raise RateLimitReachedError()

            def success(self):
                RetryableThrowingError.success_counter += 1
                if RetryableThrowingError.success_counter > 1:
                    return True
                else:
                    return False

        con = Connection()
        con.connection = Mock()
        con.responseCls = RetryableThrowingError
        result = con.request(action="/", retry_failed=True)

        self.assertEqual(result.success(), True)


class CertificateConnectionClassTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = CertificateConnection(cert_file="test.pem", url="https://test.com/test")
        self.connection.connect()

    def test_adapter_internals(self):
        adapter = self.connection.connection.session.adapters["https://"]
        self.assertTrue(isinstance(adapter, SignedHTTPSAdapter))
        self.assertEqual(adapter.cert_file, "test.pem")


if __name__ == "__main__":
    sys.exit(unittest.main())
