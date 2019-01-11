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

import unittest
import random
import requests
from libcloud.common.base import Response
from libcloud.http import LibcloudConnection
from libcloud.utils.py3 import PY2

if PY2:
    from StringIO import StringIO
else:
    from io import StringIO

import requests_mock

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import parse_qs
from libcloud.utils.py3 import parse_qsl
from libcloud.utils.py3 import urlquote


XML_HEADERS = {'content-type': 'application/xml'}


class LibcloudTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self._visited_urls = []
        self._executed_mock_methods = []
        super(LibcloudTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        self._visited_urls = []
        self._executed_mock_methods = []

    def _add_visited_url(self, url):
        self._visited_urls.append(url)

    def _add_executed_mock_method(self, method_name):
        self._executed_mock_methods.append(method_name)

    def assertExecutedMethodCount(self, expected):
        actual = len(self._executed_mock_methods)
        self.assertEqual(actual, expected,
                         'expected %d, but %d mock methods were executed'
                         % (expected, actual))


class multipleresponse(object):
    """
    A decorator that allows MockHttp objects to return multi responses
    """
    count = 0
    func = None

    def __init__(self, f):
        self.func = f

    def __call__(self, *args, **kwargs):
        ret = self.func(self.func.__class__, *args, **kwargs)
        response = ret[self.count]
        self.count = self.count + 1
        return response


class BodyStream(StringIO):
    def next(self, chunk_size=None):
        return StringIO.next(self)

    def __next__(self, chunk_size=None):
        return StringIO.__next__(self)

    def read(self, chunk_size=None):
        return StringIO.read(self)


class MockHttp(LibcloudConnection):
    """
    A mock HTTP client/server suitable for testing purposes. This replaces
    `HTTPConnection` by implementing its API and returning a mock response.

    Define methods by request path, replacing slashes (/) with underscores (_).
    Each of these mock methods should return a tuple of:

        (int status, str body, dict headers, str reason)
    """
    type = None
    use_param = None  # will use this param to namespace the request function
    test = None  # TestCase instance which is using this mock
    proxy_url = None

    def __init__(self, *args, **kwargs):
        # Load assertion methods into the class, incase people want to assert
        # within a response
        if isinstance(self, unittest.TestCase):
            unittest.TestCase.__init__(self, '__init__')
        super(MockHttp, self).__init__(*args, **kwargs)

    def _get_request(self, method, url, body=None, headers=None):
        # Find a method we can use for this request
        parsed = urlparse.urlparse(url)
        _, _, path, _, query, _ = parsed
        qs = parse_qs(query)
        if path.endswith('/'):
            path = path[:-1]
        meth_name = self._get_method_name(type=self.type,
                                          use_param=self.use_param,
                                          qs=qs, path=path)
        meth = getattr(self, meth_name.replace('%', '_'))

        if self.test and isinstance(self.test, LibcloudTestCase):
            self.test._add_visited_url(url=url)
            self.test._add_executed_mock_method(method_name=meth_name)
        return meth(method, url, body, headers)

    def request(self, method, url, body=None, headers=None, raw=False, stream=False):
        headers = self._normalize_headers(headers=headers)
        r_status, r_body, r_headers, r_reason = self._get_request(method, url, body, headers)
        if r_body is None:
            r_body = ''
        # this is to catch any special chars e.g. ~ in the request. URL
        url = urlquote(url)

        with requests_mock.mock() as m:
            m.register_uri(method, url, text=r_body, reason=r_reason,
                           headers=r_headers, status_code=r_status)
            try:
                super(MockHttp, self).request(
                    method=method, url=url, body=body, headers=headers,
                    raw=raw, stream=stream)
            except requests_mock.exceptions.NoMockAddress as nma:
                raise AttributeError("Failed to mock out URL {0} - {1}".format(
                    url, nma.request.url
                ))

    def prepared_request(self, method, url, body=None,
                         headers=None, raw=False, stream=False):
        headers = self._normalize_headers(headers=headers)
        r_status, r_body, r_headers, r_reason = self._get_request(method, url, body, headers)

        with requests_mock.mock() as m:
            m.register_uri(method, url, text=r_body, reason=r_reason,
                           headers=r_headers, status_code=r_status)
            super(MockHttp, self).prepared_request(
                method=method, url=url, body=body, headers=headers,
                raw=raw, stream=stream)

    # Mock request/response example
    def _example(self, method, url, body, headers):
        """
        Return a simple message and header, regardless of input.
        """
        return (httplib.OK, 'Hello World!', {'X-Foo': 'libcloud'},
                httplib.responses[httplib.OK])

    def _example_fail(self, method, url, body, headers):
        return (httplib.FORBIDDEN, 'Oh Noes!', {'X-Foo': 'fail'},
                httplib.responses[httplib.FORBIDDEN])

    def _get_method_name(self, type, use_param, qs, path):
        path = path.split('?')[0]
        meth_name = (
            path
            .replace('/', '_')
            .replace('.', '_')
            .replace('-', '_')
            .replace('~', '%7E'))  # Python 3.7 no longer quotes ~

        if type:
            meth_name = '%s_%s' % (meth_name, self.type)

        if use_param and use_param in qs:
            param = qs[use_param][0].replace('.', '_').replace('-', '_')
            meth_name = '%s_%s' % (meth_name, param)

        if meth_name == '':
            meth_name = 'root'

        return meth_name

    def assertUrlContainsQueryParams(self, url, expected_params, strict=False):
        """
        Assert that provided url contains provided query parameters.

        :param url: URL to assert.
        :type url: ``str``

        :param expected_params: Dictionary of expected query parameters.
        :type expected_params: ``dict``

        :param strict: Assert that provided url contains only expected_params.
                       (defaults to ``False``)
        :type strict: ``bool``
        """
        question_mark_index = url.find('?')

        if question_mark_index != -1:
            url = url[question_mark_index + 1:]

        params = dict(parse_qsl(url))

        if strict:
            assert params == expected_params
        else:
            for key, value in expected_params.items():
                assert key in params
                assert params[key] == value


class MockConnection(object):
    def __init__(self, action):
        self.action = action

StorageMockHttp = MockHttp


def make_response(status=200, headers={}, connection=None):
    response = requests.Response()
    response.status_code = status
    response.headers = headers
    return Response(response, connection)


def generate_random_data(size):
    data = ''
    current_size = 0
    while current_size < size:
        value = str(random.randint(0, 9))
        value_size = len(value)
        data += value
        current_size += value_size
    return data

if __name__ == "__main__":
    import doctest
    doctest.testmod()
