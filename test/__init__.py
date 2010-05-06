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
import httplib
from cStringIO import StringIO
from urllib2 import urlparse
from cgi import parse_qs
from libcloud.base import Node, NodeImage, NodeLocation

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


class MockResponse(object):
    """
    A mock HTTPResponse
    """
    headers = {}
    body = StringIO()
    status = 0
    reason = ''
    version = 11

    def __init__(self, status, body, headers=None, reason=None):
        self.status = status
        self.body = StringIO(body)
        self.headers = headers or self.headers
        self.reason = reason or self.reason

    def read(self, *args, **kwargs):
        return self.body.read(*args, **kwargs)

    def getheader(self, name, *args, **kwargs):
        return self.headers.get(name, *args, **kwargs)

    def getheaders(self):
        return self.headers.items()

    def msg(self):
        raise NotImplemented


class MockHttp(object):
    """
    A mock HTTP client/server suitable for testing purposes. This replaces
    `HTTPConnection` by implementing its API and returning a mock response.

    Define methods by request path, replacing slashes (/) with underscores (_).
    Each of these mock methods should return a tuple of:

        (int status, str body, dict headers, str reason)

    >>> mock = MockHttp('localhost', 8080)
    >>> mock.request('GET', '/example/')
    >>> response = mock.getresponse()
    >>> response.body.read()
    'Hello World!'
    >>> response.status
    200
    >>> response.getheaders()
    [('X-Foo', 'libcloud')]
    >>> MockHttp.type = 'fail'
    >>> mock.request('GET', '/example/')
    >>> response = mock.getresponse()
    >>> response.body.read()
    'Oh Noes!'
    >>> response.status
    403
    >>> response.getheaders()
    [('X-Foo', 'fail')]

    """
    responseCls = MockResponse
    host = None
    port = None
    response = None

    type = None
    use_param = None # will use this param to namespace the request function

    def __init__(self, host, port, *args, **kwargs):
        self.host = host
        self.port = port

    def request(self, method, url, body=None, headers=None):
        # Find a method we can use for this request
        parsed = urlparse.urlparse(url)
        scheme, netloc, path, params, query, fragment = parsed
        qs = parse_qs(query)
        if path.endswith('/'):
            path = path[:-1]
        meth_name = path.replace('/','_').replace('.', '_').replace('-','_')
        if self.type:
            meth_name = '%s_%s' % (meth_name, self.type)
        if self.use_param:
            param = qs[self.use_param][0].replace('.', '_').replace('-','_')
            meth_name = '%s_%s' % (meth_name, param)
        meth = getattr(self, meth_name)
        status, body, headers, reason = meth(method, url, body, headers)
        self.response = self.responseCls(status, body, headers, reason)

    def getresponse(self):
        return self.response

    def connect(self):
        """
        Can't think of anything to mock here.
        """
        pass

    def close(self):
        pass

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


class TestCaseMixin(object):

    def test_list_nodes_response(self):
        nodes = self.driver.list_nodes()
        self.assertTrue(isinstance(nodes, list))
        for node in nodes:
            self.assertTrue(isinstance(node, Node))

    def test_list_sizes_response(self):
        sizes = self.driver.list_sizes()
        size = sizes[0]
        self.assertTrue(isinstance(sizes, list))
        # Check that size values are ints or None
        self.assertTrue(size.ram is None or isinstance(size.ram, int))
        self.assertTrue(size.disk is None or isinstance(size.disk, int))
        self.assertTrue(size.bandwidth is None or
                            isinstance(size.bandwidth, int))

    def test_list_images_response(self):
        images = self.driver.list_images()
        self.assertTrue(isinstance(images, list))
        for image in images:
            self.assertTrue(isinstance(image, NodeImage))


    def test_list_locations_response(self):
        locations = self.driver.list_locations()
        self.assertTrue(isinstance(locations, list))
        for dc in locations:
            self.assertTrue(isinstance(dc, NodeLocation))

    def test_create_node_response(self):
        # should return a node object
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='node-name',
                                     image=image,
                                     size=size)
        self.assertTrue(isinstance(node, Node))

    def test_destroy_node_response(self):
        # should return a node object
        node = self.driver.list_nodes()[0]
        ret = self.driver.destroy_node(node)
        self.assertTrue(isinstance(ret, bool))

    def test_reboot_node_response(self):
        # should return a node object
        node = self.driver.list_nodes()[0]
        ret = self.driver.reboot_node(node)
        self.assertTrue(isinstance(ret, bool))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
