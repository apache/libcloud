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
import ssl
import time

from xml.etree import ElementTree as ET
from pipes import quote as pquote

try:
    import simplejson as json
except:
    import json

import libcloud


from libcloud.utils.py3 import PY3
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse
from libcloud.utils.py3 import urlencode
from libcloud.utils.py3 import StringIO
from libcloud.utils.py3 import u
from libcloud.utils.py3 import b

from libcloud.utils.misc import lowercase_keys
from libcloud.utils.compression import decompress_data
from libcloud.common.types import LibcloudError, MalformedResponseError

from libcloud.httplib_ssl import LibcloudHTTPSConnection

LibcloudHTTPConnection = httplib.HTTPConnection


class Response(object):
    """
    A Base Response class to derive from.
    """
    NODE_STATE_MAP = {}

    object = None
    body = None
    status = httplib.OK
    headers = {}
    error = None
    connection = None
    parse_zero_length_body = False

    def __init__(self, response, connection):
        self.body = self._decompress_response(response=response)

        if PY3:
            self.body = b(self.body).decode('utf-8')

        self.status = response.status

        # http.client In Python 3 doesn't automatically lowercase the header
        # names
        self.headers = lowercase_keys(dict(response.getheaders()))
        self.error = response.reason
        self.connection = connection

        if not self.success():
            raise Exception(self.parse_error())

        self.object = self.parse_body()

    def parse_body(self):
        """
        Parse response body.

        Override in a provider's subclass.

        @return: Parsed body.
        """
        return self.body

    def parse_error(self):
        """
        Parse the error messages.

        Override in a provider's subclass.

        @return: Parsed error.
        """
        return self.body

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        @return: C{True} or C{False}
        """
        return self.status == httplib.OK or self.status == httplib.CREATED

    def _decompress_response(self, response):
        """
        Decompress a response body if it is using deflate or gzip encoding.

        @return: Decompressed response
        """
        headers = lowercase_keys(dict(response.getheaders()))
        encoding = headers.get('content-encoding', None)

        original_data = getattr(response, '_original_data', None)

        if original_data is not None:
            return original_data

        body = response.read()

        if encoding in  ['zlib', 'deflate']:
            body = decompress_data('zlib', body)
        elif encoding in ['gzip', 'x-gzip']:
            body = decompress_data('gzip', body)
        else:
            body = body.strip()

        return body


class JsonResponse(Response):
    """
    A Base JSON Response class to derive from.
    """
    def parse_body(self):
        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            body = json.loads(self.body)
        except:
            raise MalformedResponseError(
                "Failed to parse JSON",
                body=self.body,
                driver=self.connection.driver)
        return body

    parse_error = parse_body


class XmlResponse(Response):
    """
    A Base XML Response class to derive from.
    """
    def parse_body(self):
        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML",
                                       body=self.body,
                                       driver=self.connection.driver)
        return body

    parse_error = parse_body


class RawResponse(Response):

    def __init__(self, connection):
        self._status = None
        self._response = None
        self._headers = {}
        self._error = None
        self._reason = None
        self.connection = connection

    @property
    def response(self):
        if not self._response:
            response = self.connection.connection.getresponse()
            self._response, self.body = response, response
            if not self.success():
                self.parse_error()
        return self._response

    @property
    def status(self):
        if not self._status:
            self._status = self.response.status
        return self._status

    @property
    def headers(self):
        if not self._headers:
            self._headers = lowercase_keys(dict(self.response.getheaders()))
        return self._headers

    @property
    def reason(self):
        if not self._reason:
            self._reason = self.response.reason
        return self._reason


#TODO: Move this to a better location/package
class LoggingConnection():
    """
    Debug class to log all HTTP(s) requests as they could be made
    with the C{curl} command.

    @cvar log: file-like object that logs entries are written to.
    """
    log = None

    def _log_response(self, r):
        rv = "# -------- begin %d:%d response ----------\n" % (id(self), id(r))
        ht = ""
        v = r.version
        if r.version == 10:
            v = "HTTP/1.0"
        if r.version == 11:
            v = "HTTP/1.1"
        ht += "%s %s %s\r\n" % (v, r.status, r.reason)
        body = r.read()
        for h in r.getheaders():
            ht += "%s: %s\r\n" % (h[0].title(), h[1])
        ht += "\r\n"

        # this is evil. laugh with me. ha arharhrhahahaha
        class fakesock:
            def __init__(self, s):
                self.s = s

            def makefile(self, *args, **kwargs):
                if PY3:
                    from io import BytesIO
                    cls = BytesIO
                else:
                    cls = StringIO

                return cls(b(self.s))
        rr = r
        original_data = body
        headers = lowercase_keys(dict(r.getheaders()))

        encoding = headers.get('content-encoding', None)

        if encoding in  ['zlib', 'deflate']:
            body = decompress_data('zlib', body)
        elif encoding in ['gzip', 'x-gzip']:
            body = decompress_data('gzip', body)

        if r.chunked:
            ht += "%x\r\n" % (len(body))
            ht += u(body)
            ht += "\r\n0\r\n"
        else:
            ht += u(body)
        rr = httplib.HTTPResponse(sock=fakesock(ht),
                                  method=r._method,
                                  debuglevel=r.debuglevel)
        rr.begin()
        rv += ht
        rv += ("\n# -------- end %d:%d response ----------\n"
               % (id(self), id(r)))

        rr._original_data = body
        return (rr, rv)

    def _log_curl(self, method, url, body, headers):
        cmd = ["curl", "-i"]

        cmd.extend(["-X", pquote(method)])

        for h in headers:
            cmd.extend(["-H", pquote("%s: %s" % (h, headers[h]))])

        # TODO: in python 2.6, body can be a file-like object.
        if body is not None and len(body) > 0:
            cmd.extend(["--data-binary", pquote(body)])

        cmd.extend(["--compress"])

        cmd.extend([pquote("https://%s:%d%s" % (self.host, self.port, url))])
        return " ".join(cmd)

class LoggingHTTPSConnection(LoggingConnection, LibcloudHTTPSConnection):
    """
    Utility Class for logging HTTPS connections
    """

    def getresponse(self):
        r = LibcloudHTTPSConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n" % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return LibcloudHTTPSConnection.request(self, method, url, body,
                                               headers)

class LoggingHTTPConnection(LoggingConnection, LibcloudHTTPConnection):
    """
    Utility Class for logging HTTP connections
    """

    def getresponse(self):
        r = LibcloudHTTPConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n" % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return LibcloudHTTPConnection.request(self, method, url,
                                               body, headers)


class Connection(object):
    """
    A Base Connection class to derive from.
    """
    #conn_classes = (LoggingHTTPSConnection)
    conn_classes = (LibcloudHTTPConnection, LibcloudHTTPSConnection)

    responseCls = Response
    rawResponseCls = RawResponse
    connection = None
    host = '127.0.0.1'
    port = 443
    secure = 1
    driver = None
    action = None

    def __init__(self, secure=True, host=None, port=None, url=None):
        self.secure = secure and 1 or 0
        self.ua = []
        self.context = {}

        self.request_path = ''

        if host:
            self.host = host

        if port != None:
            self.port = port
        else:
            if self.secure == 1:
                self.port = 443
            else:
                self.port = 80

        if url:
            (self.host, self.port, self.secure,
             self.request_path) = self._tuple_from_url(url)

    def set_context(self, context):
        self.context = context

    def _tuple_from_url(self, url):
        secure = 1
        port = None
        (scheme, netloc, request_path, param,
         query, fragment) = urlparse.urlparse(url)

        if scheme not in ['http', 'https']:
            raise LibcloudError('Invalid scheme: %s in url %s' % (scheme, url))

        if scheme == "http":
            secure = 0

        if ":" in netloc:
            netloc, port = netloc.rsplit(":")
            port = port

        if not port:
            if scheme == "http":
                port = 80
            else:
                port = 443

        host = netloc

        return (host, port, secure, request_path)

    def connect(self, host=None, port=None, base_url=None):
        """
        Establish a connection with the API server.

        @type host: C{str}
        @param host: Optional host to override our default

        @type port: C{int}
        @param port: Optional port to override our default

        @returns: A connection
        """
        # prefer the attribute base_url if its set or sent
        connection = None
        secure = self.secure

        if getattr(self, 'base_url', None) and base_url == None:
            (host, port, secure, request_path) = self._tuple_from_url(self.base_url)
        elif base_url != None:
            (host, port, secure, request_path) = self._tuple_from_url(base_url)
        else:
            host = host or self.host
            port = port or self.port

        kwargs = {'host': host, 'port': int(port)}

        connection = self.conn_classes[secure](**kwargs)
        # You can uncoment this line, if you setup a reverse proxy server
        # which proxies to your endpoint, and lets you easily capture
        # connections in cleartext when you setup the proxy to do SSL
        # for you
        #connection = self.conn_classes[False]("127.0.0.1", 8080)

        self.connection = connection

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                  libcloud.__version__,
                  self.driver.name,
                  "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, token):
        """
        Append a token to a user agent string.

        Users of the library should call this to uniquely identify thier requests
        to a provider.

        @type token: C{str}
        @param token: Token to add to the user agent.
        """
        self.ua.append(token)

    def request(self,
                action,
                params=None,
                data='',
                headers=None,
                method='GET',
                raw=False):
        """
        Request a given `action`.

        Basically a wrapper around the connection
        object's `request` that does some helpful pre-processing.

        @type action: C{str}
        @param action: A path

        @type params: C{dict}
        @param params: Optional mapping of additional parameters to send. If
            None, leave as an empty C{dict}.

        @type data: C{unicode}
        @param data: A body of data to send with the request.

        @type headers: C{dict}
        @param headers: Extra headers to add to the request
            None, leave as an empty C{dict}.

        @type method: C{str}
        @param method: An HTTP method such as "GET" or "POST".

        @type raw: C{bool}
        @param raw: True to perform a "raw" request aka only send the headers
                     and use the rawResponseCls class. This is used with
                     storage API when uploading a file.

        @return: An instance of type I{responseCls}
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        action = self.morph_action_hook(action)
        self.action = action
        self.method = method
        # Extend default parameters
        params = self.add_default_params(params)
        # Extend default headers
        headers = self.add_default_headers(headers)
        # We always send a user-agent header
        headers.update({'User-Agent': self._user_agent()})

        # Indicate that support gzip and deflate compression
        headers.update({'Accept-Encoding': 'gzip,deflate'})

        p = int(self.port)

        if p not in (80, 443):
            headers.update({'Host': "%s:%d" % (self.host, p)})
        else:
            headers.update({'Host': self.host})

        # Encode data if necessary
        if data != '' and data != None:
            data = self.encode_data(data)

        if data is not None:
            headers.update({'Content-Length': str(len(data))})

        params, headers = self.pre_connect_hook(params, headers)

        if params:
            url = '?'.join((action, urlencode(params)))
        else:
            url = action

        # Removed terrible hack...this a less-bad hack that doesn't execute a
        # request twice, but it's still a hack.
        self.connect()
        try:
            # @TODO: Should we just pass File object as body to request method
            # instead of dealing with splitting and sending the file ourselves?
            if raw:
                self.connection.putrequest(method, url)

                for key, value in list(headers.items()):
                    self.connection.putheader(key, str(value))

                self.connection.endheaders()
            else:
                self.connection.request(method=method, url=url, body=data,
                                        headers=headers)
        except ssl.SSLError:
            e = sys.exc_info()[1]
            raise ssl.SSLError(str(e))

        if raw:
            response = self.rawResponseCls(connection=self)
        else:
            response = self.responseCls(response=self.connection.getresponse(),
                                        connection=self)

        return response

    def morph_action_hook(self, action):
        return self.request_path + action

    def add_default_params(self, params):
        """
        Adds default parameters (such as API key, version, etc.)
        to the passed `params`

        Should return a dictionary.
        """
        return params

    def add_default_headers(self, headers):
        """
        Adds default headers (such as Authorization, X-Foo-Bar)
        to the passed `headers`

        Should return a dictionary.
        """
        return headers

    def pre_connect_hook(self, params, headers):
        """
        A hook which is called before connecting to the remote server.
        This hook can perform a final manipulation on the params, headers and
        url parameters.

        @type params: C{dict}
        @param params: Request parameters.

        @type headers: C{dict}
        @param headers: Request headers.
        """
        return params, headers

    def encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        return data

