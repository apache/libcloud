import httplib, urllib
from zope import interface
from libcloud.interface import IConnectionUserAndKey, IResponse
from libcloud.interface import IConnectionUserAndKeyFactory, IResponseFactory
from libcloud.interface import INodeDriverFactory, INodeDriver
from libcloud.interface import INodeFactory, INode
import hashlib

class Node(object):
    """
    A Base Node class to derive from.
    """
    
    interface.implements(INode)
    interface.classProvides(INodeFactory)

    def __init__(self, id, name, state, public_ip, private_ip, driver):
        self.id = id
        self.name = name
        self.state = state
        self.public_ip = public_ip
        self.private_ip = private_ip
        self.driver = driver
        self.uuid = self.get_uuid()
        
    def get_uuid(self):
        return hashlib.sha1("%s:%d" % (self.id,self.driver.type)).hexdigest()
        
    def reboot(self):
        self.driver.reboot(self)

    def destroy(self):
        self.driver.reboot(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, provider=%s ...>')
                % (self.uuid, self.name, self.driver.name))
class Response(object):
    """
    A Base Response class to derive from.
    """
    interface.implements(IResponse)
    interface.classProvides(IResponseFactory)

    NODE_STATE_MAP = {}

    tree = None
    body = None
    status_code = 200
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

        self.tree = self.parse_body()

    def parse_body(self):
        """
        Parse response body.

        Override in a provider's subclass.

        @return: Parsed body.
        """
        return self.body

    def parse_error(self):
        """
        Parse the error messags.

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
        return self.status == httplib.OK


    def to_node(self):
        """
        A method that knows how to convert a given response tree to a L{Node}.

        Override in a provider's subclass.
        """
        raise NotImplementedError, 'to_node not implemented for this response'

class ConnectionKey(object):
    """
    A Base Connection class to derive from.
    """
    interface.implements(IConnectionUserAndKey)
    interface.classProvides(IConnectionUserAndKeyFactory)

    conn_classes = (httplib.HTTPConnection, httplib.HTTPSConnection)
    responseCls = Response
    connection = None
    host = '127.0.0.1'
    port = (80, 443)
    secure = 1
    driver = None

    def __init__(self, key, secure=True):
        """
        Initialize `user_id` and `key`; set `secure` to an C{int} based on
        passed value.
        """
        self.key = key
        self.secure = secure and 1 or 0

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
        self.connection = connection

    def request(self, action, params={}, data='', headers={}, method='GET'):
        """
        Request a given `action`.
        
        Basically a wrapper around the connection
        object's `request` that does some helpful pre-processing.

        @type action: C{str}
        @param action: A path

        @type params C{dict}
        @param params: Optional mapping of additional parameters to send. If
            None, leave as an empty C{dict}.

        @type data: C{unicode}
        @param data: A body of data to send with the request.

        @type headers C{dict}
        @param headers: Extra headers to add to the request
            None, leave as an empty C{dict}.

        @type method: C{str}
        @param method: An HTTP method such as "GET" or "POST".

        @return: An instance of type I{responseCls}
        """
        # Extend default parameters
        params.update(self.default_params())
        # Extend default headers
        headers.update(self.default_headers())
        # We always send a content length and user-agent header
        headers.update({'Content-Length': len(data)})
        headers.update({'User-Agent': 'libcloud/%s' % (self.driver.name)})
        # Encode data if necessary
        if data != '':
            data = self.__encode_data(data)
        url = '?'.join((action, urllib.urlencode(params)))
        self.connection.request(method=method, url=url, body=data,
                                headers=headers)
        response = self.responseCls(self.connection.getresponse())
        response.connection = self
        return response

    def default_params(self):
        """
        Return a dictionary of default parameters to add to query parameters.

        Override in a provider's subclass.
        """
        return {}

    def default_headers(self):
        """
        Return a dictionary of default headers to add to request.

        Override in a provider's subclass.
        """
        return {}

    def __encode_data(self, data):
        """
        Encode body data.

        Override in a provider's subclass.
        """
        return data


class ConnectionUserAndKey(ConnectionKey):
    """
    Base connection which accepts a user_id and key
    """
    user_id = None

    def __init__(self, user_id, key, secure=True):
        super(ConnectionUserAndKey, self).__init__(key, secure)
        self.user_id = user_id

class NodeDriver(object):
    """
    A base NodeDriver class to derive from
    """
    interface.implements(INodeDriver)
    interface.classProvides(INodeDriverFactory)

    connectionCls = None

    def __init__(self, key, secret=None, secure=True):
        self.key = key
        self.secret = secret
        self.secure = secure
        if self.secret:
          self.connection = self.connectionCls(key, secret, secure)
        else:
          self.connection = self.connectionCls(key, secure)

        self.connection.connect()
        self.connection.driver = self
