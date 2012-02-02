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

import sys
import time
import hashlib
import os
import socket
import struct
import binascii

from libcloud.utils.py3 import b

import libcloud.compute.ssh
from libcloud.pricing import get_size_price
from libcloud.compute.types import NodeState, DeploymentError
from libcloud.compute.ssh import SSHClient

# @@TR: are the imports below part of the public api for this
# module? They aren't used in here ...
from libcloud.common.base import ConnectionKey, ConnectionUserAndKey
from libcloud.common.base import BaseDriver
from libcloud.httplib_ssl import LibcloudHTTPSConnection
from libcloud.common.base import LibcloudHTTPConnection
from libcloud.common.types import LibcloudError


# How long to wait for the node to come online after creating it
NODE_ONLINE_WAIT_TIMEOUT = 10 * 60

# How long to try connecting to a remote SSH server when running a deployment
# script.
SSH_CONNECT_TIMEOUT = 5 * 60


__all__ = [
    "Node",
    "NodeState",
    "NodeSize",
    "NodeImage",
    "NodeLocation",
    "NodeAuthSSHKey",
    "NodeAuthPassword",
    "NodeDriver",

    # @@TR: do the following need exporting?
    "ConnectionKey",
    "ConnectionUserAndKey",
    "LibcloudHTTPSConnection",
    "LibcloudHTTPConnection"
    ]

class UuidMixin(object):
    """
    Mixin class for get_uuid function.
    """

    def __init__(self):
        self._uuid = None

    def get_uuid(self):
        """Unique hash for a node, node image, or node size

        @return: C{string}

        The hash is a function of an SHA1 hash of the node, node image,
        or node size's ID and its driver which means that it should be 
        unique between all objects of its type.
        In some subclasses (e.g. GoGridNode) there is no ID
        available so the public IP address is used.  This means that,
        unlike a properly done system UUID, the same UUID may mean a
        different system install at a different time

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> node.get_uuid()
        'd3748461511d8b9b0e0bfa0d4d3383a619a2bb9f'

        Note, for example, that this example will always produce the
        same UUID!
        """
        if not self._uuid:
            self._uuid = hashlib.sha1(b("%s:%d" % (self.id, self.driver.type))).hexdigest()
        return self._uuid

    @property
    def uuid(self):
        return self.get_uuid()


class Node(UuidMixin):
    """
    Provide a common interface for handling nodes of all types.

    The Node object provides the interface in libcloud through which
    we can manipulate nodes in different cloud providers in the same
    way.  Node objects don't actually do much directly themselves,
    instead the node driver handles the connection to the node.

    You don't normally create a node object yourself; instead you use
    a driver and then have that create the node for you.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> node = driver.create_node()
    >>> node.public_ips[0]
    '127.0.0.3'
    >>> node.name
    'dummy-3'

    You can also get nodes from the driver's list_node function.

    >>> node = driver.list_nodes()[0]
    >>> node.name
    'dummy-1'

    the node keeps a reference to its own driver which means that we
    can work on nodes from different providers without having to know
    which is which.

    >>> driver = DummyNodeDriver(72)
    >>> node2 = driver.create_node()
    >>> node.driver.creds
    0
    >>> node2.driver.creds
    72

    Althrough Node objects can be subclassed, this isn't normally
    done.  Instead, any driver specific information is stored in the
    "extra" proproperty of the node.

    >>> node.extra
    {'foo': 'bar'}

    """

    def __init__(self, id, name, state, public_ips, private_ips,
                 driver, size=None, image=None, extra=None):
        self.id = str(id) if id else None
        self.name = name
        self.state = state
        self.public_ips = public_ips if public_ips else []
        self.private_ips = private_ips if private_ips else []
        self.driver = driver
        self.size = size
        self.image = image
        self.extra = extra or {}
        UuidMixin.__init__(self)

    # Note: getters and setters bellow are here only for backward compatibility.
    # They will be removed in the next release.

    def _set_public_ips(self, value):
        self.public_ips = value

    def _get_public_ips(self):
        return self.public_ips

    def _set_private_ips(self, value):
        self.private_ips = value

    def _get_private_ips(self):
        return self.private_ips

    public_ip = property(fget=_get_public_ips, fset=_set_public_ips)
    private_ip = property(fget=_get_private_ips, fset=_set_private_ips)

    def reboot(self):
        """Reboot this node

        @return: C{bool}

        This calls the node's driver and reboots the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> from libcloud.compute.types import NodeState
        >>> node.state == NodeState.RUNNING
        True
        >>> node.state == NodeState.REBOOTING
        False
        >>> node.reboot()
        True
        >>> node.state == NodeState.REBOOTING
        True
        """
        return self.driver.reboot_node(self)

    def destroy(self):
        """Destroy this node

        @return: C{bool}

        This calls the node's driver and destroys the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> from libcloud.compute.types import NodeState
        >>> node = driver.create_node()
        >>> node.state == NodeState.RUNNING
        True
        >>> node.destroy()
        True
        >>> node.state == NodeState.RUNNING
        False

        """
        return self.driver.destroy_node(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, state=%s, public_ips=%s, '
                 'provider=%s ...>')
                % (self.uuid, self.name, self.state, self.public_ips,
                   self.driver.name))