class PollingConnection(Connection):
    """
    Connection class which can also work with the async APIs.

    After initial requests, this class periodically polls for jobs status and
    waits until the job has finished.
    If job doesn't finish in timeout seconds, an Exception thrown.
    """
    poll_interval = 0.5
    timeout = 200
    request_method = 'request'

    def async_request(self, action, params=None, data='', headers=None,
                      method='GET', context=None):
        """
        Perform an 'async' request to the specified path. Keep in mind that
        this function is *blocking* and 'async' in this case means that the
        hit URL only returns a job ID which is the periodically polled until
        the job has completed.

        This function works like this:

        - Perform a request to the specified path. Response should contain a
          'job_id'.

        - Returned 'job_id' is then used to construct a URL which is used for
          retrieving job status. Constructed URL is then periodically polled
          until the response indicates that the job has completed or the timeout
          of 'self.timeout' seconds has been reached.

        @type action: C{str}
        @param action: A path

        @type params: C{dict}
        @param params: Optional mapping of additional parameters to send. If
            None, leave as an empty C{dict}.

        @type data: C{unicode}
        @param data: A body of data to send with the request.

        @type headers: C{dict}
        @param headers: Extra headers to add to the request
            None, leave as an empty C{dict}.

        @type method: C{str}
        @param method: An HTTP method such as "GET" or "POST".

        @type context: C{dict}
        @param context: Context dictionary which is passed to the functions
        which construct initial and poll URL.

        @return: An instance of type I{responseCls}
        """

        request = getattr(self, self.request_method)
        kwargs = self.get_request_kwargs(action=action, params=params,
                                         data=data, headers=headers,
                                         method=method,
                                         context=context)
        response = request(**kwargs)
        kwargs = self.get_poll_request_kwargs(response=response,
                                              context=context,
                                              request_kwargs=kwargs)

        end = time.time() + self.timeout
        completed = False
        while time.time() < end and not completed:
            response = request(**kwargs)
            completed = self.has_completed(response=response)
            if not completed:
                time.sleep(self.poll_interval)

        if not completed:
            raise LibcloudError('Job did not complete in %s seconds' %
                                (self.timeout))

        return response

    def get_request_kwargs(self, action, params=None, data='', headers=None,
                           method='GET', context=None):
        """
        Arguments which are passed to the initial request() call inside
        async_request.
        """
        kwargs = {'action': action, 'params': params, 'data': data,
                  'headers': headers, 'method': method}
        return kwargs

    def get_poll_request_kwargs(self, response, context, request_kwargs):
        """
        Return keyword arguments which are passed to the request() method when
        polling for the job status.

        @param response: Response object returned by poll request.
        @type response: C{HTTPResponse}

        @param request_kwargs: Kwargs previously used to initiate the
                                  poll request.
        @type response: C{dict}

        @return C{dict} Keyword arguments
        """
        raise NotImplementedError('get_poll_request_kwargs not implemented')

    def has_completed(self, response):
        """
        Return job completion status.

        @param response: Response object returned by poll request.
        @type response: C{HTTPResponse}

        @return C{bool} True if the job has completed, False otherwise.
        """
        raise NotImplementedError('has_completed not implemented')


