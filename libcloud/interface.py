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
from zope.interface import Interface, Attribute


class INode(Interface):
    """
    A node (instance, etc)
    """
    uuid = Attribute("""Unique identifier""")
    name = Attribute("""Hostname or similar identifier""")
    state = Attribute("""A standard Node state as provided by L{NodeState}""")
    ip = Attribute("""IP Address of the Node""")
    driver = Attribute("""The NodeDriver for this Node""")

    def destroy():
        """
        Call `self.driver.destroy_node(self)`. A convenience method.
        """

    def reboot():
        """
        Call `self.driver.reboot_node(self)`. A convenience method.
        """


class INodeFactory(Interface):
    """
    Create nodes
    """
    def __call__(uuid, name, state, ip, driver, **kwargs):
        """
        Set values for ivars, including any other requisite kwargs
        """


class INodeDriver(Interface):
    """
    A driver which provides nodes, such as an Amazon EC2 instance, or Slicehost slice
    """

    def create_node(name, size, os, from=None):
        """
        Creates a new node based on provided params.

        `from` takes a node to base the new one off of.

        FIXME: Parameters not finalized (no current drivers create nodes)
        """

    def destroy_node(node):
        """
        Destroys the given node
        """

    def list_nodes():
        """
        Returns a list of nodes for this provider
        """

    def reboot_node(node):
        """
        Reboots the given node
        """
    
    def __transform_create_params(name, size, os):
        """
        Transform given create parameters into something the API will
        understand.

        FIXME: Parameters not finalized (no current drivers create nodes)
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


class IResponse(Interface):
    """
    A response as provided by a given HTTP Client.
    """
    NODE_STATE_MAP = Attribute("""A mapping of states found in the response to
                              their standard type. This is a constant.""")

    tree = Attribute("""The processed response tree, e.g. via lxml""")
    body = Attribute("""Unparsed response body""")
    status_code = Attribute("""response status code""")
    error = Attribute("""Response error, L{None} if no error.""")

    def parse_body():
        """
        Parse the response body (as XML, etc.)
        """

    def success():
        """
        Does the response indicate a successful request?
        """

    def to_node():
        """
        Convert the response to a node.
        """


class IResponseFactory(Interface):
    """
    Creates Responses.
    """
    def __call__(response):
        """
        Process the given response, setting ivars.
        """

