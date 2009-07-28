from zope.interface import Interface, Attribute


class IDriver(Interface):
    """
    TODO
    
    A Driver represents an interface to a provider Web Service. This is the
    Interface which all base drivers (`EC2Driver`, `SliceDriver`, etc.) should
    implement!
    """
    connectionCls = Attribute("""A suitable provider-specific Connection class""")
    nodesCls = Attribute("""A suitable provider-specific NodeDriver class""")
    connection = Attribute("""A suitable provider-specific Connection instance""")
    node = Attribute("""A suitable provider-specific NodeDriver instance""")


class IDriverFactory(Interface):
    """
    TODO

    Creates IDrivers
    """
    def __call__():
        """
        Initialize `connection` and `nodes` 
        """


class INodeDriver(Interface):
  """
  A driver which provides nodes, such as an Amazon EC2 instance, or Slicehost slice
  """

  def create(node):
    """
    Creates a new node based on the given skeleton node
    """

  def destroy(node):
    """
    Destroys (shuts down) the given node
    """

  def list():
    """
    Returns a list of nodes for this provider
    """

  def reboot(node):
    """
    Reboots the given node
    """


"""
Connection Interfaces / Factories.

Usage:
"""
class IConnection(Interface):
    """
    A Connection represents an interface between a Client and a Provider's Web
    Service. It is capable of authenticating, making requests, and returning
    responses.
    """
    conn_classes = Attribute("""Classes used to create connections, should be
                            in the form of `(insecure, secure)`""")
    responseCls = Attribute("""Provider-specific Class used for creating
                           responses""")
    connection = Attribute("""Represents the lower-level connection to the
                          server""")
    host = Attribute("""Default host for this connection""")
    port = Attribute("""Default port for this connection. This should be a
                    tuple of the form `(insecure, secure)` or for single-port
                    Providers, simply `(port,)`""")
    secure = Attribute("""Indicates if this is a secure connection. If previous
                      recommendations were followed, it would be advantageous
                      for this to be in the form: 0=insecure, 1=secure""")

    def connect(host=None, port=None):
        """
        A method for establishing a connection. If no host or port are given,
        existing ivars should be used.
        """

    def request(action, params={}, data='', method='GET'):
        """
        Make a request.

        An `action` should represent a path, such as `/list/nodes`. Query
        parameters necessary to the request should be passed in `params` and
        any data to encode goes in `data`. `method` should be one of: (GET,
        POST).

        Should return a response object (specific to a provider).
        """

    def __append_default_params(query_params):
        """
        Append default parameters (such as API key, version, etc.) to the query.

        Should return an extended dictionary.
        """

    def __encode_data(data):
        """
        Data may need to be encoded before sent in a request. If not, simply
        return the data.
        """

    def __headers():
        """
        Return a set of necessary headers as a dictionary, to be added to the
        request (or an empty dict).
        """


class IConnectionKey(IConnection):
    """
    IConnection which only depends on an API key for authentication.
    """
    key = Attribute("""API key, token, etc.""")



class IConnectionUserAndKey(IConnectionKey):
    """
    IConnection which depends on a user identifier and an API for authentication.
    """
    user_id = Attribute("""User identifier""")


class IConnectionUserAndKeyFactory(Interface):
    """
    Create Connections which depends on both a user identifier and API key.
    """
    def __call__(user_id, key, secure=True):
        """
        Create a Connection.

        The first two arguments provide the initial values for `user_id` and
        `key`, respectively, which should be used for authentication.
        
        The `secure` argument indicates whether or not a secure connection
        should be made. Not all providers support this, so it may be ignored.
        """


class IConnectionKeyFactory(Interface):
    """
    Create Connections which depend solely on an API key.
    """
    def __call__(key, secure=True):
        """
        Create a Connection.

        The acceptance of only `key` provides support for APIs with only one
        authentication bit.
        
        The `secure` argument indicates whether or not a secure connection
        should be made. Not all providers support this, so it may be ignored.
        """
