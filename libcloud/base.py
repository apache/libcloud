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
Provides base classes for working with drivers
"""
import httplib, urllib
import libcloud
from zope import interface
from libcloud.interface import IConnectionUserAndKey, IResponse
from libcloud.interface import IConnectionKey, IConnectionKeyFactory
from libcloud.interface import IConnectionUserAndKeyFactory, IResponseFactory
from libcloud.interface import INodeDriverFactory, INodeDriver
from libcloud.interface import INodeFactory, INode
from libcloud.interface import INodeSizeFactory, INodeSize
from libcloud.interface import INodeImageFactory, INodeImage
from libcloud.types import NodeState, DeploymentException
from libcloud.ssh import SSHClient
import time
import hashlib
import StringIO
import os
import socket
import struct
from pipes import quote as pquote


class Node(object):
    """
    A Base Node class to derive from.
    """

    interface.implements(INode)
    interface.classProvides(INodeFactory)

    def __init__(self, id, name, state, public_ip, private_ip,
                 driver, extra=None):
        self.id = id
        self.name = name
        self.state = state
        self.public_ip = public_ip
        self.private_ip = private_ip
        self.driver = driver
        self.uuid = self.get_uuid()
        if not extra:
            self.extra = {}
        else:
            self.extra = extra

    def get_uuid(self):
        """Unique hash for this node
        @return: C{string}
        """
        return hashlib.sha1("%s:%d" % (self.id,self.driver.type)).hexdigest()

    def reboot(self):
        """Reboot this node
        @return: C{bool}
        """
        return self.driver.reboot_node(self)

    def destroy(self):
        """Destroy this node
        @return: C{bool}
        """
        return self.driver.destroy_node(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, state=%s, public_ip=%s, '
                 'provider=%s ...>')
                % (self.uuid, self.name, self.state, self.public_ip,
                   self.driver.name))


class NodeSize(object):
    """
    A Base NodeSize class to derive from.
    """

    interface.implements(INodeSize)
    interface.classProvides(INodeSizeFactory)

    def __init__(self, id, name, ram, disk, bandwidth, price, driver):
        self.id = id
        self.name = name
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver
    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))


class NodeImage(object):
    """
    A Base NodeImage class to derive from.
    """

    interface.implements(INodeImage)
    interface.classProvides(INodeImageFactory)

    def __init__(self, id, name, driver, extra=None):
        self.id = id
        self.name = name
        self.driver = driver
        if not extra:
            self.extra = {}
        else:
            self.extra = extra
    def __repr__(self):
        return (('<NodeImage: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))

class NodeLocation(object):
    """
    A base NodeLocation class to derive from.
    """
    interface.implements(INodeImage)
    interface.classProvides(INodeImageFactory)
    def __init__(self, id, name, country, driver):
        self.id = id
        self.name = name
        self.country = country
        self.driver = driver
    def __repr__(self):
        return (('<NodeLocation: id=%s, name=%s, country=%s, driver=%s>')
                % (self.id, self.name, self.country, self.driver.name))

class NodeAuthSSHKey(object):
    """
    An SSH key to be installed for authentication to a node.
    """
    def __init__(self, pubkey):
        self.pubkey = pubkey
    def __repr__(self):
        return '<NodeAuthSSHKey>'

class NodeAuthPassword(object):
    """
    A password to be used for authentication to a node.
    """
    def __init__(self, password):
        self.password = password
    def __repr__(self):
        return '<NodeAuthPassword>'

class Response(object):
    """
    A Base Response class to derive from.
    """
    interface.implements(IResponse)
    interface.classProvides(IResponseFactory)

    NODE_STATE_MAP = {}

    object = None
    body = None
    status = httplib.OK
    headers = {}
    error = None
    connection = None

    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

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
            def makefile(self, mode, foo):
                return StringIO.StringIO(self.s)
        rr = r
        if r.chunked:
            ht += "%x\r\n" % (len(body))
            ht += body
            ht += "\r\n0\r\n"
        else:
            ht += body
        rr = httplib.HTTPResponse(fakesock(ht),
                                  method=r._method,
                                  debuglevel=r.debuglevel)
        rr.begin()
        rv += ht
        rv += ("\n# -------- end %d:%d response ----------\n"
               % (id(self), id(r)))
        return (rr, rv)

    def _log_curl(self, method, url, body, headers):
        cmd = ["curl", "-i"]

        cmd.extend(["-X", pquote(method)])

        for h in headers:
            cmd.extend(["-H", pquote("%s: %s" % (h, headers[h]))])

        # TODO: in python 2.6, body can be a file-like object.
        if body is not None and len(body) > 0:
            cmd.extend(["--data-binary", pquote(body)])

        cmd.extend([pquote("https://%s:%d%s" % (self.host, self.port, url))])
        return " ".join(cmd)

class LoggingHTTPSConnection(LoggingConnection, httplib.HTTPSConnection):
    """
    Utility Class for logging HTTPS connections
    """

    def getresponse(self):
        r = httplib.HTTPSConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n"  % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return httplib.HTTPSConnection.request(self, method, url,
                                               body, headers)

class LoggingHTTPConnection(LoggingConnection, httplib.HTTPConnection):
    """
    Utility Class for logging HTTP connections
    """

    def getresponse(self):
        r = httplib.HTTPConnection.getresponse(self)
        if self.log is not None:
            r, rv = self._log_response(r)
            self.log.write(rv + "\n")
            self.log.flush()
        return r

    def request(self, method, url, body=None, headers=None):
        headers.update({'X-LC-Request-ID': str(id(self))})
        if self.log is not None:
            pre = "# -------- begin %d request ----------\n"  % id(self)
            self.log.write(pre +
                           self._log_curl(method, url, body, headers) + "\n")
            self.log.flush()
        return httplib.HTTPConnection.request(self, method, url,
                                               body, headers)

class ConnectionKey(object):
    """
    A Base Connection class to derive from.
    """
    interface.implementsOnly(IConnectionKey)
    interface.classProvides(IConnectionKeyFactory)

    #conn_classes = (httplib.LoggingHTTPConnection, LoggingHTTPSConnection)
    conn_classes = (httplib.HTTPConnection, httplib.HTTPSConnection)

    responseCls = Response
    connection = None
    host = '127.0.0.1'
    port = (80, 443)
    secure = 1
    driver = None
    action = None

    def __init__(self, key, secure=True, host=None, force_port=None):
        """
        Initialize `user_id` and `key`; set `secure` to an C{int} based on
        passed value.
        """
        self.key = key
        self.secure = secure and 1 or 0
        self.ua = []
        if host:
            self.host = host

        if force_port:
            self.port = (force_port, force_port)

    def connect(self, host=None, port=None):
        """
        Establish a connection with the API server.

        @type host: C{str}
        @param host: Optional host to override our default

        @type port: C{int}
        @param port: Optional port to override our default

        @returns: A connection
        """
        host = host or self.host
        port = port or self.port[self.secure]

        connection = self.conn_classes[self.secure](host, port)
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
                method='GET'):
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

        @return: An instance of type I{responseCls}
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        self.action = action
        # Extend default parameters
        params = self.add_default_params(params)
        # Extend default headers
        headers = self.add_default_headers(headers)
        # We always send a content length and user-agent header
        headers.update({'User-Agent': self._user_agent()})
        headers.update({'Host': self.host})
        # Encode data if necessary
        if data != '':
            data = self.encode_data(data)
        headers.update({'Content-Length': len(data)})
        url = '?'.join((action, urllib.urlencode(params)))

        # Removed terrible hack...this a less-bad hack that doesn't execute a
        # request twice, but it's still a hack.
        self.connect()
        self.connection.request(method=method, url=url, body=data,
                                headers=headers)
        response = self.responseCls(self.connection.getresponse())
        response.connection = self
        return response

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

    def encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        return data


class ConnectionUserAndKey(ConnectionKey):
    """
    Base connection which accepts a user_id and key
    """
    interface.implementsOnly(IConnectionUserAndKey)
    interface.classProvides(IConnectionUserAndKeyFactory)

    user_id = None

    def __init__(self, user_id, key, secure=True, host=None, port=None):
        super(ConnectionUserAndKey, self).__init__(key, secure, host, port)
        self.user_id = user_id


class NodeDriver(object):
    """
    A base NodeDriver class to derive from
    """
    interface.implements(INodeDriver)
    interface.classProvides(INodeDriverFactory)

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None
    features = {"create_node": []}
    """
    List of available features for a driver.
        - L{create_node}
            - ssh_key: Supports L{NodeAuthSSHKey} as an authentication method
              for nodes.
            - password: Supports L{NodeAuthPassword} as an authentication
              method for nodes.
            - generates_password: Returns a password attribute on the Node
              object returned from creation.
    """

    NODE_STATE_MAP = {}

    def __init__(self, key, secret=None, secure=True, host=None, port=None):
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
        """
        self.key = key
        self.secret = secret
        self.secure = secure
        args = [self.key]

        if self.secret != None:
            args.append(self.secret)

        args.append(secure)

        if host != None:
            args.append(host)

        if port != None:
            args.append(port)

        self.connection = self.connectionCls(*args)

        self.connection.driver = self
        self.connection.connect()

    def create_node(self, **kwargs):
        """Create a new node instance.

        @keyword    name:   String with a name for this new node (required)
        @type       name:   str

        @keyword    size:   The size of resources allocated to this node.
                            (required)
        @type       size:   L{NodeSize}

        @keyword    image:  OS Image to boot on node. (required)
        @type       image:  L{NodeImage}

        @keyword    location: Which data center to create a node in. If empty,
                              undefined behavoir will be selected. (optional)
        @type       location: L{NodeLocation}

        @keyword    auth:   Initial authentication information for the node
                            (optional)
        @type       auth:   L{NodeAuthSSHKey} or L{NodeAuthPassword}

        @return: The newly created L{Node}.
        """
        raise NotImplementedError, \
            'create_node not implemented for this driver'

    def destroy_node(self, node):
        """Destroy a node.

        Depending upon the provider, this may destroy all data associated with
        the node, including backups.

        @return: C{bool} True if the destroy was successful, otherwise False
        """
        raise NotImplementedError, \
            'destroy_node not implemented for this driver'

    def reboot_node(self, node):
        """
        Reboot a node.
        @return: C{bool} True if the reboot was successful, otherwise False
        """
        raise NotImplementedError, \
            'reboot_node not implemented for this driver'

    def list_nodes(self):
        """
        List all nodes
        @return: C{list} of L{Node} objects
        """
        raise NotImplementedError, \
            'list_nodes not implemented for this driver'

    def list_images(self, location=None):
        """
        List images on a provider
        @return: C{list} of L{NodeImage} objects
        """
        raise NotImplementedError, \
            'list_images not implemented for this driver'

    def list_sizes(self, location=None):
        """
        List sizes on a provider
        @return: C{list} of L{NodeSize} objects
        """
        raise NotImplementedError, \
            'list_sizes not implemented for this driver'

    def list_locations(self):
        """
        List data centers for a provider
        @return: C{list} of L{NodeLocation} objects
        """
        raise NotImplementedError, \
            'list_locations not implemented for this driver'

    def deploy_node(self, **kwargs):
        """
        Create a new node, and start deployment.

        Depends on a Provider Driver supporting either using a specific password
        or returning a generated password.

        This function may raise a L{DeplyomentException}, if a create_node
        call was successful, but there is a later error (like SSH failing or 
        timing out).  This exception includes a Node object which you may want
        to destroy if incomplete deployments are not desirable.

        @keyword    deploy: Deployment to run once machine is online and availble to SSH.
        @type       deploy: L{Deployment}

        See L{NodeDriver.create_node} for more keyword args.
        """
        # TODO: support ssh keys
        WAIT_PERIOD=3
        password = None

        if 'generates_password' not in self.features["create_node"]:
            if 'password' not in self.features["create_node"]:
                raise NotImplementedError, \
                    'deploy_node not implemented for this driver'

            if not kwargs.has_key('auth'):
                kwargs['auth'] = NodeAuthPassword(os.urandom(16).encode('hex'))

            password = kwargs['auth'].password
        node = self.create_node(**kwargs)
        try:
          if 'generates_password' in self.features["create_node"]:
              password = node.extra.get('password')
          start = time.time()
          end = start + (60 * 15)
          while time.time() < end:
              # need to wait until we get a public IP address.
              # TODO: there must be a better way of doing this
              time.sleep(WAIT_PERIOD)
              nodes = self.list_nodes()
              nodes = filter(lambda n: n.uuid == node.uuid, nodes)
              if len(nodes) == 0:
                  raise DeploymentException(node, "Booted node[%s] is missing form list_nodes." % node)
              if len(nodes) > 1:
                  raise DeploymentException(node, "Booted single node[%s], but multiple nodes have same UUID"% node)

              node = nodes[0]

              if node.public_ip is not None and node.public_ip != "" and node.state == NodeState.RUNNING:
                  break

          client = SSHClient(hostname=node.public_ip[0],
                              port=22, username='root',
                              password=password)
          laste = None
          while time.time() < end:
              laste = None
              try:
                  client.connect()
                  break
              except (IOError, socket.gaierror, socket.error), e:
                  laste = e
              time.sleep(WAIT_PERIOD)
          if laste is not None:
              raise e

          n = kwargs["deploy"].run(node, client)
          client.close()
        except DeploymentException, e:
          raise
        except Exception, e:
          raise DeploymentException(node, e)
        return n

def is_private_subnet(ip):
    """
    Utility function to check if an IP address is inside a private subnet.

    @type ip: C{str}
    @keyword ip: IP address to check

    @return: C{bool} if the specified IP address is private.
    """
    priv_subnets = [ {'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                     {'subnet': '172.16.0.0', 'mask': '255.240.0.0'},
                     {'subnet': '192.168.0.0', 'mask': '255.255.0.0'} ]

    ip = struct.unpack('I',socket.inet_aton(ip))[0]

    for network in priv_subnets:
        subnet = struct.unpack('I',socket.inet_aton(network['subnet']))[0]
        mask = struct.unpack('I',socket.inet_aton(network['mask']))[0]

        if (ip & mask) == (subnet & mask):
            return True

    return False