class NodeSize(UuidMixin):
    """
    A Base NodeSize class to derive from.

    NodeSizes are objects which are typically returned a driver's
    list_sizes function.  They contain a number of different
    parameters which define how big an image is.

    The exact parameters available depends on the provider.

    N.B. Where a parameter is "unlimited" (for example bandwidth in
    Amazon) this will be given as 0.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> size = driver.list_sizes()[0]
    >>> size.ram
    128
    >>> size.bandwidth
    500
    >>> size.price
    4
    """

    def __init__(self, id, name, ram, disk, bandwidth, price, driver):
        self.id = str(id)
        self.name = name
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver
        UuidMixin.__init__(self)

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))


class NodeImage(UuidMixin):
    """
    An operating system image.

    NodeImage objects are typically returned by the driver for the
    cloud provider in response to the list_images function

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> image = driver.list_images()[0]
    >>> image.name
    'Ubuntu 9.10'

    Apart from name and id, there is no further standard information;
    other parameters are stored in a driver specific "extra" variable

    When creating a node, a node image should be given as an argument
    to the create_node function to decide which OS image to use.

    >>> node = driver.create_node(image=image)

    """

    def __init__(self, id, name, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return (('<NodeImage: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))


class NodeLocation(object):
    """
    A physical location where nodes can be.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> location = driver.list_locations()[0]
    >>> location.country
    'US'
    """

    def __init__(self, id, name, country, driver):
        self.id = str(id)
        self.name = name
        self.country = country
        self.driver = driver

    def __repr__(self):
        return (('<NodeLocation: id=%s, name=%s, country=%s, driver=%s>')
                % (self.id, self.name, self.country, self.driver.name))


class NodeAuthSSHKey(object):
    """
    An SSH key to be installed for authentication to a node.

    This is the actual contents of the users ssh public key which will
    normally be installed as root's public key on the node.

    >>> pubkey = '...' # read from file
    >>> from libcloud.compute.base import NodeAuthSSHKey
    >>> k = NodeAuthSSHKey(pubkey)
    >>> k
    <NodeAuthSSHKey>
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


class NodeDriver(BaseDriver):
    """
    A base NodeDriver class to derive from

    This class is always subclassed by a specific driver.  For
    examples of base behavior of most functions (except deploy node)
    see the dummy driver.

    """

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

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None):
        super(NodeDriver, self).__init__(key=key, secret=secret, secure=secure,
                                         host=host, port=port,
                                         api_version=api_version)

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
        raise NotImplementedError(
            'create_node not implemented for this driver')

    def destroy_node(self, node):
        """Destroy a node.

        Depending upon the provider, this may destroy all data associated with
        the node, including backups.

        @param node: The node to be destroyed
        @type node: L{Node}

        @return: C{bool} True if the destroy was successful, otherwise False
        """
        raise NotImplementedError(
            'destroy_node not implemented for this driver')

    def reboot_node(self, node):
        """
        Reboot a node.

        @param node: The node to be rebooted
        @type node: L{Node}

        @return: C{bool} True if the reboot was successful, otherwise False
        """
        raise NotImplementedError(
            'reboot_node not implemented for this driver')

    def list_nodes(self):
        """
        List all nodes
        @return: C{list} of L{Node} objects
        """
        raise NotImplementedError(
            'list_nodes not implemented for this driver')

    def list_images(self, location=None):
        """
        List images on a provider

        @keyword location: The location at which to list images
        @type location: L{NodeLocation}

        @return: C{list} of L{NodeImage} objects
        """
        raise NotImplementedError(
            'list_images not implemented for this driver')

    def list_sizes(self, location=None):
        """
        List sizes on a provider

        @keyword location: The location at which to list sizes
        @type location: L{NodeLocation}

        @return: C{list} of L{NodeSize} objects
        """
        raise NotImplementedError(
            'list_sizes not implemented for this driver')

    def list_locations(self):
        """
        List data centers for a provider
        @return: C{list} of L{NodeLocation} objects
        """
        raise NotImplementedError(
            'list_locations not implemented for this driver')

    def deploy_node(self, **kwargs):
        """
        Create a new node, and start deployment.

        Depends on a Provider Driver supporting either using a specific
        password or returning a generated password.

        This function may raise a L{DeploymentException}, if a create_node
        call was successful, but there is a later error (like SSH failing or
        timing out).  This exception includes a Node object which you may want
        to destroy if incomplete deployments are not desirable.

        @keyword    deploy: Deployment to run once machine is online and
                            availble to SSH.
        @type       deploy: L{Deployment}

        @keyword    ssh_username: Optional name of the account which is used
                                  when connecting to
                                  SSH server (default is root)
        @type       ssh_username: C{str}

        @keyword    ssh_port: Optional SSH server port (default is 22)
        @type       ssh_port: C{int}

        @keyword    ssh_timeout: Optional SSH connection timeout in seconds
                                 (default is None)
        @type       ssh_timeout: C{float}

        @keyword    auth:   Initial authentication information for the node
                            (optional)
        @type       auth:   L{NodeAuthSSHKey} or L{NodeAuthPassword}

        @keyword    ssh_key: A path (or paths) to an SSH private key with which
                             to attempt to authenticate. (optional)
        @type       ssh_key: C{string} or C{list} of C{string}s

        See L{NodeDriver.create_node} for more keyword args.

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> from libcloud.compute.deployment import ScriptDeployment
        >>> from libcloud.compute.deployment import MultiStepDeployment
        >>> from libcloud.compute.base import NodeAuthSSHKey
        >>> driver = DummyNodeDriver(0)
        >>> key = NodeAuthSSHKey('...') # read from file
        >>> script = ScriptDeployment("yum -y install emacs strace tcpdump")
        >>> msd = MultiStepDeployment([key, script])
        >>> def d():
        ...     try:
        ...         node = driver.deploy_node(deploy=msd)
        ...     except NotImplementedError:
        ...         print ("not implemented for dummy driver")
        >>> d()
        not implemented for dummy driver

        Deploy node is typically not overridden in subclasses.  The
        existing implementation should be able to handle most such.
        """
        if not libcloud.compute.ssh.have_paramiko:
            raise RuntimeError('paramiko is not installed. You can install ' +
                               'it using pip: pip install paramiko')

        password = None

        if 'create_node' not in self.features:
            raise NotImplementedError(
                    'deploy_node not implemented for this driver')
        elif 'generates_password' not in self.features["create_node"]:
            if 'password' not in self.features["create_node"] and \
               'ssh_key' not in self.features["create_node"]:
                raise NotImplementedError(
                    'deploy_node not implemented for this driver')

            if 'auth' not in kwargs:
                kwargs['auth'] = NodeAuthPassword(binascii.hexlify(os.urandom(16)))

            if 'ssh_key' not in kwargs:
                password = kwargs['auth'].password

        node = self.create_node(**kwargs)

        if 'generates_password' in self.features['create_node']:
            password = node.extra.get('password')

        try:
            # Wait until node is up and running and has public IP assigned
            node = self._wait_until_running(node=node, wait_period=3,
                                            timeout=NODE_ONLINE_WAIT_TIMEOUT)

            ssh_username = kwargs.get('ssh_username', 'root')
            ssh_port = kwargs.get('ssh_port', 22)
            ssh_timeout = kwargs.get('ssh_timeout', 10)
            ssh_key_file = kwargs.get('ssh_key', None)

            ssh_client = SSHClient(hostname=node.public_ips[0],
                                   port=ssh_port, username=ssh_username,
                                   password=password,
                                   key=ssh_key_file,
                                   timeout=ssh_timeout)

            # Connect to the SSH server running on the node
            ssh_client = self._ssh_client_connect(ssh_client=ssh_client,
                                                  timeout=SSH_CONNECT_TIMEOUT)

            # Execute the deployment task
            self._run_deployment_script(task=kwargs['deploy'],
                                        node=node,
                                        ssh_client=ssh_client,
                                        max_tries=3)
        except Exception:
            e = sys.exc_info()[1]
            raise DeploymentError(node, e)
        return node

    def _wait_until_running(self, node, wait_period=3, timeout=600):
        """
        Block until node is fully booted and has an IP address assigned.

        @keyword    node: Node instance.
        @type       node: C{Node}

        @keyword    wait_period: How many seconds to between each loop
                                 iteration (default is 3)
        @type       wait_period: C{int}

        @keyword    timeout: How many seconds to wait before timing out
                             (default is 600)
        @type       timeout: C{int}

        @return: C{Node} Node instance on success.
        """
        start = time.time()
        end = start + timeout

        while time.time() < end:
            nodes = self.list_nodes()
            nodes = list([n for n in nodes if n.uuid == node.uuid])

            if len(nodes) == 0:
                raise LibcloudError(value=('Booted node[%s] ' % node
                                    + 'is missing from list_nodes.'),
                                    driver=self)

            if len(nodes) > 1:
                raise LibcloudError(value=('Booted single node[%s], ' % node
                                    + 'but multiple nodes have same UUID'),
                                    driver=self)

            node = nodes[0]

            if (node.public_ips and node.state == NodeState.RUNNING):
                return node
            else:
                time.sleep(wait_period)
                continue

        raise LibcloudError(value='Timed out after %s seconds' % (timeout),
                            driver=self)

    def _ssh_client_connect(self, ssh_client, timeout=300):
        """
        Try to connect to the remote SSH server. If a connection times out or
        is refused it is retried up to timeout number of seconds.

        @keyword    ssh_client: A configured SSHClient instance
        @type       ssh_client: C{SSHClient}

        @keyword    timeout: How many seconds to wait before timing out
                             (default is 600)
        @type       timeout: C{int}

        @return: C{SSHClient} on success
        """
        start = time.time()
        end = start + timeout

        while time.time() < end:
            try:
                ssh_client.connect()
            except (IOError, socket.gaierror, socket.error):
                # Retry if a connection is refused or timeout
                # occurred
                ssh_client.close()
                continue
            else:
                return ssh_client

        raise LibcloudError(value='Could not connect to the remote SSH ' +
                            'server. Giving up.', driver=self)

    def _run_deployment_script(self, task, node, ssh_client, max_tries=3):
        """
        Run the deployment script on the provided node. At this point it is
        assumed that SSH connection has already been established.

        @keyword    task: Deployment task to run on the node.
        @type       task: C{Deployment}

        @keyword    node: Node to operate one
        @type       node: C{Node}

        @keyword    ssh_client: A configured and connected SSHClient instance
        @type       ssh_client: C{SSHClient}

        @keyword    max_tries: How many times to retry if a deployment fails
                               before giving up (default is 3)
        @type       max_tries: C{int}

        @return: C{Node} Node instance on success.
        """
        tries = 0
        while tries < max_tries:
            try:
                node = task.run(node, ssh_client)
            except Exception:
                tries += 1
                if tries >= max_tries:
                    raise LibcloudError(value='Failed after %d tries'
                                        % (max_tries), driver=self)
            else:
                ssh_client.close()
                return node

    def _get_size_price(self, size_id):
        return get_size_price(driver_type='compute',
                              driver_name=self.api_name,
                              size_id=size_id)


def is_private_subnet(ip):
    """
    Utility function to check if an IP address is inside a private subnet.

    @type ip: C{str}
    @keyword ip: IP address to check

    @return: C{bool} if the specified IP address is private.
    """
    priv_subnets = [{'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                    {'subnet': '172.16.0.0', 'mask': '255.240.0.0'},
                    {'subnet': '192.168.0.0', 'mask': '255.255.0.0'}]

    ip = struct.unpack('I', socket.inet_aton(ip))[0]

    for network in priv_subnets:
        subnet = struct.unpack('I', socket.inet_aton(network['subnet']))[0]
        mask = struct.unpack('I', socket.inet_aton(network['mask']))[0]

        if (ip & mask) == (subnet & mask):
            return True

    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()