class ConnectionKey(Connection):
    """
    A Base Connection class to derive from, which includes a
    """
    def __init__(self, key, secure=True, host=None, port=None, url=None):
        """
        Initialize `user_id` and `key`; set `secure` to an C{int} based on
        passed value.
        """
        super(ConnectionKey, self).__init__(secure=secure, host=host, port=port, url=url)
        self.key = key

class ConnectionUserAndKey(ConnectionKey):
    """
    Base connection which accepts a user_id and key
    """

    user_id = None

    def __init__(self, user_id, key, secure=True, host=None, port=None, url=None):
        super(ConnectionUserAndKey, self).__init__(key, secure=secure,
                                                   host=host, port=port, url=url)
        self.user_id = user_id


class BaseDriver(object):
    """
    Base driver class from which other classes can inherit from.
    """

    connectionCls = ConnectionKey

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None):
        """
        @keyword    key:    API key or username to used
        @type       key:    str

        @keyword    secret: Secret password to be used
        @type       secret: str

        @keyword    secure: Weither to use HTTPS or HTTP. Note: Some providers
                            only support HTTPS, and it is on by default.
        @type       secure: bool

        @keyword    host: Override hostname used for connections.
        @type       host: str

        @keyword    port: Override port used for connections.
        @type       port: int

        @keyword    api_version: Optional API version. Only used by drivers
                                 which support multiple API versions.
        @type       api_version: str

        """
        self.key = key
        self.secret = secret
        self.secure = secure
        args = [self.key]

        if self.secret is not None:
            args.append(self.secret)

        args.append(secure)

        if host is not None:
            args.append(host)

        if port is not None:
            args.append(port)

        self.connection = self.connectionCls(*args, **self._ex_connection_class_kwargs())

        self.connection.driver = self
        self.connection.connect()

    def _ex_connection_class_kwargs(self):
        """
        Return extra connection keyword arguments which are passed to the
        Connection class constructor.
        """
        return {}
