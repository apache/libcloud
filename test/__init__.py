# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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


class multipleresponse(object):
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

    def __init__(self, host, port, *args, **kwargs):
        self.host = host
        self.port = port

    def request(self, method, url, body=None, headers=None):
        # Find a method we can use for this request
        path = urlparse.urlparse(url)[2]
        if path.endswith('/'):
            path = path[:-1]
        meth = getattr(self, path.replace('/','_').replace('.', '_'))
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
    @multipleresponse
    def _example(self, method, url, body, headers):
        """
        Return a simple message and header, regardless of input.
        """
        return ((httplib.OK, 'Hello World!', {'X-Foo': 'libcloud'},
                httplib.responses[httplib.OK]),
                (httplib.FORBIDDEN, 'Oh Noes!', {'X-Foo': 'fail'},
                httplib.responses[httplib.FORBIDDEN]))



if __name__ == "__main__":
    import doctest
    doctest.testmod()

